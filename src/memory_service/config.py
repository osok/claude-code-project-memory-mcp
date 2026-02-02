"""Configuration management using pydantic-settings.

This module provides configuration loading with the following precedence:
1. CLI arguments (highest priority)
2. Environment variables (CLAUDE_MEMORY_* prefix)
3. Global config file (~/.config/claude-memory/config.toml)
4. Built-in defaults (lowest priority)

Requirements:
    REQ-MEM-002-FN-020: Global config at ~/.config/claude-memory/config.toml
    REQ-MEM-002-FN-021: Database connection settings
    REQ-MEM-002-FN-022: API key settings
    REQ-MEM-002-FN-023: Environment variable overrides (CLAUDE_MEMORY_*)
    REQ-MEM-002-DATA-002: Config precedence
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project ID validation pattern (REQ-MEM-002-DATA-010)
PROJECT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_project_id(project_id: str) -> bool:
    """Validate project_id format.

    Args:
        project_id: Project identifier to validate

    Returns:
        True if valid, False otherwise

    Pattern: ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$
    - Must start with alphanumeric
    - Can contain alphanumeric, underscore, hyphen
    - 1-64 characters total
    - Case-sensitive (REQ-MEM-002-DATA-011)
    """
    return bool(PROJECT_ID_PATTERN.match(project_id))


def get_config_path() -> Path:
    """Get the global config file path (XDG compliant).

    Returns:
        Path to config file:
        - Linux/macOS: ~/.config/claude-memory/config.toml
        - Windows: %APPDATA%/claude-memory/config.toml

    REQ-MEM-002-DATA-001: XDG Base Directory specification
    """
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:  # Linux/macOS
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "claude-memory" / "config.toml"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables use CLAUDE_MEMORY_ prefix:
    - CLAUDE_MEMORY_QDRANT_HOST
    - CLAUDE_MEMORY_NEO4J_URI
    - CLAUDE_MEMORY_VOYAGE_API_KEY
    etc.
    """

    model_config = SettingsConfigDict(
        env_prefix="CLAUDE_MEMORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Qdrant Configuration (REQ-MEM-002-FN-021)
    qdrant_host: str = Field(default="localhost", description="Qdrant server hostname")
    qdrant_port: int = Field(default=6333, description="Qdrant server port")
    qdrant_api_key: SecretStr | None = Field(default=None, description="Qdrant API key (optional)")
    qdrant_grpc_port: int = Field(default=6334, description="Qdrant gRPC port")

    # Neo4j Configuration (REQ-MEM-002-FN-021)
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: SecretStr = Field(default=SecretStr(""), description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")
    neo4j_max_connection_pool_size: int = Field(default=50, description="Neo4j connection pool size")

    # Voyage AI Configuration (REQ-MEM-002-FN-022)
    voyage_api_key: SecretStr = Field(default=SecretStr(""), description="Voyage AI API key")
    voyage_model: str = Field(default="voyage-code-3", description="Voyage embedding model name")
    voyage_batch_size: int = Field(default=128, description="Max texts per Voyage API request")

    # Embedding Cache Configuration
    embedding_cache_path: str = Field(default="~/.cache/claude-memory/embeddings.db", description="SQLite cache file path")
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

    # Metrics Configuration (optional HTTP server for debugging)
    metrics_enabled: bool = Field(default=False, description="Enable Prometheus metrics HTTP server")
    metrics_host: str = Field(default="127.0.0.1", description="HTTP server bind address")
    metrics_port: int = Field(default=9090, description="HTTP server port for metrics/health")

    # Project Configuration
    # Note: project_id is now passed via --project-id CLI argument, not config
    # This field is kept for backward compatibility but deprecated
    project_id: str = Field(
        default="default",
        description="[DEPRECATED] Use --project-id CLI argument instead",
    )
    project_path: str = Field(default=".", description="Project directory path (for indexing)")

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


def load_toml_config(path: Path | None = None) -> dict[str, Any]:
    """Load configuration from TOML file.

    Args:
        path: Path to config file (uses default if None)

    Returns:
        Configuration dictionary (empty if file doesn't exist)
    """
    try:
        import tomli
    except ImportError:
        # Python 3.11+ has tomllib in stdlib
        try:
            import tomllib as tomli  # type: ignore
        except ImportError:
            return {}

    config_path = path or get_config_path()
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomli.load(f)
    return {}


def flatten_toml_config(toml_config: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested TOML config to flat dictionary for Settings.

    Args:
        toml_config: Nested TOML configuration

    Returns:
        Flattened configuration dictionary
    """
    overrides: dict[str, Any] = {}

    if "qdrant" in toml_config:
        for key in ["host", "port", "api_key", "grpc_port"]:
            if key in toml_config["qdrant"]:
                overrides[f"qdrant_{key}"] = toml_config["qdrant"][key]

    if "neo4j" in toml_config:
        for key in ["uri", "user", "password", "database", "max_connection_pool_size"]:
            if key in toml_config["neo4j"]:
                overrides[f"neo4j_{key}"] = toml_config["neo4j"][key]

    if "voyage" in toml_config:
        for key in ["api_key", "model", "batch_size"]:
            if key in toml_config["voyage"]:
                overrides[f"voyage_{key}"] = toml_config["voyage"][key]

    if "server" in toml_config:
        if "log_level" in toml_config["server"]:
            overrides["log_level"] = toml_config["server"]["log_level"]
        if "log_format" in toml_config["server"]:
            overrides["log_format"] = toml_config["server"]["log_format"]
        if "log_file" in toml_config["server"]:
            overrides["log_file"] = toml_config["server"]["log_file"]

    if "cache" in toml_config:
        if "path" in toml_config["cache"]:
            overrides["embedding_cache_path"] = toml_config["cache"]["path"]
        if "size" in toml_config["cache"]:
            overrides["embedding_cache_size"] = toml_config["cache"]["size"]
        if "ttl_days" in toml_config["cache"]:
            overrides["embedding_cache_ttl_days"] = toml_config["cache"]["ttl_days"]

    if "search" in toml_config:
        if "default_limit" in toml_config["search"]:
            overrides["search_default_limit"] = toml_config["search"]["default_limit"]
        if "max_limit" in toml_config["search"]:
            overrides["search_max_limit"] = toml_config["search"]["max_limit"]
        if "duplicate_threshold" in toml_config["search"]:
            overrides["duplicate_threshold"] = toml_config["search"]["duplicate_threshold"]
        if "conflict_threshold" in toml_config["search"]:
            overrides["conflict_threshold"] = toml_config["search"]["conflict_threshold"]

    if "normalization" in toml_config:
        if "batch_size" in toml_config["normalization"]:
            overrides["normalization_batch_size"] = toml_config["normalization"]["batch_size"]
        if "soft_delete_retention_days" in toml_config["normalization"]:
            overrides["soft_delete_retention_days"] = toml_config["normalization"]["soft_delete_retention_days"]

    if "sync" in toml_config:
        if "interval_seconds" in toml_config["sync"]:
            overrides["sync_interval_seconds"] = toml_config["sync"]["interval_seconds"]
        if "max_retries" in toml_config["sync"]:
            overrides["sync_max_retries"] = toml_config["sync"]["max_retries"]
        if "retry_delay_seconds" in toml_config["sync"]:
            overrides["sync_retry_delay_seconds"] = toml_config["sync"]["retry_delay_seconds"]

    if "performance" in toml_config and "graph_max_depth" in toml_config["performance"]:
        overrides["graph_max_depth"] = toml_config["performance"]["graph_max_depth"]

    if "fallback" in toml_config:
        if "enabled" in toml_config["fallback"]:
            overrides["fallback_embedding_enabled"] = toml_config["fallback"]["enabled"]
        if "model" in toml_config["fallback"]:
            overrides["fallback_embedding_model"] = toml_config["fallback"]["model"]

    return overrides


def load_settings_with_toml(config_path: Path | None = None) -> Settings:
    """Load settings with TOML config as base, env vars as override.

    This implements the config precedence:
    1. Environment variables (via pydantic-settings)
    2. TOML config file
    3. Built-in defaults

    Args:
        config_path: Optional path to TOML config file

    Returns:
        Settings instance with merged configuration
    """
    toml_config = load_toml_config(config_path)
    overrides = flatten_toml_config(toml_config)
    return Settings(**overrides)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Note: This uses the legacy approach without TOML support for backward
    compatibility. New code should use load_settings_with_toml() or the
    CLI module's configuration loading.

    Returns:
        Settings instance (cached)
    """
    return Settings()
