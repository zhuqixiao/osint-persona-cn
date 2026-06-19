"""OpenAPI comment hydration and zhihu enrich tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from osint_toolkit.models.intel_item import IntelItem, IntelMetrics
from osint_toolkit.services import search as search_mod


def test_apply_openapi_comment_layers_copies_for_all_zhihu_items():
    items = [
        IntelItem(
            source="zhihu",
            type="answer",
            url="https://www.zhihu.com/answer/1",
            title="a1",
            personal={"openapi_comments": [{"author": "u1", "content": "c1", "likes": 3}]},
        ),
        IntelItem(
            source="zhihu",
            type="question",
            url="https://www.zhihu.com/question/2",
            title="q1",
            personal={"openapi_comments": [{"author": "u2", "content": "c2", "likes": 1}]},
        ),
        IntelItem(source="bilibili", type="video", url="https://bilibili.com/1", title="v"),
    ]
    search_mod._apply_openapi_comment_layers(items)
    assert len(items[0].layers["comments"]) == 1
    assert items[0].layers["comments"][0]["content"] == "c1"
    assert len(items[1].layers["comments"]) == 1
    assert "comments" not in items[2].layers


def test_apply_openapi_comment_layers_skips_when_already_set():
    existing = [{"author": "x", "content": "y", "likes": 0}]
    item = IntelItem(
        source="zhihu",
        type="answer",
        url="https://www.zhihu.com/answer/9",
        title="t",
        personal={"openapi_comments": [{"author": "u", "content": "new", "likes": 1}]},
    )
    item.layers["comments"] = existing
    search_mod._apply_openapi_comment_layers([item])
    assert item.layers["comments"] is existing


@pytest.mark.asyncio
async def test_zhihu_question_keeps_openapi_and_attempts_comment_deep_fetch(monkeypatch):
    question = IntelItem(
        source="zhihu",
        type="question",
        url="https://www.zhihu.com/question/123",
        title="test question",
        content="short",
        personal={
            "openapi_comments": [{"author": "a", "content": "hot comment", "likes": 10}],
            "deep_fetch_plan": {"fetch_body": False, "fetch_comments": True, "reason": "test"},
        },
    )
    question.signals.relevance = 0.8

    async def fake_summarize(comments, *, no_ai, disabled_steps=None):
        return f"summary:{len(comments)}"

    collector = AsyncMock()
    collector.fetch_comments = AsyncMock(return_value=[])
    monkeypatch.setattr(search_mod, "ZhihuCollector", lambda: collector)
    monkeypatch.setattr(search_mod, "summarize_comments", fake_summarize)
    monkeypatch.setattr(search_mod, "is_step_enabled", lambda *a, **k: True)

    mined = await search_mod._mine_comments(
        [question],
        top=1,
        no_ai=False,
        comment_mine_sources=["zhihu"],
    )

    assert question.layers["comments"][0]["content"] == "hot comment"
    assert question.layers["comments_summary"] == "summary:1"
    assert mined[0]["comment_count"] == 1
    collector.fetch_comments.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_short_zhihu_openapi_fetches_deeper_content():
    item = IntelItem(
        source="zhihu",
        type="answer",
        url="https://www.zhihu.com/answer/42",
        title="short title",
        content="brief snippet",
        personal={"via": "zhihu_openapi"},
    )
    item.signals.relevance = 0.9

    deeper = IntelItem(
        source="zhihu",
        type="answer",
        url=item.url,
        title="full title",
        content="x" * 800,
        author="author",
        metrics=IntelMetrics(likes=5, comments=2),
    )

    with patch.object(search_mod.ZhihuCollector, "fetch", new_callable=AsyncMock, return_value=deeper):
        plans = {item.id: {"fetch_body": True, "fetch_comments": True, "reason": "test"}}
        enriched = await search_mod._enrich_short_zhihu_openapi(
            [item],
            {
                "zhihu_openapi_deep_fetch_top": 5,
                "zhihu_openapi_deep_fetch_min_relevance": 0.35,
                "zhihu_openapi_deep_fetch_max_snippet_len": 400,
            },
            plans,
        )

    assert len(item.content) == 800
    assert item.title == "full title"
    assert item.author == "author"
    assert enriched[0]["item_id"] == item.id


@pytest.mark.asyncio
async def test_enrich_short_zhihu_openapi_skips_when_plan_disables_body():
    item = IntelItem(
        source="zhihu",
        type="article",
        url="https://zhuanlan.zhihu.com/p/1",
        title="t",
        content="x" * 800,
        personal={"via": "zhihu_openapi"},
    )
    item.signals.relevance = 0.9
    plans = {item.id: {"fetch_body": False, "fetch_comments": False, "reason": "已够"}}

    with patch.object(search_mod.ZhihuCollector, "fetch", new_callable=AsyncMock) as mock_fetch:
        enriched = await search_mod._enrich_short_zhihu_openapi(
            [item],
            {"zhihu_openapi_deep_fetch_top": 5, "zhihu_openapi_deep_fetch_max_snippet_len": 400},
            plans,
        )

    assert enriched == []
    mock_fetch.assert_not_called()
