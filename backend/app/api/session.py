from fastapi import APIRouter, HTTPException
from app.services.session_service import get_or_create_session, remove_file, clear_session
from app.rag.qdrant_store import delete_file, delete_session
from app.utils.logger import get_logger

router = APIRouter(tags=["session"])
logger = get_logger(__name__)


@router.get("/session/{session_id}/files")
async def get_session_files(session_id: str):
    session = get_or_create_session(session_id)
    return {"files": session.uploaded_files}


@router.delete("/session/{session_id}/files/{filename}")
async def delete_session_file(session_id: str, filename: str):
    try:
        success = await delete_file(session_id, filename)
    except Exception:
        logger.exception("Qdrant error deleting file %s from session %s", filename, session_id)
        raise HTTPException(status_code=500, detail="Failed to remove the document. Please try again.")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove the document. Please try again.")

    remove_file(session_id, filename)
    return {"status": "success", "message": f"Removed {filename} from your research session."}


@router.delete("/session/{session_id}")
async def delete_entire_session(session_id: str):
    try:
        success = await delete_session(session_id)
    except Exception:
        logger.exception("Qdrant error clearing session %s", session_id)
        raise HTTPException(status_code=500, detail="Failed to clear the session. Please try again.")
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear the session. Please try again.")

    clear_session(session_id)
    return {"status": "success", "message": "Session cleared successfully."}
