"""MCP server exposing the JMRA DS研究会 第4期 working paper (LiNGAMによる統計的因果探索)."""
from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .corpus import Corpus

DATA = Path(__file__).resolve().parents[1] / "data" / "wp_raw.txt"

INSTRUCTIONS = """\
JMRA リサーチイノベーション委員会 データサイエンス研究会 第4期報告書
「LiNGAMによる統計的因果探索」(2026-11-13, 研究代表者 森本修, 全164ページ) の本文を引くためのサーバー。
使い方: まず list_sections で構成を把握し、該当しそうな節を get_section で読む。
どこに書いてあるか分からないときは search でキーワード検索する (複数語はAND)。
ページ番号はすべて PDF のページ番号 (印刷ページ番号 + 1)。
テキストはPDFからの抽出のため、図表・数式は欠落または崩れている。図が必要なら該当PDFページを案内すること。
"""

mcp = MCPServer("jmra-wp", instructions=INSTRUCTIONS)
_corpus: Corpus | None = None


def corpus() -> Corpus:
    global _corpus
    if _corpus is None:
        _corpus = Corpus.from_file(DATA)
    return _corpus


@mcp.tool()
def list_sections() -> str:
    """報告書の章・節一覧を、開始ページ (PDFページ番号) つきで返す。最初に呼ぶとよい。"""
    lines = []
    for s in corpus().sections:
        if s.is_chapter:
            lines.append(f"{s.id}. {s.title} (p.{s.start_page})")
        else:
            lines.append(f"  {s.id} {s.title} (p.{s.start_page})")
    return "\n".join(lines)


@mcp.tool()
def get_section(section_id: str) -> str:
    """指定した節または章の本文を返す。section_id は "5.4" (節), "5" (章全体), "5.引用文献", "A.2" (付録) のように指定する。
    本文中の [p.N] は PDF ページ番号。"""
    c = corpus()
    try:
        sec = c.section(section_id.strip())
    except KeyError:
        return f"節 ID '{section_id}' は存在しません。list_sections で有効な ID を確認してください。"
    label = f"{sec.id}. {sec.title}" if sec.is_chapter else f"{sec.id} {sec.title}"
    return f"# {label}\n\n{c.get_section(sec.id)}"


@mcp.tool()
def search(query: str, limit: int = 20) -> str:
    """報告書全文をキーワード検索する。空白区切りの複数語は AND 条件。大文字小文字と空白は無視。
    ヒットしたページごとに、所属する節と前後の文脈を返す。"""
    hits = corpus().search(query, limit=limit)
    if not hits:
        return f"'{query}' に一致する箇所は見つかりませんでした。語を減らすか別の表現を試してください。"
    out = [f"'{query}' のヒット: {len(hits)} ページ (ヒット数の多い順)\n"]
    for h in hits:
        out.append(f"- p.{h.page} [{h.section_id} {h.section_title}] ({h.count}件)\n  …{h.snippet}…")
    return "\n".join(out)


@mcp.tool()
def get_pages(first: int, last: int | None = None) -> str:
    """PDF ページ番号を指定して原文を返す (first〜last、last 省略時は 1 ページ)。一度に最大 10 ページ。"""
    c = corpus()
    last = first if last is None else last
    if last - first >= 10:
        return "一度に取得できるのは 10 ページまでです。範囲を狭めてください。"
    try:
        return c.get_pages(first, last)
    except ValueError:
        return f"ページ範囲が不正です。1-{c.last_page} の範囲で first <= last となるよう指定してください。"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
