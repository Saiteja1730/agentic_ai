"""Google GenAI text-embedding-004 API wrapper for document embedding."""
from functools import lru_cache
from google.genai import types

from app.config.settings import get_settings
from app.llm.gemini import get_client
from app.utils.logger import get_logger
from app.utils.retry import async_retry
from langsmith import traceable

settings = get_settings()
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_embedding_dim() -> int:
    return settings.EMBEDDING_DIM


@traceable(run_type="llm")
@async_retry(max_attempts=3, base_delay=1.5)
async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts asynchronously using Google's text-embedding-004 API."""
    if not texts:
        return []
        
    client = get_client()
    
    logger.info("Embedding batch of %d texts using %s API...", len(texts), settings.EMBEDDING_MODEL)
    try:
        response = await client.aio.models.embed_content(
            model=settings.EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                output_dimensionality=settings.EMBEDDING_DIM
            )
        )
        if not response or not response.embeddings:
            logger.warning("Empty embeddings returned from Google API.")
            return [[0.0] * settings.EMBEDDING_DIM for _ in texts]
            
        return [e.values for e in response.embeddings]
    except Exception as exc:
        logger.error("Failed to generate Google embeddings: %s", exc)
        # Fallback to zero vectors to prevent pipeline crashes
        return [[0.0] * settings.EMBEDDING_DIM for _ in texts]


async def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    vectors = await embed_texts([text])
    return vectors[0] if vectors else [0.0] * settings.EMBEDDING_DIM
