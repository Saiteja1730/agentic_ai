"""Evidence Collector Agent: merges, de-duplicates, and ranks web + PDF evidence."""
from difflib import SequenceMatcher
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

_SIMILARITY_THRESHOLD = 0.85


def _is_duplicate(a: str, b: str) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= _SIMILARITY_THRESHOLD


def _deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    for item in items:
        snippet = item.get("snippet", "")
        if any(_is_duplicate(snippet, existing.get("snippet", "")) for existing in unique):
            continue
        unique.append(item)
    return unique


from app.rag.reranker import GeminiRelevanceReranker

_reranker = None

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = GeminiRelevanceReranker()
    return _reranker


async def collect_evidence(
    question: str,
    web_results: list[dict[str, Any]],
    pdf_results: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Merge web + PDF evidence, remove near-duplicates, rerank using Cross-Encoder,
    and produce a combined context string plus a structured source list."""
    combined = _deduplicate([*web_results, *pdf_results])
    
    reranker = get_reranker()
    ranked = await reranker.rerank(question, combined, top_k=15)

    context_lines = []
    for idx, item in enumerate(ranked, start=1):
        origin_label = "PDF" if item.get("origin") == "pdf" else "Web"
        context_lines.append(
            f"[{idx}] ({origin_label}) {item.get('title', 'Source')}: {item.get('snippet', item.get('text', ''))}"
        )
        
    if not web_results and pdf_results:
        context_lines.append("\n[SYSTEM NOTE]: The live web search failed or returned no results. Proceed with the PDF evidence and explicitly state that live external information could not be retrieved.")
    elif not pdf_results and web_results:
        context_lines.append("\n[SYSTEM NOTE]: The PDF search failed or returned no relevant results. Proceed with the Web evidence and explicitly state that no relevant uploaded document information was found.")
        
    combined_context = "\n\n".join(context_lines)

    logger.info("Collected %s unique evidence items (from %s raw)", len(ranked), len(web_results) + len(pdf_results))
    return combined_context, ranked
