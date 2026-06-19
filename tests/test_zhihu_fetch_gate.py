"""知乎加深抓取门控测试."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from osint_toolkit.analyzers.zhihu_fetch_gate import (
    heuristic_zhihu_deep_plan,
    merge_comment_lists,
    plan_zhihu_deep_fetch,
)
from osint_toolkit.models.intel_item import IntelItem, IntelMetrics
from osint_toolkit.services import search as search_mod


def test_merge_comment_lists_dedupes_and_keeps_higher_likes():
    prefetched = [{"author": "a", "content": "same text", "likes": 2}]
    fetched = [{"author": "a", "content": "same text", "likes": 9}, {"author": "b", "content": "other", "likes": 1}]
    merged = merge_comment_lists(prefetched, fetched)
    assert len(merged) == 2
    assert merged[0]["likes"] == 9


def test_heuristic_skips_clearly_low_value():
    item = IntelItem(
        source="zhihu",
        type="article",
        url="https://zhuanlan.zhihu.com/p/1",
        title="t",
        content="x" * 900,
        personal={"via": "zhihu_openapi"},
    )
    item.signals.relevance = 0.08
    plan = heuristic_zhihu_deep_plan(item, {"zhihu_openapi_deep_fetch_max_snippet_len": 400})
    assert plan["fetch_body"] is False
    assert plan["fetch_comments"] is False


def test_heuristic_fetches_when_openapi_comments_incomplete():
    item = IntelItem(
        source="zhihu",
        type="answer",
        url="https://www.zhihu.com/answer/1",
        title="t",
        content="short",
        personal={"via": "zhihu_openapi", "openapi_comments": [{"author": "u", "content": "c", "likes": 1}]},
        metrics=IntelMetrics(comments=12),
    )
    item.signals.relevance = 0.6
    plan = heuristic_zhihu_deep_plan(item, {"zhihu_openapi_deep_fetch_max_snippet_len": 400})
    assert plan["fetch_body"] is True
    assert plan["fetch_comments"] is True


@pytest.mark.asyncio
async def test_mine_comments_merges_openapi_and_fetched(monkeypatch):
    item = IntelItem(
        source="zhihu",
        type="answer",
        url="https://www.zhihu.com/answer/99",
        title="t",
        content="snippet",
        personal={
            "via": "zhihu_openapi",
            "openapi_comments": [{"author": "u1", "content": "openapi only", "likes": 1}],
            "deep_fetch_plan": {"fetch_body": False, "fetch_comments": True, "reason": "test"},
        },
    )
    item.signals.relevance = 0.8

    collector = AsyncMock()
    collector.fetch_comments = AsyncMock(
        return_value=[{"author": "u2", "content": "deep comment", "likes": 5}]
    )
    monkeypatch.setattr(search_mod, "ZhihuCollector", lambda: collector)
    monkeypatch.setattr(
        search_mod,
        "summarize_comments",
        AsyncMock(return_value="summary"),
    )
    monkeypatch.setattr(search_mod, "is_step_enabled", lambda *a, **k: True)

    mined = await search_mod._mine_comments(
        [item],
        top=1,
        no_ai=True,
        comment_mine_sources=["zhihu"],
    )

    assert len(item.layers["comments"]) == 2
    assert item.layers["comments_summary"] == "summary"
    collector.fetch_comments.assert_awaited_once()
    assert mined[0]["comment_count"] == 2


@pytest.mark.asyncio
async def test_plan_zhihu_deep_fetch_ai_overrides(monkeypatch):
    item = IntelItem(
        source="zhihu",
        type="answer",
        url="https://www.zhihu.com/answer/1",
        title="t",
        content="x" * 900,
        personal={"via": "zhihu_openapi"},
    )
    item.signals.relevance = 0.5

    class FakeClient:
        def chat(self, messages):
            return (
                '{"decisions":[{"id":"'
                + item.id
                + '","fetch_body":false,"fetch_comments":false,"reason":"AI判定信息已够"}]}'
            )

    monkeypatch.setattr("osint_toolkit.analyzers.zhihu_fetch_gate.DeepSeekClient", lambda: FakeClient())
    plans = await plan_zhihu_deep_fetch([item], "test", {}, no_ai=False, disabled_steps=None)
    assert plans[item.id]["fetch_body"] is False
    assert plans[item.id]["via"] == "ai"
