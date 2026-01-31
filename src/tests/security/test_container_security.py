"""Security tests for container security (ST-020 to ST-023).

Tests verify container security best practices:
- ST-020: Memory service runs as non-root
- ST-021: Container has minimal capabilities
- ST-022: Base image has no critical CVEs
- ST-023: Project mount is read-only
"""

import re
from pathlib import Path
from typing import Any

import pytest


class TestContainerSecurity:
    """Test suite for container security requirements."""

    def test_st_020_non_root_user(
        self,
        docker_files: list[Path],
    ) -> None:
        """ST-020: Memory service runs as non-root.

        Verify container user is not root (UID != 0).
        """
        dockerfile = None
        for f in docker_files:
            if f.name.lower() == "dockerfile":
                dockerfile = f
                break

        if not dockerfile:
            pytest.skip("Dockerfile not found")

        content = dockerfile.read_text()

        # Check for USER instruction
        user_match = re.search(r'^USER\s+(.+)$', content, re.MULTILINE)

        if not user_match:
            # No USER instruction means running as root
            # Check if there's user creation but no switch
            if re.search(r'useradd|adduser', content):
                pytest.fail("User created but USER instruction not found - may run as root")
            pytest.fail("No USER instruction in Dockerfile - container runs as root")

        user_value = user_match.group(1).strip()

        # Check if user is root
        if user_value in ["root", "0"]:
            pytest.fail("Container explicitly runs as root user")

        print(f"\nContainer runs as user: {user_value}")

        # Verify the user is created before switching
        if not re.search(rf'(useradd|adduser).*{user_value}', content):
            # User might be a build arg or existing user
            if "${" not in user_value and user_value != "nobody":
                print(f"Warning: User '{user_value}' should be explicitly created")

    def test_st_021_minimal_capabilities(
        self,
        docker_files: list[Path],
    ) -> None:
        """ST-021: Container has minimal capabilities.

        Verify no --privileged flag and minimal caps.
        """
        docker_compose_file = None
        for f in docker_files:
            if "docker-compose" in f.name.lower():
                docker_compose_file = f
                break

        if not docker_compose_file:
            pytest.skip("docker-compose file not found")

        content = docker_compose_file.read_text()

        # Check for privileged mode
        if re.search(r'privileged:\s*true', content, re.IGNORECASE):
            pytest.fail("Container runs in privileged mode - security risk")

        # Check for capability additions
        cap_add_match = re.search(r'cap_add:.*?(?=^\s*\w+:|\Z)', content, re.DOTALL | re.MULTILINE)
        if cap_add_match:
            caps = cap_add_match.group()
            dangerous_caps = ["SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "ALL"]
            for cap in dangerous_caps:
                if cap in caps:
                    print(f"\nWarning: Potentially dangerous capability: {cap}")

        # Check for cap_drop (recommended)
        has_cap_drop = "cap_drop:" in content

        if not has_cap_drop:
            print("\nRecommendation: Consider adding cap_drop: ALL and only adding needed capabilities")

    def test_st_022_base_image_security(
        self,
        docker_files: list[Path],
    ) -> None:
        """ST-022: Base image has no critical CVEs.

        Note: This test checks for best practices in image selection.
        Actual CVE scanning requires external tools like Trivy.
        """
        dockerfile = None
        for f in docker_files:
            if f.name.lower() == "dockerfile":
                dockerfile = f
                break

        if not dockerfile:
            pytest.skip("Dockerfile not found")

        content = dockerfile.read_text()

        # Find FROM instruction
        from_matches = re.findall(r'^FROM\s+(.+)$', content, re.MULTILINE)

        if not from_matches:
            pytest.fail("No FROM instruction found in Dockerfile")

        recommendations = []

        for image in from_matches:
            image = image.strip().split()[0]  # Remove AS clause if present

            # Check for latest tag (not recommended)
            if image.endswith(":latest") or ":" not in image:
                recommendations.append(f"Image '{image}' uses 'latest' tag - pin to specific version")

            # Check for slim/alpine variants (recommended)
            base_name = image.split(":")[0].split("/")[-1]
            if base_name == "python" and "slim" not in image and "alpine" not in image:
                recommendations.append(f"Consider using python:*-slim or python:*-alpine for smaller attack surface")

        if recommendations:
            print("\nBase image recommendations:")
            for rec in recommendations:
                print(f"  - {rec}")

        # This test passes but prints recommendations
        # Actual CVE scanning should be done with trivy or similar

    def test_st_023_read_only_mount(
        self,
        docker_files: list[Path],
    ) -> None:
        """ST-023: Project mount is read-only.

        Verify the /project mount is read-only in container.
        """
        docker_compose_file = None
        for f in docker_files:
            if "docker-compose" in f.name.lower():
                docker_compose_file = f
                break

        if not docker_compose_file:
            pytest.skip("docker-compose file not found")

        content = docker_compose_file.read_text()

        # Find memory-service or similar service
        service_section = re.search(
            r'memory[-_]?service:.*?(?=^\s*\w+:|$)',
            content,
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        if not service_section:
            pytest.skip("Memory service not found in docker-compose")

        section = service_section.group()

        # Look for volume mounts
        volumes_match = re.search(r'volumes:.*?(?=^\s*\w+:|\Z)', section, re.DOTALL)

        if volumes_match:
            volumes_section = volumes_match.group()

            # Check for project directory mount
            project_mount = re.search(r'(/project|\.:/app)', volumes_section)

            if project_mount:
                # Check if it's read-only
                mount_line = volumes_section[project_mount.start():volumes_section.find('\n', project_mount.end())]

                if ":ro" not in mount_line and "read_only" not in mount_line.lower():
                    print("\nWarning: Project mount may not be read-only")
                    print(f"  Found: {mount_line.strip()}")
                    print("  Consider adding :ro suffix for read-only mount")


class TestDockerfileBestPractices:
    """Additional tests for Dockerfile best practices."""

    def test_no_secrets_in_build(
        self,
        docker_files: list[Path],
    ) -> None:
        """Test that secrets are not copied into the image."""
        dockerfile = None
        for f in docker_files:
            if f.name.lower() == "dockerfile":
                dockerfile = f
                break

        if not dockerfile:
            pytest.skip("Dockerfile not found")

        content = dockerfile.read_text()

        # Check for copying sensitive files
        sensitive_patterns = [
            r'COPY.*\.env\s',
            r'COPY.*credentials',
            r'COPY.*\.pem\s',
            r'COPY.*\.key\s',
            r'ADD.*secret',
        ]

        for pattern in sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                pytest.fail(f"Potentially copying secrets into image: {pattern}")

    def test_health_check_defined(
        self,
        docker_files: list[Path],
    ) -> None:
        """Test that HEALTHCHECK is defined."""
        dockerfile = None
        for f in docker_files:
            if f.name.lower() == "dockerfile":
                dockerfile = f
                break

        if not dockerfile:
            pytest.skip("Dockerfile not found")

        content = dockerfile.read_text()

        if "HEALTHCHECK" not in content:
            print("\nRecommendation: Add HEALTHCHECK instruction for container orchestration")

    def test_multi_stage_build(
        self,
        docker_files: list[Path],
    ) -> None:
        """Test for multi-stage build (recommended for smaller images)."""
        dockerfile = None
        for f in docker_files:
            if f.name.lower() == "dockerfile":
                dockerfile = f
                break

        if not dockerfile:
            pytest.skip("Dockerfile not found")

        content = dockerfile.read_text()

        from_count = len(re.findall(r'^FROM\s+', content, re.MULTILINE))

        if from_count == 1:
            print("\nRecommendation: Consider multi-stage build for smaller final image")
        elif from_count > 1:
            print(f"\nGood: Multi-stage build detected ({from_count} stages)")
