"""
Centralized, environment-driven configuration.

Nothing in this application should read `os.environ` directly outside of
this module. All configuration flows through `Settings`, which is
instantiated once (see `get_settings`) and injected wherever needed.

This is a v0.1/v0.2 config surface: app metadata, database, CORS,
logging, and auth (secret key, token TTL, cookie flags). Object
storage, embedding/LLM provider, and Redis settings are added in later
versions as those subsystems are built — we don't pre-declare settings
for features that don't exist yet.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App metadata ---
    app_name: str = "ai-knowledge-assistant"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True

    # --- API ---
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Database ---
    # Example: postgresql+psycopg://user:password@localhost:5432/ai_knowledge_assistant
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/ai_knowledge_assistant"
    )
    database_echo: bool = False

    # --- Auth (v0.2) ---
    # No default: an app boot with a guessable/default secret key is a
    # real vulnerability, not a convenience — this must come from the
    # environment (.env.example documents generating one).
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # False for local HTTP dev; must be True wherever the app is served
    # over HTTPS, or browsers will refuse to send the cookie at all —
    # which is exactly the kind of thing that's invisible until someone
    # actually logs in through a browser rather than curl/pytest.
    auth_cookie_secure: bool = False
    auth_cookie_name: str = "access_token"

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Cached via lru_cache so environment parsing happens once per process,
    not once per request. `get_settings` is a plain function, not a
    FastAPI dependency wired via `Depends` anywhere in the app — nothing
    currently needs per-request settings. For endpoint-level tests that
    need to simulate a specific outcome (e.g. a DB failure), override the
    `get_db` FastAPI dependency directly with `app.dependency_overrides`
    (see `tests/test_health.py`). For a test suite that needs a genuinely
    different DATABASE_URL, set the env var before the app is imported,
    or call `get_settings.cache_clear()` together with
    `app.db.session.get_engine.cache_clear()` /
    `get_sessionmaker.cache_clear()`.
    """
    return Settings()  # type: ignore[call-arg]
    # mypy sees `secret_key: str` (no default) as a required constructor
    # arg, but pydantic-settings resolves it from the environment at
    # runtime — a well-known false positive for BaseSettings subclasses
    # without the dedicated mypy plugin. The ignore is intentional, not
    # a sign the field should get a default; see the field's own
    # docstring for why it must not have one.
