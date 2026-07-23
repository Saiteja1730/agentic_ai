"""Gemini API-based relevance reranker for evidence chunks."""
from typing import Any

from app.llm.gemini import generate_json
from app.utils.logger import get_logger
from langsmith import traceable

logger = get_logger(__name__)

SYSTEM_INSTRUCTION = """You are a precise document ranking assistant.
Your task is to rank the relevance of a list of documents to a user's research query.
Review the documents and output a JSON list of objects containing the index of the document (0-based), a relevance score from 0 to 100, and a brief reasoning for the score.

Respond ONLY with valid JSON in the exact shape:
{
  "rankings": [
    {
      "index": <int>,
      "score": <float>,
      "reasoning": "<brief explanation>"
    },
    ...
  ]
}"""


class GeminiRelevanceReranker:
    """Reranks retrieved documents using Gemini to assess relevance to the query."""
    
    @traceable(run_type="llm")
    async def rerank(self, query: str, documents: list[dict[str, Any]], top_k: int = 15) -> list[dict[str, Any]]:
        """Asynchronously reranks documents using Gemini API."""
        if not documents:
            return []
            
        logger.info("Reranking %d documents using Gemini API...", len(documents))
        
        # Format documents with their original indices
        formatted_docs = []
        for idx, doc in enumerate(documents):
            text = doc.get("snippet") or doc.get("text") or ""
            formatted_docs.append(f"Document [{idx}]: {text}")
            
        docs_text = "\n\n".join(formatted_docs)
        prompt = (
            f"User Query: {query}\n\n"
            f"Documents to rank:\n{docs_text}\n\n"
            "Analyze and rank the documents based on their relevance to the query."
        )
        
        try:
            result = await generate_json(prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.1)
            rankings = result.get("rankings", [])
            
            # Map rankings back to the original documents
            ranked_docs = []
            for rank in rankings:
                idx = rank.get("index")
                if idx is not None and 0 <= idx < len(documents):
                    doc = documents[idx]
                    doc["score"] = float(rank.get("score", 0.0))
                    doc["rerank_reasoning"] = rank.get("reasoning", "")
                    ranked_docs.append(doc)
                    
            # Fallback if Gemini missed some documents or returned invalid indices
            # Include missing documents at the end with score 0.0
            seen_indices = {rank.get("index") for rank in rankings if rank.get("index") is not None}
            for idx, doc in enumerate(documents):
                if idx not in seen_indices:
                    doc["score"] = 0.0
                    ranked_docs.append(doc)
                    
            # Sort by score descending
            ranked = sorted(ranked_docs, key=lambda x: x.get("score", 0.0), reverse=True)
            return ranked[:top_k]
            
        except Exception as exc:
            logger.error("Gemini relevance reranking failed: %s. Returning unranked results.", exc)
            return documents[:top_k]
