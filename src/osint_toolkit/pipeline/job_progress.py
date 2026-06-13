"""后台任务（完整同步等）进度辅助。"""

from __future__ import annotations

import time
from typing import Any, Callable

from osint_toolkit.pipeline.progress import check_cancelled, update_progress

FULL_SYNC_PHASES: list[tuple[str, str]] = [
    ("preflight", "Cookie 预检"),
    ("accounts-sync", "B站/知乎 API"),
    ("browser-history", "Edge 浏览历史"),
    ("browser-sync", "浏览器补洞"),
    ("aicu", "AICU 发评"),
    ("extension-flush", "扩展上报"),
]


def init_full_sync_progress(job_id: str) -> None:
    from datetime import UTC, datetime

    update_progress(
        job_id,
        "preflight",
        detail="准备完整同步…",
        step_total=len(FULL_SYNC_PHASES),
        step_done=0,
        phases=[label for _, label in FULL_SYNC_PHASES],
        percent=0,
        started_at=datetime.now(UTC).isoformat(),
    )


def make_full_sync_callbacks(job_id: str | None) -> tuple[Callable[..., None], Callable[[str], None]]:
    started = time.perf_counter()
    step_started = time.perf_counter()
    step_durations: list[float] = []
    phase_index = {name: idx for idx, (name, _) in enumerate(FULL_SYNC_PHASES)}

    def on_progress(phase: str, detail: str = "", **extra: Any) -> None:
        if not job_id:
            return
        check_cancelled(job_id)
        idx = phase_index.get(phase, 0)
        step_done = int(extra.get("step_done", idx))
        eta_sec = None
        if step_durations and step_done < len(FULL_SYNC_PHASES):
            avg = sum(step_durations) / len(step_durations)
            eta_sec = max(0, int(avg * (len(FULL_SYNC_PHASES) - step_done)))
        label = next((lbl for name, lbl in FULL_SYNC_PHASES if name == phase), phase)
        update_progress(
            job_id,
            phase,
            detail=detail or label,
            step_done=step_done,
            step_total=len(FULL_SYNC_PHASES),
            eta_sec=eta_sec,
            **{k: v for k, v in extra.items() if k not in {"step_done"}},
        )

    def on_step_completed(phase: str) -> None:
        nonlocal step_started
        step_durations.append(max(0.1, time.perf_counter() - step_started))
        step_started = time.perf_counter()
        idx = phase_index.get(phase, 0)
        on_progress(phase, step_done=idx + 1)

    return on_progress, on_step_completed
