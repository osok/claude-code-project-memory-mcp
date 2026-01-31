"""Neo4j graph database adapter."""

import asyncio
from typing import Any
from uuid import UUID

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import Neo4jError

from memory_service.models import MemoryType, RelationshipType
from memory_service.utils.logging import get_logger
from memory_service.utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()

# Node labels for each memory type
NODE_LABELS = {
    MemoryType.REQUIREMENTS: "Requirement",
    MemoryType.DESIGN: "Design",
    MemoryType.CODE_PATTERN: "CodePattern",
    MemoryType.COMPONENT: "Component",
    MemoryType.FUNCTION: "Function",
    MemoryType.TEST_HISTORY: "TestHistory",
    MemoryType.SESSION: "Session",
    MemoryType.USER_PREFERENCE: "UserPreference",
}


class Neo4jAdapter:
    """Adapter for Neo4j graph database operations.

    Provides methods for:
    - Connection management with health checks
    - Schema/index initialization
    - Node CRUD operations
    - Relationship management
    - Graph traversal queries
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: Any = "",
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
    ) -> None:
        """Initialize Neo4j adapter.

        Args:
            uri: Neo4j connection URI
            user: Database username
            password: Database password
            database: Database name
            max_connection_pool_size: Connection pool size
        """
        self.uri = uri
        self.database = database

        # Extract secret value if SecretStr
        password_value = password.get_secret_value() if hasattr(password, "get_secret_value") else password

        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password_value),
            max_connection_pool_size=max_connection_pool_size,
        )
        logger.info("neo4j_adapter_initialized", uri=uri, database=database)

    async def health_check(self) -> bool:
        """Check if Neo4j is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with self._driver.session(database=self.database) as session:
                await session.run("RETURN 1")
            metrics.storage_connection_status.labels(storage="neo4j").set(1)
            return True
        except Exception as e:
            logger.error("neo4j_health_check_failed", error=str(e))
            metrics.storage_connection_status.labels(storage="neo4j").set(0)
            return False

    async def initialize_schema(self) -> None:
        """Initialize Neo4j schema with indexes and constraints."""
        async with self._driver.session(database=self.database) as session:
            # Create unique constraint on id for each node label
            for memory_type, label in NODE_LABELS.items():
                try:
                    await session.run(
                        f"CREATE CONSTRAINT {label.lower()}_id_unique IF NOT EXISTS "
                        f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                    )
                    logger.debug("neo4j_constraint_created", label=label)
                except Neo4jError as e:
                    if "already exists" not in str(e):
                        raise

            # Create indexes for common query patterns
            indexes = [
                # Memory type indexes
                ("Memory", "type"),
                ("Memory", "sync_status"),
                ("Memory", "deleted"),
                # Specific type indexes
                ("Requirement", "requirement_id"),
                ("Requirement", "status"),
                ("Design", "design_type"),
                ("Design", "status"),
                ("Component", "component_type"),
                ("Function", "name"),
                ("Function", "file_path"),
            ]

            for label, property_name in indexes:
                try:
                    await session.run(
                        f"CREATE INDEX {label.lower()}_{property_name}_idx IF NOT EXISTS "
                        f"FOR (n:{label}) ON (n.{property_name})"
                    )
                except Neo4jError as e:
                    if "already exists" not in str(e):
                        logger.warning("neo4j_index_creation_warning", error=str(e))

            logger.info("neo4j_schema_initialized")

    async def create_node(
        self,
        label: str,
        properties: dict[str, Any],
    ) -> str:
        """Create a node with the given label and properties.

        Args:
            label: Node label
            properties: Node properties

        Returns:
            Node ID
        """
        import time

        start = time.perf_counter()

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"CREATE (n:{label}:Memory $props) RETURN n.id as id",
                    props=properties,
                )
                record = await result.single()

                duration = time.perf_counter() - start
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="create_node",
                    status="success",
                ).inc()
                metrics.storage_operation_duration_seconds.labels(
                    storage="neo4j",
                    operation="create_node",
                ).observe(duration)

                return record["id"] if record else properties.get("id", "")

            except Neo4jError as e:
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="create_node",
                    status="error",
                ).inc()
                logger.error("neo4j_create_node_failed", label=label, error=str(e))
                raise

    async def get_node(
        self,
        node_id: str | UUID,
        label: str | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve a node by ID.

        Args:
            node_id: Node ID
            label: Optional label to filter by

        Returns:
            Node properties or None if not found
        """
        label_filter = f":{label}" if label else ""

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"MATCH (n{label_filter}:Memory {{id: $id}}) RETURN properties(n) as props",
                    id=str(node_id),
                )
                record = await result.single()
                return dict(record["props"]) if record else None

            except Neo4jError as e:
                logger.error("neo4j_get_node_failed", node_id=str(node_id), error=str(e))
                raise

    async def update_node(
        self,
        node_id: str | UUID,
        properties: dict[str, Any],
        label: str | None = None,
    ) -> bool:
        """Update node properties.

        Args:
            node_id: Node ID
            properties: Properties to update
            label: Optional label to filter by

        Returns:
            True if updated
        """
        label_filter = f":{label}" if label else ""

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"MATCH (n{label_filter}:Memory {{id: $id}}) SET n += $props RETURN n",
                    id=str(node_id),
                    props=properties,
                )
                record = await result.single()

                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="update_node",
                    status="success" if record else "not_found",
                ).inc()

                return record is not None

            except Neo4jError as e:
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="update_node",
                    status="error",
                ).inc()
                logger.error("neo4j_update_node_failed", node_id=str(node_id), error=str(e))
                raise

    async def delete_node(
        self,
        node_id: str | UUID,
        label: str | None = None,
        detach: bool = True,
    ) -> bool:
        """Delete a node by ID.

        Args:
            node_id: Node ID
            label: Optional label to filter by
            detach: Whether to delete relationships (DETACH DELETE)

        Returns:
            True if deleted
        """
        label_filter = f":{label}" if label else ""
        delete_cmd = "DETACH DELETE" if detach else "DELETE"

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"MATCH (n{label_filter}:Memory {{id: $id}}) {delete_cmd} n RETURN count(n) as deleted",
                    id=str(node_id),
                )
                record = await result.single()

                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="delete_node",
                    status="success",
                ).inc()

                return record["deleted"] > 0 if record else False

            except Neo4jError as e:
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="delete_node",
                    status="error",
                ).inc()
                logger.error("neo4j_delete_node_failed", node_id=str(node_id), error=str(e))
                raise

    async def create_relationship(
        self,
        source_id: str | UUID,
        target_id: str | UUID,
        relationship_type: RelationshipType | str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Create a relationship between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Type of relationship
            properties: Relationship properties

        Returns:
            True if created
        """
        rel_type = relationship_type.value if isinstance(relationship_type, RelationshipType) else relationship_type
        props = properties or {}

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"""
                    MATCH (a:Memory {{id: $source_id}})
                    MATCH (b:Memory {{id: $target_id}})
                    CREATE (a)-[r:{rel_type} $props]->(b)
                    RETURN r
                    """,
                    source_id=str(source_id),
                    target_id=str(target_id),
                    props=props,
                )
                record = await result.single()

                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="create_relationship",
                    status="success" if record else "not_found",
                ).inc()

                return record is not None

            except Neo4jError as e:
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="create_relationship",
                    status="error",
                ).inc()
                logger.error("neo4j_create_relationship_failed", error=str(e))
                raise

    async def delete_relationship(
        self,
        source_id: str | UUID,
        target_id: str | UUID,
        relationship_type: RelationshipType | str | None = None,
    ) -> int:
        """Delete relationships between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Optional type filter

        Returns:
            Number of relationships deleted
        """
        rel_filter = f":{relationship_type.value if isinstance(relationship_type, RelationshipType) else relationship_type}" if relationship_type else ""

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"""
                    MATCH (a:Memory {{id: $source_id}})-[r{rel_filter}]->(b:Memory {{id: $target_id}})
                    DELETE r
                    RETURN count(r) as deleted
                    """,
                    source_id=str(source_id),
                    target_id=str(target_id),
                )
                record = await result.single()
                return record["deleted"] if record else 0

            except Neo4jError as e:
                logger.error("neo4j_delete_relationship_failed", error=str(e))
                raise

    async def get_related(
        self,
        node_id: str | UUID,
        relationship_types: list[RelationshipType | str] | None = None,
        direction: str = "both",
        depth: int = 1,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get nodes related to a given node.

        Args:
            node_id: Starting node ID
            relationship_types: Filter by relationship types
            direction: "outgoing", "incoming", or "both"
            depth: Maximum traversal depth
            limit: Maximum results

        Returns:
            List of related nodes with relationship info
        """
        import time

        start = time.perf_counter()

        # Build relationship pattern
        rel_types = ""
        if relationship_types:
            type_strs = [
                r.value if isinstance(r, RelationshipType) else r
                for r in relationship_types
            ]
            rel_types = ":" + "|".join(type_strs)

        # Build direction pattern
        if direction == "outgoing":
            pattern = f"-[r{rel_types}*1..{depth}]->"
        elif direction == "incoming":
            pattern = f"<-[r{rel_types}*1..{depth}]-"
        else:
            pattern = f"-[r{rel_types}*1..{depth}]-"

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"""
                    MATCH (start:Memory {{id: $id}}){pattern}(related:Memory)
                    WHERE related.id <> $id
                    RETURN DISTINCT
                        related.id as id,
                        labels(related) as labels,
                        properties(related) as properties,
                        type(r[-1]) as relationship_type
                    LIMIT $limit
                    """,
                    id=str(node_id),
                    limit=limit,
                )

                records = await result.data()

                duration = time.perf_counter() - start
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="get_related",
                    status="success",
                ).inc()
                metrics.storage_operation_duration_seconds.labels(
                    storage="neo4j",
                    operation="get_related",
                ).observe(duration)

                return [
                    {
                        "id": r["id"],
                        "labels": r["labels"],
                        "properties": r["properties"],
                        "relationship_type": r["relationship_type"],
                    }
                    for r in records
                ]

            except Neo4jError as e:
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="get_related",
                    status="error",
                ).inc()
                logger.error("neo4j_get_related_failed", node_id=str(node_id), error=str(e))
                raise

    async def execute_cypher(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query results as list of dictionaries
        """
        import time

        start = time.perf_counter()

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(query, parameters or {})
                records = await result.data()

                duration = time.perf_counter() - start
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="execute_cypher",
                    status="success",
                ).inc()
                metrics.storage_operation_duration_seconds.labels(
                    storage="neo4j",
                    operation="execute_cypher",
                ).observe(duration)

                return records

            except Neo4jError as e:
                metrics.storage_operations_total.labels(
                    storage="neo4j",
                    operation="execute_cypher",
                    status="error",
                ).inc()
                logger.error("neo4j_execute_cypher_failed", error=str(e))
                raise

    async def find_path(
        self,
        start_id: str | UUID,
        end_id: str | UUID,
        relationship_types: list[RelationshipType | str] | None = None,
        max_depth: int = 5,
    ) -> list[dict[str, Any]] | None:
        """Find shortest path between two nodes.

        Args:
            start_id: Starting node ID
            end_id: Ending node ID
            relationship_types: Filter by relationship types
            max_depth: Maximum path length

        Returns:
            Path as list of nodes, or None if no path exists
        """
        rel_types = ""
        if relationship_types:
            type_strs = [
                r.value if isinstance(r, RelationshipType) else r
                for r in relationship_types
            ]
            rel_types = ":" + "|".join(type_strs)

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"""
                    MATCH path = shortestPath(
                        (start:Memory {{id: $start_id}})-[{rel_types}*1..{max_depth}]-(end:Memory {{id: $end_id}})
                    )
                    RETURN [node in nodes(path) | {{id: node.id, labels: labels(node), properties: properties(node)}}] as path
                    """,
                    start_id=str(start_id),
                    end_id=str(end_id),
                )
                record = await result.single()
                return record["path"] if record else None

            except Neo4jError as e:
                logger.error("neo4j_find_path_failed", error=str(e))
                raise

    async def count_nodes(
        self,
        label: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count nodes matching criteria.

        Args:
            label: Optional label filter
            filters: Optional property filters

        Returns:
            Node count
        """
        label_filter = f":{label}" if label else ""
        where_clause = ""
        params: dict[str, Any] = {}

        if filters:
            conditions = []
            for i, (key, value) in enumerate(filters.items()):
                param_name = f"p{i}"
                conditions.append(f"n.{key} = ${param_name}")
                params[param_name] = value
            where_clause = "WHERE " + " AND ".join(conditions)

        async with self._driver.session(database=self.database) as session:
            try:
                result = await session.run(
                    f"MATCH (n{label_filter}:Memory) {where_clause} RETURN count(n) as count",
                    **params,
                )
                record = await result.single()
                return record["count"] if record else 0

            except Neo4jError as e:
                logger.error("neo4j_count_nodes_failed", error=str(e))
                raise

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        try:
            await self._driver.close()
            logger.info("neo4j_connection_closed")
        except Exception as e:
            logger.error("neo4j_close_failed", error=str(e))

    def get_node_label(self, memory_type: MemoryType) -> str:
        """Get Neo4j node label for a memory type.

        Args:
            memory_type: Memory type

        Returns:
            Node label
        """
        return NODE_LABELS[memory_type]
