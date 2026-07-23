"""Typed state shared across all LangGraph nodes."""
from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
    question: str
    session_id: str
    use_pdf_context: bool

    plan: dict[str, Any]

    web_results: list[dict[str, Any]]
    pdf_results: list[dict[str, Any]]

    combined_context: str
    sources: list[dict[str, Any]]

    draft: str
    critic_feedback: str
    critic_score: float
    critic_evaluations: dict
    critic_approved: bool
    retry_count: int
    final_answer: str

    next_step: str
    supervisor_reasoning: str
    
    # Adaptive Graph / Metrics
    route: str
    gemini_calls: int
    tool_calls: int
    skipped_agents: list[str]
