"""合并采集阶段的重复来源提示 / Consolidate duplicate source warnings & errors."""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

_API_FAIL_RE = re.compile(r"^(.+? API 失败):\s*(.+)$", re.IGNORECASE)
_API_RATE_RE = re.compile(r"^(.+? API 速率限制.*)$", re.IGNORECASE)


def _notice_text(entry: dict[str, Any], *, text_key: str) -> str:
    return str(entry.get(text_key) or entry.get("message") or entry.get("error") or "").strip()


def _finalize_entry(entry: dict[str, Any], text_key: str) -> dict[str, Any]:
    out = {k: v for k, v in entry.items() if not str(k).startswith("_")}
    count = int(entry.get("_count") or 1)
    text = str(out.get(text_key) or "")
    if count > 1 and text and "（共 " not in text:
        out[text_key] = f"{text}（共 {count} 次）"
    return out


def _truncate_detail(text: str, *, max_len: int = 72) -> str:
    t = " ".join(text.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _merge_api_failure_bucket(bucket: list[dict[str, Any]], *, text_key: str) -> dict[str, Any]:
    total = sum(int(b.get("_count") or 1) for b in bucket)
    base = dict(bucket[0])
    first = _notice_text(bucket[0], text_key=text_key)
    rate = _API_RATE_RE.match(first)
    if rate:
        out = _finalize_entry({**base, text_key: first, "_count": total}, text_key)
        return out

    details: list[str] = []
    for entry in bucket:
        text = _notice_text(entry, text_key=text_key)
        m = _API_FAIL_RE.match(text)
        detail = _truncate_detail(m.group(2) if m else text)
        count = int(entry.get("_count") or 1)
        if count > 1:
            details.append(f"{detail} ×{count}")
        else:
            details.append(detail)

    api_label = "API"
    m0 = _API_FAIL_RE.match(first)
    if m0:
        api_label = m0.group(1).removesuffix(" API 失败").strip() or m0.group(1)

    if len(details) == 1 and total > 1:
        summary = f"{api_label} API 失败: {details[0].split(' ×')[0]}（共 {total} 次），已尝试回退"
    elif len(details) == 1:
        summary = first
    else:
        shown = "；".join(details[:2])
        if len(details) > 2:
            shown = f"{shown} 等 {len(details)} 类错误"
        summary = f"{api_label} API 多次失败（{total} 次），已尝试回退：{shown}"

    out = dict(base)
    out[text_key] = summary
    return out


def consolidate_source_notices(
    notices: list[dict[str, Any]] | None,
    *,
    text_key: str = "warning",
) -> list[dict[str, str]]:
    """合并同源、同文案或同类 API 失败的重复提示。"""
    if not notices:
        return []

    exact: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()
    order: list[tuple[str, str]] = []

    for raw in notices:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "?").strip() or "?"
        text = _notice_text(raw, text_key=text_key)
        if not text:
            continue
        key = (source, text)
        if key not in exact:
            entry = dict(raw)
            entry["source"] = source
            entry[text_key] = text
            entry["_count"] = 1
            exact[key] = entry
            order.append(key)
        else:
            exact[key]["_count"] = int(exact[key].get("_count") or 1) + 1

    api_order: list[str] = []
    api_buckets: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    standalone: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()

    for key in order:
        entry = exact[key]
        source = str(entry.get("source") or "?")
        text = _notice_text(entry, text_key=text_key)
        if _API_FAIL_RE.match(text) or _API_RATE_RE.match(text):
            if source not in api_buckets:
                api_buckets[source] = []
                api_order.append(source)
            api_buckets[source].append(entry)
        else:
            standalone[key] = entry

    out: list[dict[str, str]] = []
    emitted_api: set[str] = set()

    for key in order:
        entry = exact[key]
        source = str(entry.get("source") or "?")
        text = _notice_text(entry, text_key=text_key)
        if _API_FAIL_RE.match(text) or _API_RATE_RE.match(text):
            if source in emitted_api:
                continue
            bucket = api_buckets.get(source) or [entry]
            if len(bucket) == 1 and int(bucket[0].get("_count") or 1) == 1:
                out.append(_finalize_entry(bucket[0], text_key))  # type: ignore[arg-type]
            else:
                out.append(_merge_api_failure_bucket(bucket, text_key=text_key))  # type: ignore[arg-type]
            emitted_api.add(source)
            continue
        if key in standalone:
            out.append(_finalize_entry(entry, text_key))  # type: ignore[arg-type]

    return out
