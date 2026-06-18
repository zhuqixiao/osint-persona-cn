"""Bilibili account ingest helpers tests."""

from __future__ import annotations

from osint_toolkit.ingest.bilibili_account import _video_url


def test_video_url_from_bvid():
    assert _video_url({"bvid": "BV1xx411c7mD"}) == "https://www.bilibili.com/video/BV1xx411c7mD"


def test_video_url_from_bare_bv_string():
    assert _video_url({"uri": "BV1xx411c7mD"}) == "https://www.bilibili.com/video/BV1xx411c7mD"


def test_video_url_from_aid():
    assert _video_url({"aid": 12345}) == "https://www.bilibili.com/video/av12345"
