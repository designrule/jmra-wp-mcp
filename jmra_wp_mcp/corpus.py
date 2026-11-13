"""Page/section model for the JMRA DS working paper text dump."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PAGE_MARK = re.compile(r"^===== PAGE (\d+) =====$", re.M)
TOC_PAGES = range(2, 6)
# "5.4 タイトル ....... 46"  /  "問題意識 ....... 5"
TOC_ENTRY = re.compile(r"^(?:(\d{1,2})\.(\d{1,2})\s*)?(.*?)\s*\.{3,}\s*(\d{1,3})$")
NUMBERED_HEADING = re.compile(r"^(\d{1,2})\.(\d{1,2})\s*(\S.*)$")
PRINTED_TO_PDF = 1  # pdf page = printed page + 1

# PDFKit emitted the two-line chapter-9 title out of order; TOC is authoritative elsewhere.
TITLE_OVERRIDES = {
    "9": "社会的情報環境を考慮した個体レベル因果の表現 ― 構造的因果モデルのマーケティングへの試行的応用 ―",
}
REFS = "引用文献"
APPENDIX = "A"


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


@dataclass(frozen=True)
class Section:
    id: str
    title: str
    start_page: int
    chapter: str
    is_chapter: bool = False


@dataclass(frozen=True)
class Hit:
    page: int
    section_id: str
    section_title: str
    count: int
    snippet: str


def split_pages(raw: str) -> list[str]:
    """Return pages as a 1-indexed list (index 0 is ''), footer page numbers removed."""
    parts = PAGE_MARK.split(raw)
    pages = [""]
    for i in range(1, len(parts), 2):
        assert int(parts[i]) == len(pages), "pages must be consecutive"
        pages.append(_strip_footer(parts[i + 1].strip("\n")))
    return pages


def _strip_footer(text: str) -> str:
    lines = text.rstrip().split("\n")
    if len(lines) > 1 and lines[-1].strip().isdigit():
        lines.pop()
    return "\n".join(lines)


def parse_toc(pages: list[str]) -> list[Section]:
    lines: list[str] = []
    for p in TOC_PAGES:
        lines += pages[p].split("\n")

    sections: list[Section] = []
    chapter_no = 0
    chapter = ""
    sub_no = 0
    pending: list[str] = []
    for line in lines:
        line = line.strip()
        if re.fullmatch(r"目\s*次", line):
            continue
        m = TOC_ENTRY.match(line)
        if not m:
            if line and not line.startswith("キーワード"):
                pending.append(line)
            continue
        ch, sub, title, printed = m.groups()
        page = int(printed) + PRINTED_TO_PDF
        if pending:
            title = "".join(pending) + title
            pending = []
        if ch:
            chapter = ch
            sections.append(Section(f"{ch}.{sub}", title, page, chapter))
        elif title == REFS:
            sections.append(Section(f"{chapter}.{REFS}", title, page, chapter))
        elif title.startswith("付録"):
            chapter = APPENDIX
            sub_no = 0
            sections.append(Section(APPENDIX, title, page, chapter, is_chapter=True))
        elif chapter == APPENDIX:
            sub_no += 1
            sections.append(Section(f"{APPENDIX}.{sub_no}", title, page, chapter))
        else:
            chapter_no += 1
            chapter = str(chapter_no)
            title = TITLE_OVERRIDES.get(chapter, title)
            sections.append(Section(chapter, title, page, chapter, is_chapter=True))
    return sections


class Corpus:
    def __init__(self, pages: list[str], sections: list[Section]):
        self.pages = pages
        self.sections = sections
        self._by_id = {s.id: s for s in sections}
        self.last_page = len(pages) - 1

    @classmethod
    def from_file(cls, path: Path) -> "Corpus":
        pages = split_pages(Path(path).read_text(encoding="utf-8"))
        return cls(pages, parse_toc(pages))

    # ---- lookup -----------------------------------------------------------
    def section(self, section_id: str) -> Section:
        try:
            return self._by_id[section_id]
        except KeyError:
            raise KeyError(f"unknown section id: {section_id}") from None

    def section_for_page(self, page: int) -> Section:
        best = self.sections[0]
        for s in self.sections:
            if s.start_page <= page:
                best = s
        return best

    def _next_boundary(self, sec: Section) -> Section | None:
        """First later entry that is not inside `sec` (for a chapter: the next chapter)."""
        idx = self.sections.index(sec)
        for s in self.sections[idx + 1:]:
            if not (sec.is_chapter and s.chapter == sec.chapter):
                return s
        return None

    # ---- heading location --------------------------------------------------
    def _heading_line(self, sec: Section, page: int) -> int | None:
        lines = self.pages[page].split("\n")
        if sec.title == REFS:
            key = REFS
            for i, ln in enumerate(lines):
                if ln.strip() == key:
                    return i
            return None
        tn = _norm(sec.title)
        prefix = _norm(sec.id) if (not sec.is_chapter and sec.chapter.isdigit()) else ""
        for i, ln in enumerate(lines):
            n = _norm(ln)
            if prefix and not n.startswith(prefix):
                continue
            body = n[len(prefix):]
            if body[:2] == tn[:2] or tn.startswith(body[:4]):
                return i
        return None

    # ---- public API ----------------------------------------------------------
    def get_section(self, section_id: str) -> str:
        sec = self.section(section_id)
        nxt = self._next_boundary(sec)
        end_page = nxt.start_page if nxt else self.last_page
        start_line = self._heading_line(sec, sec.start_page) or 0
        out: list[str] = []
        for p in range(sec.start_page, end_page + 1):
            lines = self.pages[p].split("\n")
            lo = start_line if p == sec.start_page else 0
            hi = len(lines)
            if nxt and p == end_page:
                cut = self._heading_line(nxt, p)
                hi = cut if cut is not None else hi
                if cut == 0 and p != sec.start_page:
                    continue
            out.append(f"[p.{p}]\n" + "\n".join(lines[lo:hi]))
        return "\n".join(out).strip()

    def get_pages(self, first: int, last: int) -> str:
        if not (1 <= first <= last <= self.last_page):
            raise ValueError(f"page range must be within 1-{self.last_page} and ascending")
        return "\n".join(f"===== PAGE {p} =====\n{self.pages[p]}" for p in range(first, last + 1))

    def search(self, query: str, context: int = 60, limit: int = 20) -> list[Hit]:
        terms = [_norm(t) for t in query.split() if t.strip()]
        if not terms:
            return []
        hits: list[Hit] = []
        for p in range(1, self.last_page + 1):
            disp = re.sub(r"\s+", "", self.pages[p])
            text = disp.lower()
            if not all(t in text for t in terms):
                continue
            pos = text.find(terms[0])
            snippet = disp[max(0, pos - context): pos + len(terms[0]) + context]
            sec = self.section_for_page(p)
            hits.append(Hit(p, sec.id, sec.title, sum(text.count(t) for t in terms), snippet))
        hits.sort(key=lambda h: (-h.count, h.page))
        return hits[:limit]
