"""探测知乎浏览历史相关端点，包括 read_history 的 GET 变体。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from osint_toolkit.http.client import HttpClient


async def probe(client: HttpClient, url: str, label: str) -> None:
    try:
        resp = await client.get(url, timeout=15.0, headers={"Referer": "https://www.zhihu.com/"})
        ct = resp.headers.get("content-type", "")
        body_text = resp.text[:300].replace("\n", " ")
        item_count = -1
        if "json" in ct:
            try:
                d = resp.json()
                data = d.get("data") if isinstance(d, dict) else None
                if isinstance(data, list):
                    item_count = len(data)
                    if data and isinstance(data[0], dict):
                        print(f"  [{label}] {resp.status_code} items={item_count} first_keys={list(data[0].keys())[:8]}")
                        return
                elif isinstance(data, dict):
                    item_count = 1
                print(f"  [{label}] {resp.status_code} items={item_count} body={body_text[:120]}")
            except Exception:
                print(f"  [{label}] {resp.status_code} non-json: {body_text[:100]}")
        else:
            print(f"  [{label}] {resp.status_code} ct={ct[:30]}")
    except Exception as exc:
        print(f"  [{label}] error: {exc}")


async def main() -> None:
    client = HttpClient()
    me = await client.get("https://www.zhihu.com/api/v4/me")
    token = str(me.json().get("url_token") or "")
    print(f"token: {token}")

    base = "https://www.zhihu.com"
    candidates = [
        ("read_history", f"{base}/api/v4/read_history?offset=0&limit=10"),
        ("read_history_v2", f"{base}/api/v4/read_history/list?offset=0&limit=10"),
        ("me_read_history", f"{base}/api/v4/me/read_history?offset=0&limit=10"),
        ("self_read_history", f"{base}/api/v4/self/read_history?offset=0&limit=10"),
        ("read_history_items", f"{base}/api/v4/read_history/items?offset=0&limit=10"),
        ("recent_viewed_v3", f"{base}/api/v3/moments/{token}/read_history?limit=10"),
        ("moments_browse", f"{base}/api/v3/moments/{token}/browse?limit=10"),
        ("profile_visits", f"{base}/api/v4/me?include=visits_count"),
    ]
    print("=== GET 端点探测 ===")
    for label, url in candidates:
        await probe(client, url, label)

    # 也测 moments 端点的其它 verb（可能有浏览相关）
    print("\n=== moments 端点变体 ===")
    moments_paths = [
        f"/api/v3/moments/{token}/activities?limit=5",
    ]
    for p in moments_paths:
        await probe(client, base + p, p.split("?")[0])


if __name__ == "__main__":
    asyncio.run(main())
