"""Tests for recognition records API."""

from __future__ import annotations

import json

from osint_toolkit.ingest.likes import list_recognition_records
from osint_toolkit.storage.sqlite import connect


def test_list_recognition_records_from_events(tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_DATA_DIR", str(tmp_path))

    conn = connect()
    conn.execute(
        "INSERT INTO events (event_type, data_json) VALUES (?, ?)",
        (
            "bilibili_like",
            json.dumps(
                {"source": "bilibili", "title": "测试视频", "url": "https://www.bilibili.com/video/BV1xx", "via": "api"},
                ensure_ascii=False,
            ),
        ),
    )
    conn.execute(
        "INSERT INTO events (event_type, data_json) VALUES (?, ?)",
        (
            "zhihu_vote",
            json.dumps(
                {
                    "source": "zhihu",
                    "title": "如何学习 Python",
                    "url": "https://www.zhihu.com/question/1/answer/2",
                    "via": "voteanswers_api",
                },
                ensure_ascii=False,
            ),
        ),
    )
    conn.commit()
    conn.close()

    result = list_recognition_records(limit=10)
    assert result["count"] == 2
    assert len(result["recent"]) == 2
    assert result["summary"]["bilibili"]["like"] == 1
    assert result["summary"]["zhihu"]["vote"] == 1


def test_list_recognition_records_groups_inventory(tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_DATA_DIR", str(tmp_path))

    conn = connect()
    conn.execute(
        "INSERT INTO events (event_type, data_json) VALUES (?, ?)",
        (
            "zhihu_fav",
            json.dumps(
                {"source": "zhihu", "title": "收藏文章", "url": "https://www.zhihu.com/question/9/answer/9"},
                ensure_ascii=False,
            ),
        ),
    )
    conn.commit()
    conn.close()

    result = list_recognition_records(limit=10)
    assert result["count"] == 1
    assert len(result["inventory"]) == 1
    assert result["inventory"][0]["group"] == "inventory"
    assert result["summary_by_group"]["inventory"]["favorite"] == 1
