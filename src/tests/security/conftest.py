"""Security test fixtures."""

import os
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def project_root() -> Path:
    """Get project root directory."""
    # Navigate from tests/security to project root
    current = Path(__file__).resolve()
    # Go up: security -> tests -> src -> project_root
    return current.parent.parent.parent.parent


@pytest.fixture
def source_files(project_root: Path) -> list[Path]:
    """Get all Python source files."""
    src_dir = project_root / "src"
    if not src_dir.exists():
        return []
    return list(src_dir.rglob("*.py"))


@pytest.fixture
def docker_files(project_root: Path) -> list[Path]:
    """Get all Docker-related files."""
    docker_files = []
    docker_dir = project_root / "docker"
    if docker_dir.exists():
        docker_files.extend(docker_dir.glob("Dockerfile*"))
        docker_files.extend(docker_dir.glob("docker-compose*.yml"))
        docker_files.extend(docker_dir.glob("docker-compose*.yaml"))

    # Also check root for docker files
    docker_files.extend(project_root.glob("Dockerfile*"))
    docker_files.extend(project_root.glob("docker-compose*.yml"))
    docker_files.extend(project_root.glob("docker-compose*.yaml"))

    return docker_files


@pytest.fixture
def config_files(project_root: Path) -> list[Path]:
    """Get configuration files that might contain secrets."""
    config_patterns = [
        "*.env*",
        "*.conf",
        "*.config",
        "*.json",
        "*.yaml",
        "*.yml",
        "*.toml",
    ]
    config_files = []
    for pattern in config_patterns:
        config_files.extend(project_root.glob(pattern))
        config_files.extend((project_root / "docker").glob(pattern) if (project_root / "docker").exists() else [])
    return config_files


# Secret patterns to scan for
SECRET_PATTERNS = [
    # API Keys
    (r"VOYAGE_API_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{20,}['\"]?", "Voyage API Key"),
    (r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9_-]{20,}['\"]", "API Key"),
    (r"sk-[A-Za-z0-9]{20,}", "Secret Key"),
    (r"Bearer\s+[A-Za-z0-9_-]{20,}", "Bearer Token"),

    # Passwords
    (r"NEO4J_PASSWORD\s*=\s*['\"]?(?![\$\{])[^\s'\"]{8,}['\"]?", "Neo4j Password"),
    (r"password\s*[:=]\s*['\"][^'\"]{8,}['\"]", "Password"),
    (r"passwd\s*[:=]\s*['\"][^'\"]{8,}['\"]", "Password"),

    # Database URIs
    (r"mongodb://[^:]+:[^@]+@", "MongoDB URI with credentials"),
    (r"postgresql://[^:]+:[^@]+@", "PostgreSQL URI with credentials"),
    (r"mysql://[^:]+:[^@]+@", "MySQL URI with credentials"),

    # AWS
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]", "AWS Secret Key"),

    # Private Keys
    (r"-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----", "Private Key"),
    (r"-----BEGIN OPENSSH PRIVATE KEY-----", "OpenSSH Private Key"),
]


@pytest.fixture
def secret_patterns() -> list[tuple[str, str]]:
    """Get secret patterns to scan for."""
    return SECRET_PATTERNS
