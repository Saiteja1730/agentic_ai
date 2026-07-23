"""Modular retrievers: Dense, BM25, and Hybrid (RRF)."""
import asyncio
from abc import ABC, abstractmethod
from typing import Any

from rank_bm25 import BM25Okapi

from app.rag.embeddings import embed_query
from app.rag.qdrant_store import search as qdrant_search, fetch_all_session_chunks


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: str, session_id: str, top_k: int) -> list[dict[str, Any]]:
        """Retrieve top_k chunks for the query within the given session."""
        pass


class DenseRetriever(BaseRetriever):
    """Semantic vector search using Qdrant."""
    async def retrieve(self, query: str, session_id: str, top_k: int) -> list[dict[str, Any]]:
        from app.config.settings import get_settings
        settings = get_settings()
        
        query_vector = await embed_query(query)
        if not query_vector:
            return []
            
        results = await qdrant_search(query_vector, session_id, top_k=top_k)
        
        # Retrieval Confidence Check
        # Only keep chunks above the configured threshold
        filtered = [r for r in results if r.get("score", 0) >= settings.RETRIEVAL_THRESHOLD]
        return filtered


class BM25Retriever(BaseRetriever):
    """Lexical keyword search using BM25."""
    async def retrieve(self, query: str, session_id: str, top_k: int) -> list[dict[str, Any]]:
        chunks = await fetch_all_session_chunks(session_id)
        if not chunks:
            return []

        # Tokenize documents
        corpus_tokens = [chunk["text"].lower().split() for chunk in chunks]
        query_tokens = query.lower().split()
        
        bm25 = BM25Okapi(corpus_tokens)
        scores = bm25.get_scores(query_tokens)
        
        # Attach scores to chunks
        for idx, chunk in enumerate(chunks):
            chunk["score"] = scores[idx]
            
        # Sort and return top_k
        ranked = sorted(chunks, key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]


class HybridRetriever(BaseRetriever):
    """Combines Dense and BM25 using Reciprocal Rank Fusion (RRF)."""
    def __init__(self):
        self.dense = DenseRetriever()
        self.bm25 = BM25Retriever()
        
    async def retrieve(self, query: str, session_id: str, top_k: int) -> list[dict[str, Any]]:
        results = await asyncio.gather(
            self.dense.retrieve(query, session_id, top_k=top_k * 2),
            self.bm25.retrieve(query, session_id, top_k=top_k * 2),
            return_exceptions=True
        )
        
        dense_results = results[0] if not isinstance(results[0], Exception) else []
        bm25_results = results[1] if not isinstance(results[1], Exception) else []
        
        if isinstance(results[0], Exception):
            import logging
            logging.getLogger(__name__).warning("Dense retrieval failed, falling back to BM25: %s", results[0])
        if isinstance(results[1], Exception):
            import logging
            logging.getLogger(__name__).warning("BM25 retrieval failed, falling back to Dense: %s", results[1])
        
        # Reciprocal Rank Fusion
        k_const = 60
        rrf_scores = {}
        items = {}
        
        for rank, item in enumerate(dense_results):
            txt = item["text"]
            if not txt:
                continue
            items[txt] = item
            rrf_scores[txt] = rrf_scores.get(txt, 0) + 1.0 / (k_const + rank + 1)
            
        for rank, item in enumerate(bm25_results):
            txt = item["text"]
            if not txt:
                continue
            items[txt] = item
            rrf_scores[txt] = rrf_scores.get(txt, 0) + 1.0 / (k_const + rank + 1)
            
        for txt, score in rrf_scores.items():
            items[txt]["score"] = score
            
        fused = sorted(list(items.values()), key=lambda x: x["score"], reverse=True)
        return fused[:top_k]
