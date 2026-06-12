"""AI 配置服务 / AI configuration service."""

from __future__ import annotations

from typing import Any

from osint_toolkit.ai.prompt_loader import (
    BUILTIN_PROMPTS,
    load_prompt,
    reset_user_prompt,
    save_user_prompt,
)
from osint_toolkit.ai.steering import load_directives, save_directives


def get_directives() -> dict[str, Any]:
    return load_directives()


def update_directives(data: dict[str, Any]) -> dict[str, Any]:
    save_directives(data)
    return load_directives()


def list_prompts() -> list[dict[str, str]]:
    return [{"name": name, "source": load_prompt(name)[1]} for name in BUILTIN_PROMPTS]


def get_prompt(name: str) -> dict[str, str]:
    text, source = load_prompt(name)
    return {"name": name, "text": text, "source": source}


def update_prompt(name: str, text: str) -> dict[str, str]:
    save_user_prompt(name, text)
    return get_prompt(name)


def reset_prompt(name: str) -> dict[str, Any]:
    ok = reset_user_prompt(name)
    if ok:
        return {"ok": True, "prompt": get_prompt(name)}
    return {"ok": False, "message": "无用户覆盖"}
