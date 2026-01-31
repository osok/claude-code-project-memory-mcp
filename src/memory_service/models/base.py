"""Base memory model and common types."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryType(str, Enum):
    """Memory type discriminator."""

    REQUIREMENTS = "requirements"
    DESIGN = "design"
    CODE_PATTERN = "code_pattern"
    COMPONENT = "component"
    FUNCTION = "function"
    TEST_HISTORY = "test_history"
    SESSION = "session"
    USER_PREFERENCE = "user_preference"


class SyncStatus(str, Enum):
    """Cross-store synchronization status."""

    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"


class BaseMemory(BaseModel):
    """Base memory model shared by all memory types.

    All memory types inherit from this base model which provides:
    - Unique identification
    - Content for embedding generation
    - Embedding vector storage
    - Timestamps and access tracking
    - Importance scoring
    - Cross-store sync status
    - Soft delete support
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    # Identity
    id: UUID = Field(default_factory=uuid4, description="Globally unique identifier (UUID v4)")
    type: MemoryType = Field(..., description="Memory type discriminator")

    # Content
    content: str = Field(..., min_length=1, description="Primary content for embedding generation")
    embedding: list[float] = Field(
        default_factory=list,
        description="Voyage-Code-3 embedding vector (1024 dimensions)",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp (ISO8601)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last modification timestamp (ISO8601)",
    )

    # Access tracking
    access_count: int = Field(default=0, ge=0, description="Number of times memory was retrieved")
    last_accessed_at: datetime | None = Field(default=None, description="Last access timestamp")

    # Scoring
    importance_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Priority for retrieval ranking (0.0-1.0)",
    )

    # Cross-store sync
    neo4j_node_id: str | None = Field(default=None, description="Reference to Neo4j node (if applicable)")
    sync_status: SyncStatus = Field(
        default=SyncStatus.SYNCED,
        description="Cross-store synchronization status",
    )

    # Soft delete
    deleted: bool = Field(default=False, description="Soft delete flag")
    deleted_at: datetime | None = Field(default=None, description="Soft delete timestamp (ISO8601)")

    # Extension point
    metadata: dict[str, Any] = Field(default_factory=dict, description="Type-specific additional data")

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, v: list[float]) -> list[float]:
        """Validate embedding has correct dimensions (1024 for voyage-code-3)."""
        if v and len(v) != 1024:
            raise ValueError(f"Embedding must have 1024 dimensions, got {len(v)}")
        return v

    def mark_deleted(self) -> None:
        """Mark the memory as soft-deleted."""
        self.deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def record_access(self) -> None:
        """Record an access to this memory."""
        self.access_count += 1
        self.last_accessed_at = datetime.now(timezone.utc)

    def update_timestamp(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def set_embedding(self, embedding: list[float]) -> None:
        """Set the embedding vector.

        Args:
            embedding: 1024-dimensional embedding vector
        """
        self.embedding = embedding
        self.update_timestamp()

    def mark_sync_pending(self) -> None:
        """Mark as pending synchronization."""
        self.sync_status = SyncStatus.PENDING

    def mark_sync_failed(self) -> None:
        """Mark synchronization as failed."""
        self.sync_status = SyncStatus.FAILED

    def mark_synced(self, neo4j_node_id: str | None = None) -> None:
        """Mark as successfully synchronized.

        Args:
            neo4j_node_id: Neo4j node ID if applicable
        """
        self.sync_status = SyncStatus.SYNCED
        if neo4j_node_id:
            self.neo4j_node_id = neo4j_node_id

    def to_qdrant_payload(self) -> dict[str, Any]:
        """Convert to Qdrant point payload.

        Returns:
            Dictionary suitable for Qdrant point payload
        """
        return self.model_dump(
            mode="json",
            exclude={"embedding"},
        )

    def to_neo4j_properties(self) -> dict[str, Any]:
        """Convert to Neo4j node properties.

        Neo4j only supports primitive types (str, int, float, bool) or
        arrays of primitives. Complex types (dicts, lists of dicts) are
        serialized to JSON strings.

        Returns:
            Dictionary suitable for Neo4j node properties
        """
        import json

        props = self.model_dump(
            mode="json",
            exclude={"embedding", "neo4j_node_id"},
        )
        # Convert id to string for Neo4j
        props["id"] = str(props["id"])

        # Serialize complex types to JSON strings for Neo4j compatibility
        def serialize_value(v: Any) -> Any:
            if v is None:
                return None
            if isinstance(v, dict):
                return json.dumps(v)
            if isinstance(v, list):
                # Check if list contains complex types
                if v and isinstance(v[0], (dict, list)):
                    return json.dumps(v)
                # List of primitives or UUIDs - convert to list of strings
                return [str(item) if not isinstance(item, (str, int, float, bool)) else item for item in v]
            if isinstance(v, (str, int, float, bool)):
                return v
            # Any other type - convert to string
            return str(v)

        return {k: serialize_value(v) for k, v in props.items()}
