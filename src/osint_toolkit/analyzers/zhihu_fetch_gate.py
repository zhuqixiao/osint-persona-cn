"""知乎 OpenAPI 摘要后的加深抓取门控 / Zhihu deep-fetch gating after OpenAPI snippets."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from osint_toolkit.ai.client import DeepSeekClient
from osint_toolkit.ai.steering import build_system_prompt, is_step_enabled
from osint_toolkit.models.intel_item import IntelItem

_COMMENT_KEY_RE = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)


def _comment_key(comment: dict[str, Any]) -> str:
    body = str(comment.get("content") or "").strip().lower()
    body = _COMMENT_KEY_RE.sub("", body)[:160]
    author = str(comment.get("author") or "").strip().lower()
    return f"{author}:{body}"


def merge_comment_lists(
    prefetched: list[dict[str, Any]] | None,
    fetched: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """合并 OpenAPI 预取与站内深抓评论，按内容去重并保留更高赞版本。"""
    merged: dict[str, dict[str, Any]] = {}
    for row in list(prefetched or []) + list(fetched or []):
        if not isinstance(row, dict):
            continue
        content = str(row.get("content") or "").strip()
        if not content:
            continue
        key = _comment_key(row)
        prev = merged.get(key)
        if prev is None or int(row.get("likes") or 0) > int(prev.get("likes") or 0):
            merged[key] = dict(row)
            if prev is not None and "replies" in prev and "replies" not in row:
                merged[key]["replies"] = prev["replies"]
        elif "replies" in row and "replies" not in prev:
            prev["replies"] = row["replies"]
    return sorted(merged.values(), key=lambda c: int(c.get("likes") or 0), reverse=True)


def _openapi_via(item: IntelItem) -> bool:
    return str(item.personal.get("via") or "").startswith("zhihu_openapi")


def heuristic_zhihu_deep_plan(item: IntelItem, search_cfg: dict[str, Any]) -> dict[str, Any]:
    """
    规则门控：默认倾向加深；仅在信息价值明显不足时跳过。
    返回 fetch_body / fetch_comments 与原因说明。
    """
    rel = float(getattr(getattr(item, "signals", None), "relevance", 0) or 0)
    content_len = len((item.content or "").strip())
    max_snippet = int(search_cfg.get("zhihu_openapi_deep_fetch_max_snippet_len", 400))
    skip_rel = float(search_cfg.get("zhihu_deep_fetch_skip_relevance", 0.12))
    metrics_comments = int(getattr(getattr(item, "metrics", None), "comments", 0) or 0)
    openapi_comments = list(item.personal.get("openapi_comments") or [])
    openapi_n = len(openapi_comments)
    item_type = str(item.type or "")

    reasons: list[str] = []
    fetch_body = False
    fetch_comments = False

    ample_body = content_len > int(max_snippet * 1.25)
    no_discussion = metrics_comments <= 0 and openapi_n <= 0
    clearly_low_value = rel < skip_rel and ample_body and no_discussion

    if clearly_low_value:
        return {
            "fetch_body": False,
            "fetch_comments": False,
            "reason": "低相关、正文已较完整且无评论讨论信号",
            "via": "heuristic_skip",
        }

    if _openapi_via(item) and not ample_body:
        fetch_body = True
        reasons.append("openapi正文偏短")
    elif content_len <= max_snippet and rel >= float(search_cfg.get("zhihu_openapi_deep_fetch_min_relevance", 0.35)):
        fetch_body = True
        reasons.append("相关度达标且摘要较短")

    can_comment_api = item_type in {"answer", "article"} or (
        item_type == "question" and openapi_n > 0
    )
    if can_comment_api:
        if metrics_comments > openapi_n:
            fetch_comments = True
            reasons.append("站内评论数多于openapi样本")
        elif openapi_n > 0 and metrics_comments > 0:
            fetch_comments = True
            reasons.append("openapi评论可能不完整")
        elif rel >= 0.22 and (metrics_comments > 0 or openapi_n > 0):
            fetch_comments = True
            reasons.append("有相关讨论信号")
        elif rel >= 0.3 and item_type in {"answer", "article"}:
            fetch_comments = True
            reasons.append("相关度较高默认加深评论")

    if not fetch_body and not fetch_comments and rel >= 0.12:
        if _openapi_via(item) and content_len <= max_snippet:
            fetch_body = True
            reasons.append("放宽：openapi条目默认尝试补全文")
        elif item_type in {"answer", "article"}:
            fetch_comments = True
            reasons.append("放宽：comment_mine条目默认尝试评论")

    return {
        "fetch_body": fetch_body,
        "fetch_comments": fetch_comments,
        "reason": "；".join(reasons) if reasons else "保持openapi摘要",
        "via": "heuristic",
    }


def _plan_payload(item: IntelItem) -> dict[str, Any]:
    openapi = list(item.personal.get("openapi_comments") or [])
    return {
        "id": item.id,
        "type": item.type,
        "title": (item.title or "")[:120],
        "snippet": (item.content or "")[:280],
        "relevance": float(getattr(getattr(item, "signals", None), "relevance", 0) or 0),
        "content_len": len((item.content or "").strip()),
        "metrics_comments": int(getattr(getattr(item, "metrics", None), "comments", 0) or 0),
        "openapi_comment_count": len(openapi),
        "openapi_comment_sample": (openapi[0].get("content", "")[:80] if openapi else ""),
    }


async def plan_zhihu_deep_fetch(
    items: list[IntelItem],
    query: str,
    search_cfg: dict[str, Any],
    *,
    no_ai: bool = False,
    disabled_steps: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """为候选知乎条目生成加深计划（规则 + 可选 AI）。"""
    plans: dict[str, dict[str, Any]] = {}
    candidates = [i for i in items if i.source == "zhihu"]
    if not candidates:
        return plans

    for item in candidates:
        plans[item.id] = heuristic_zhihu_deep_plan(item, search_cfg)

    use_ai = bool(search_cfg.get("zhihu_deep_fetch_ai", True))
    if no_ai or not use_ai or not is_step_enabled("comment_mine", no_ai=no_ai, disabled_steps=disabled_steps):
        return plans

    ai_targets = [
        item
        for item in candidates
        if _openapi_via(item) or str(item.personal.get("via") or "") == "zhihu_openapi"
        or len((item.content or "").strip()) <= int(search_cfg.get("zhihu_openapi_deep_fetch_max_snippet_len", 400))
    ]
    if not ai_targets:
        ai_targets = candidates[: min(8, len(candidates))]

    client = DeepSeekClient()
    payload = {
        "query": query,
        "items": [_plan_payload(i) for i in ai_targets[:12]],
        "rules": (
            "OpenAPI 仅提供短摘要/少量热评。请判断每条是否值得花费请求加深："
            "fetch_body=拉取全文，fetch_comments=拉取站内完整热评。"
            "信息价值明显不足（离题、纯标题党、无讨论且正文已够）可 skip；不确定时倾向 fetch。"
        ),
    }
    try:
        raw = await asyncio.to_thread(
            client.chat,
            messages=[
                {
                    "role": "system",
                    "content": build_system_prompt(
                        task="你是情报搜罗助手，根据 OpenAPI 短摘要判断条目是否值得加深抓取。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "仅输出 JSON："
                        '{"decisions":[{"id":"...","fetch_body":true,"fetch_comments":true,"reason":"..."}]}'
                        f"\n{json.dumps(payload, ensure_ascii=False)}"
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
        for row in data.get("decisions") or []:
            if not isinstance(row, dict):
                continue
            iid = str(row.get("id") or "").strip()
            if not iid or iid not in plans:
                continue
            plans[iid] = {
                "fetch_body": bool(row.get("fetch_body")),
                "fetch_comments": bool(row.get("fetch_comments")),
                "reason": str(row.get("reason") or "AI门控"),
                "via": "ai",
            }
    except Exception:  # noqa: BLE001
        pass

    return plans
