"""按话题解析本次搜索应启用的信源 / Per-query source resolution."""

from __future__ import annotations

import re
from typing import Any

from osint_toolkit.collectors.registry import COLLECTORS
from osint_toolkit.collectors.source_catalog import (
    comprehensive_native_source_ids,
    get_source_labels,
    merge_source_priority,
)
from osint_toolkit.collectors.source_routing import (
    _music_source_ids,
    compute_source_scores,
    match_domain_route,
)
from osint_toolkit.utils.config import get_search_config

_CORE_DEFAULT = ("zhihu", "web")


def blend_rule_and_ai_scores(
    rule_scores: dict[str, float],
    ai_plan: dict[str, Any] | None,
    *,
    is_cryptic: bool = False,
) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    """合并规则分与 AI 分，返回 (综合分, 分项明细)。"""
    cfg = _auto_route_cfg()
    blend = float(cfg.get("ai_blend", 0.55))
    if is_cryptic:
        blend = float(cfg.get("ai_blend_cryptic", 0.78))

    from osint_toolkit.ai.source_planner import extract_ai_score_map

    ai_map = extract_ai_score_map(ai_plan)
    ai_meta = (ai_plan or {}).get("source_scores") or {}

    final: dict[str, float] = {}
    breakdown: dict[str, dict[str, Any]] = {}
    all_ids = set(COLLECTORS) | set(rule_scores) | set(ai_map)

    for sid in all_ids:
        rule = float(rule_scores.get(sid, 0))
        ai = float(ai_map.get(sid, 0))
        if ai > 0 and rule > 0:
            score = rule * (1.0 - blend) + ai * blend
        elif ai > 0:
            score = ai
        else:
            score = rule
        if score <= 0 and rule <= 0 and ai <= 0:
            continue
        meta = ai_meta.get(sid) if isinstance(ai_meta.get(sid), dict) else {}
        breakdown[sid] = {
            "rule": round(rule, 1),
            "ai": round(ai, 1),
            "final": round(score, 1),
            "tier": str(meta.get("tier") or ""),
            "reason": str(meta.get("reason") or ""),
        }
        final[sid] = score

    return final, breakdown


def detect_cryptic_from_scores(rule_scores: dict[str, float]) -> bool:
    cfg = _auto_route_cfg()
    threshold = float(cfg.get("cryptic_rule_max", 35))
    if not rule_scores:
        return True
    return max(rule_scores.values()) < threshold


def _effective_strong_threshold(cfg: dict[str, Any], *, is_cryptic: bool) -> float:
    base = float(cfg.get("strong_threshold", 45))
    if is_cryptic:
        return float(cfg.get("cryptic_strong_threshold", min(base, 38)))
    return base


def _substantive_query_heuristic(query: str) -> bool:
    """无 AI 时判断查询是否有实质检索价值（避免对灌水词自动扩源）。"""
    q = (query or "").strip()
    if len(q) < 2:
        return False
    if re.fullmatch(r"(.)\1{4,}", q):
        return False
    if re.fullmatch(r"[\W\d_]+", q):
        return False
    if re.search(r"[\u4e00-\u9fff]", q) or re.search(r"[a-zA-Z]{3,}", q):
        return True
    return len(q) >= 4


def _boost_scores_from_ai_plan(
    scores: dict[str, float],
    ai_plan: dict[str, Any],
    cfg: dict[str, Any],
    *,
    is_cryptic: bool,
) -> dict[str, float]:
    """将 AI 明确建议与 strong 档信源抬到可自动启用区间。"""
    from osint_toolkit.ai.source_planner import extract_ai_auto_enable, extract_ai_score_map, is_nonsense_plan

    if is_nonsense_plan(ai_plan):
        return scores

    out = dict(scores)
    ai_map = extract_ai_score_map(ai_plan)
    strong_th = _effective_strong_threshold(cfg, is_cryptic=is_cryptic)
    floor = strong_th + 0.5
    auto_min = float(cfg.get("ai_auto_enable_min", 55))
    tier_min = float(cfg.get("ai_strong_tier_min", 65))

    for sid in extract_ai_auto_enable(ai_plan):
        if ai_map.get(sid, 0) >= auto_min:
            out[sid] = max(out.get(sid, 0), floor)

    for sid, meta in (ai_plan.get("source_scores") or {}).items():
        if not isinstance(meta, dict):
            continue
        if str(meta.get("tier") or "") != "strong":
            continue
        if float(meta.get("score") or 0) < tier_min:
            continue
        out[str(sid)] = max(out.get(str(sid), 0), floor)

    return out


