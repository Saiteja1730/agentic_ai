"""Splits raw document text into overlapping chunks for embedding."""
import re

from app.config.settings import get_settings

settings = get_settings()


def _split_sentences(text: str) -> list[str]:
    # Lightweight sentence splitter; avoids heavy NLP dependencies.
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> list[str]:
    """Chunk text into ~chunk_size character windows, respecting sentence
    boundaries where possible, with `overlap` characters shared between
    consecutive chunks to preserve context continuity."""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    sentences = _split_sentences(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk, carrying over trailing overlap of previous chunk
            tail = current[-overlap:] if overlap and current else ""
            current = f"{tail} {sentence}".strip()

    if current:
        chunks.append(current)

    # Fallback: if a single sentence exceeds chunk_size, hard-split it.
    final_chunks: list[str] = []
    for c in chunks:
        if len(c) <= chunk_size * 1.5:
            final_chunks.append(c)
        else:
            for i in range(0, len(c), chunk_size - overlap):
                final_chunks.append(c[i : i + chunk_size])

    return final_chunks
