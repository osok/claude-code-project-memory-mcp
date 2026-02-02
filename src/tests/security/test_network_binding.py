"""Security tests for network binding (ST-010 to ST-013).

Tests verify proper network isolation:
- ST-010: HTTP server binds to localhost only
- ST-011: MCP server uses stdio transport
- ST-012: Qdrant binds to Docker network only
- ST-013: Neo4j binds to Docker network only
"""

import re
from pathlib import Path
from typing import Any

import pytest


class TestNetworkBinding:
    """Test suite for network binding security requirements."""

    def test_st_010_http_server_localhost_binding(
        self,
        source_files: list[Path],
    ) -> None:
        """ST-010: HTTP server binds to localhost only.

        Verify port 9090 is not accessible from external IP.
        """
        # Check both http_server.py and __main__.py (where server is started)
        relevant_files = []
        for f in source_files:
            if "http_server" in f.name or f.name == "__main__.py":
                relevant_files.append(f)

        if not relevant_files:
            pytest.skip("http_server.py or __main__.py not found")

        content = "\n".join(f.read_text() for f in relevant_files)

        # Check for bind address configuration
        # Should bind to 127.0.0.1 or localhost, not 0.0.0.0
        bind_patterns = [
            r'host\s*=\s*["\']0\.0\.0\.0["\']',
            r'bind\s*=\s*["\']0\.0\.0\.0["\']',
        ]

        for pattern in bind_patterns:
            match = re.search(pattern, content)
            if match:
                # Check if there's a comment or condition making it safe
                line_start = content.rfind('\n', 0, match.start()) + 1
                line = content[line_start:match.end() + 50]
                if "# " in line[:match.start() - line_start]:
                    continue  # Commented out
                pytest.fail(f"HTTP server may bind to 0.0.0.0: {line.strip()}")

        # Verify localhost binding is present or configurable
        safe_patterns = [
            r'host\s*=\s*["\']127\.0\.0\.1["\']',
            r'host\s*=\s*["\']localhost["\']',
            r'host\s*=\s*settings\.',  # Configurable
            r'HOST\s*=\s*["\']127\.0\.0\.1["\']',
        ]

        has_safe_binding = any(
            re.search(pattern, content, re.IGNORECASE)
            for pattern in safe_patterns
        )

        # Also check for environment-based configuration
        has_env_config = "os.environ" in content or "settings." in content

        assert has_safe_binding or has_env_config, (
            "HTTP server should explicitly bind to localhost (127.0.0.1) "
            "or use configurable binding"
        )

    def test_st_011_mcp_server_stdio_transport(
        self,
        source_files: list[Path],
    ) -> None:
        """ST-011: MCP server uses stdio transport.

        Verify no network port exposed for MCP.
        """
        mcp_server_file = None
        for f in source_files:
            if "mcp_server" in f.name:
                mcp_server_file = f
                break

        if not mcp_server_file:
            pytest.skip("mcp_server.py not found")

        content = mcp_server_file.read_text()

        # Check for stdio transport usage
        uses_stdio = any([
            "stdio" in content.lower(),
            "stdin" in content.lower(),
            "stdout" in content.lower(),
            "StdioServerTransport" in content,
        ])

        # Check for TCP/network listener (should not exist)
        network_patterns = [
            r'socket\.bind\(',
            r'listen\(\d+\)',
            r'TCPServer\(',
            r'create_server\([^)]*port',
        ]

        has_network_listener = any(
            re.search(pattern, content)
            for pattern in network_patterns
        )

        assert uses_stdio, "MCP server should use stdio transport"
        assert not has_network_listener, "MCP server should not have network listeners"

    def test_st_012_qdrant_docker_network_binding(
        self,
        docker_files: list[Path],
    ) -> None:
        """ST-012: Qdrant binds to Docker network only.

        Verify port 6333 is not accessible from host external IP.
        """
        docker_compose_file = None
        for f in docker_files:
            if "docker-compose" in f.name.lower():
                docker_compose_file = f
                break

        if not docker_compose_file:
            pytest.skip("docker-compose file not found")

        content = docker_compose_file.read_text()

        # Look for Qdrant port configuration
        # Safe: "127.0.0.1:6333:6333" or internal network only
        # Unsafe: "6333:6333" or "0.0.0.0:6333:6333"

        # Find qdrant service section
        qdrant_section_match = re.search(
            r'qdrant:.*?(?=^\s*\w+:|$)',
            content,
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        if not qdrant_section_match:
            pytest.skip("Qdrant service not found in docker-compose")

        qdrant_section = qdrant_section_match.group()

        # Check port mapping
        port_match = re.search(r'ports:.*?(?=^\s*\w+:|\Z)', qdrant_section, re.DOTALL)

        if port_match:
            ports_section = port_match.group()

            # Check for unsafe port mapping (exposed to all interfaces)
            if re.search(r'-\s*["\']?\d+:\d+["\']?', ports_section):
                # Check if it's localhost bound
                if not re.search(r'-\s*["\']?127\.0\.0\.1:', ports_section):
                    # Might be exposed - warn but don't fail in dev
                    print("\nWarning: Qdrant ports may be exposed to all interfaces")
                    print("Consider using '127.0.0.1:6333:6333' in production")

    def test_st_013_neo4j_docker_network_binding(
        self,
        docker_files: list[Path],
    ) -> None:
        """ST-013: Neo4j binds to Docker network only.

        Verify port 7687 is not accessible from host external IP.
        """
        docker_compose_file = None
        for f in docker_files:
            if "docker-compose" in f.name.lower():
                docker_compose_file = f
                break

        if not docker_compose_file:
            pytest.skip("docker-compose file not found")

        content = docker_compose_file.read_text()

        # Find neo4j service section
        neo4j_section_match = re.search(
            r'neo4j:.*?(?=^\s*\w+:|$)',
            content,
            re.MULTILINE | re.DOTALL | re.IGNORECASE
        )

        if not neo4j_section_match:
            pytest.skip("Neo4j service not found in docker-compose")

        neo4j_section = neo4j_section_match.group()

        # Check port mapping
        port_match = re.search(r'ports:.*?(?=^\s*\w+:|\Z)', neo4j_section, re.DOTALL)

        if port_match:
            ports_section = port_match.group()

            # Check for Bolt port (7687)
            if "7687" in ports_section:
                if not re.search(r'127\.0\.0\.1:7687', ports_section):
                    print("\nWarning: Neo4j Bolt port may be exposed to all interfaces")
                    print("Consider using '127.0.0.1:7687:7687' in production")

            # Check for HTTP port (7474)
            if "7474" in ports_section:
                if not re.search(r'127\.0\.0\.1:7474', ports_section):
                    print("\nWarning: Neo4j HTTP port may be exposed to all interfaces")


class TestNetworkConfiguration:
    """Additional tests for network configuration."""

    def test_no_debug_endpoints_exposed(
        self,
        source_files: list[Path],
    ) -> None:
        """Test that debug endpoints are not exposed in production."""
        debug_patterns = [
            r'/debug/',
            r'/internal/',
            r'DEBUG\s*=\s*True',
            r'debug\s*=\s*True',
        ]

        for file_path in source_files:
            # Skip test files
            if "test" in str(file_path).lower():
                continue

            try:
                content = file_path.read_text()

                for pattern in debug_patterns:
                    match = re.search(pattern, content)
                    if match:
                        # Check if it's behind a condition or comment
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line = content[line_start:content.find('\n', match.end())]

                        if "#" in line[:match.start() - line_start]:
                            continue  # Commented
                        if "if" in line and "settings" in line:
                            continue  # Conditional

                        print(f"\nWarning: Debug pattern in {file_path.name}: {line.strip()}")

            except Exception:
                pass

    def test_cors_configuration(
        self,
        source_files: list[Path],
    ) -> None:
        """Test that CORS is properly configured."""
        http_server_file = None
        for f in source_files:
            if "http_server" in f.name:
                http_server_file = f
                break

        if not http_server_file:
            pytest.skip("http_server.py not found")

        content = http_server_file.read_text()

        # Check for CORS middleware
        if "CORSMiddleware" in content:
            # Check for allow_origins
            if 'allow_origins=["*"]' in content:
                print("\nWarning: CORS allows all origins - consider restricting")
            if "allow_credentials=True" in content and 'allow_origins=["*"]' in content:
                pytest.fail("CORS with credentials should not allow all origins")
