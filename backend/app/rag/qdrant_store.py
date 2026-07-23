"""Qdrant vector database client and collection management."""
import uuid
from typing import Any, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import get_settings
from app.rag.embeddings import get_embedding_dim
from app.utils.logger import get_logger
from app.utils.retry import async_retry

settings = get_settings()
logger = get_logger(__name__)

_client: Optional[AsyncQdrantClient] = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
    return _client


@async_retry(max_attempts=3, base_delay=1.0)
async def _ensure_collection_internal() -> None:
    client = get_qdrant_client()
    collections = await client.get_collections()
    names = {c.name for c in collections.collections}
    if settings.QDRANT_COLLECTION not in names:
        logger.info("Creating Qdrant collection: %s", settings.QDRANT_COLLECTION)
        await client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config={
                "default": qmodels.VectorParams(
                    size=get_embedding_dim(),
                    distance=qmodels.Distance.COSINE,
                )
            },
        )

async def ensure_collection() -> bool:
    try:
        await _ensure_collection_internal()
        client = get_qdrant_client()
        # Always verify/create keyword payload index on session_id
        try:
            await client.create_payload_index(
                collection_name=settings.QDRANT_COLLECTION,
                field_name="session_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
        except Exception as e:
            logger.debug("Payload index on session_id already exists or failed to create: %s", e)
            
        # Always verify/create keyword payload index on filename (required for filter-based deletion)
        try:
            await client.create_payload_index(
                collection_name=settings.QDRANT_COLLECTION,
                field_name="filename",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
        except Exception as e:
            logger.debug("Payload index on filename already exists or failed to create: %s", e)
            
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to ensure Qdrant collection: %s", exc)
        return False


async def upsert_chunks(
    session_id: str,
    filename: str,
    chunks: list[str],
    vectors: list[list[float]],
) -> int:
    ready = await ensure_collection()
    if not ready:
        logger.error("Qdrant unavailable; skipping chunk upsert.")
        return 0
    try:
        client = get_qdrant_client()
        points = [
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector={"default": vector},
                payload={
                    "text": chunk,
                    "filename": filename,
                    "session_id": session_id,
                    "chunk_index": idx,
                },
            )
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        await client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
        return len(points)
    except Exception as exc:  # noqa: BLE001
        logger.error("Qdrant upsert failed: %s", exc)
        return 0


async def search(
    query_vector: list[float],
    session_id: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    ready = await ensure_collection()
    if not ready:
        return []
    try:
        client = get_qdrant_client()
        result = await client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            using="default",
            limit=top_k,
            query_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="session_id", match=qmodels.MatchValue(value=session_id))]
            ),
            with_payload=True,
        )
        return [
            {
                "text": p.payload.get("text", "") if p.payload else "",
                "filename": p.payload.get("filename", "") if p.payload else "",
                "score": getattr(p, "score", 0.0),
            }
            for p in result.points
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant search failed: %s", exc)
        return []


async def fetch_all_session_chunks(session_id: str) -> list[dict[str, Any]]:
    ready = await ensure_collection()
    if not ready:
        return []
    try:
        client = get_qdrant_client()
        result, _ = await client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key="session_id", match=qmodels.MatchValue(value=session_id))]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        return [
            {
                "id": p.id,
                "text": p.payload.get("text", "") if p.payload else "",
                "filename": p.payload.get("filename", "") if p.payload else "",
            }
            for p in result
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant scroll failed: %s", exc)
        return []


async def is_connected() -> bool:
    try:
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant connection check failed: %s", exc)
        return False


async def delete_file(session_id: str, filename: str) -> bool:
    ready = await ensure_collection()
    if not ready:
        return False
    try:
        client = get_qdrant_client()
        await client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="session_id", match=qmodels.MatchValue(value=session_id)),
                        qmodels.FieldCondition(key="filename", match=qmodels.MatchValue(value=filename))
                    ]
                )
            )
        )
        return True
    except Exception as exc:
        logger.error("Failed to delete file from Qdrant: %s", exc)
        return False


async def delete_session(session_id: str) -> bool:
    ready = await ensure_collection()
    if not ready:
        return False
    try:
        client = get_qdrant_client()
        await client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="session_id", match=qmodels.MatchValue(value=session_id))
                    ]
                )
            )
        )
        return True
    except Exception as exc:
        logger.error("Failed to delete session from Qdrant: %s", exc)
        return False
