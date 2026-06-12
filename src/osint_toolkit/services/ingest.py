"""导入服务 / Ingest service."""

from __future__ import annotations

import asyncio
from typing import Any

from osint_toolkit.ingest.bilibili_account import ingest_history
from osint_toolkit.ingest.browser import ingest_browser_history
from osint_toolkit.ingest.likes import list_endorsements
from osint_toolkit.ingest.zhihu_account import ingest_votes


def ingest_browser(*, since_days: int = 90) -> dict[str, Any]:
    rows = ingest_browser_history(since_days=since_days)
    return {"count": len(rows), "rows": rows[:20]}


def ingest_bilibili() -> dict[str, Any]:
    rows = asyncio.run(ingest_history())
    return {"count": len(rows), "rows": rows[:20]}


def ingest_zhihu() -> dict[str, Any]:
    rows = asyncio.run(ingest_votes())
    return {"count": len(rows), "rows": rows[:20]}


def get_likes() -> dict[str, Any]:
    rows = list_endorsements()
    return {"count": len(rows), "rows": rows}
