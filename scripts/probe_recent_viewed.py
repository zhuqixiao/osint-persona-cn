"""探测 /recent-viewed 页面：先抓 HTML 看 initialData，再用 Playwright 拦截 XHR。"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


async def probe_html():
    """1. 抓 HTML 看 initialData。"""
    from osint_toolkit.http.client import HttpClient

    c = HttpClient()
    resp = await c.get("https://www.zhihu.com/recent-viewed", headers={"Referer": "https://www.zhihu.com/"})
    text = resp.text or ""
    print(f"=== HTML probe: status={resp.status_code} len={len(text)} ===")

    m = re.search(r'<script id="js-initialData"[^>]*>(.*?)</script>', text, re.S)
    if not m:
        print("  NO initialData")
        for kw in ["recent", "viewed", "history", "read", "antispider", "412", "登录"]:
            if kw in text:
                print(f"  found keyword: {kw}")
        tm = re.search(r"<title>(.*?)</title>", text, re.S)
        if tm:
            print(f"  title: {tm.group(1).strip()[:80]}")
        return

    print("  FOUND initialData!")
    data = json.loads(m.group(1))
    state = data.get("initialState", {})

    def find_keys(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{path}.{k}" if path else k
                if any(w in k.lower() for w in ("recent", "view", "history", "read", "browse", "visit", "footprint")):
                    if isinstance(v, dict):
                        sub_keys = list(v.keys())[:8]
                        print(f"  {p}: dict keys={sub_keys}")
                        for sk in ("data", "items", "ids", "list"):
                            if sk in v and isinstance(v[sk], list):
                                print(f"    {p}.{sk}: list[{len(v[sk])}]")
                                if v[sk] and isinstance(v[sk][0], dict):
                                    print(f"      first keys: {list(v[sk][0].keys())[:10]}")
                    elif isinstance(v, list):
                        print(f"  {p}: list[{len(v)}]")
                if isinstance(v, (dict, list)) and len(p.split(".")) < 4:
                    find_keys(v, p)
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:2]):
                if isinstance(item, dict):
                    find_keys(item, f"{path}[{i}]")

    find_keys(state)


async def probe_playwright():
    """2. 用 Playwright 打开 recent-viewed 页面拦截 XHR。"""
    from playwright.async_api import async_playwright
    from osint_toolkit.auth.cookie_sync import cookies_for_playwright

    captured: list[dict] = []

    async def on_response(response):
        url = response.url or ""
        if "/api/" not in url:
            return
        try:
            body = None
            try:
                body = await response.json()
            except Exception:
                pass
            dc = -1
            if isinstance(body, dict):
                d = body.get("data")
                if isinstance(d, list):
                    dc = len(d)
                elif isinstance(d, dict):
                    dc = 1
            interesting = any(w in url.lower() for w in ("read", "history", "recent", "view", "browse", "visit", "footprint"))
            if interesting or dc > 0:
                tag = " ***" if interesting else ""
                print(f"  [{response.request.method}] {response.status} dc={dc} {url[:140]}{tag}")
                if dc > 0 and isinstance(body, dict):
                    data = body.get("data")
                    if isinstance(data, list) and data:
                        first = data[0] if isinstance(data[0], dict) else {}
                        print(f"    first keys: {list(first.keys())[:10]}")
                        # 看有没有 url/title
                        for k in ("url", "title", "target", "question"):
                            if k in first:
                                print(f"    {k}: {str(first[k])[:80]}")
                captured.append({"url": url[:200], "status": response.status, "method": response.request.method, "dc": dc, "interesting": interesting})
        except Exception:
            pass

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        )
        pw_cookies = cookies_for_playwright()
        if pw_cookies:
            await context.add_cookies(pw_cookies)

        page = await context.new_page()
        page.on("response", on_response)

        print("\n=== Playwright: /recent-viewed ===")
        try:
            await page.goto("https://www.zhihu.com/recent-viewed", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            title = await page.title()
            print(f"  title: {title}")
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
        except Exception as exc:
            print(f"  error: {exc}")

        await context.close()
        await browser.close()

    browse_xhrs = [c for c in captured if c["interesting"]]
    print(f"\n=== 浏览历史相关 XHR: {len(browse_xhrs)} ===")
    for c in browse_xhrs:
        print(f"  [{c['method']}] {c['status']} dc={c['dc']} {c['url']}")
    if not browse_xhrs:
        print("  (无浏览历史相关 XHR)")
        print("\n=== 所有有数据的 XHR ===")
        for c in captured:
            if c["dc"] > 0:
                print(f"  [{c['method']}] {c['status']} dc={c['dc']} {c['url']}")

    out = Path.home() / ".osint" / "zhihu_recent_viewed_probe.json"
    out.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten: {out}")


async def main():
    await probe_html()
    await probe_playwright()


if __name__ == "__main__":
    asyncio.run(main())
