"""High level retrieval API combining embeddings + Qdrant search."""
from app.config.settings import get_settings
from app.rag import qdrant_store
from app.rag.chunker import chunk_text
from app.rag.embeddings import embed_query, embed_texts
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


async def index_document(session_id: str, filename: str, raw_text: str) -> int:
    """Chunk, embed, and store a document's text under the given session."""
    chunks = chunk_text(raw_text)
    if not chunks:
        return 0
    vectors = await embed_texts(chunks)
    count = await qdrant_store.upsert_chunks(session_id, filename, chunks, vectors)
    logger.info("Indexed %s chunks from %s for session %s", count, filename, session_id)
    return count


from app.rag.retrievers import HybridRetriever

_hybrid_retriever = None

def get_hybrid_retriever():
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever

async def retrieve_relevant_chunks(
    session_id: str,
    query: str,
    top_k: int = None,
) -> list[dict]:
    top_k = top_k or settings.TOP_K
    retriever = get_hybrid_retriever()
    return await retriever.retrieve(query, session_id, top_k=top_k)
