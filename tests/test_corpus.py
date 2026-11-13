from pathlib import Path

import pytest

from jmra_wp_mcp.corpus import Corpus, split_pages, parse_toc

RAW = Path(__file__).resolve().parents[1] / "data" / "wp_raw.txt"


@pytest.fixture(scope="module")
def pages():
    return split_pages(RAW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def corpus():
    return Corpus.from_file(RAW)


def test_split_pages_yields_164_pages_indexed_from_one(pages):
    assert len(pages) == 165  # index 0 unused
    assert pages[0] == ""
    assert pages[1].startswith("JMRA リサーチイノベーション委員会")
    assert "討論" in pages[157]


def test_split_pages_strips_trailing_printed_page_number(pages):
    assert not pages[2].rstrip().endswith("\n1")
    assert pages[2].rstrip().endswith("引用文献 ............................................................................... 42")


def test_parse_toc_numbered_section_has_title_and_pdf_page(pages):
    secs = {s.id: s for s in parse_toc(pages)}
    assert secs["5.4"].title == "DirectLiNGAMの中心的な考え方"
    assert secs["5.4"].start_page == 47  # printed 46 -> pdf 47
    assert secs["5.4"].chapter == "5"


def test_parse_toc_chapters_are_numbered_sequentially(pages):
    chapters = [s for s in parse_toc(pages) if s.is_chapter]
    assert [c.id for c in chapters] == [str(i) for i in range(1, 14)] + ["A"]
    assert chapters[0].title == "問題意識"
    assert chapters[4].title == "DirectLiNGAM"
    assert chapters[4].start_page == 44
    assert chapters[12].title == "討論"


def test_parse_toc_repairs_split_chapter_nine_title(pages):
    secs = {s.id: s for s in parse_toc(pages)}
    assert secs["9"].title == "社会的情報環境を考慮した個体レベル因果の表現 ― 構造的因果モデルのマーケティングへの試行的応用 ―"


def test_parse_toc_reference_sections_belong_to_chapter(pages):
    secs = {s.id: s for s in parse_toc(pages)}
    assert secs["2.引用文献"].start_page == 24
    assert secs["2.引用文献"].chapter == "2"


def test_parse_toc_appendix_sections(pages):
    secs = {s.id: s for s in parse_toc(pages)}
    assert secs["A"].title.startswith("付録")
    assert secs["A.1"].title == "開発の背景"
    assert secs["A.4"].title == "入手方法と参考情報"
    assert secs["A.4"].start_page == 164


def test_parse_toc_ignores_keyword_lines(pages):
    assert all("キーワード" not in s.title for s in parse_toc(pages))


def test_get_section_returns_text_from_heading_to_next_heading(corpus):
    text = corpus.get_section("5.4")
    assert text.splitlines()[0] == "[p.47]"
    assert text.splitlines()[1] == "5.4DirectLiNGAM の中心的な考え方"
    assert "5.5アルゴリズムの手順" not in text
    assert "5.3識別の鍵" not in text


def test_get_section_handles_space_variant_heading(corpus):
    text = corpus.get_section("10.3")
    assert text.splitlines()[1] == "10.3 RCT（A/B テスト）"
    assert "10.4 集団から個人へ" not in text


def test_get_section_for_chapter_spans_all_subsections(corpus):
    text = corpus.get_section("5")
    assert "5.1はじめに" in text
    assert "5.7まとめと今後の課題" in text
    assert "6.1はじめに" not in text


def test_get_section_last_entry_runs_to_end_of_document(corpus):
    text = corpus.get_section("A.引用文献")
    assert text.splitlines()[:2] == ["[p.164]", "引用文献"]
    assert "Ikeuchi" in text


def test_get_section_unknown_id_raises(corpus):
    with pytest.raises(KeyError):
        corpus.get_section("99.9")


def test_get_pages_returns_requested_range(corpus):
    text = corpus.get_pages(47, 48)
    assert "===== PAGE 47 =====" in text
    assert "===== PAGE 48 =====" in text
    assert "===== PAGE 49 =====" not in text


def test_get_pages_rejects_out_of_range(corpus):
    with pytest.raises(ValueError):
        corpus.get_pages(0, 3)
    with pytest.raises(ValueError):
        corpus.get_pages(10, 5)


def test_search_is_and_match_and_ignores_spacing(corpus):
    hits = corpus.search("DirectLiNGAM 中心的な考え方")
    assert hits[0].page == 47
    assert hits[0].section_id == "5.4"
    assert "DirectLiNGAM" in hits[0].snippet.replace(" ", "")


def test_search_is_case_insensitive(corpus):
    assert {h.page for h in corpus.search("directlingam")} >= {47}


def test_search_returns_empty_for_no_match(corpus):
    assert corpus.search("そんな語はない絶対に") == []


def test_section_for_page_maps_to_innermost_section(corpus):
    assert corpus.section_for_page(47).id == "5.4"
    assert corpus.section_for_page(44).id == "5"


def test_every_section_heading_is_found_on_its_start_page(corpus):
    missing = [s.id for s in corpus.sections if corpus._heading_line(s, s.start_page) is None]
    assert missing == []


def test_search_skips_cover_and_toc_pages(corpus):
    assert all(h.page > 5 for h in corpus.search("弱い操作変数"))
