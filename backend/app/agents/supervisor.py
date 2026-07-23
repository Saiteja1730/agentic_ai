"""Supervisor Agent: dynamically routes the research workflow."""
import json
from typing import Any

from app.llm.gemini import generate_with_tools
from app.tools.registry import registry
import app.tools.search  # ensure registered
import app.tools.utilities  # ensure registered
from app.utils.logger import get_logger
from app.graph.state import ResearchState

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = """You are the Supervisor Agent of a research workflow.
Your job is to inspect the current state and decide the next step.
You have access to tools (web search, calculator, date, etc.). You may use these tools to gather quick information before making a routing decision.

CRITICAL INSTRUCTIONS FOR TOOL USAGE:
- Use tools only when necessary.
- Never repeatedly call the same tool with the same or similar arguments.
- After sufficient evidence is collected, answer directly.
- Prefer answering instead of searching again. Do not keep searching for tiny improvements.
- If a tool returns no results, do not keep trying slightly different queries. Use the existing information.

Possible routing destinations:
- "planner": Create a research plan (only do this if no plan exists and complex research is needed).
- "parallel_search": Run both web and PDF search in parallel (if no search results exist and both are needed).
- "web_search": Run web search (only if web_results are empty and web search is needed).
- "pdf_search": Run PDF search (only if pdf_results are empty, use_pdf_context is true, and PDF search is needed).
- "collector": Aggregate search results (only do this if search results exist but combined_context is empty).
- "writer": Write the draft report (only do this if combined_context exists but draft is empty, or if critic requested retry).
- "critic": Review the draft (only do this if draft exists but needs review).
- "direct_response": Generate an immediate answer without external search (for simple greetings or basic questions).
- "end": The research is complete and the final answer is ready.

Once you are ready to make a decision, respond with ONLY valid JSON in this exact shape:
{
  "next_step": "<one of the destinations above>",
  "reasoning": "<brief explanation of why this step is next>"
}"""

async def run_supervisor(state: ResearchState) -> dict[str, Any]:
    question = state.get("question", "")
    use_pdf = state.get("use_pdf_context", True)
    has_plan = bool(state.get("plan"))
    has_web_results = bool(state.get("web_results"))
    has_pdf_results = bool(state.get("pdf_results"))
    has_context = bool(state.get("combined_context"))
    has_draft = bool(state.get("draft"))
    has_feedback = bool(state.get("critic_feedback"))
    is_approved = state.get("critic_approved", False)
    has_final_answer = bool(state.get("final_answer"))
    session_id = state.get("session_id", "default")

    if has_final_answer or is_approved:
        return {"next_step": "end", "supervisor_reasoning": "Final answer is ready."}

    # Simplify state representation to help LLM reason
    state_summary = (
        f"Session ID: {session_id}\n"
        f"Question: {question}\n"
        f"Use PDF context: {use_pdf}\n"
        f"Has Plan: {has_plan}\n"
        f"Has Web Results: {has_web_results}\n"
        f"Has PDF Results: {has_pdf_results}\n"
        f"Has Combined Context: {has_context}\n"
        f"Has Draft: {has_draft}\n"
        f"Has Critic Feedback: {has_feedback}\n"
        f"Critic Approved: {is_approved}\n"
    )

    # Determine limits based on route
    route = state.get("route", "COMPLEX_RESEARCH")
    max_calls = 2 if route in ["GENERAL_SIMPLE", "PDF_SIMPLE", "WEB_SIMPLE"] else 6

    prompt = f"Current state summary:\n{state_summary}\n\nYou may use tools if you need to quickly check something. What is the next step?"
    
    raw = await generate_with_tools(
        prompt=prompt,
        tools=registry.get_all_tools(),
        system_instruction=SYSTEM_INSTRUCTION,
        require_json=True,
        max_total_calls=max_calls
    )
    
    result = {}
    if raw:
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from Supervisor response.")

    if not result or "next_step" not in result:
        logger.warning("Supervisor returned malformed response; defaulting to end.")
        result = {"next_step": "end", "reasoning": "Malformed supervisor output."}
        
    next_step = result.get("next_step")
    reasoning = result.get("reasoning", "")
    
    # Fallback/sanity checks
    valid_steps = {"planner", "web_search", "pdf_search", "parallel_search", "collector", "writer", "critic", "direct_response", "end"}
    if next_step not in valid_steps:
        logger.warning("Invalid next_step from supervisor: %s. Defaulting to end.", next_step)
        next_step = "end"
        
    logger.info("Supervisor decision: %s - %s", next_step, reasoning)
    return {"next_step": next_step, "supervisor_reasoning": reasoning}
