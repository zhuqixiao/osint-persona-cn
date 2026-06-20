"""深入分析 read_history 数据结构，提取 URL/title。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from osint_toolkit.http.client import HttpClient


async def main() -> None:
    c = HttpClient()
    url = "https://www.zhihu.com/api/v4/unify-consumption/read_history?offset=0&limit=5"
    resp = await c.get(url, headers={"Referer": "https://www.zhihu.com/recent-viewed"})
    d = resp.json()
    data = d.get("data") or []

    for i, item in enumerate(data[:3]):
        print(f"\n=== item [{i}] ===")
        print(json.dumps(item, ensure_ascii=False, indent=2)[:2000])

    # 深入 content 字段
    print("\n\n=== 深入 content 字段 ===")
    if data:
        inner = data[0].get("data") or {}
        content = inner.get("content") or {}
        print(f"content keys: {list(content.keys())}")
        print(json.dumps(content, ensure_ascii=False, indent=2)[:2000])

        header = inner.get("header") or {}
        print(f"\nheader keys: {list(header.keys())}")
        print(json.dumps(header, ensure_ascii=False, indent=2)[:1000])


if __name__ == "__main__":
    asyncio.run(main())
