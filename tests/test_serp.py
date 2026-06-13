"""SERP 搜索引擎测试."""

from __future__ import annotations

import pytest

from osint_toolkit.collectors.serp.detection import is_blocked_response
from osint_toolkit.collectors.serp.engine import SerpEngine, hits_to_items
from osint_toolkit.collectors.serp.models import SerpHit
from osint_toolkit.collectors.web import WebCollector


def test_is_blocked_captcha():
    assert is_blocked_response("<html>captcha required</html>")
    assert is_blocked_response("", status_code=429)
    assert not is_blocked_response("<html><li class='b_algo'>ok</li></html>")


def test_hits_to_items_dedup():
    hits = [
        SerpHit(title="A", url="https://a.com", snippet="s", engine="bing_html", query="q"),
        SerpHit(title="A dup", url="https://a.com", snippet="s2", engine="bing_html", query="q"),
    ]
    items = hits_to_items(hits)
    assert len(items) == 1
    assert items[0].personal["serp_engine"] == "bing_html"


@pytest.mark.asyncio
async def test_serp_engine_fallback(monkeypatch):
    from osint_toolkit.collectors.serp import engine as serp_engine
    from osint_toolkit.collectors.serp import providers

    async def fake_api(client, query, limit, cfg):
        return [], "bing_api: empty"

    async def fake_html(client, query, limit):
        return [SerpHit(title="T", url="https://example.com", snippet="s", engine="bing_html", query=query)], None

    monkeypatch.setitem(providers.PROVIDERS, "bing_api", fake_api)
    monkeypatch.setitem(providers.PROVIDERS, "bing_html", fake_html)
    monkeypatch.setattr(
        serp_engine,
        "get_serp_config",
        lambda: {"primary": "bing_api", "fallbacks": ["bing_html"]},
    )

    hits, attempts = await SerpEngine().search("test", limit=5)
    assert len(hits) == 1
    assert any("bing_api" in a for a in attempts)
    assert any("bing_html" in a for a in attempts)


@pytest.mark.asyncio
async def test_web_collector_uses_serp(monkeypatch):
    async def fake_search(self, query, limit=10):
        return (
            [SerpHit(title="Hit", url="https://ex.com", snippet="sn", engine="bing_html", query=query)],
            ["bing_html: ok (1)"],
        )

    async def fake_site(self, domain, query, limit=10):
        return [], []

    async def fake_enrich(self, items):
        return None

    monkeypatch.setattr(SerpEngine, "search", fake_search)
    monkeypatch.setattr(SerpEngine, "site_search", fake_site)
    monkeypatch.setattr(WebCollector, "_enrich_content", fake_enrich)
    monkeypatch.setattr(
        "osint_toolkit.collectors.web.get_serp_config",
        lambda: {"site_searches": [], "web_fetch_content": False},
    )

    items = await WebCollector().search("hello", limit=5)
    assert len(items) == 1
    assert items[0].url == "https://ex.com"
