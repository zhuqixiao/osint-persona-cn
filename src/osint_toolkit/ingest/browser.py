"""浏览器历史导入 / Browser history ingest."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from osint_toolkit.storage.knowledge import log_event_deduped

_SKIP_URL_PREFIXES = (
    "file:",
    "edge:",
    "chrome:",
    "about:",
    "devtools:",
    "javascript:",
)
_SKIP_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}


def _edge_history_path() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return None
    return Path(local) / "Microsoft" / "Edge" / "User Data" / "Default" / "History"


def _should_skip_url(url: str) -> bool:
    raw = (url or "").strip()
    if not raw.startswith("http"):
        return True
    lower = raw.lower()
    if any(lower.startswith(p) for p in _SKIP_URL_PREFIXES):
        return True
    host = (urlparse(raw).hostname or "").lower()
    return host in _SKIP_HOSTS


def _dedup_key(url: str, visited_at: str) -> str:
    day = visited_at[:10]
    digest = hashlib.sha256(f"browser_visit|{url}|{day}".encode()).hexdigest()[:32]
    return f"browser_visit:{digest}"


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
    except (PermissionError, OSError):
        return []
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except PermissionError:
            pass
    results: list[dict] = []
    for url, title, visit_time in rows:
        if not url or _should_skip_url(str(url)):
            continue
        visited = chrome_epoch + timedelta(microseconds=visit_time)
        if visited < since:
            continue
        visited_iso = visited.isoformat()
        entry = {
            "source": "browser",
            "url": url,
            "title": title or "",
            "visited_at": visited_iso,
            "event_kind": "browser_history",
            "via": "edge_history",
        }
        if log_event_deduped("browser_visit", entry, _dedup_key(str(url), visited_iso)):
            results.append(entry)
    return results
