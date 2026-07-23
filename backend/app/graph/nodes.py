"""LangGraph node implementations. Each node takes the shared ResearchState,
performs its work, and returns a partial state update."""
from typing import Any

from app.agents.collector import collect_evidence
from app.agents.critic import run_critic
from app.agents.pdf_agent import run_pdf_search
from app.agents.planner import run_planner
from app.agents.web_agent import run_web_search
from app.agents.writer import run_writer
from app.agents.supervisor import run_supervisor
from app.llm.gemini import generate_text
from app.config.settings import get_settings
from app.graph.state import ResearchState
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


async def planner_node(state: ResearchState) -> dict[str, Any]:
    plan = await run_planner(state["question"])
    return {"plan": plan}


async def web_search_node(state: ResearchState) -> dict[str, Any]:
    queries = state.get("plan", {}).get("web_search_queries") or [state["question"]]
    results = await run_web_search(queries)
    return {"web_results": results}


async def pdf_search_node(state: ResearchState) -> dict[str, Any]:
    if not state.get("use_pdf_context", True):
        return {"pdf_results": []}
    queries = state.get("plan", {}).get("pdf_search_queries") or [state.get("question", "")]
    session_id = state.get("session_id", "")
    if not session_id:
        return {"pdf_results": []}
    results = await run_pdf_search(session_id, queries)
    
    if not results:
        # Zero chunk handling
        question = state.get("question", "").lower()
        pdf_keywords = [
            "this pdf", "uploaded pdf", "uploaded file", "attached file", "attached document", 
            "document", "resume", "cv", "page", "section", "chapter", "this resume", 
            "candidate", "profile", "education", "experience", "skills", "projects", "summarize"
        ]
        if any(kw in question for kw in pdf_keywords):
            # Explicit intent
            return {
                "pdf_results": [],
                "final_answer": "No relevant information was found in the uploaded document."
            }
        else:
            # Implicit intent (fallback to general)
            return {
                "pdf_results": [],
                "route": "GENERAL_SIMPLE"
            }

    return {"pdf_results": results}


async def collector_node(state: ResearchState) -> dict[str, Any]:
    combined_context, ranked_sources = await collect_evidence(
        state.get("question", ""),
        state.get("web_results", []), 
        state.get("pdf_results", [])
    )
    return {"combined_context": combined_context, "sources": ranked_sources}


async def writer_node(state: ResearchState) -> dict[str, Any]:
    draft = await run_writer(
        question=state["question"],
        combined_context=state.get("combined_context", ""),
        critic_feedback=state.get("critic_feedback"),
        previous_draft=state.get("draft"),
        route=state.get("route", "GENERAL_SIMPLE")
    )
    return {"draft": draft}


async def critic_node(state: ResearchState) -> dict[str, Any]:
    review = await run_critic(
        question=state["question"],
        combined_context=state.get("combined_context", ""),
        draft=state.get("draft", ""),
    )
    score = float(review.get("score", 0.0))
    evaluations = review.get("evaluations", {})
    feedback = review.get("feedback", "")
    
    # Threshold for approval is 80/100
    approved = score >= 80.0
    retry_count = state.get("retry_count", 0)

    update: dict[str, Any] = {
        "critic_approved": approved,
        "critic_score": score,
        "critic_evaluations": evaluations,
        "critic_feedback": feedback if not approved else "",
    }

    if approved or retry_count >= settings.MAX_CRITIC_RETRIES:
        update["final_answer"] = state.get("draft", "")
    else:
        update["retry_count"] = retry_count + 1

    return update


def route_after_critic(state: ResearchState) -> str:
    """Conditional edge: retry the writer, or finish."""
    if state.get("final_answer"):
        return "end"
    return "retry"

async def supervisor_node(state: ResearchState) -> dict[str, Any]:
    result = await run_supervisor(state)
    return result

async def direct_response_node(state: ResearchState) -> dict[str, Any]:
    question = state.get("question", "")
    prompt = f"Answer this query directly (no extensive research needed): {question}"
    answer = await generate_text(prompt, system_instruction="You are a helpful AI assistant. Be brief and direct.")
    return {"final_answer": answer}

def route_from_supervisor(state: ResearchState):
    """Conditional edge from the supervisor node."""
    step = state.get("next_step", "end")
    if step == "end":
        return "END"
    if step == "parallel_search":
        return ["web_search", "pdf_search"]
    return step
