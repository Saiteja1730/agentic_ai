"""Lightweight in-memory session tracking (no persistent DB required)."""
import uuid
from dataclasses import dataclass, field


@dataclass
class Session:
    session_id: str
    uploaded_files: list[str] = field(default_factory=list)


_sessions: dict[str, Session] = {}


def create_session() -> Session:
    session_id = str(uuid.uuid4())
    session = Session(session_id=session_id)
    _sessions[session_id] = session
    return session


def get_or_create_session(session_id: str | None) -> Session:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    if session_id:
        session = Session(session_id=session_id)
        _sessions[session_id] = session
        return session
    return create_session()


def register_upload(session_id: str, filename: str) -> None:
    session = get_or_create_session(session_id)
    if filename not in session.uploaded_files:
        session.uploaded_files.append(filename)


def remove_file(session_id: str, filename: str) -> None:
    if session_id in _sessions:
        session = _sessions[session_id]
        if filename in session.uploaded_files:
            session.uploaded_files.remove(filename)


def clear_session(session_id: str) -> None:
    if session_id in _sessions:
        _sessions[session_id].uploaded_files.clear()
