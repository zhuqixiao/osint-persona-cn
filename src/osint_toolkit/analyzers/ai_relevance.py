"""AI 辅助相关度精炼 / AI-assisted relevance refinement (auxiliary to rules)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from osint_toolkit.ai.client import DeepSeekClient
from osint_toolkit.ai.steering import build_system_prompt, is_step_enabled
from osint_toolkit.models.intel_item import IntelItem
from osint_toolkit.utils.config import get_search_config


def _borderline_items(items: list[IntelItem], cfg: dict[str, Any]) -> list[IntelItem]:
    low = float(cfg.get("ai_relevance_borderline_low", 0.12))
    high = float(cfg.get("ai_relevance_borderline_high", 0.58))
    top = int(cfg.get("ai_relevance_refine_top", 36))
    candidates: list[IntelItem] = []
    for item in items:
        rel = float(getattr(getattr(item, "signals", None), "relevance", 0) or 0)
        fold = getattr(getattr(item, "signals", None), "fold_reason", None)
        if fold and rel < 0.4:
            candidates.append(item)
        elif low <= rel <= high:
            candidates.append(item)
    candidates.sort(key=lambda i: float(getattr(getattr(i, "signals", None), "relevance", 0) or 0), reverse=True)
    return candidates[:top]


async def refine_relevance_with_ai(
    items: list[IntelItem],
    query: str,
    *,
    no_ai: bool = False,
    disabled_steps: list[str] | None = None,
    search_cfg: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """对规则相关度边界条目做 AI 辅助打分，与规则分加权融合（不替代去重）。"""
    cfg = search_cfg or get_search_config()
    if no_ai or not bool(cfg.get("ai_relevance_refine", True)):
        return []
    if not is_step_enabled("relevance_refine", no_ai=no_ai, disabled_steps=disabled_steps):
        return []

    targets = _borderline_items(items, cfg)
    if not targets:
        return []

    by_id = {i.id: i for i in targets}
    payload = [
        {
            "id": it.id,
            "source": it.source,
            "title": (it.title or "")[:120],
            "snippet": (it.content or "")[:240],
            "rule_relevance": float(it.signals.relevance or 0),
            "fold_reason": it.signals.fold_reason or "",
        }
        for it in targets
    ]

    client = DeepSeekClient()
    blend = float(cfg.get("ai_relevance_blend", 0.35))
    changes: list[dict[str, Any]] = []

    try:
        raw = await asyncio.to_thread(
            client.chat,
            messages=[
                {
                    "role": "system",
                    "content": build_system_prompt(
                        task="你是情报搜罗助手，辅助判断条目与查询的相关度（不删除条目，仅调整分数）。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"查询: {query}\n"
                        "对每条给出 relevance(0-1)、clear_fold(是否解除误折叠)、note(可选一句理由)。"
                        "不确定时贴近 rule_relevance；明显离题则降低；被误伤的扩展词命中可提高并 clear_fold。\n"
                        '仅输出 JSON: {"scores":[{"id":"...","relevance":0.0,"clear_fold":false,"note":""}]}\n'
                        f"条目:\n{json.dumps(payload, ensure_ascii=False)}"
                    ),
                },
            ],
        )
        text = str(raw or "").strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        return []

    for row in data.get("scores") or []:
        if not isinstance(row, dict):
            continue
        iid = str(row.get("id") or "").strip()
        item = by_id.get(iid)
        if item is None:
            continue
        try:
            ai_rel = float(row.get("relevance", item.signals.relevance))
        except (TypeError, ValueError):
            continue
        ai_rel = max(0.0, min(1.0, ai_rel))
        rule_rel = float(item.signals.relevance or 0)
        final = round(max(0.0, min(1.0, rule_rel * (1.0 - blend) + ai_rel * blend)), 2)
        item.signals.relevance = final
        note = str(row.get("note") or "").strip()
        if note:
            item.personal["ai_relevance_note"] = note
        if row.get("clear_fold") and item.signals.fold_reason and final >= 0.26:
            item.personal["fold_reason_before_ai"] = item.signals.fold_reason
            item.signals.fold_reason = None
        changes.append(
            {
                "item_id": iid,
                "rule_relevance": rule_rel,
                "ai_relevance": ai_rel,
                "final_relevance": final,
                "cleared_fold": bool(row.get("clear_fold")),
            }
        )
    return changes
