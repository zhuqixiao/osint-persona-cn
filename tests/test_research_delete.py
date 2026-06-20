"""Research tree delete and rename tests."""

from __future__ import annotations

import pytest

from osint_toolkit.research.tree import (
    add_node,
    create_tree,
    delete_node,
    delete_tree,
    load_tree,
    rename_tree,
)


def test_delete_node(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("Test")
    root_id = tree["nodes"][0]["id"]
    note = add_node(tree["id"], parent_id=root_id, kind="note", title="My Note")
    child = add_node(tree["id"], parent_id=note["id"], kind="note", title="Child Note")
    deleted = delete_node(tree["id"], note["id"])
    assert deleted["id"] == note["id"]
    reloaded = load_tree(tree["id"])
    node_ids = {n["id"] for n in reloaded["nodes"]}
    assert note["id"] not in node_ids
    assert child["id"] not in node_ids
    assert root_id in node_ids


def test_delete_root_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("Test")
    root_id = tree["nodes"][0]["id"]
    with pytest.raises(ValueError, match="cannot delete root"):
        delete_node(tree["id"], root_id)


def test_delete_node_nonexistent(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("Test")
    with pytest.raises(FileNotFoundError):
        delete_node(tree["id"], "nonexistent")


def test_delete_tree(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("To Delete")
    delete_tree(tree["id"])
    with pytest.raises(FileNotFoundError):
        load_tree(tree["id"])


def test_delete_tree_nonexistent(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    with pytest.raises(FileNotFoundError):
        delete_tree("nonexistent")


def test_rename_tree(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.research.tree.get_data_dir", lambda: tmp_path)
    tree = create_tree("Old Title")
    renamed = rename_tree(tree["id"], "New Title")
    assert renamed["title"] == "New Title"
    reloaded = load_tree(tree["id"])
    assert reloaded["title"] == "New Title"
