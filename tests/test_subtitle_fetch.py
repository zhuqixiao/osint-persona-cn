"""Bilibili subtitle fetch edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from osint_toolkit.ingest import bilibili_sdk
from osint_toolkit.processors.subtitle import parse_subtitle_json


def test_parse_video_page_index_from_query():
    assert bilibili_sdk.parse_video_page_index("https://www.bilibili.com/video/BV1?p=3") == 2
    assert bilibili_sdk.parse_video_page_index("https://www.bilibili.com/video/BV1") == 0


def test_parse_subtitle_json_list_body():
    body = '{"body": [{"content": "第一句"}, {"content": "第二句"}]}'
    assert parse_subtitle_json(body) == "第一句\n第二句"


@pytest.mark.asyncio
async def test_fetch_subtitle_sdk_empty_falls_back_to_wbi(monkeypatch):
    monkeypatch.setattr(bilibili_sdk, "sdk_installed", lambda: True)
    monkeypatch.setattr(bilibili_sdk, "sdk_enabled", lambda _f: True)

    class FakeVideo:
        async def get_subtitle(self, cid: int):
            return {"subtitles": []}

    async def fake_instance(_url):
        return FakeVideo()

    async def fake_resolve(_v, page_index=0):
        assert page_index == 1
        return 999

    async def fake_aid_cid(url, *, page_index=0, client=None):
        assert page_index == 1
        return 111, 222

    async def fake_player(aid, cid, *, client=None):
        return {"text": "分P字幕", "track": {"lan_doc": "中文"}, "source": "wbi_player"}

    monkeypatch.setattr(bilibili_sdk, "_video_instance", fake_instance)
    monkeypatch.setattr(bilibili_sdk, "_resolve_cid", fake_resolve)
    monkeypatch.setattr(bilibili_sdk, "resolve_video_aid_cid", fake_aid_cid)
    monkeypatch.setattr(bilibili_sdk, "fetch_subtitle_for_aid_cid", fake_player)

    result = await bilibili_sdk.fetch_subtitle_for_url(
        "https://www.bilibili.com/video/BVtest?p=2"
    )
    assert result["text"] == "分P字幕"
    assert result["source"] == "wbi_player"
