"""Browser sync page list tests."""

from osint_toolkit.ingest.browser_sync import build_sync_pages


def test_zhihu_only_pages():
    """知乎 probe 页已启用：应生成动态/收藏/回答/文章 4 个页面。"""
    pages = build_sync_pages(platforms=("zhihu",), zhihu_token="sankichu")
    assert len(pages) == 4
    urls = [p["url"] for p in pages]
    assert any("people/sankichu/activities" in u for u in urls)
    assert any("people/sankichu/collections" in u for u in urls)
    assert any("people/sankichu/answers" in u for u in urls)
    assert any("people/sankichu/posts" in u for u in urls)


def test_bilibili_only_pages():
    pages = build_sync_pages(platforms=("bilibili",), bilibili_mid="32823281")
    assert len(pages) == 5
    assert any("account/history" in p["url"] for p in pages)
    assert any("/dynamic" in p["url"] for p in pages)


def test_empty_without_tokens():
    assert build_sync_pages(platforms=("bilibili", "zhihu")) == []
