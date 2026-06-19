"""Source notice consolidation tests."""

from __future__ import annotations

from osint_toolkit.utils.source_notices import consolidate_source_notices


def test_exact_duplicate_warnings_merged_with_count():
    warns = [
        {"source": "github", "warning": "GitHub API 失败: Server disconnected", "query": "q1"},
        {"source": "github", "warning": "GitHub API 失败: Server disconnected", "query": "q2"},
        {"source": "github", "warning": "GitHub API 失败: Server disconnected", "query": "q3"},
    ]
    out = consolidate_source_notices(warns)
    assert len(out) == 1
    assert "共 3 次" in out[0]["warning"]
    assert out[0]["source"] == "github"


def test_different_api_failures_same_source_merged():
    warns = [
        {"source": "github", "warning": "GitHub API 失败: Server disconnected without sending a response."},
        {"source": "github", "warning": "GitHub API 失败: Server disconnected without sending a response."},
        {"source": "github", "warning": "GitHub API 失败: peer closed connection without sending complete message body"},
    ]
    out = consolidate_source_notices(warns)
    assert len(out) == 1
    assert "多次失败" in out[0]["warning"] or "共" in out[0]["warning"]
    assert out[0]["source"] == "github"


def test_unrelated_warnings_preserved():
    warns = [
        {"source": "weixin", "warning": "已跳过：未登录，将用搜索引擎摘要兜底"},
        {"source": "*", "warning": "已采集足够相关内容 (73 条)，提前结束"},
    ]
    out = consolidate_source_notices(warns)
    assert len(out) == 2
    assert out[0]["source"] == "weixin"
    assert out[1]["source"] == "*"


def test_consolidate_errors():
    errors = [
        {"source": "github", "error": "GitHub API 失败: timeout", "query": "a"},
        {"source": "github", "error": "GitHub API 失败: timeout", "query": "b"},
    ]
    out = consolidate_source_notices(errors, text_key="error")
    assert len(out) == 1
    assert "共 2 次" in out[0]["error"]
