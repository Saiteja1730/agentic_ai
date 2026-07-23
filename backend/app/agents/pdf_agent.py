"""PDF Research Agent: extracts, indexes, and retrieves from uploaded PDFs."""
from typing import Any

from pypdf import PdfReader

from app.rag.retriever import index_document, retrieve_relevant_chunks
from app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from a PDF file on disk."""
    reader = PdfReader(file_path)
    pages_text = []
    for page in reader.pages:
        try:
            pages_text.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to extract a page: %s", exc)
    return "\n".join(pages_text)


async def process_and_index_pdf(session_id: str, filename: str, file_path: str) -> int:
    """Extract text from an uploaded PDF, chunk it, embed it, and store it
    in Qdrant scoped to the session."""
    text = extract_text_from_pdf(file_path)
    if not text.strip():
        logger.warning("No extractable text found in %s", filename)
        return 0
    return await index_document(session_id, filename, text)


async def run_pdf_search(session_id: str, queries: list[str]) -> list[dict[str, Any]]:
    """Retrieve relevant chunks for each query from the session's indexed PDFs."""
    evidence: list[dict[str, Any]] = []
    for query in queries:
        chunks = await retrieve_relevant_chunks(session_id, query)
        for chunk in chunks:
            evidence.append(
                {
                    "title": chunk.get("filename", "Uploaded PDF"),
                    "url": None,
                    "snippet": chunk.get("text", "")[:800],
                    "origin": "pdf",
                    "query": query,
                    "score": chunk.get("score", 0.0),
                }
            )
    return evidence
