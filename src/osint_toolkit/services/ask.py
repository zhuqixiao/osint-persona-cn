"""追问服务 / Ask service."""

from __future__ import annotations

import json
from typing import Any

from osint_toolkit.ai.client import DeepSeekClient
from osint_toolkit.services.runs import show_run


def ask_question(question: str, *, run_id: str | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if run_id:
        try:
            context = show_run(run_id)
        except FileNotFoundError:
            context = {"error": f"run not found: {run_id}"}
    client = DeepSeekClient()
    answer = client.chat(
        messages=[
            {"role": "system", "content": "你是个人情报助手，基于给定搜索上下文回答追问。"},
            {
                "role": "user",
                "content": f"上下文:{json.dumps(context, ensure_ascii=False)[:4000]}\n问题:{question}",
            },
        ]
    )
    return {"question": question, "answer": answer, "run_id": run_id}
