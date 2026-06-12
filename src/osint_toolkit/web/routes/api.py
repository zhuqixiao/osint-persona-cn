"""REST API 路由 / REST API routes."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse

from osint_toolkit.auth.paths import get_data_dir
from osint_toolkit.services import (
    ai_config,
    auth,
    digest,
    feedback,
    ingest,
    knowledge,
    persona,
    runs,
    save,
    tools,
)
from osint_toolkit.services.ask import ask_question
from osint_toolkit.web.schemas import (
    AskRequest,
    DirectivesUpdate,
    FeedbackRequest,
    IngestBrowserRequest,
    PersonaRollbackRequest,
    PromptUpdate,
    SaveRequest,
    SearchRequest,
    SyncCookiesRequest,
)
from osint_toolkit.web.tasks import get_job, start_search_job

router = APIRouter(prefix="/api")


def _serialize_search_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": result["run_id"],
        "items": [i.to_dict() for i in result["items"]],
        "report": result.get("report", ""),
        "report_path": result.get("report_path"),
        "simulations": result.get("simulations", []),
        "run_dir": result.get("run_dir"),
    }


@router.post("/search")
async def api_search(body: SearchRequest) -> dict[str, Any]:
    run_id = start_search_job(
        query=body.query,
        sources=body.sources,
        limit=body.limit,
        digest=body.digest,
        trace=body.trace,
        profile=body.profile,
        ai_instruct=body.ai_instruct,
        no_ai=body.no_ai,
        no_simulate=body.no_simulate,
        disabled_ai_steps=body.disabled_ai_steps,
        deep_top=body.deep_top,
    )
    return {"run_id": run_id, "status": "running"}


@router.get("/search/{run_id}")
async def api_search_result(run_id: str) -> dict[str, Any]:
    job = get_job(run_id)
    if job:
        if job["status"] == "running":
            return {"run_id": run_id, "status": "running"}
        if job["status"] == "error":
            raise HTTPException(500, detail=job["error"])
        return {"run_id": run_id, "status": "done", **_serialize_search_result(job["result"])}
    run_dir = get_data_dir() / "runs" / run_id
    if not run_dir.exists():
        raise HTTPException(404, detail="run not found")
    try:
        manifest = runs.show_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return {"run_id": run_id, "status": "done", "manifest": manifest}


@router.get("/search/{run_id}/events")
async def api_search_events(run_id: str) -> StreamingResponse:
    run_dir = get_data_dir() / "runs" / run_id

    async def event_stream():
        seen: set[str] = set()
        for _ in range(300):
            job = get_job(run_id)
            if run_dir.exists():
                for path in sorted(run_dir.glob("*_*.json")):
                    if path.name == "manifest.json" or path.name in seen:
                        continue
                    seen.add(path.name)
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        payload = json.dumps({"type": "step", "file": path.name, "step": data}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                    except json.JSONDecodeError:
                        continue
            if job and job["status"] == "done":
                result = _serialize_search_result(job["result"])
                yield f"data: {json.dumps({'type': 'done', 'result': result}, ensure_ascii=False)}\n\n"
                break
            if job and job["status"] == "error":
                yield f"data: {json.dumps({'type': 'error', 'error': job['error']}, ensure_ascii=False)}\n\n"
                break
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
            await asyncio.sleep(1)
        else:
            yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/save")
async def api_save(body: SaveRequest) -> dict[str, Any]:
    result = await save.save_url(body.url, with_comments=body.with_comments, no_ai=body.no_ai)
    return {"item": result["item"].to_dict(), "card_path": result["card_path"]}


@router.get("/knowledge/recall")
async def api_recall(q: str, limit: int = 20) -> dict[str, Any]:
    items = knowledge.recall(q, limit=limit)
    return {"items": [i.to_dict() for i in items], "count": len(items)}


@router.get("/knowledge/items")
async def api_knowledge_items(
    q: str = "",
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    items = knowledge.list_items(query=q, source=source, limit=limit, offset=offset)
    return {
        "items": [i.to_dict() for i in items],
        "count": len(items),
        "total": knowledge.count_items(source=source),
    }


@router.post("/ask")
async def api_ask(body: AskRequest) -> dict[str, Any]:
    return ask_question(body.question, run_id=body.run_id)


@router.post("/feedback")
async def api_feedback(body: FeedbackRequest) -> dict[str, Any]:
    return feedback.submit_feedback(
        target_id=body.target_id,
        rating=body.rating,
        reason=body.reason,
        run_id=body.run_id,
        step=body.step,
    )


@router.get("/digest/daily")
async def api_digest_daily() -> dict[str, str]:
    return {"content": digest.get_daily_digest()}


@router.get("/digest/reports")
async def api_digest_reports(limit: int = 50) -> dict[str, Any]:
    return {"reports": digest.list_reports(limit=limit)}


@router.post("/ingest/browser")
async def api_ingest_browser(body: IngestBrowserRequest) -> dict[str, Any]:
    return ingest.ingest_browser(since_days=body.since_days)


@router.post("/ingest/bilibili")
async def api_ingest_bilibili() -> dict[str, Any]:
    from osint_toolkit.ingest.bilibili_account import ingest_history

    rows = await ingest_history()
    return {"count": len(rows), "rows": rows[:20]}


@router.post("/ingest/zhihu")
async def api_ingest_zhihu() -> dict[str, Any]:
    from osint_toolkit.ingest.zhihu_account import ingest_votes

    rows = await ingest_votes()
    return {"count": len(rows), "rows": rows[:20]}


@router.get("/ingest/likes")
async def api_ingest_likes() -> dict[str, Any]:
    return ingest.get_likes()


@router.post("/persona/build")
async def api_persona_build(review: bool = False) -> dict[str, Any]:
    return persona.build_persona(review=review)


@router.get("/persona")
async def api_persona() -> dict[str, Any]:
    return persona.show_persona()


@router.post("/persona/rollback")
async def api_persona_rollback(body: PersonaRollbackRequest) -> dict[str, Any]:
    return persona.rollback_persona(body.version)


@router.get("/runs")
async def api_runs(limit: int = 20) -> dict[str, Any]:
    return {"runs": runs.list_runs(limit=limit)}


@router.get("/runs/{run_id}")
async def api_run_detail(run_id: str, step: str | None = None) -> Any:
    try:
        return runs.show_run(run_id, step=step)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/artifacts/{name}")
async def api_run_artifact(run_id: str, name: str) -> PlainTextResponse:
    try:
        content, media_type = runs.get_run_artifact(run_id, name)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return PlainTextResponse(content, media_type=media_type)


@router.get("/ai/directives")
async def api_directives_get() -> dict[str, Any]:
    return ai_config.get_directives()


@router.put("/ai/directives")
async def api_directives_put(body: DirectivesUpdate) -> dict[str, Any]:
    return ai_config.update_directives(body.data)


@router.get("/ai/prompts")
async def api_prompts_list() -> dict[str, Any]:
    return {"prompts": ai_config.list_prompts()}


@router.get("/ai/prompts/{name}")
async def api_prompt_get(name: str) -> dict[str, str]:
    return ai_config.get_prompt(name)


@router.put("/ai/prompts/{name}")
async def api_prompt_put(name: str, body: PromptUpdate) -> dict[str, str]:
    return ai_config.update_prompt(name, body.text)


@router.post("/ai/prompts/{name}/reset")
async def api_prompt_reset(name: str) -> dict[str, Any]:
    return ai_config.reset_prompt(name)


@router.get("/auth/status")
async def api_auth_status(target: str = "all") -> dict[str, Any]:
    return {"items": auth.get_auth_status(target)}


@router.post("/auth/sync-cookies")
async def api_sync_cookies(body: SyncCookiesRequest) -> dict[str, Any]:
    result = auth.sync_cookies(
        browser=body.browser,
        domains=body.domains or None,
    )
    return {
        "browser": result.browser,
        "domains_synced": result.domains_synced,
        "cookie_counts": result.cookie_counts,
        "errors": result.errors,
        "output_dir": str(result.output_dir),
    }


@router.get("/auth/paths")
async def api_auth_paths() -> dict[str, Any]:
    return auth.get_paths()


@router.get("/auth/domains")
async def api_auth_domains() -> dict[str, Any]:
    return {"domains": auth.list_domains()}


@router.get("/tools/domain/{domain}")
async def api_domain_lookup(domain: str) -> dict[str, Any]:
    return tools.lookup_domain(domain)
