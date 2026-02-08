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
    qdrant_url: str = "http://localhost:6335"

    # Anthropic
    anthropic_api_key: str = ""
    yourai_model_fast: str = "claude-haiku-4-5-20251001"
    yourai_model_standard: str = "claude-sonnet-4-5-20250929"
    yourai_model_advanced: str = "claude-opus-4-6"

    # Auth
    jwt_audience: str = "yourai-api"
    jwt_issuer: str = ""
    jwks_url: str = ""
    jwt_secret_key: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # SSE
    sse_replay_window_seconds: int = 300  # 5 minute replay buffer
    sse_heartbeat_interval_seconds: int = 15

    # Knowledge / Document Pipeline
    upload_dir: str = "./uploads"
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB

    # Embedding
    embedding_provider: str = "voyage"
    embedding_model: str = "voyage-3-large"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 128
    voyage_api_key: str = ""

    # Chunking
    chunk_target_tokens: int = 512
    chunk_max_tokens: int = 1024
    chunk_overlap_tokens: int = 77  # ~15% of 512

    # Reranker
    reranker_provider: str = "noop"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Lex
    lex_base_url: str = "http://localhost:8080"
    lex_public_fallback_url: str = "https://lex.lab.i.ai.gov.uk"
    lex_health_check_interval: int = 30  # seconds
    lex_qdrant_url: str = "http://localhost:6333"
    lex_pipeline_container: str = "lex-pipeline"

    model_config = {"env_prefix": "YOURAI_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
