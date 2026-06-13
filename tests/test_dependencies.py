"""Dependencies / setup helpers tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from osint_toolkit.web.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_dependencies_status_shape():
    from osint_toolkit.services.dependencies import get_dependencies_status

    data = get_dependencies_status()
    assert "items" in data
    assert "playwright_installed" in data
    assert any(i["id"] == "playwright" for i in data["items"])


@pytest.mark.asyncio
async def test_install_playwright_already_installed():
    from osint_toolkit.services import dependencies

    with patch.object(dependencies, "playwright_available", return_value=True):
        with patch.object(dependencies, "_run_subprocess", new_callable=AsyncMock) as run:
            run.return_value = (0, "ok")
            result = await dependencies.install_playwright()
    assert result["ok"] is True
    assert run.await_count == 1


def test_setup_status_includes_playwright(client):
    r = client.get("/api/setup/status")
    assert r.status_code == 200
    data = r.json()
    assert "playwright_installed" in data
    assert any(s["id"] == "playwright" for s in data["steps"])


def test_setup_dependencies_api(client):
    r = client.get("/api/setup/dependencies")
    assert r.status_code == 200
    data = r.json()
    assert data["items"]
    assert "blockers" in data


def test_install_playwright_job_api(client, monkeypatch):
    monkeypatch.setattr(
        "osint_toolkit.web.routes.api.start_playwright_install_job",
        lambda: "job-test-1",
    )
    r = client.post("/api/setup/install-playwright")
    assert r.status_code == 200
    assert r.json()["job_id"] == "job-test-1"
