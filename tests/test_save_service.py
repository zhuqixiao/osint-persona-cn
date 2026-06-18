"""Save service routing tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_save_url_routes_weixin(monkeypatch):
    from osint_toolkit.services import save as save_svc

    class FakeCollector:
        async def fetch(self, url):
            from osint_toolkit.models.intel_item import IntelItem

            return IntelItem(source="weixin", type="article", url=url, title="t", content="c")

    monkeypatch.setattr(save_svc, "WeixinCollector", lambda: FakeCollector())
    monkeypatch.setattr(save_svc, "save_item", lambda item: 1)
    monkeypatch.setattr(save_svc, "export_card", lambda item, path: path / "card.md")

    result = await save_svc.save_url("https://mp.weixin.qq.com/s/abc", no_ai=True)
    assert result["item"].source == "weixin"


@pytest.mark.asyncio
async def test_save_url_enriches_bilibili_video(monkeypatch):
    from osint_toolkit.models.intel_item import IntelItem
    from osint_toolkit.services import save as save_svc

    enriched = {"called": False}

    class FakeCollector:
        async def fetch(self, url):
            return IntelItem(
                source="bilibili",
                type="video",
                url=url,
                title="t",
                content="c",
            )

        async def enrich_video(self, item):
            enriched["called"] = True
            item.layers["subtitle"] = {"text": "sub"}

    monkeypatch.setattr(save_svc, "BilibiliCollector", lambda: FakeCollector())
    monkeypatch.setattr(save_svc, "save_item", lambda item: 1)
    monkeypatch.setattr(save_svc, "export_card", lambda item, path: path / "card.md")

    await save_svc.save_url("https://www.bilibili.com/video/BV1", no_ai=True)
    assert enriched["called"] is True


def test_bilibili_fetch_type_from_url():
    from osint_toolkit.collectors.bilibili import BilibiliCollector

    assert BilibiliCollector._type_from_url("https://www.bilibili.com/read/cv123") == "article"
    assert BilibiliCollector._type_from_url("https://www.bilibili.com/opus/456") == "article"
    assert BilibiliCollector._type_from_url("https://www.bilibili.com/video/BV1") == "video"
