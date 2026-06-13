"""Search progress and collect URL helpers."""

from osint_toolkit.pipeline.progress import get_progress, init_progress, update_progress
from osint_toolkit.services.search import _collect_target_url, _source_label


def test_search_progress_updates():
    run_id = "test-run-progress"
    init_progress(run_id)
    update_progress(run_id, "collect_all", detail="B站 · 测试（1/3）")
    state = get_progress(run_id)
    assert state is not None
    assert state["phase"] == "collect_all"
    assert "B站" in state["detail"]
    update_progress(
        run_id,
        "dedup",
        mark_completed={"step": "collect_all", "duration_ms": 1200, "summary": "12 items", "status": "ok"},
    )
    state = get_progress(run_id)
    assert state["phase"] == "dedup"
    assert len(state["completed_steps"]) == 1


def test_search_progress_collect_fields():
    run_id = "test-collect-fields"
    init_progress(run_id)
    update_progress(
        run_id,
        "collect_all",
        detail="B站 · 测试（1/3）",
        collect_done=1,
        collect_total=3,
        items_found=5,
        eta_sec=42,
        current_url="https://www.bilibili.com/video/BV1",
        recent_urls=[{"url": "https://example.com/a", "title": "示例"}],
    )
    state = get_progress(run_id)
    assert state["collect_done"] == 1
    assert state["eta_sec"] == 42
    assert state["items_found"] == 5
    assert state["recent_urls"][0]["title"] == "示例"


def test_collect_target_url():
    url = _collect_target_url("bilibili", "国模 AI")
    assert "search.bilibili.com" in url
    assert _source_label("bilibili") == "B站"
