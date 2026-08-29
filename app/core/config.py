"""
Centralized configuration.

WHY THIS PATTERN:
Instead of scattering `os.getenv("SOME_VAR")` calls across the codebase,
every setting lives in one typed object. Benefits:
  1. Typos are caught at startup (Pydantic validates types), not at
     3am in production when a string that should've been an int crashes
     a deep function call.
  2. Autocomplete works everywhere: `settings.DATABASE_URL` instead of
     remembering the exact env var string.
  3. One object to mock in tests instead of monkeypatching env vars
     all over the place.

`@lru_cache` on `get_settings()` means the .env file is parsed once per
process, not once per request -- settings are constant machine-wide,
so re-reading the file on every request would be pure waste.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App metadata ---
    PROJECT_NAME: str = "E-Commerce API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # "development" | "staging" | "production"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./ecommerce.db"

    # --- Security / JWT ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using a function (instead of a module-level `settings = Settings()`)
    means FastAPI's dependency-injection system can override this in
    tests via `app.dependency_overrides[get_settings] = ...` without
    needing to reimport modules or patch globals.
    """
    return Settings()


# Convenience singleton for non-DI contexts (e.g. Alembic's env.py,
# scripts). Route handlers should prefer `Depends(get_settings)`.
settings = get_settings()
