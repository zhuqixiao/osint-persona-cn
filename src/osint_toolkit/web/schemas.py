"""Web API 模型 / Web API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    sources: list[str] = Field(default_factory=lambda: ["zhihu", "bilibili", "web"])
    limit: int = 10
    digest: bool = False
    trace: bool = True
    profile: str = "default"
    ai_instruct: str = ""
    no_ai: bool = False
    no_simulate: bool = False
    disabled_ai_steps: list[str] = Field(default_factory=list)
    deep_top: int = 0


class SaveRequest(BaseModel):
    url: str
    with_comments: bool = False
    no_ai: bool = False


class FeedbackRequest(BaseModel):
    target_id: str
    rating: str
    reason: str = ""
    run_id: str | None = None
    step: str | None = None


class AskRequest(BaseModel):
    question: str
    run_id: str | None = None


class PersonaRollbackRequest(BaseModel):
    version: int


class IngestBrowserRequest(BaseModel):
    since_days: int = 90


class SyncCookiesRequest(BaseModel):
    browser: str | None = None
    domains: list[str] = Field(default_factory=list)


class DirectivesUpdate(BaseModel):
    data: dict[str, Any]


class PromptUpdate(BaseModel):
    text: str
