"""MCP tool implementations."""

from memory_service.api.tools.memory_crud import (
    memory_add,
    memory_bulk_add,
    memory_delete,
    memory_get,
    memory_update,
)
from memory_service.api.tools.search import (
    code_search,
    find_duplicates,
    get_related,
    graph_query,
    memory_search,
)
from memory_service.api.tools.indexing import (
    index_directory,
    index_file,
    index_status,
    reindex,
)
from memory_service.api.tools.analysis import (
    check_consistency,
    get_design_context,
    trace_requirements,
    validate_fix,
)
from memory_service.api.tools.maintenance import (
    export_memory,
    import_memory,
    memory_statistics,
    normalize_memory,
    normalize_status,
)

__all__ = [
    # Memory CRUD
    "memory_add",
    "memory_update",
    "memory_delete",
    "memory_get",
    "memory_bulk_add",
    # Search
    "memory_search",
    "code_search",
    "graph_query",
    "find_duplicates",
    "get_related",
    # Indexing
    "index_file",
    "index_directory",
    "index_status",
    "reindex",
    # Analysis
    "check_consistency",
    "validate_fix",
    "get_design_context",
    "trace_requirements",
    # Maintenance
    "normalize_memory",
    "normalize_status",
    "memory_statistics",
    "export_memory",
    "import_memory",
]
