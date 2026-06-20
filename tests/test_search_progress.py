"""Search progress, cancel, and job progress helpers."""

import pytest

from osint_toolkit.models.intel_item import IntelItem
from osint_toolkit.pipeline.job_progress import FULL_SYNC_PHASES, init_full_sync_progress
from osint_toolkit.pipeline.progress import (
    JobCancelled,
    check_cancelled,
    clear_progress,
    get_progress,
    init_progress,
    request_cancel,
    update_progress,
)
from osint_toolkit.services.search import _collect_target_url, _preview_item, _source_label


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
    clear_progress(run_id)


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
    clear_progress(run_id)


def test_search_progress_partial_items_dedup():
    run_id = "test-partial"
    init_progress(run_id)
    update_progress(
        run_id,
        "collect_all",
        partial_items_append=[{"id": "a1", "title": "第一条", "url": "https://a", "source": "bilibili"}],
    )
    update_progress(
        run_id,
        "collect_all",
        partial_items_append=[
            {"id": "a1", "title": "第一条", "url": "https://a", "source": "bilibili"},
            {"id": "a2", "title": "第二条", "url": "https://b", "source": "zhihu"},
        ],
    )
    state = get_progress(run_id)
    assert len(state["partial_items"]) == 2
    assert state["items_found"] == 2
    clear_progress(run_id)


def test_search_cancel_raises():
    run_id = "test-cancel"
    init_progress(run_id)
    request_cancel(run_id)
    with pytest.raises(JobCancelled):
        check_cancelled(run_id)
    clear_progress(run_id)


def test_full_sync_progress_init():
    job_id = "test-full-sync"
    init_full_sync_progress(job_id)
    state = get_progress(job_id)
    assert state is not None
    assert state["step_total"] == len(FULL_SYNC_PHASES)
    assert state["step_done"] == 0
    clear_progress(job_id)


def test_preview_item():
    item = IntelItem(id="x1", source="bilibili", type="video", title="测试标题", url="https://example.com")
    preview = _preview_item(item)
    assert preview["id"] == "x1"
    assert preview["source"] == "bilibili"
    assert preview["title"] == "测试标题"


def test_collect_target_url():
    url = _collect_target_url("bilibili", "国模 AI")
    assert "search.bilibili.com" in url
    assert _source_label("bilibili") == "B站"
