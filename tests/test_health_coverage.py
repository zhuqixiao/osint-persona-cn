"""Health coverage mapping tests."""

from __future__ import annotations

from osint_toolkit.services.health import platform_coverage


def test_platform_coverage_includes_bilibili_comment_events():
    event_types = [
        behavior["event_type"]
        for platform in platform_coverage()
        for behavior in platform.get("behaviors") or []
    ]
    assert "bilibili_comment_post" in event_types
    assert "bilibili_comment_like" in event_types
    labels = {
        behavior["event_type"]: behavior["behavior"]
        for platform in platform_coverage()
        for behavior in platform.get("behaviors") or []
    }
    assert labels["bilibili_comment_post"] == "发评"
    assert labels["bilibili_comment_like"] == "评论赞"
