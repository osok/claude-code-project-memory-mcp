"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Qdrant Configuration
    qdrant_host: str = Field(default="localhost", description="Qdrant server hostname")
    qdrant_port: int = Field(default=6333, description="Qdrant server port")
    qdrant_api_key: SecretStr | None = Field(default=None, description="Qdrant API key (optional)")
    qdrant_grpc_port: int = Field(default=6334, description="Qdrant gRPC port")

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: SecretStr = Field(default=SecretStr(""), description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")
    neo4j_max_connection_pool_size: int = Field(default=50, description="Neo4j connection pool size")

    # Voyage AI Configuration
    voyage_api_key: SecretStr = Field(default=SecretStr(""), description="Voyage AI API key")
    voyage_model: str = Field(default="voyage-code-3", description="Voyage embedding model name")
    voyage_batch_size: int = Field(default=128, description="Max texts per Voyage API request")

    # Embedding Cache Configuration
    embedding_cache_path: str = Field(default=".cache/embeddings.db", description="SQLite cache file path")
    embedding_cache_size: int = Field(default=10000, description="Max cached embeddings")
    embedding_cache_ttl_days: int = Field(default=30, description="Cache entry TTL in days")

    # Duplicate Detection Configuration
    duplicate_threshold: float = Field(
        default=0.85,
        ge=0.70,
        le=0.95,
        description="Similarity threshold for duplicate detection",
    )
    conflict_threshold: float = Field(
        default=0.95,
        ge=0.90,
        le=1.0,
        description="Similarity threshold for conflict detection",
    )

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: Literal["json", "console"] = Field(
        default="json",
        description="Log output format",
    )
    log_file: str | None = Field(default=None, description="Log file path (optional)")

    # Metrics Configuration
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_host: str = Field(default="127.0.0.1", description="HTTP server bind address (use 0.0.0.0 for Docker)")
    metrics_port: int = Field(default=9090, description="HTTP server port for metrics/health")

    # Project Configuration
    project_path: str = Field(default="/project", description="Mounted project directory path")

    # Sync Configuration
    sync_interval_seconds: int = Field(default=300, description="Interval between sync checks (5 minutes)")
    sync_max_retries: int = Field(default=3, description="Max retries for failed sync operations")
    sync_retry_delay_seconds: int = Field(default=60, description="Delay between sync retries")

    # Normalization Configuration
    normalization_batch_size: int = Field(default=1000, description="Batch size for normalization")
    soft_delete_retention_days: int = Field(default=30, description="Days to keep soft-deleted items")

    # Performance Configuration
    search_default_limit: int = Field(default=10, description="Default search result limit")
    search_max_limit: int = Field(default=100, description="Maximum search result limit")
    graph_max_depth: int = Field(default=5, description="Maximum graph traversal depth")

    # Fallback Configuration
    fallback_embedding_enabled: bool = Field(default=False, description="Enable fallback embedding model")
    fallback_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Fallback local embedding model",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
