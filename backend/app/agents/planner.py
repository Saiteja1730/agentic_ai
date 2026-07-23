"""Planner Agent: breaks the user question into a structured research plan."""
import json
from typing import Any

from app.llm.gemini import generate_with_tools
from app.tools.registry import registry
import app.tools.search  # ensure registered
import app.tools.utilities  # ensure registered
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = """You are a meticulous research planner.
You have access to tools (e.g. web search, date, calculator) to help you gather initial context before finalizing your plan.
Once you are ready, produce a JSON research plan with this exact shape:
{
  "objective": "<one sentence restatement of the goal>",
  "sub_questions": ["<question 1>", "<question 2>", "..."],
  "web_search_queries": ["<query 1>", "<query 2>", "..."],
  "pdf_search_queries": ["<query 1>", "<query 2>", "..."]
}
Keep sub_questions to 2-4 items. Keep each query list to 2-4 concise search queries.
Respond with ONLY valid JSON, no markdown fences, no commentary."""


async def run_planner(question: str) -> dict[str, Any]:
    prompt = f"Research question: {question}"
    
    raw = await generate_with_tools(
        prompt=prompt,
        tools=registry.get_all_tools(),
        system_instruction=SYSTEM_INSTRUCTION,
        require_json=True
    )

    plan = {}
    if raw:
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Planner response: %s", raw[:500])

    if not plan or "web_search_queries" not in plan:
        logger.warning("Planner returned malformed plan; using fallback plan.")
        plan = {
            "objective": question,
            "sub_questions": [question],
            "web_search_queries": [question],
            "pdf_search_queries": [question],
        }
    return plan
