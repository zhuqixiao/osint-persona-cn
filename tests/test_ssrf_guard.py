"""SSRF 防护测试."""

from __future__ import annotations

import pytest

from osint_toolkit.http.ssrf import SSRFError, assert_loopback_url, assert_public_http_url


def test_blocks_loopback():
    with pytest.raises(SSRFError):
        assert_public_http_url("http://127.0.0.1:8787/api/auth/status")


def test_blocks_file_scheme():
    with pytest.raises(SSRFError):
        assert_public_http_url("file:///etc/passwd")


def test_allows_public_https():
    assert assert_public_http_url("https://example.com/article") == "https://example.com/article"


def test_assert_loopback_allows_localhost():
    assert assert_loopback_url("http://127.0.0.1:9222/json/version") == "http://127.0.0.1:9222/json/version"
    assert assert_loopback_url("http://localhost:9222/") == "http://localhost:9222/"


def test_assert_loopback_blocks_link_local_metadata():
    """169.254.169.254（云元数据服务）必须被拒绝，即使用于 CDP 场景。"""
    with pytest.raises(SSRFError):
        assert_loopback_url("http://169.254.169.254/latest/meta-data/")


def test_assert_loopback_blocks_public_and_private():
    with pytest.raises(SSRFError):
        assert_loopback_url("https://example.com/")
    with pytest.raises(SSRFError):
        assert_loopback_url("http://10.0.0.1/")


def test_assert_loopback_blocks_non_http():
    with pytest.raises(SSRFError):
        assert_loopback_url("file:///etc/passwd")

