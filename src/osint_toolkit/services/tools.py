"""工具服务 / Utility services."""

from __future__ import annotations

from typing import Any

from osint_toolkit.collectors.domain import collect_domain_info


def lookup_domain(domain: str) -> dict[str, Any]:
    return collect_domain_info(domain)
