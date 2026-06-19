"""Per-source query resolution tests."""

from __future__ import annotations

from osint_toolkit.collectors.queries_by_source import (
    build_queries_by_source,
    is_primarily_latin,
    resolve_queries_for_source,
)


def test_is_primarily_latin():
    assert is_primarily_latin("Composer capabilities")
    assert not is_primarily_latin("丰川祥子")


def test_zhihu_does_not_get_latin_only():
    base = ["祥子", "Composer IDE"]
    foreign = ["Sakiko", "Mutsumi"]
    qs = resolve_queries_for_source("zhihu", base, foreign)
    assert "Composer IDE" not in qs
    assert "Sakiko" not in qs
    assert "祥子" in qs


def test_github_gets_foreign():
    base = ["祥子"]
    foreign = ["Sakiko Togawa"]
    qs = resolve_queries_for_source("github", base, foreign)
    assert "Sakiko Togawa" in qs
    assert "祥子" in qs


def test_build_queries_by_source_map():
    m = build_queries_by_source(["zhihu", "github"], ["祥子"], ["Sakiko"])
    assert "Sakiko" not in m["zhihu"]
    assert "Sakiko" in m["github"]
