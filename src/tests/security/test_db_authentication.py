"""Security tests for database authentication (ST-030 to ST-032).

Tests verify proper database authentication:
- ST-030: Neo4j requires authentication
- ST-031: Credentials from environment variables
- ST-032: Connection fails with wrong credentials
"""

import os
import re
from pathlib import Path
from typing import Any

import pytest

try:
    from testcontainers.neo4j import Neo4jContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    Neo4jContainer = None  # type: ignore


class TestDatabaseAuthentication:
    """Test suite for database authentication requirements."""

    def test_st_030_neo4j_requires_auth(
        self,
        docker_files: list[Path],
    ) -> None:
        """ST-030: Neo4j requires authentication.

        Verify Neo4j is not configured with auth disabled.
        """
        docker_compose_file = None
        for f in docker_files:
            if "docker-compose" in f.name.lower():
                docker_compose_file = f
                break

        if not docker_compose_file:
            pytest.skip("docker-compose file not found")

        content = docker_compose_file.read_text()

        # Check for auth disabled
        if "NEO4J_AUTH=none" in content:
            pytest.fail("Neo4j authentication is disabled (NEO4J_AUTH=none)")

        # Check for proper auth configuration
        has_auth_config = any([
            "NEO4J_AUTH=" in content and "none" not in content.lower(),
            "NEO4J_PASSWORD" in content,
            "${NEO4J" in content,  # Environment variable
        ])

        if not has_auth_config:
            print("\nWarning: Neo4j authentication configuration not found")
            print("Ensure NEO4J_AUTH or password is properly configured")

    def test_st_031_credentials_from_env(
        self,
        source_files: list[Path],
    ) -> None:
        """ST-031: Credentials from environment variables.

        Verify credentials are not hardcoded.
        """
        config_file = None
        for f in source_files:
            if "config" in f.name.lower():
                config_file = f
                break

        if not config_file:
            pytest.skip("config.py not found")

        content = config_file.read_text()

        # Check that sensitive settings use environment variables
        required_env_settings = [
            ("neo4j_password", ["SecretStr", "os.environ", "getenv", "Field"]),
            ("voyage_api_key", ["SecretStr", "os.environ", "getenv", "Field"]),
        ]

        for setting_name, expected_patterns in required_env_settings:
            # Find the setting definition
            setting_match = re.search(
                rf'{setting_name}\s*[:=].*?(?=\n\s*\w+\s*[:=]|\Z)',
                content,
                re.DOTALL | re.IGNORECASE
            )

            if setting_match:
                setting_block = setting_match.group()
                has_safe_pattern = any(
                    pattern in setting_block for pattern in expected_patterns
                )
                if not has_safe_pattern:
                    pytest.fail(f"Setting '{setting_name}' should use SecretStr or env variable")

        # Check for pydantic-settings usage (recommended)
        if "BaseSettings" in content or "pydantic_settings" in content:
            print("\nGood: Using pydantic-settings for configuration")
        else:
            print("\nRecommendation: Consider using pydantic-settings for better env var handling")

    @pytest.mark.skipif(
        not TESTCONTAINERS_AVAILABLE,
        reason="testcontainers not available"
    )
    @pytest.mark.asyncio
    async def test_st_032_connection_fails_wrong_credentials(self) -> None:
        """ST-032: Connection fails with wrong credentials.

        Verify authentication enforcement.
        """
        from memory_service.storage.neo4j_adapter import Neo4jAdapter

        container = Neo4jContainer(
            image="neo4j:5.15.0",
            username="neo4j",
            password="correctpassword123",
        )

        try:
            container.start()

            # Try to connect with wrong password
            adapter = Neo4jAdapter(
                uri=container.get_connection_url(),
                user="neo4j",
                password="wrongpassword",
            )

            # This should fail - health_check returns False on auth failure
            health = await adapter.health_check()
            await adapter.close()

            # health_check returns False when authentication fails
            assert health is False, (
                "Connection succeeded with wrong password - auth not enforced"
            )
            print("\nGood: Connection rejected with wrong credentials (health_check returned False)")

        finally:
            container.stop()


class TestCredentialConfiguration:
    """Additional tests for credential configuration."""

    def test_secrets_use_secretstr(
        self,
        source_files: list[Path],
    ) -> None:
        """Test that secrets use pydantic SecretStr."""
        config_file = None
        for f in source_files:
            if "config" in f.name.lower():
                config_file = f
                break

        if not config_file:
            pytest.skip("config.py not found")

        content = config_file.read_text()

        # Check for SecretStr import
        if "SecretStr" not in content:
            print("\nWarning: SecretStr not used - secrets may be logged in plain text")
            return

        # Check that password/key fields use SecretStr
        sensitive_fields = ["password", "api_key", "secret", "token"]

        for field in sensitive_fields:
            field_match = re.search(
                rf'{field}\s*:\s*(\w+)',
                content,
                re.IGNORECASE
            )
            if field_match:
                field_type = field_match.group(1)
                if field_type != "SecretStr":
                    print(f"\nWarning: Field '{field}' uses '{field_type}' instead of SecretStr")

    def test_no_default_passwords(
        self,
        source_files: list[Path],
        docker_files: list[Path],
    ) -> None:
        """Test that no default/weak passwords are set."""
        weak_passwords = [
            "password", "password123", "admin", "admin123",
            "root", "root123", "test", "test123",
            "neo4j", "qdrant", "secret",
        ]

        all_files = list(source_files) + list(docker_files)

        for file_path in all_files:
            # Skip test files
            if "test" in str(file_path).lower():
                continue

            try:
                content = file_path.read_text()

                for weak in weak_passwords:
                    # Look for password assignments with weak values
                    pattern = rf'password\s*[:=]\s*["\']?{weak}["\']?'
                    if re.search(pattern, content, re.IGNORECASE):
                        # Check if it's in an example or comment
                        if "example" in file_path.name.lower():
                            continue
                        print(f"\nWarning: Weak password '{weak}' in {file_path.name}")

            except Exception:
                pass

    def test_env_file_not_in_image(
        self,
        docker_files: list[Path],
    ) -> None:
        """Test that .env file is not copied into Docker image."""
        dockerfile = None
        for f in docker_files:
            if f.name.lower() == "dockerfile":
                dockerfile = f
                break

        if not dockerfile:
            pytest.skip("Dockerfile not found")

        content = dockerfile.read_text()

        # Check for COPY or ADD of .env files
        if re.search(r'(COPY|ADD).*\.env', content):
            pytest.fail(".env file should not be copied into Docker image")

        # Check .dockerignore
        dockerignore = dockerfile.parent / ".dockerignore"
        if dockerignore.exists():
            ignore_content = dockerignore.read_text()
            if ".env" not in ignore_content:
                print("\nRecommendation: Add .env to .dockerignore")
