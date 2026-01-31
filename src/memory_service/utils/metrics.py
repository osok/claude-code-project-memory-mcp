"""Prometheus metrics for observability."""

from functools import lru_cache
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info


class Metrics:
    """Prometheus metrics for the memory service."""

    def __init__(self) -> None:
        """Initialize all metrics."""
        # Service info
        self.info = Info(
            "memory_service",
            "Memory service information",
        )
        self.info.info({"version": "0.1.0"})

        # Memory operations
        self.memory_operations_total = Counter(
            "memory_operations_total",
            "Total number of memory operations",
            ["operation", "memory_type", "status"],
        )

        self.memory_operation_duration_seconds = Histogram(
            "memory_operation_duration_seconds",
            "Duration of memory operations in seconds",
            ["operation", "memory_type"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # Search metrics
        self.search_requests_total = Counter(
            "search_requests_total",
            "Total number of search requests",
            ["search_type", "status"],
        )

        self.search_duration_seconds = Histogram(
            "search_duration_seconds",
            "Duration of search operations in seconds",
            ["search_type"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
        )

        self.search_results_count = Histogram(
            "search_results_count",
            "Number of results returned by search operations",
            ["search_type"],
            buckets=[0, 1, 5, 10, 25, 50, 100],
        )

        # Embedding metrics
        self.embedding_requests_total = Counter(
            "embedding_requests_total",
            "Total number of embedding generation requests",
            ["source", "status"],
        )

        self.embedding_cache_hits_total = Counter(
            "embedding_cache_hits_total",
            "Total number of embedding cache hits",
        )

        self.embedding_cache_misses_total = Counter(
            "embedding_cache_misses_total",
            "Total number of embedding cache misses",
        )

        self.embedding_duration_seconds = Histogram(
            "embedding_duration_seconds",
            "Duration of embedding generation in seconds",
            ["source"],
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        self.embedding_batch_size = Histogram(
            "embedding_batch_size",
            "Size of embedding batches",
            buckets=[1, 5, 10, 25, 50, 100, 128],
        )

        # Storage metrics
        self.storage_operations_total = Counter(
            "storage_operations_total",
            "Total number of storage operations",
            ["storage", "operation", "status"],
        )

        self.storage_operation_duration_seconds = Histogram(
            "storage_operation_duration_seconds",
            "Duration of storage operations in seconds",
            ["storage", "operation"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        # Sync metrics
        self.sync_pending_count = Gauge(
            "sync_pending_count",
            "Number of memories pending synchronization",
        )

        self.sync_failed_count = Gauge(
            "sync_failed_count",
            "Number of memories with failed synchronization",
        )

        self.sync_operations_total = Counter(
            "sync_operations_total",
            "Total number of sync operations",
            ["status"],
        )

        # Indexing metrics
        self.indexing_files_total = Counter(
            "indexing_files_total",
            "Total number of files indexed",
            ["language", "status"],
        )

        self.indexing_duration_seconds = Histogram(
            "indexing_duration_seconds",
            "Duration of file indexing in seconds",
            ["language"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        self.indexed_functions_total = Counter(
            "indexed_functions_total",
            "Total number of functions indexed",
            ["language"],
        )

        self.indexed_classes_total = Counter(
            "indexed_classes_total",
            "Total number of classes indexed",
            ["language"],
        )

        # Normalization metrics
        self.normalization_jobs_total = Counter(
            "normalization_jobs_total",
            "Total number of normalization jobs",
            ["status"],
        )

        self.normalization_duration_seconds = Histogram(
            "normalization_duration_seconds",
            "Duration of normalization jobs in seconds",
            buckets=[10, 30, 60, 120, 300, 600, 1800],
        )

        self.duplicates_merged_total = Counter(
            "duplicates_merged_total",
            "Total number of duplicate memories merged",
        )

        self.orphans_cleaned_total = Counter(
            "orphans_cleaned_total",
            "Total number of orphaned entries cleaned",
        )

        # Memory counts by type
        self.memory_count = Gauge(
            "memory_count",
            "Current count of memories by type",
            ["memory_type"],
        )

        # Connection health
        self.storage_connection_status = Gauge(
            "storage_connection_status",
            "Storage connection status (1=connected, 0=disconnected)",
            ["storage"],
        )

        # MCP tool metrics
        self.mcp_tool_calls_total = Counter(
            "mcp_tool_calls_total",
            "Total number of MCP tool calls",
            ["tool", "status"],
        )

        self.mcp_tool_duration_seconds = Histogram(
            "mcp_tool_duration_seconds",
            "Duration of MCP tool calls in seconds",
            ["tool"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

    def record_memory_operation(
        self,
        operation: str,
        memory_type: str,
        status: str,
        duration: float,
    ) -> None:
        """Record a memory operation metric.

        Args:
            operation: Operation name (add, update, delete, get)
            memory_type: Memory type name
            status: Operation status (success, error)
            duration: Operation duration in seconds
        """
        self.memory_operations_total.labels(
            operation=operation,
            memory_type=memory_type,
            status=status,
        ).inc()
        self.memory_operation_duration_seconds.labels(
            operation=operation,
            memory_type=memory_type,
        ).observe(duration)

    def record_search(
        self,
        search_type: str,
        status: str,
        duration: float,
        result_count: int,
    ) -> None:
        """Record a search operation metric.

        Args:
            search_type: Type of search (semantic, graph, hybrid)
            status: Search status (success, error)
            duration: Search duration in seconds
            result_count: Number of results returned
        """
        self.search_requests_total.labels(
            search_type=search_type,
            status=status,
        ).inc()
        self.search_duration_seconds.labels(
            search_type=search_type,
        ).observe(duration)
        self.search_results_count.labels(
            search_type=search_type,
        ).observe(result_count)

    def record_embedding(
        self,
        source: str,
        status: str,
        duration: float,
        batch_size: int = 1,
    ) -> None:
        """Record an embedding generation metric.

        Args:
            source: Embedding source (voyage, fallback, cache)
            status: Operation status (success, error)
            duration: Generation duration in seconds
            batch_size: Number of texts in batch
        """
        self.embedding_requests_total.labels(
            source=source,
            status=status,
        ).inc()
        self.embedding_duration_seconds.labels(
            source=source,
        ).observe(duration)
        self.embedding_batch_size.observe(batch_size)

    def record_mcp_tool_call(
        self,
        tool: str,
        status: str,
        duration: float,
    ) -> None:
        """Record an MCP tool call metric.

        Args:
            tool: Tool name
            status: Call status (success, error)
            duration: Call duration in seconds
        """
        self.mcp_tool_calls_total.labels(
            tool=tool,
            status=status,
        ).inc()
        self.mcp_tool_duration_seconds.labels(
            tool=tool,
        ).observe(duration)


@lru_cache
def get_metrics() -> Metrics:
    """Get cached metrics instance."""
    return Metrics()
