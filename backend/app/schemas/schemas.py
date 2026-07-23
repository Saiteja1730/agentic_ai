"""Pydantic v2 schemas for request/response validation."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's research question")
    session_id: Optional[str] = Field(default=None, description="Existing session id, if any")
    use_pdf_context: bool = Field(default=True, description="Whether to search uploaded PDFs")


class Source(BaseModel):
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = None
    origin: Literal["web", "pdf"]


class ChatResponse(BaseModel):
    session_id: str
    final_answer: str
    sources: list[Source] = Field(default_factory=list)
    retry_count: int = 0


class StreamEvent(BaseModel):
    event: str
    data: dict[str, Any] = Field(default_factory=dict)


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    session_id: str


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    qdrant_connected: bool


class GraphResponse(BaseModel):
    nodes: list[str]
    edges: list[dict[str, str]]
    mermaid: str