def _auto_enable_sort_key(
    sid: str,
    scores: dict[str, float],
    ai_plan: dict[str, Any] | None,
) -> tuple[float, float, float, float]:
    from osint_toolkit.ai.source_planner import extract_ai_auto_enable, extract_ai_score_map

    explicit = set(extract_ai_auto_enable(ai_plan))
    ai_map = extract_ai_score_map(ai_plan)
    tier = ""
    meta = (ai_plan or {}).get("source_scores", {}).get(sid)
    if isinstance(meta, dict):
        tier = str(meta.get("tier") or "")
    return (
        1.0 if sid in explicit else 0.0,
        1.0 if tier == "strong" else 0.0,
        ai_map.get(sid, 0),
        scores.get(sid, 0),
    )


def _auto_route_cfg() -> dict[str, Any]:
    raw = get_search_config().get("source_auto_route")
    return raw if isinstance(raw, dict) else {}


def _profile_restrict_pool(profile: str) -> set[str] | None:
    from osint_toolkit.collectors.profile_catalog import get_search_profile

    prof = get_search_profile(profile)
    if not prof:
        return None
    if prof.get("source_auto_restrict"):
        return {s for s in (prof.get("sources") or []) if s in COLLECTORS}
    return None


def _allowed_catalog(
    user_sources: list[str],
    *,
    profile: str,
    cfg: dict[str, Any],
) -> set[str]:
    restrict = _profile_restrict_pool(profile)
    if restrict is not None:
        return restrict
    scope = str(cfg.get("auto_enable_scope") or "catalog")
    if scope == "user_pool" and user_sources:
        return {s for s in user_sources if s in COLLECTORS}
    return set(COLLECTORS.keys())


