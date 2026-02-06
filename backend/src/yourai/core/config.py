"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings. All values can be overridden via environment variables."""

    # Application
    app_name: str = "YourAI"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://yourai:yourai@localhost:5432/yourai"
    database_pool_min: int = 5
    database_pool_max: int = 20
    database_statement_timeout: int = 30000  # milliseconds

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # Anthropic
    anthropic_api_key: str = ""
    yourai_model_fast: str = "claude-haiku-4-5-20251001"
    yourai_model_standard: str = "claude-sonnet-4-5-20250929"
    yourai_model_advanced: str = "claude-opus-4-6"

    # Auth
    jwt_audience: str = "yourai-api"
    jwt_issuer: str = ""
    jwks_url: str = ""

    # Lex
    lex_base_url: str = "http://localhost:8080"
    lex_public_fallback_url: str = "https://lex.lab.i.ai.gov.uk"
    lex_health_check_interval: int = 30  # seconds

    model_config = {"env_prefix": "YOURAI_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
