"""
Environment-driven application settings.

This is the ONLY module in the backend that should read environment
variables / the .env file directly. Every other module that needs a config
value (API keys, paths, CORS origins) must go through `get_settings()`.

No secret has a default value baked into source code. A missing required
secret should be visible (raise / be None and be checked by the module that
needs it) rather than silently substituted.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/config/settings.py -> parents[1] == backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    # --- General ---
    app_name: str = "Ustad Assist API"
    environment: str = "development"

    # --- CORS ---
    # Comma-separated list of allowed frontend origins, e.g.
    # "http://localhost:5173,https://ustad-assist.example.com"
    cors_origins: str = "http://localhost:5173"

    # --- Knowledge base ---
    data_dir: Path = BACKEND_ROOT / "data"
    verified_records_filename: str = "verified_records.json"

    # --- RAG (reserved for the retrieval phase — not used in Phase 1) ---
    embeddings_cache_dir: Path = BACKEND_ROOT / "data" / "embeddings_cache"
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # --- Gemini (reserved for the grounding phase — not used in Phase 1) ---
    # No default on purpose: a missing key should be an explicit, visible
    # failure once a later phase actually depends on it, not a silent None
    # that gets treated as configured.
    gemini_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def verified_records_path(self) -> Path:
        return self.data_dir / self.verified_records_filename

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Settings are cached for the process lifetime — loaded once, not
    re-read from disk/env on every request.
    """
    return Settings()