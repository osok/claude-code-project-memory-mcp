"""Performance tests for graph traversal latency (PT-010 to PT-013).

Tests measure graph traversal and query latency against targets:
- PT-010: 1-hop traversal P95 < 100ms (100K nodes)
- PT-011: 2-hop traversal P95 < 150ms (100K nodes)
- PT-012: 3-hop traversal P95 < 200ms (100K nodes)
- PT-013: Complex Cypher query < 500ms (100K nodes, multiple conditions)
"""

import asyncio
import random
import time
from uuid import uuid4

import pytest

from memory_service.models import MemoryType, RelationshipType
from memory_service.storage.neo4j_adapter import Neo4jAdapter
from memory_service.core.query_engine import QueryEngine

from .conftest import (
    PerformanceMetrics,
    create_test_function_memory,
    create_test_component_memory,
)


# Reduced counts for CI - scale up for production testing
NODE_COUNT = 1000  # Use 100000 for full test
QUERY_COUNT = 50  # Use 100 for full test


class TestGraphTraversalLatency:
    """Test suite for graph traversal latency requirements."""

    @pytest.fixture
    async def populated_graph(
        self,
        neo4j_adapter: Neo4jAdapter,
    ) -> tuple[Neo4jAdapter, list[str]]:
        """Populate Neo4j with test nodes and relationships."""
        # Create nodes in batches
        node_ids: list[str] = []

        for i in range(NODE_COUNT):
            node_id = str(uuid4())
            node_ids.append(node_id)

            # Use correct API: create_node(label, properties)
            await neo4j_adapter.create_node(
                label="Function",
                properties={
                    "id": node_id,
                    "memory_id": node_id,
                    "memory_type": "function",
                    "name": f"function_{i}",
                    "file_path": f"src/module_{i // 100}/file_{i}.py",
                },
            )

        # Create relationships (chain-like structure for depth testing)
        for i, node_id in enumerate(node_ids):
            if i > 0:
                # Connect to previous node
                await neo4j_adapter.create_relationship(
                    source_id=node_ids[i - 1],
                    target_id=node_ids[i],
                    relationship_type=RelationshipType.CALLS,
                    properties={"line": i * 10},
                )

            # Add some cross-connections
            if i > 10 and random.random() < 0.3:
                target_idx = random.randint(0, i - 1)
                await neo4j_adapter.create_relationship(
                    source_id=node_id,
                    target_id=node_ids[target_idx],
                    relationship_type=RelationshipType.IMPORTS,
                    properties={},
                )

        return neo4j_adapter, node_ids

    @pytest.mark.asyncio
    async def test_pt_010_one_hop_traversal(
        self,
        populated_graph: tuple[Neo4jAdapter, list[str]],
        query_engine: QueryEngine,
    ) -> None:
        """PT-010: 1-hop traversal P95 < 100ms.

        Target: Single hop relationship traversal under 100ms.
        """
        neo4j_adapter, node_ids = populated_graph
        metrics = PerformanceMetrics()

        # Use first 100 node IDs for testing
        test_node_ids = node_ids[:100]

        for _ in range(QUERY_COUNT):
            start_id = random.choice(test_node_ids)

            start = time.perf_counter()
            results = await query_engine.get_related(
                entity_id=start_id,
                relationship_types=[RelationshipType.CALLS, RelationshipType.IMPORTS],
                depth=1,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-010: 1-hop traversal P95 = {p95:.2f}ms (target: <100ms)")
        print(f"  Mean = {metrics.mean():.2f}ms, Count = {metrics.count()}")

        assert p95 < 100, f"P95 {p95:.2f}ms exceeds target 100ms"

    @pytest.mark.asyncio
    async def test_pt_011_two_hop_traversal(
        self,
        populated_graph: tuple[Neo4jAdapter, list[str]],
        query_engine: QueryEngine,
    ) -> None:
        """PT-011: 2-hop traversal P95 < 150ms.

        Target: Two hop relationship traversal under 150ms.
        """
        neo4j_adapter, node_ids = populated_graph
        metrics = PerformanceMetrics()
        test_node_ids = node_ids[:100]

        for _ in range(QUERY_COUNT):
            start_id = random.choice(test_node_ids)

            start = time.perf_counter()
            results = await query_engine.get_related(
                entity_id=start_id,
                relationship_types=[RelationshipType.CALLS, RelationshipType.IMPORTS],
                depth=2,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-011: 2-hop traversal P95 = {p95:.2f}ms (target: <150ms)")

        assert p95 < 150, f"P95 {p95:.2f}ms exceeds target 150ms"

    @pytest.mark.asyncio
    async def test_pt_012_three_hop_traversal(
        self,
        populated_graph: tuple[Neo4jAdapter, list[str]],
        query_engine: QueryEngine,
    ) -> None:
        """PT-012: 3-hop traversal P95 < 200ms.

        Target: Three hop relationship traversal under 200ms.
        """
        neo4j_adapter, node_ids = populated_graph
        metrics = PerformanceMetrics()
        test_node_ids = node_ids[:100]

        for _ in range(QUERY_COUNT):
            start_id = random.choice(test_node_ids)

            start = time.perf_counter()
            results = await query_engine.get_related(
                entity_id=start_id,
                relationship_types=[RelationshipType.CALLS, RelationshipType.IMPORTS],
                depth=3,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-012: 3-hop traversal P95 = {p95:.2f}ms (target: <200ms)")

        assert p95 < 200, f"P95 {p95:.2f}ms exceeds target 200ms"

    @pytest.mark.asyncio
    async def test_pt_013_complex_cypher_query(
        self,
        populated_graph: tuple[Neo4jAdapter, list[str]],
        query_engine: QueryEngine,
    ) -> None:
        """PT-013: Complex Cypher query < 500ms.

        Target: Complex query with multiple conditions under 500ms.
        """
        neo4j_adapter, node_ids = populated_graph
        metrics = PerformanceMetrics()

        for _ in range(QUERY_COUNT):
            # Complex query with multiple conditions
            query = """
            MATCH (n:Function)-[r:CALLS|IMPORTS]->(m:Memory)
            WHERE n.memory_type = $type
            AND n.name IS NOT NULL
            RETURN n.memory_id as source,
                   type(r) as relationship,
                   m.memory_id as target,
                   m.name as target_name
            LIMIT 50
            """

            start = time.perf_counter()
            results = await query_engine.graph_query(
                cypher=query,
                parameters={"type": "function"},
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPT-013: Complex Cypher query P95 = {p95:.2f}ms (target: <500ms)")

        assert p95 < 500, f"P95 {p95:.2f}ms exceeds target 500ms"


class TestGraphQueryPatterns:
    """Additional tests for graph query patterns."""

    @pytest.mark.asyncio
    async def test_path_finding_query(
        self,
        neo4j_adapter: Neo4jAdapter,
        query_engine: QueryEngine,
    ) -> None:
        """Test path finding between nodes."""
        # Create a small graph
        node_ids = []
        for i in range(100):
            node_id = str(uuid4())
            node_ids.append(node_id)
            await neo4j_adapter.create_node(
                label="Function",
                properties={
                    "id": node_id,
                    "memory_id": node_id,
                    "memory_type": "function",
                    "name": f"func_{i}",
                },
            )

        # Create chain
        for i in range(len(node_ids) - 1):
            await neo4j_adapter.create_relationship(
                source_id=node_ids[i],
                target_id=node_ids[i + 1],
                relationship_type=RelationshipType.CALLS,
                properties={},
            )

        metrics = PerformanceMetrics()

        for _ in range(20):
            # Find path between two random nodes
            start_idx = random.randint(0, 50)
            end_idx = random.randint(51, 99)

            query = """
            MATCH path = shortestPath(
                (start:Memory {memory_id: $start_id})-[*..10]->(end:Memory {memory_id: $end_id})
            )
            RETURN length(path) as path_length,
                   [n in nodes(path) | n.name] as node_names
            """

            start = time.perf_counter()
            results = await query_engine.graph_query(
                cypher=query,
                parameters={"start_id": node_ids[start_idx], "end_id": node_ids[end_idx]},
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nPath finding P95 = {p95:.2f}ms")

        # Path finding can be slower but should still be reasonable
        assert p95 < 500, f"Path finding P95 {p95:.2f}ms too slow"

    @pytest.mark.asyncio
    async def test_aggregation_query(
        self,
        neo4j_adapter: Neo4jAdapter,
        query_engine: QueryEngine,
    ) -> None:
        """Test aggregation queries."""
        # Create nodes with varying properties
        for i in range(200):
            node_id = str(uuid4())
            label = "Function" if i % 2 == 0 else "Component"
            memory_type = "function" if i % 2 == 0 else "component"
            await neo4j_adapter.create_node(
                label=label,
                properties={
                    "id": node_id,
                    "memory_id": node_id,
                    "memory_type": memory_type,
                    "name": f"item_{i}",
                    "module": f"module_{i % 10}",
                },
            )

        metrics = PerformanceMetrics()

        for _ in range(20):
            query = """
            MATCH (n:Memory)
            WHERE n.memory_type IN ['function', 'component']
            RETURN n.memory_type as type,
                   count(n) as count,
                   collect(n.module)[..5] as sample_modules
            """

            start = time.perf_counter()
            results = await query_engine.graph_query(cypher=query, parameters={})
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.add(duration_ms)

        p95 = metrics.p95()
        print(f"\nAggregation query P95 = {p95:.2f}ms")

        assert p95 < 200, f"Aggregation query P95 {p95:.2f}ms too slow"
