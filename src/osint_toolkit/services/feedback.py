"""反馈服务 / Feedback service."""

from __future__ import annotations

from typing import Any

from osint_toolkit.feedback.apply import apply_step_feedback
from osint_toolkit.feedback.store import FeedbackStore


def submit_feedback(
    *,
    target_id: str,
    rating: str,
    reason: str = "",
    run_id: str | None = None,
    step: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if step:
        result["step_feedback"] = apply_step_feedback(rating, reason, step=step)
    store = FeedbackStore()
    entry = store.add(
        target_type="item",
        target_id=target_id,
        rating=rating,
        reason=reason,
        run_id=run_id,
        step=step,
    )
    result["entry"] = entry
    return result
