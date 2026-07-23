"""Health check endpoint."""
from fastapi import APIRouter

from app.config.settings import get_settings
from app.rag.qdrant_store import is_connected
from app.schemas.schemas import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    qdrant_ok = await is_connected()
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        qdrant_connected=qdrant_ok,
    )
