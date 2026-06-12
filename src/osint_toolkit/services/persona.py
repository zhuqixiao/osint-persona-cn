"""Persona 服务 / Persona service."""

from __future__ import annotations

from typing import Any

from osint_toolkit.persona.builder import build_persona_draft
from osint_toolkit.persona.store import (
    list_versions,
    load_mental_model,
    load_persona_brief,
    mental_model_path,
    rollback_version,
)


def show_persona() -> dict[str, Any]:
    versions = [p.stem.replace("mental_model.", "") for p in list_versions()]
    return {
        "mental_model": load_mental_model(),
        "brief": load_persona_brief(),
        "mental_model_path": str(mental_model_path()),
        "versions": versions,
    }


def build_persona(*, review: bool = False) -> dict[str, Any]:
    draft = build_persona_draft()
    result = {
        "version": draft["mental_model"].get("version"),
        "mental_model_path": str(mental_model_path()),
        "review": review,
    }
    return result


def rollback_persona(version: int) -> dict[str, Any]:
    ok = rollback_version(version)
    return {"ok": ok, "version": version}
