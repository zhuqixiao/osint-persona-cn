"""搜罗任务进度（内存态，供 Web SSE 推送）。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_store: dict[str, dict[str, Any]] = {}


def init_progress(run_id: str) -> None:
    _store[run_id] = {
        "phase": "starting",
        "detail": "正在启动搜罗任务…",
        "started_at": datetime.now(UTC).isoformat(),
        "completed_steps": [],
        "collect_done": 0,
        "collect_total": 0,
        "items_found": 0,
        "eta_sec": None,
        "current_url": "",
        "recent_urls": [],
    }


def clear_progress(run_id: str) -> None:
    _store.pop(run_id, None)


def get_progress(run_id: str) -> dict[str, Any] | None:
    return _store.get(run_id)


def update_progress(
    run_id: str | None,
    phase: str,
    *,
    detail: str = "",
    mark_completed: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    if not run_id:
        return
    state = _store.setdefault(
        run_id,
        {
            "phase": phase,
            "detail": detail,
            "started_at": datetime.now(UTC).isoformat(),
            "completed_steps": [],
        },
    )
    state["phase"] = phase
    if detail:
        state["detail"] = detail
    if mark_completed:
        completed = list(state.get("completed_steps") or [])
        completed.append(mark_completed)
        state["completed_steps"] = completed
    for key, val in extra.items():
        if val is not None:
            state[key] = val
