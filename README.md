# jmra-wp-mcp

JMRA リサーチイノベーション委員会 データサイエンス研究会 第4期報告書
「LiNGAMによる統計的因果探索」(2026-11-13) の本文を Claude から引くための MCP サーバー。
ローカル stdio 接続、外部 API なし。

**取り扱い注意**: `data/wp_raw.txt` は内部資料の全文です。リポジトリを公開リモートに push しないでください。

## セットアップ

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest
```

## Claude Code への登録

```sh
claude mcp add --scope user jmra-wp -- "$PWD/.venv/bin/python" -m jmra_wp_mcp.server
```

## ツール

| ツール | 内容 |
|---|---|
| `list_sections` | 章・節一覧（PDFページ番号つき） |
| `get_section(section_id)` | `"5.4"` / `"5"` / `"5.引用文献"` / `"A.2"` の本文 |
| `search(query, limit)` | 全文キーワード検索（空白区切り AND、空白・大小文字無視） |
| `get_pages(first, last)` | PDF ページ番号で原文取得（最大10ページ） |

ページ番号はすべて PDF のページ番号（印刷ページ番号 + 1）。

## データの再生成

PDF から `data/wp_raw.txt` を作り直す場合（macOS、PDFKit 使用）:

```sh
osascript -l JavaScript scripts/pdf2txt.js "<pdf path>" data/wp_raw.txt
```
