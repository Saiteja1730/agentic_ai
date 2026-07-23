"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str

    # Search
    TAVILY_API_KEY: str = ""

    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "research_documents"

    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIM: int = 768

    # RAG
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120
    TOP_K: int = 5
    RETRIEVAL_THRESHOLD: float = 0.35

    # App
    APP_NAME: str = "Agentic Research Assistant"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 25
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Agent control
    MAX_CRITIC_RETRIES: int = 2

    # LangSmith
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "AgenticResearchAssistant"

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    import os

    if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    return settings