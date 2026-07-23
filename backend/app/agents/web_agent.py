"""Web Search Agent: queries Tavily and summarizes results with citations."""
import asyncio
from typing import Any

from tavily import AsyncTavilyClient

from app.config.settings import get_settings
from app.llm.gemini import generate_text
from app.utils.logger import get_logger
from app.utils.retry import async_retry

settings = get_settings()
logger = get_logger(__name__)

_client: AsyncTavilyClient | None = None


def get_tavily_client() -> AsyncTavilyClient:
    global _client
    if _client is None:
        _client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
    return _client


@async_retry(max_attempts=3, base_delay=1.5)
async def _search_one(query: str) -> dict[str, Any]:
    client = get_tavily_client()
    try:
        # Wrap search in a 10s timeout to ensure it doesn't hang
        result = await asyncio.wait_for(
            client.search(query=query, search_depth="advanced", max_results=5, include_answer=False), 
            timeout=10.0
        )
        return result
    except asyncio.TimeoutError:
        logger.error("Web search timed out for query: %s", query)
        raise
    except Exception as exc:
        logger.error("Web search failed for query '%s': %s", query, exc)
        raise


async def run_web_search(queries: list[str]) -> list[dict[str, Any]]:
    """Run Tavily searches for each query in parallel and return summarized,
    citation-bearing evidence items."""
    if not settings.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set; skipping web search.")
        return []

    try:
        raw_results = await asyncio.gather(*(_search_one(q) for q in queries), return_exceptions=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("Web search batch failed: %s", exc)
        return []

    evidence: list[dict[str, Any]] = []
    for query, result in zip(queries, raw_results):
        if isinstance(result, Exception):
            logger.error("Web search failed for query '%s': %s", query, result)
            continue
        for item in result.get("results", []):
            content = item.get("content", "")
            if not content:
                continue
            summary = await _summarize_snippet(query, content)
            evidence.append(
                {
                    "title": item.get("title", "Untitled"),
                    "url": item.get("url", ""),
                    "snippet": summary,
                    "origin": "web",
                    "query": query,
                }
            )
    return evidence


async def _summarize_snippet(query: str, content: str) -> str:
    prompt = (
        f"Research query: {query}\n\n"
        f"Source content:\n{content[:3000]}\n\n"
        "Summarize the parts of this source relevant to the query in 2-3 sentences. "
        "Be factual and concise."
    )
    try:
        return await generate_text(prompt, temperature=0.2, max_output_tokens=256)
    except Exception as exc:  # noqa: BLE001
        logger.error("Snippet summarization failed: %s", exc)
        return content[:400]
