"""Extension status tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from osint_toolkit.services import extension


def test_connected_from_recent_ping(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.services.extension.get_data_dir", lambda: tmp_path)
    extension.ping_extension("0.3.0", True, pending_queue=3)
    status = extension.get_extension_status()
    assert status["connected"] is True
    assert status["pending_queue"] == 3
    assert status["extension_version"] == "0.3.0"


def test_connected_false_when_stale(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.services.extension.get_data_dir", lambda: tmp_path)
    stale = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    path = tmp_path / "extension_status.json"
    path.write_text(f'{{"last_seen": "{stale}"}}', encoding="utf-8")
    status = extension.get_extension_status()
    assert status["connected"] is False


def test_ping_clears_flush_error_when_queue_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.services.extension.get_data_dir", lambda: tmp_path)
    extension.ping_extension("0.3.0", True, pending_queue=5, last_flush_error="HTTP 500")
    extension.ping_extension("0.3.0", True, pending_queue=0)
    status = extension.get_extension_status()
    assert status["pending_queue"] == 0
    assert status.get("last_flush_error") == ""
