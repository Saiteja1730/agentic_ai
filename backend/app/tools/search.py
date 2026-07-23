from app.tools.registry import registry
from app.agents.web_agent import run_web_search
from app.rag.retriever import retrieve_relevant_chunks
from langsmith import traceable

@traceable(run_type="tool")
@registry.register
async def web_search(query: str) -> str:
    """Search the web for information using Tavily.
    
    Args:
        query: The search query string.
    """
    try:
        results = await run_web_search([query])
        if not results:
            return "No additional relevant documents were found. Please use the existing context to answer."
        
        # Format the top few results into a structured readable string
        formatted = ["Top Results:"]
        for r in results[:3]:
            formatted.append(f"Document: {r.get('title')}\nURL: {r.get('url')}\nRelevant Passage: {r.get('snippet')}\nScore: {r.get('score', 'N/A')}\n---")
            
        return "\n".join(formatted)
    except Exception as exc:
        return f"Web search failed: {exc}"

@traceable(run_type="tool")
@registry.register
async def pdf_search(query: str, session_id: str) -> str:
    """Search uploaded PDF documents for information.
    
    Args:
        query: The search query string.
        session_id: The current session ID (must be provided).
    """
    if not session_id:
        return "Error: session_id is required to search PDFs."
        
    try:
        results = await retrieve_relevant_chunks(session_id, query, top_k=3)
        if not results:
            return "No additional relevant documents were found. Please use the existing context to answer."
            
        formatted = ["Top Results:"]
        for r in results:
            formatted.append(f"Document: {r.get('filename')}\nRelevant Passage: {r.get('text')}\nScore: {r.get('score', 'N/A')}\n---")
            
        return "\n".join(formatted)
    except Exception as exc:
        return f"PDF search failed: {exc}"
