import asyncio

import pytest

from jmra_wp_mcp.server import mcp


def call(name, **args):
    async def go():
        res = await mcp.call_tool(name, args)
        return "".join(c.text for c in res.content if hasattr(c, "text"))
    return asyncio.run(go())


def test_tools_are_registered():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"list_sections", "get_section", "search", "get_pages"}


def test_list_sections_shows_chapters_and_sections_with_pages():
    out = call("list_sections")
    assert "5. DirectLiNGAM (p.44)" in out
    assert "  5.4 DirectLiNGAMの中心的な考え方 (p.47)" in out
    assert "A. 付録" in out


def test_get_section_returns_body_with_page_markers():
    out = call("get_section", section_id="5.4")
    assert out.startswith("# 5.4 DirectLiNGAMの中心的な考え方")
    assert "[p.47]" in out


def test_get_section_unknown_id_gives_helpful_message():
    out = call("get_section", section_id="42.1")
    assert "42.1" in out and "list_sections" in out


def test_search_lists_page_section_and_snippet():
    out = call("search", query="アップリフトモデリング")
    assert "p.123" in out
    assert "10.5" in out


def test_search_no_hit_message():
    out = call("search", query="そんな語はない絶対に")
    assert "見つかりません" in out


def test_get_pages_bounds_message():
    out = call("get_pages", first=300, last=301)
    assert "1-164" in out
