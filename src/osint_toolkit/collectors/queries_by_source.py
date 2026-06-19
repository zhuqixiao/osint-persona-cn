"""Per-source query resolution for domestic vs international collectors."""

from __future__ import annotations

import re

from osint_toolkit.collectors.source_catalog import get_source_locale_meta

_CJK = re.compile(r"[\u4e00-\u9fff]")


def is_primarily_latin(text: str) -> bool:
    t = str(text or "").strip()
    if not t:
        return False
    latin = sum(1 for c in t if c.isascii() and c.isalpha())
    cjk = len(_CJK.findall(t))
    if latin >= 2 and latin > cjk:
        return True
    if cjk == 0 and latin >= 2:
        return True
    return False


def _dedupe_preserve_order(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        t = term.strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def resolve_queries_for_source(
    source_id: str,
    base_queries: list[str],
    foreign_queries: list[str],
    *,
    max_per_source: int = 5,
) -> list[str]:
    meta = get_source_locale_meta(source_id)
    if meta.get("accept_foreign_queries"):
        merged = _dedupe_preserve_order(list(base_queries) + list(foreign_queries))
    else:
        merged = [q for q in base_queries if not is_primarily_latin(q)]
        if not merged:
            merged = base_queries[:1] if base_queries else []
    return merged[:max_per_source]


def build_queries_by_source(
    sources: list[str],
    base_queries: list[str],
    foreign_queries: list[str],
    *,
    max_per_source: int = 5,
) -> dict[str, list[str]]:
    return {
        s: resolve_queries_for_source(s, base_queries, foreign_queries, max_per_source=max_per_source)
        for s in sources
        if s
    }
