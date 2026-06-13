"""SERP 提供方 / Search engine providers."""

from __future__ import annotations

import os
from urllib.parse import quote

from bs4 import BeautifulSoup

from osint_toolkit.collectors.serp.detection import is_blocked_response
from osint_toolkit.collectors.serp.models import SerpHit
from osint_toolkit.http.client import HttpClient


def _resolve_key(cfg: dict, key_name: str, env_name: str) -> str:
    val = str(cfg.get(key_name) or os.environ.get(env_name) or "").strip()
    return val


async def search_bing_html(client: HttpClient, query: str, limit: int) -> tuple[list[SerpHit], str | None]:
    url = f"https://www.bing.com/search?q={quote(query)}&setlang=zh-Hans"
    resp = await client.get(url)
    text = resp.text
    if is_blocked_response(text, status_code=resp.status_code):
        return [], "bing_html: 检测到 CAPTCHA/风控页面"
    soup = BeautifulSoup(text, "html.parser")
    hits: list[SerpHit] = []
    for li in soup.select("li.b_algo")[:limit]:
        a = li.find("a")
        if not a or not a.get("href"):
            continue
        snippet = ""
        p = li.find("p")
        if p:
            snippet = p.get_text(strip=True)
        hits.append(
            SerpHit(
                title=a.get_text(strip=True),
                url=a["href"],
                snippet=snippet,
                engine="bing_html",
                query=query,
            )
        )
    if not hits and "b_algo" not in text:
        return [], "bing_html: 未解析到结果（可能页面结构已变更）"
    return hits, None


async def search_baidu_html(client: HttpClient, query: str, limit: int) -> tuple[list[SerpHit], str | None]:
    url = f"https://www.baidu.com/s?wd={quote(query)}&rn={min(limit, 50)}"
    resp = await client.get(url)
    text = resp.text
    if is_blocked_response(text, status_code=resp.status_code):
        return [], "baidu_html: 检测到验证码/风控页面"
    soup = BeautifulSoup(text, "html.parser")
    hits: list[SerpHit] = []
    containers = soup.select("#content_left .result, #content_left .c-container")
    for block in containers[:limit]:
        a = block.select_one("h3 a, a[href^='http']")
        if not a or not a.get("href"):
            continue
        snippet_el = block.select_one(".c-abstract, .content-right_8Zs40, .c-span-last")
        hits.append(
            SerpHit(
                title=a.get_text(strip=True),
                url=a["href"],
                snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                engine="baidu_html",
                query=query,
            )
        )
    if not hits:
        return [], "baidu_html: 未解析到结果"
    return hits, None


async def search_bing_api(client: HttpClient, query: str, limit: int, cfg: dict) -> tuple[list[SerpHit], str | None]:
    key = _resolve_key(cfg, "bing_api_key", "BING_SEARCH_API_KEY")
    if not key:
        return [], "bing_api: 未配置 BING_SEARCH_API_KEY"
    url = f"https://api.bing.microsoft.com/v7.0/search?q={quote(query)}&count={limit}&mkt=zh-CN"
    resp = await client.get(url, headers={"Ocp-Apim-Subscription-Key": key})
    if resp.status_code != 200:
        return [], f"bing_api: HTTP {resp.status_code}"
    data = resp.json()
    hits: list[SerpHit] = []
    for entry in (data.get("webPages") or {}).get("value") or []:
        hits.append(
            SerpHit(
                title=str(entry.get("name") or ""),
                url=str(entry.get("url") or ""),
                snippet=str(entry.get("snippet") or ""),
                engine="bing_api",
                query=query,
                meta={"date": entry.get("dateLastCrawled")},
            )
        )
    return hits[:limit], None if hits else "bing_api: 空结果"


async def search_serpapi(client: HttpClient, query: str, limit: int, cfg: dict) -> tuple[list[SerpHit], str | None]:
    key = _resolve_key(cfg, "serpapi_key", "SERPAPI_KEY")
    if not key:
        return [], "serpapi: 未配置 SERPAPI_KEY"
    url = (
        f"https://serpapi.com/search.json?engine=bing&q={quote(query)}"
        f"&count={limit}&api_key={quote(key)}"
    )
    resp = await client.get(url)
    if resp.status_code != 200:
        return [], f"serpapi: HTTP {resp.status_code}"
    data = resp.json()
    if data.get("error"):
        return [], f"serpapi: {data.get('error')}"
    hits: list[SerpHit] = []
    for entry in data.get("organic_results") or []:
        hits.append(
            SerpHit(
                title=str(entry.get("title") or ""),
                url=str(entry.get("link") or ""),
                snippet=str(entry.get("snippet") or ""),
                engine="serpapi",
                query=query,
            )
        )
    return hits[:limit], None if hits else "serpapi: 空结果"


PROVIDERS = {
    "bing_html": search_bing_html,
    "baidu_html": search_baidu_html,
    "bing_api": search_bing_api,
    "serpapi": search_serpapi,
}
