"""Chat endpoint: runs the multi-agent research graph and streams progress."""
import json
import time

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.graph.builder import get_graph
from app.graph.router import classify_query
from app.graph.state import ResearchState
from app.schemas.schemas import ChatRequest
from app.services.session_service import get_or_create_session
from app.utils.logger import get_logger

router = APIRouter(tags=["chat"])
logger = get_logger(__name__)

_STAGE_LABELS = {
    "supervisor": "Analyzing your request",
    "direct_response": "Generating answer",
    "planner": "Creating a research plan",
    "web_search": "🌐 Searching the web",
    "pdf_search": "📄 Searching uploaded documents",
    "collector": "🔄 Merging evidence",
    "writer": "✍️ Writing final answer",
    "critic": "Reviewing the draft",
}


def _sse_event(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data)}


@router.post("/chat")
async def chat_endpoint(request: ChatRequest) -> EventSourceResponse:
    """Stream LangGraph execution events via SSE."""
    session = get_or_create_session(request.session_id)
    graph = get_graph()
    
    # Pre-classify query to conserve quota
    route = classify_query(request.question, request.use_pdf_context)
    
    # User-requested logging format
    display_route = "GENERAL" if "GENERAL" in route else "PDF" if "PDF" in route else "WEB"
    print(f"\n[Router] {display_route}", flush=True)

    initial_state: ResearchState = {
        "question": request.question,
        "use_pdf_context": request.use_pdf_context,
        "session_id": session.session_id,
        "plan": {},
        "web_results": [],
        "pdf_results": [],
        "combined_context": "",
        "sources": [],
        "draft": "",
        "final_answer": "",
        "retry_count": 0,
        "critic_approved": False,
        "critic_score": 0.0,
        "critic_evaluations": {},
        "critic_feedback": "",
        "next_step": "",
        "supervisor_reasoning": "",
        "route": route,
        "gemini_calls": 0,
        "tool_calls": 0,
        "skipped_agents": [],
    }
    config = {"configurable": {"thread_id": session.session_id}}

    async def event_generator():
        yield _sse_event("status", {"stage": "started", "message": "Planner Started..."})
        final_state: dict = {}
        try:
            start_time = time.time()
            
            async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
                if isinstance(event, dict):
                    for node_name, node_output in event.items():
                        # Explicit logs for the test expectation
                        if node_name == "pdf_search" and isinstance(node_output, dict):
                            num_chunks = len(node_output.get("pdf_results", []))
                            print(f"[Retriever] {num_chunks} chunks", flush=True)
                        elif node_name == "writer":
                            print("[Writer]", flush=True)
                        elif node_name == "direct_response":
                            print("[Direct Response] Gemini", flush=True)

                        label = _STAGE_LABELS.get(node_name, f"Running {node_name}...")
                        yield _sse_event(
                            "status",
                            {"stage": node_name, "message": label},
                        )
                        if isinstance(node_output, dict):
                            final_state.update(node_output)

            execution_time = time.time() - start_time
            print("Completed", flush=True)
            
            final_route = final_state.get("route", route)
            logger.info("Graph execution completed. Route: %s, Time: %.2fs", final_route, execution_time)

            sources = final_state.get("sources", [])
            final_answer = final_state.get("final_answer", "") or final_state.get("draft", "")
            yield _sse_event(
                "result",
                {
                    "session_id": session.session_id,
                    "final_answer": final_answer,
                    "sources": [
                        {
                            "title": s.get("title", ""),
                            "url": s.get("url"),
                            "snippet": s.get("snippet", ""),
                            "origin": s.get("origin", "web"),
                        }
                        for s in sources
                    ],
                    "retry_count": final_state.get("retry_count", 0),
                    "metrics": {
                        "route": final_route,
                        "execution_time_seconds": execution_time,
                    }
                },
            )
            yield _sse_event("status", {"stage": "completed", "message": f"Completed ({final_route} route in {execution_time:.1f}s)"})
        except Exception:  # noqa: BLE001
            logger.exception("Error while running research graph")
            yield _sse_event(
                "error",
                {
                    "status": "error",
                    "message": "An error occurred while processing your request. Please try again.",
                },
            )
            
    return EventSourceResponse(event_generator())

