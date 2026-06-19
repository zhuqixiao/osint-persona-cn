"""AI relevance refinement tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from osint_toolkit.analyzers.ai_relevance import refine_relevance_with_ai
from osint_toolkit.models.intel_item import IntelItem, IntelSignals


@pytest.mark.asyncio
async def test_refine_relevance_blends_ai_score():
    item = IntelItem(
        source="zhihu",
        type="answer",
        url="https://www.zhihu.com/answer/1",
        title="相关讨论",
        content="关于 deepseek 识图",
    )
    item.signals = IntelSignals(relevance=0.3, fold_reason="扩展词漂移")

    class FakeClient:
        def chat(self, messages):
            return (
                '{"scores":[{"id":"'
                + item.id
                + '","relevance":0.72,"clear_fold":true,"note":"与主题相关"}]}'
            )

    with patch("osint_toolkit.analyzers.ai_relevance.DeepSeekClient", lambda: FakeClient()):
        changes = await refine_relevance_with_ai(
            [item],
            "deepseek 识图",
            no_ai=False,
            search_cfg={"ai_relevance_refine": True, "ai_relevance_blend": 0.4},
        )

    assert changes
    assert item.signals.fold_reason is None
    assert item.signals.relevance > 0.3
    assert item.personal.get("ai_relevance_note")


@pytest.mark.asyncio
async def test_refine_relevance_skipped_when_no_ai():
    item = IntelItem(source="web", type="page", url="https://x.com", title="t", content="c")
    item.signals = IntelSignals(relevance=0.25)
    changes = await refine_relevance_with_ai([item], "q", no_ai=True)
    assert changes == []
    assert item.signals.relevance == 0.25
