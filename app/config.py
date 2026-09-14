"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "DripsLens"
    app_version: str = "0.1.0"
    debug: bool = False
    scheduler_enabled: bool = True
    initial_refresh_on_startup: bool = True

    # --- Database ---
    database_url: str = "sqlite:///./dripslens.db"

    # --- Redis / cache ---
    redis_url: str = ""  # empty -> in-process fallback cache
    cache_ttl_seconds: int = 300

    # --- Refresh engine ---
    refresh_interval_hours: float = 6.0

    # --- GitHub ---
    github_token: str = ""
    github_api_base: str = "https://api.github.com"
    github_max_retries: int = 3

    # --- Drips ---
    drips_repos_url: str = "https://drips.network/wave/stellar/repos"

    # --- Stellar ---
    stellar_horizon_url: str = "https://horizon.stellar.org"
    stellar_rpc_url: str = ""  # optional Soroban RPC for contract verification


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
