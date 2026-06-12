"""后台搜索任务 / Background search tasks."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from osint_toolkit.services import search as search_service

_jobs: dict[str, dict[str, Any]] = {}


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S") + f"-{uuid4().hex[:8]}"


def get_job(run_id: str) -> dict[str, Any] | None:
    return _jobs.get(run_id)


def start_search_job(**kwargs: Any) -> str:
    run_id = new_run_id()
    _jobs[run_id] = {"status": "running", "result": None, "error": None}
    asyncio.create_task(_execute_search(run_id, **kwargs))
    return run_id


async def _execute_search(run_id: str, **kwargs: Any) -> None:
    try:
        result = await search_service.run_search(**kwargs, run_id=run_id)
        _jobs[run_id] = {"status": "done", "result": result, "error": None}
    except Exception as exc:  # noqa: BLE001
        _jobs[run_id] = {"status": "error", "result": None, "error": str(exc)}