def _build_hint(
    *,
    route: dict[str, Any] | None,
    mode: str,
    auto_enabled: list[str],
    skipped: list[str],
    active: list[str],
    labels: dict[str, str],
    ai_plan: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    if route:
        parts.append(f"话题「{route['label']}」")
    if mode == "off":
        if route and active:
            boosted = "、".join(labels.get(s, s) for s in active[:5])
            parts.append(f"已优先：{boosted}")
        return "。".join(parts) + ("。" if parts else "")

    if auto_enabled:
        names = "、".join(labels.get(s, s) for s in auto_enabled[:8])
        parts.append(f"自动启用 {names}")
    if ai_plan and ai_plan.get("source_scores") and mode != "off":
        parts.append("AI 已参与信源评分与取舍")
    if skipped:
        names = "、".join(labels.get(s, s) for s in skipped[:8])
        parts.append(f"跳过弱相关 {names}")
    if route and not auto_enabled and not skipped and active:
        names = "、".join(labels.get(s, s) for s in active[:5])
        parts.append(f"采集 {names}")
    if not parts:
        return ""
    return "；".join(parts) + "。"


def _attach_decisions(
    active: list[str],
    skipped: list[str],
    breakdown: dict[str, dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for sid in active:
        row = dict((breakdown or {}).get(sid) or {})
        row["decision"] = "active"
        out[sid] = row
    for sid in skipped:
        row = dict((breakdown or {}).get(sid) or {})
        row["decision"] = "skipped"
        out[sid] = row
    return out


def _apply_source_overrides(
    active: list[str],
    skipped: list[str],
    *,
    overrides: dict[str, list[str]] | None,
) -> tuple[list[str], list[str]]:
    if not overrides:
        return active, skipped
    force = [s for s in (overrides.get("force") or []) if s in COLLECTORS]
    block = {s for s in (overrides.get("block") or []) if s in COLLECTORS}
    active = [s for s in active if s not in block]
    skipped = [s for s in skipped if s not in block]
    for sid in force:
        if sid in block:
            continue
        if sid not in active:
            active.insert(0, sid)
        if sid in skipped:
            skipped.remove(sid)
    return active, skipped


def resolve_search_sources(
    query: str,
    user_sources: list[str],
    *,
    ai_recommended: list[str] | None = None,
    profile: str = "default",
    mode: str | None = None,
    scores: dict[str, float] | None = None,
    score_breakdown: dict[str, dict[str, Any]] | None = None,
    ai_plan: dict[str, Any] | None = None,
    source_overrides: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """温和模式：强相关自动启用，弱相关跳过；off 时等同仅调优先级。"""
    cfg = _auto_route_cfg()
    mode = str(mode or cfg.get("mode") or "gentle").lower()
    labels = get_source_labels()
    route = match_domain_route(query)
    user = [s for s in user_sources if s in COLLECTORS]
    rule_scores = compute_source_scores(query, ai_priority=ai_recommended)
    if scores is None:
        scores = rule_scores
    if score_breakdown is None:
        score_breakdown = {
            s: {"rule": round(rule_scores.get(s, 0), 1), "ai": 0.0, "final": round(scores.get(s, 0), 1), "reason": ""}
            for s in scores
            if scores.get(s, 0) > 0
        }

    if mode == "off":
        active = merge_source_priority(user, ai_recommended)
        return {
            "mode": mode,
            "domain": str(route["id"]) if route else "",
            "label": str(route["label"]) if route else "",
            "active_sources": active,
            "recommended_sources": active,
            "user_sources": user,
            "auto_enabled": [],
            "skipped": [],
            "scores": {s: round(scores[s], 1) for s in active if scores.get(s, 0) > 0},
            "score_breakdown": {s: score_breakdown[s] for s in active if s in score_breakdown},
            "rule_scores": {s: round(rule_scores[s], 1) for s in active if rule_scores.get(s, 0) > 0},
            "source_plan": ai_plan or {},
            "is_cryptic": bool((ai_plan or {}).get("is_cryptic")),
            "hint": _build_hint(
                route=route,
                mode=mode,
                auto_enabled=[],
                skipped=[],
                active=active,
                labels=labels,
                ai_plan=ai_plan,
            ),
            "suggested_sources": [],
            "boost_site_domains": list(route.get("site_domains") or []) if route else [],
        }

    is_cryptic = bool((ai_plan or {}).get("is_cryptic")) or detect_cryptic_from_scores(rule_scores)
    from osint_toolkit.ai.source_planner import is_nonsense_plan

    user_set = set(user)
    weak_th = float(cfg.get("weak_threshold", 12))
    protect_core = bool(cfg.get("protect_core", True))
    if mode == "aggressive":
        weak_th = max(5.0, weak_th - 4.0)
        protect_core = False

    if ai_plan and is_nonsense_plan(ai_plan):
        scores = dict(scores)
        for sid in list(scores.keys()):
            if sid not in user_set:
                scores[sid] = min(float(scores.get(sid, 0)), weak_th - 0.1)
        if score_breakdown is not None:
            for sid in scores:
                if sid in score_breakdown:
                    score_breakdown[sid]["final"] = round(scores[sid], 1)
    elif ai_plan and ai_plan.get("ai_invoked"):
        scores = _boost_scores_from_ai_plan(scores, ai_plan, cfg, is_cryptic=is_cryptic)
        if score_breakdown is not None:
            for sid, sc in scores.items():
                if sid in score_breakdown:
                    score_breakdown[sid]["final"] = round(sc, 1)
                elif sc > 0:
                    score_breakdown[sid] = {
                        "rule": round(rule_scores.get(sid, 0), 1),
                        "ai": 0.0,
                        "final": round(sc, 1),
                        "reason": "",
                    }

    strong_th = _effective_strong_threshold(cfg, is_cryptic=is_cryptic)
    if mode == "aggressive":
        strong_th = max(weak_th + 1.0, strong_th - 12.0)
    min_active = int(cfg.get("min_active_sources", 3))
    max_active = int(cfg.get("max_active_sources", 12))
    max_auto = int(cfg.get("max_auto_enable", 6))
    core_sources = set(cfg.get("core_sources") or list(_CORE_DEFAULT))
    allowed = _allowed_catalog(user, profile=profile, cfg=cfg)
    music_ids = _music_source_ids()
    comprehensive_natives = comprehensive_native_source_ids()

    def _skip_music_source(sid: str) -> bool:
        # 音乐站仅用户主动勾选时参与采集，不自动拉起
        return sid in music_ids and sid not in user_set

    active: list[str] = []
    auto_enabled: list[str] = []
    skipped: list[str] = []

    strong_candidates = sorted(
        [(s, scores[s]) for s in allowed if scores.get(s, 0) >= strong_th],
        key=lambda x: _auto_enable_sort_key(x[0], scores, ai_plan),
        reverse=True,
    )
    auto_count = 0
    for sid, _ in strong_candidates:
        if _skip_music_source(sid):
            continue
        if sid in active:
            continue
        if sid not in user_set:
            if auto_count >= max_auto:
                continue
            auto_count += 1
            auto_enabled.append(sid)
        active.append(sid)

    for sid in user:
        if sid not in allowed:
            skipped.append(sid)
            continue
        if _skip_music_source(sid):
            skipped.append(sid)
            continue
        if sid in active:
            continue
        if sid in comprehensive_natives:
            active.append(sid)
            continue
        sc = scores.get(sid, 0)
        if sc >= weak_th:
            active.append(sid)
        elif protect_core and sid in core_sources:
            active.append(sid)
        else:
            skipped.append(sid)

    if len(active) < min_active and not (ai_plan and is_nonsense_plan(ai_plan)):
        fallback_ok = (ai_plan and ai_plan.get("ai_invoked")) or _substantive_query_heuristic(query)
        if fallback_ok:
            for sid, sc in sorted(
                scores.items(),
                key=lambda x: _auto_enable_sort_key(x[0], scores, ai_plan),
                reverse=True,
            ):
                if sid not in allowed or sid in active or sc < weak_th:
                    continue
                if _skip_music_source(sid):
                    continue
                active.append(sid)
                if sid not in user_set and sid not in auto_enabled:
                    auto_enabled.append(sid)
                if len(active) >= min_active:
                    break

    if len(active) > max_active:
        protect_user = bool(cfg.get("protect_user_selected", True))
        ranked = sorted(active, key=lambda s: -scores.get(s, 0))
        if protect_user:
            must_keep = [s for s in user if s in ranked]
            tail = [s for s in ranked if s not in must_keep]
            slots = max(0, max_active - len(must_keep))
            active = must_keep + tail[:slots]
        else:
            active = ranked[:max_active]
        for sid in user:
            if sid not in active and sid not in skipped:
                skipped.append(sid)

    active = sorted(active, key=lambda s: -scores.get(s, 0))
    auto_enabled = [s for s in auto_enabled if s in active]
    skipped = list(dict.fromkeys(skipped))
    active, skipped = _apply_source_overrides(active, skipped, overrides=source_overrides)

    return {
        "mode": mode,
        "domain": str(route["id"]) if route else "",
        "label": str(route["label"]) if route else "",
        "active_sources": active,
        "recommended_sources": active,
        "user_sources": user,
        "auto_enabled": auto_enabled,
        "skipped": skipped,
        "scores": {s: round(scores[s], 1) for s in active if scores.get(s, 0) > 0},
        "score_breakdown": _attach_decisions(active, skipped, score_breakdown),
        "rule_scores": {s: round(rule_scores.get(s, 0), 1) for s in set(active) | set(skipped) if rule_scores.get(s, 0) > 0},
        "source_plan": ai_plan or {},
        "is_cryptic": is_cryptic,
        "hint": _build_hint(
            route=route,
            mode=mode,
            auto_enabled=auto_enabled,
            skipped=skipped,
            active=active,
            labels=labels,
            ai_plan=ai_plan,
        ),
        "suggested_sources": auto_enabled,
        "boost_site_domains": list(route.get("site_domains") or []) if route else [],
    }
