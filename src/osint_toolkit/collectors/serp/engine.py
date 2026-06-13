"""SERP 编排引擎 / SERP orchestration engine."""

from __future__ import annotations

import os

from osint_toolkit.collectors.serp.models import SerpHit
from osint_toolkit.collectors.serp.providers import PROVIDERS
from osint_toolkit.http.client import HttpClient
from osint_toolkit.models.intel_item import IntelItem
from osint_toolkit.utils.config import get_serp_config


def _auto_provider_order(cfg: dict) -> list[str]:
    order: list[str] = []
    if cfg.get("bing_api_key") or os.environ.get("BING_SEARCH_API_KEY"):
        order.append("bing_api")
    if cfg.get("serpapi_key") or os.environ.get("SERPAPI_KEY"):
        order.append("serpapi")
    order.extend(["bing_html", "baidu_html"])
    return order


def _provider_chain(cfg: dict) -> list[str]:
    primary = str(cfg.get("primary") or "auto").lower()
    fallbacks = [str(p).lower() for p in (cfg.get("fallbacks") or [])]
    if primary == "auto":
        chain = _auto_provider_order(cfg)
    else:
        chain = [primary]
    for fb in fallbacks:
        if fb not in chain:
            chain.append(fb)
    return [p for p in chain if p in PROVIDERS]


class SerpEngine:
    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()
        self.cfg = get_serp_config()

    async def search(self, query: str, limit: int = 10) -> tuple[list[SerpHit], list[str]]:
        """按配置链尝试各 SERP 提供方，返回 hits 与尝试日志。"""
        attempts: list[str] = []
        for name in _provider_chain(self.cfg):
            fn = PROVIDERS[name]
            if name in {"bing_api", "serpapi"}:
                hits, err = await fn(self.client, query, limit, self.cfg)
            else:
                hits, err = await fn(self.client, query, limit)
            if hits:
                attempts.append(f"{name}: ok ({len(hits)})")
                return hits[:limit], attempts
            attempts.append(err or f"{name}: empty")
        return [], attempts

    async def site_search(self, domain: str, query: str, limit: int = 10) -> tuple[list[SerpHit], list[str]]:
        site_query = f"site:{domain} {query}".strip()
        hits, attempts = await self.search(site_query, limit=limit)
        for h in hits:
            h.meta["site"] = domain
        return hits, attempts


async def site_search(query: str, domain: str, limit: int = 10, client: HttpClient | None = None) -> list[SerpHit]:
    engine = SerpEngine(client=client)
    hits, _ = await engine.site_search(domain, query, limit=limit)
    return hits


def hits_to_items(hits: list[SerpHit], *, source: str = "web") -> list[IntelItem]:
    items: list[IntelItem] = []
    seen: set[str] = set()
    for hit in hits:
        url = hit.url.strip()
        if not url or url in seen:
            continue
        seen.add(url)
        item = IntelItem(
            source=source,
            type="snippet",
            url=url,
            title=hit.title,
            content=hit.snippet,
        )
        item.personal["serp_engine"] = hit.engine
        item.personal["serp_query"] = hit.query
        if hit.meta.get("site"):
            item.personal["site_search"] = hit.meta["site"]
        items.append(item)
    return items
