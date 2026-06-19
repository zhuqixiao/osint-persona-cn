"""International reachability probe tests."""

from __future__ import annotations

import osint_toolkit.http.reachability as reach


async def test_reachability_with_proxy(monkeypatch):
    monkeypatch.setattr(reach, "has_proxy_configured", lambda: True)
    reach._cache["at"] = 0
    reach._cache["result"] = None
    result = await reach.probe_international_reachability(force=True)
    assert result["reachable"] is True
    assert result["proxy_configured"] is True
