"""Application configuration.

Only *publishable* values ever leave the backend (see the api layer). All other
secrets stay server-side: service-role key, JWT secret, LLM key, SQL secrets.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Supabase ---
    supabase_url: str = "http://localhost:54321"
    supabase_service_role_key: str = Field(default="service-role")
    supabase_publishable_key: str = "anon"
    supabase_jwt_secret: str = ""

    # --- LLM ---
    llm_enabled: bool = False
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 120

    # --- File limits ---
    max_upload_mb: int = 100
    allowed_file_extensions: str = "csv,xls,xlsx"

    # --- SQL connectors ---
    sql_secrets_key: str = ""  # Fernet key; empty disables encrypted connectors
    sql_allowed_hosts: str = "*"

    # --- Jobs ---
    job_concurrency: int = 2
    job_poll_interval_seconds: float = 1.0

    # --- App ---
    app_env: str = "production"
    cors_origins: str = "*"

    @property
    def allowed_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_file_extensions.split(",") if e.strip()}

    @property
    def allowed_hosts(self) -> set[str] | None:
        if self.sql_allowed_hosts.strip() == "*":
            return None  # allowlist disabled (dev)
        return {h.strip().lower() for h in self.sql_allowed_hosts.split(",") if h.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
