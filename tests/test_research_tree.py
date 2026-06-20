"""Research tree tests."""

from __future__ import annotations

import json

from osint_toolkit.research.tree import (
    add_node,
    attach_search_node,
    create_tree,
    load_tree,
    save_tree,
    tree_to_markmap,
    update_search_node_status,
)


def test_create_tree_and_add_search_node(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("MCP 协议", query="MCP")
    root_id = tree["nodes"][0]["id"]
    node = attach_search_node(
        tree["id"],
        parent_node_id=root_id,
        run_id="run-abc",
        query="MCP",
    )
    assert node["kind"] == "search"
    assert node["run_id"] == "run-abc"
    loaded = load_tree(tree["id"])
    assert len(loaded["nodes"]) == 2


def test_update_search_node_status(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("测试")
    root_id = tree["nodes"][0]["id"]
    attach_search_node(tree["id"], parent_node_id=root_id, run_id="r1", query="q")
    update_search_node_status(tree["id"], "r1", status="done")
    loaded = load_tree(tree["id"])
    search_nodes = [n for n in loaded["nodes"] if n["kind"] == "search"]
    assert search_nodes[0]["meta"]["status"] == "done"


def test_tree_to_markmap(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("根主题")
    root_id = tree["nodes"][0]["id"]
    add_node(tree["id"], parent_id=root_id, kind="note", title="笔记", payload="内容")
    md = tree_to_markmap(load_tree(tree["id"]))
    assert "根主题" in md
    assert "笔记" in md


def test_save_tree_optimistic_concurrency(tmp_path, monkeypatch):
    """乐观并发：基于 updated_at 检测并发覆盖。"""
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("并发")
    base_updated = tree["updated_at"]
    # 模拟另一写入：直接保存一次，刷新 updated_at
    tree["title"] = "并发-v2"
    save_tree(tree)
    # 现在用陈旧的 expected_updated_at 再保存应失败
    tree["title"] = "并发-v3-stale"
    try:
        save_tree(tree, expected_updated_at=base_updated)
        raised = False
    except FileNotFoundError:
        raised = True
    assert raised, "expected FileNotFoundError on concurrent save"


def test_save_tree_atomic_no_truncated_file(tmp_path, monkeypatch):
    """save_tree 用 temp+rename，保存后文件是合法 JSON。"""
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("原子")
    root_id = tree["nodes"][0]["id"]
    add_node(tree["id"], parent_id=root_id, kind="note", title="笔记", payload="内容")
    path = tmp_path / "research" / "trees" / f"{tree['id']}.json"
    raw = path.read_text(encoding="utf-8")
    # 必须是完整 JSON（原子写入后不会截断）
    parsed = json.loads(raw)
    assert parsed["title"] == "原子"
    assert len(parsed["nodes"]) == 2

