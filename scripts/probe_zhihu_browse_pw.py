"""用 Playwright 打开知乎最近浏览/首页，拦截 XHR 找浏览历史 API。

知乎首页右侧可能有"最近浏览"模块，或者 /recent 页面。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


async def main() -> None:
    from playwright.async_api import async_playwright
    from osint_toolkit.auth.cookie_sync import cookies_for_playwright

    token = "sankichu"
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
                captured.append({"url": url[:200], "status": response.status, "method": response.request.method, "dc": dc, "interesting": interesting})
                tag = " ***" if interesting else ""
                print(f"  [{response.request.method}] {response.status} dc={dc} {url[:130]}{tag}")
                if dc > 0 and isinstance(body, dict):
                    data = body.get("data")
                    if isinstance(data, list) and data:
                        first = data[0] if isinstance(data[0], dict) else {}
                        print(f"    first keys: {list(first.keys())[:10]}")
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

        # 知乎首页（可能有最近浏览模块）
        for target_url in [
            "https://www.zhihu.com/",
            f"https://www.zhihu.com/people/{token}/activities",
            "https://www.zhihu.com/recent",
            "https://www.zhihu.com/recent-viewed",
        ]:
            print(f"\n=== {target_url} ===")
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(4)
                # 滚动
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
            except Exception as exc:
                print(f"  error: {exc}")

        await context.close()
        await browser.close()

    print(f"\n=== 浏览相关 XHR: {sum(1 for c in captured if c['interesting'])} ===")
    for c in captured:
        if c["interesting"]:
            print(f"  [{c['method']}] {c['status']} dc={c['dc']} {c['url']}")

    out = Path.home() / ".osint" / "zhihu_browse_probe.json"
    out.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    asyncio.run(main())
