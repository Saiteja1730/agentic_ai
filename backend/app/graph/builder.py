"""Builds the LangGraph StateGraph wiring together all research agents."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    collector_node,
    critic_node,
    pdf_search_node,
    planner_node,
    route_after_critic,
    web_search_node,
    writer_node,
    supervisor_node,
    direct_response_node,
    route_from_supervisor,
)
from app.graph.state import ResearchState

_checkpointer = MemorySaver()
_compiled_graph = None


def build_graph():
    """Construct and compile the multi-agent research StateGraph."""
    graph = StateGraph(ResearchState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("direct_response", direct_response_node)
    graph.add_node("planner", planner_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("pdf_search", pdf_search_node)
    graph.add_node("collector", collector_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)

    # Smart Routing logic at the entry of the graph
    def route_entry(state: ResearchState) -> str:
        route = state.get("route", "COMPLEX_RESEARCH")
        if route == "GENERAL_SIMPLE":
            return "direct_response" 
        elif route == "PDF_SIMPLE":
            return "pdf_search"
        elif route == "WEB_SIMPLE":
            return "web_search"
        return "supervisor" # COMPLEX goes to supervisor which kicks off planner

    graph.set_conditional_entry_point(
        route_entry,
        {
            "supervisor": "supervisor",
            "pdf_search": "pdf_search",
            "web_search": "web_search",
            "direct_response": "direct_response"
        }
    )

    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "planner": "planner",
            "web_search": "web_search",
            "pdf_search": "pdf_search",
            "writer": "writer",
            "critic": "critic",
            "collector": "collector",
            "direct_response": "direct_response",
            "END": END,
        },
    )

    # Simplified routes bypass planner and supervisor on the way back
    def route_after_search(state: ResearchState) -> str:
        if state.get("final_answer"):
            return "END"
        if state.get("route") == "GENERAL_SIMPLE":
            return "direct_response"
        if state.get("route") in ["PDF_SIMPLE", "WEB_SIMPLE"]:
            return "collector"
        return "supervisor"

    graph.add_edge("planner", "supervisor")
    graph.add_conditional_edges("web_search", route_after_search, {"collector": "collector", "supervisor": "supervisor", "END": END, "direct_response": "direct_response"})
    graph.add_conditional_edges("pdf_search", route_after_search, {"collector": "collector", "supervisor": "supervisor", "END": END, "direct_response": "direct_response"})
    
    def route_after_collector(state: ResearchState) -> str:
        if state.get("route") in ["PDF_SIMPLE", "WEB_SIMPLE"]:
            return "writer"
        return "supervisor"
        
    graph.add_conditional_edges("collector", route_after_collector, {"writer": "writer", "supervisor": "supervisor"})
    graph.add_edge("direct_response", END)
    
    # Critic has its own retry loop or returns to supervisor
    def route_after_writer(state: ResearchState) -> str:
        from app.config.settings import get_settings
        if state.get("route") in ["GENERAL_SIMPLE", "PDF_SIMPLE", "WEB_SIMPLE"] or get_settings().MODE == "development":
            return "END"
        return "critic"
        
    graph.add_conditional_edges("writer", route_after_writer, {"critic": "critic", "END": END})
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"retry": "writer", "end": "supervisor"},
    )

    return graph.compile(checkpointer=_checkpointer)


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def get_graph_description() -> dict:
    """Static description of the graph topology for the /graph endpoint."""
    nodes = ["supervisor", "direct_response", "planner", "web_search", "pdf_search", "collector", "writer", "critic"]
    edges = [
        {"from": "supervisor", "to": "planner", "label": "routing"},
        {"from": "supervisor", "to": "web_search", "label": "routing"},
        {"from": "supervisor", "to": "pdf_search", "label": "routing"},
        {"from": "supervisor", "to": "collector", "label": "routing"},
        {"from": "supervisor", "to": "writer", "label": "routing"},
        {"from": "supervisor", "to": "critic", "label": "routing"},
        {"from": "supervisor", "to": "direct_response", "label": "routing"},
        {"from": "planner", "to": "supervisor"},
        {"from": "web_search", "to": "supervisor"},
        {"from": "pdf_search", "to": "supervisor"},
        {"from": "collector", "to": "supervisor"},
        {"from": "direct_response", "to": "supervisor"},
        {"from": "writer", "to": "critic"},
        {"from": "critic", "to": "writer", "label": "retry (score < 80)"},
        {"from": "critic", "to": "supervisor", "label": "approved (score >= 80)"},
    ]
    mermaid = (
        "graph TD\n"
        "  supervisor[Supervisor Agent]\n"
        "  supervisor --> planner[Planner Agent]\n"
        "  supervisor --> web_search[Web Search Agent]\n"
        "  supervisor --> pdf_search[PDF Research Agent]\n"
        "  supervisor --> collector[Evidence Collector]\n"
        "  supervisor --> writer[Writer Agent]\n"
        "  supervisor --> critic[Critic Agent]\n"
        "  supervisor --> direct_response[Direct Response]\n"
        "  planner --> supervisor\n"
        "  web_search --> supervisor\n"
        "  pdf_search --> supervisor\n"
        "  collector --> supervisor\n"
        "  direct_response --> supervisor\n"
        "  writer --> critic\n"
        "  critic -- retry (score < 80) --> writer\n"
        "  critic -- approved (score >= 80) --> supervisor\n"
    )
    return {"nodes": nodes, "edges": edges, "mermaid": mermaid}
