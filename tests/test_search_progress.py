"""Search progress store tests."""

from osint_toolkit.pipeline.progress import get_progress, init_progress, update_progress


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
