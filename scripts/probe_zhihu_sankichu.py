"""对 sankichu（或任意 url_token）实测所有候选端点。

目的：找出哪些端点对"自己"有数据，为重新启用 activities / 点赞历史 / 浏览历史提供事实依据。
结果落盘 ~/.osint/zhihu_sankichu_probe.json。
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from osint_toolkit.http.client import HttpClient

TARGET_TOKEN = "sankichu"


async def probe_endpoint(client: HttpClient, url: str, *, label: str = "") -> dict:
    try:
        resp = await client.get(url, timeout=15.0)
        ct = resp.headers.get("content-type", "")
        body_text = resp.text[:600].replace("\n", " ")
        item_count = -1
        sample_keys: list[str] = []
        is_blocked = resp.status_code in (401, 403, 412) or "验证码" in body_text or "antispider" in body_text
        if "json" in ct:
            try:
                d = resp.json()
                data = d.get("data")
                if isinstance(data, list):
                    item_count = len(data)
                    if data:
                        sample_keys = list((data[0] if isinstance(data[0], dict) else {}).keys())[:10]
                elif isinstance(data, dict):
                    item_count = 1
                    sample_keys = list(data.keys())[:10]
                else:
                    sample_keys = list(d.keys())[:10]
            except Exception:
                pass
        return {
            "label": label or url.split("?")[0].split("/api/v4/")[-1],
            "url": url,
            "status": resp.status_code,
            "item_count": item_count,
            "sample_keys": sample_keys,
            "blocked": is_blocked,
            "snippet": body_text[:200],
        }
    except Exception as exc:
        return {
            "label": label or url.split("?")[0].split("/api/v4/")[-1],
            "url": url,
            "status": -1,
            "item_count": -1,
            "error": str(exc)[:200],
        }


async def main() -> int:
    client = HttpClient()
    me_resp = await client.get("https://www.zhihu.com/api/v4/me")
    me_token = ""
    try:
        me_token = str(me_resp.json().get("url_token") or "")
    except Exception:
        pass
    print(f"me token: {me_token!r}  target: {TARGET_TOKEN!r}")

    token = me_token or TARGET_TOKEN
    base = "https://www.zhihu.com"

    candidates: list[tuple[str, str]] = [
        ("profile", f"{base}/api/v4/members/{token}"),
        ("answers", f"{base}/api/v4/members/{token}/answers?offset=0&limit=5&include=data[*].is_normal,voteup_count,comment_count"),
        ("articles", f"{base}/api/v4/members/{token}/articles?offset=0&limit=5"),
        ("pins", f"{base}/api/v4/members/{token}/pins?offset=0&limit=5"),
        ("favlists", f"{base}/api/v4/members/{token}/favlists?include=answers&offset=0&limit=5"),
        ("followees", f"{base}/api/v4/members/{token}/followees?offset=0&limit=5"),
        # === 动态流（最关键）===
        ("activities_default", f"{base}/api/v4/members/{token}/activities?limit=20"),
        ("activities_include_target", f"{base}/api/v4/members/{token}/activities?limit=20&include=data[*].target,actor"),
        ("activities_include_full", f"{base}/api/v4/members/{token}/activities?limit=20&include=data[*].target,actor,origin,suggestion"),
        ("activities_after_id", f"{base}/api/v4/members/{token}/activities?limit=20&after_id=0"),
        # === 点赞历史（再确认 404 + 新变体）===
        ("voteanswers", f"{base}/api/v4/members/{token}/voteanswers?offset=0&limit=5"),
        ("vote_answers", f"{base}/api/v4/members/{token}/vote_answers?offset=0&limit=5"),
        ("answers_voted", f"{base}/api/v4/members/{token}/answers/voted?offset=0&limit=5"),
        ("voters", f"{base}/api/v4/members/{token}/voters?offset=0&limit=5"),
        ("likes", f"{base}/api/v4/members/{token}/likes?offset=0&limit=5"),
        ("vote_answers_v2", f"{base}/api/v4/members/{token}/vote_answers?offset=0&limit=5&include=data[*].target"),
        ("logs", f"{base}/api/v4/members/{token}/logs?offset=0&limit=5"),
        # === 浏览历史（再确认 404 + 新变体）===
        ("browsing_histories", f"{base}/api/v4/members/{token}/browsing_histories?offset=0&limit=5"),
        ("footprints", f"{base}/api/v4/members/{token}/footprints?offset=0&limit=5"),
        ("self_recent_viewed", f"{base}/api/v4/self/recent_viewed?offset=0&limit=5"),
        ("me_recent_viewed", f"{base}/api/v4/me/recent_viewed?offset=0&limit=5"),
        ("record_viewed_v2", f"{base}/api/v4/record_viewed_v2?offset=0&limit=5"),
        # === 关注的问题动态 ===
        ("following_question_activities", f"{base}/api/v4/members/{token}/following-question-activities?offset=0&limit=5"),
        # === 想法点赞 ===
        ("pins_voted", f"{base}/api/v4/members/{token}/pins/voted?offset=0&limit=5"),
        # === 文章点赞 ===
        ("articles_voted", f"{base}/api/v4/members/{token}/articles/voted?offset=0&limit=5"),
    ]

    results: list[dict] = []
    for label, url in candidates:
        print(f"  probing {label}...", end=" ", flush=True)
        r = await probe_endpoint(client, url, label=label)
        results.append(r)
        status = r.get("status")
        count = r.get("item_count")
        blocked = r.get("blocked")
        marker = "BLOCKED" if blocked else ("DATA" if (count is not None and count > 0) else "empty/404")
        print(f"{status} items={count} [{marker}]")
        if count and count > 0:
            print(f"    keys: {r.get('sample_keys')}")

    report = {
        "me_token": me_token,
        "target_token": token,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "results": results,
        "working_endpoints": [r for r in results if r.get("item_count", -1) > 0],
        "blocked_endpoints": [r["label"] for r in results if r.get("blocked")],
        "dead_endpoints": [r["label"] for r in results if r.get("status") == 404],
    }

    out_path = Path.home() / ".osint" / "zhihu_sankichu_probe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== summary ===")
    print(f"working: {[r['label'] for r in report['working_endpoints']]}")
    print(f"blocked: {report['blocked_endpoints']}")
    print(f"dead(404): {report['dead_endpoints']}")
    print(f"written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
