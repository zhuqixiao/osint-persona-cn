"""浏览器历史导入 / Browser history ingest."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from osint_toolkit.storage.knowledge import log_event


def _edge_history_path() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    return Path(local) / "Microsoft" / "Edge" / "User Data" / "Default" / "History"


def ingest_browser_history(since_days: int = 90) -> list[dict]:
    src = _edge_history_path()
    if not src or not src.exists():
        return []
    since = datetime.now(UTC) - timedelta(days=since_days)
    chrome_epoch = datetime(1601, 1, 1, tzinfo=UTC)
    fd, tmp_name = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(src, tmp)
        conn = sqlite3.connect(f"file:{tmp.as_posix()}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 5000"
            ).fetchall()
        finally:
            conn.close()
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except PermissionError:
            pass
    results = []
    for url, title, visit_time in rows:
        if not url:
            continue
        visited = chrome_epoch + timedelta(microseconds=visit_time)
        if visited < since:
            continue
        entry = {"source": "browser", "url": url, "title": title or "", "visited_at": visited.isoformat()}
        log_event("browser_visit", entry)
        results.append(entry)
    return results
