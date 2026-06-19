"""International endpoint reachability probes (proxy-aware)."""

from __future__ import annotations

import time
from typing import Any

from osint_toolkit.http.client import HttpClient
from osint_toolkit.utils.config import load_config

_CACHE_TTL_SEC = 300.0
_cache: dict[str, Any] = {"at": 0.0, "result": None}


def _http_cfg() -> dict[str, Any]:
    return dict(load_config().get("http") or {})


def has_proxy_configured() -> bool:
    proxy = _http_cfg().get("proxy")
    return bool(proxy and str(proxy).strip())


async def probe_international_reachability(*, force: bool = False) -> dict[str, Any]:
    """HEAD/GET github.com; cached. True if proxy set or direct access works."""
    now = time.monotonic()
    if not force and _cache.get("result") is not None and now - float(_cache.get("at") or 0) < _CACHE_TTL_SEC:
        return dict(_cache["result"])

    proxy_configured = has_proxy_configured()
    result: dict[str, Any] = {
        "proxy_configured": proxy_configured,
        "github_ok": False,
        "reddit_ok": False,
        "reachable": proxy_configured,
        "detail": "",
    }
    if proxy_configured:
        result["detail"] = "已配置 http.proxy，假定国际信源可用"
        result["github_ok"] = True
        _cache["at"] = now
        _cache["result"] = result
        return result

    client = HttpClient()
    try:
        resp = await client.get("https://api.github.com/zen", timeout=8.0)
        result["github_ok"] = resp.status_code in (200, 403, 429)
        result["reachable"] = result["github_ok"]
        if result["github_ok"]:
            result["detail"] = "GitHub API 可达"
        else:
            result["detail"] = f"GitHub API HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        result["detail"] = f"国际网络不可达: {exc}"
        result["reachable"] = False

    _cache["at"] = now
    _cache["result"] = result
    return result


def intl_probe_enabled(cfg: dict[str, Any] | None = None) -> bool:
    from osint_toolkit.utils.config import load_config

    fe = dict((cfg or load_config().get("search") or {}).get("foreign_expand") or {})
    mode = str(fe.get("intl_probe_enabled") or "auto")
    if mode == "off":
        return False
    if mode == "on":
        return True
    return has_proxy_configured()
