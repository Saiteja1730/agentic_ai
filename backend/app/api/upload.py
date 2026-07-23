"""Upload endpoint: accepts a PDF, extracts text, chunks, embeds, and
stores it in Qdrant scoped to a session."""
import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.pdf_agent import process_and_index_pdf
from app.config.settings import get_settings
from app.schemas.schemas import UploadResponse
from app.services.session_service import get_or_create_session, register_upload
from app.utils.logger import get_logger

router = APIRouter(tags=["upload"])
logger = get_logger(__name__)
settings = get_settings()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds max size of {settings.MAX_UPLOAD_MB}MB.",
        )

    session = get_or_create_session(session_id)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    try:
        with open(file_path, "wb") as f:
            f.write(contents)

        chunks_indexed = await process_and_index_pdf(session.session_id, file.filename, file_path)
        register_upload(session.session_id, file.filename)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process uploaded PDF")
        raise HTTPException(
            status_code=500,
            detail="Failed to process the uploaded PDF. Please ensure it is a valid, text-based PDF and try again.",
        ) from exc
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return UploadResponse(
        filename=file.filename,
        chunks_indexed=chunks_indexed,
        session_id=session.session_id,
    )
