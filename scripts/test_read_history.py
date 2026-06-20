"""测试 HttpClient 能否直接调 /api/v4/unify-consumption/read_history。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from osint_toolkit.http.client import HttpClient


async def main() -> None:
    c = HttpClient()
    url = "https://www.zhihu.com/api/v4/unify-consumption/read_history?offset=0&limit=20"
    resp = await c.get(url, headers={"Referer": "https://www.zhihu.com/recent-viewed"})
    print(f"status={resp.status_code}")
    d = resp.json()
    data = d.get("data") or []
    print(f"items={len(data)}")

    if data:
        for i, item in enumerate(data[:5]):
            card_type = item.get("card_type")
            inner = item.get("data") or {}
            print(f"\n  [{i}] card_type={card_type}")
            print(f"      inner keys: {list(inner.keys())[:12]}")
            # 尝试提取 url/title
            target = inner.get("target") or inner
            question = target.get("question") or {}
            title = question.get("title") or target.get("title") or inner.get("title") or ""
            url_ = target.get("url") or inner.get("url") or ""
            obj_id = target.get("id") or inner.get("id") or ""
            obj_type = target.get("type") or inner.get("type") or ""
            print(f"      title: {title[:80]}")
            print(f"      url: {url_[:100]}")
            print(f"      id: {obj_id} type: {obj_type}")
            if "created_time" in inner:
                print(f"      created_time: {inner['created_time']}")
            if "updated_time" in inner:
                print(f"      updated_time: {inner['updated_time']}")

        # 看 paging
        paging = d.get("paging") or {}
        print(f"\npaging: {list(paging.keys())[:6]}")
        print(f"is_end: {paging.get('is_end')}")
        print(f"next: {str(paging.get('next', ''))[:120]}")

        # 翻页测试
        next_url = paging.get("next")
        if next_url:
            resp2 = await c.get(next_url, headers={"Referer": "https://www.zhihu.com/recent-viewed"})
            d2 = resp2.json()
            data2 = d2.get("data") or []
            print(f"\npage 2: status={resp2.status_code} items={len(data2)}")
            if data2:
                item = data2[0]
                inner = item.get("data") or {}
                target = inner.get("target") or inner
                question = target.get("question") or {}
                title = question.get("title") or target.get("title") or ""
                print(f"  first title: {title[:80]}")

    # 也测 total
    print("\n=== read_history/total ===")
    resp_t = await c.get("https://www.zhihu.com/api/v4/read_history/total", headers={"Referer": "https://www.zhihu.com/recent-viewed"})
    print(f"status={resp_t.status_code}")
    try:
        print(f"body: {resp_t.json()}")
    except Exception:
        print(f"body: {resp_t.text[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
