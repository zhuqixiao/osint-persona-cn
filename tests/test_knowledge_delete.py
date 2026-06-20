"""Knowledge base delete and URL dedup tests."""

from __future__ import annotations

from osint_toolkit.models.intel_item import IntelItem
from osint_toolkit.storage.knowledge import (
    delete_item,
    delete_items,
    recall,
    save_item,
)


def _make_item(item_id: str = "item-1", url: str = "https://example.com/1", title: str = "Title 1") -> IntelItem:
    item = IntelItem(source="web", type="article", url=url, title=title, content="content")
    item.id = item_id
    return item


def test_delete_item_existing(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.storage.sqlite.get_db_path", lambda: tmp_path / "knowledge.db")
    item = _make_item()
    save_item(item)
    assert delete_item(item.id) is True
    assert recall("Title", limit=5) == []


def test_delete_item_nonexistent(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.storage.sqlite.get_db_path", lambda: tmp_path / "knowledge.db")
    assert delete_item("nonexistent-id") is False


def test_delete_items_batch(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.storage.sqlite.get_db_path", lambda: tmp_path / "knowledge.db")
    items = [_make_item(f"i-{i}", f"https://example.com/{i}", f"Title {i}") for i in range(3)]
    for item in items:
        save_item(item)
    deleted = delete_items([items[0].id, items[2].id, "nonexistent"])
    assert deleted == 2
    remaining = recall("Title", limit=10)
    assert len(remaining) == 1
    assert remaining[0].id == items[1].id


def test_save_item_url_dedup(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.storage.sqlite.get_db_path", lambda: tmp_path / "knowledge.db")
    item_a = _make_item("a-1", "https://example.com/shared", "First Save")
    save_item(item_a)
    item_b = _make_item("b-1", "https://example.com/shared", "Second Save")
    save_item(item_b)
    results = recall("Second", limit=5)
    assert len(results) == 1
    assert results[0].id == "a-1"
    assert results[0].title == "Second Save"


def test_recall_fts_error_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("osint_toolkit.storage.sqlite.get_db_path", lambda: tmp_path / "knowledge.db")
    item = _make_item(title="Fallback Test Content")
    save_item(item)
    results = recall("Fallback", limit=5)
    assert len(results) >= 1
    assert any("Fallback" in r.title for r in results)
