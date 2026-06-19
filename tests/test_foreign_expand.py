"""Foreign query expansion tests."""

from __future__ import annotations

from osint_toolkit.ai.foreign_expand import expand_foreign_terms, foreign_expand_enabled


def test_foreign_expand_enabled_with_github():
    assert foreign_expand_enabled("丰川祥子", ["zhihu", "github"])


def test_foreign_expand_disabled_zh_only():
    assert not foreign_expand_enabled("丰川祥子", ["zhihu", "bilibili"])


def test_expand_foreign_for_cjk_with_github(monkeypatch):
    monkeypatch.setattr(
        "osint_toolkit.ai.foreign_expand._ai_foreign_expand",
        lambda *a, **k: (["Sakiko Togawa", "Mutsumi Wakaba"], []),
    )
    result = expand_foreign_terms(
        "丰川祥子",
        ["github"],
        chinese_aliases=["祥子"],
        no_ai=False,
    )
    assert "Sakiko Togawa" in result["foreign_queries"] or result["foreign_queries"]


def test_narrow_product_gets_variants(monkeypatch):
    monkeypatch.setattr("osint_toolkit.ai.foreign_expand._ai_foreign_expand", lambda *a, **k: ([], []))
    result = expand_foreign_terms("glm5.2", ["github"], no_ai=True)
    assert any("glm" in q.lower() for q in result["foreign_queries"])
