"""Relationship model for graph database edges."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RelationshipType(str, Enum):
    """Types of relationships between entities in the graph.

    These relationship types model the connections between code elements,
    requirements, designs, and other memory types.
    """

    # Code relationships
    CALLS = "CALLS"
    """Function A calls function B."""

    IMPORTS = "IMPORTS"
    """Module A imports module B."""

    EXTENDS = "EXTENDS"
    """Class A extends class B (inheritance)."""

    IMPLEMENTS = "IMPLEMENTS"
    """Class A implements interface B."""

    DEPENDS_ON = "DEPENDS_ON"
    """Component A depends on component B."""

    CONTAINS = "CONTAINS"
    """Class A contains method B; Module A contains class B."""

    USES = "USES"
    """Function A uses type/class B."""

    # Requirement relationships
    DERIVED_FROM = "DERIVED_FROM"
    """Requirement A is derived from requirement B."""

    SATISFIED_BY = "SATISFIED_BY"
    """Requirement A is satisfied by component B."""

    TESTED_BY = "TESTED_BY"
    """Requirement A is tested by test B."""

    # Design relationships
    ADDRESSES = "ADDRESSES"
    """Design decision A addresses requirement B."""

    AFFECTS = "AFFECTS"
    """Design decision A affects component B."""

    SUPERSEDES = "SUPERSEDES"
    """Design A supersedes design B."""

    # Pattern relationships
    FOLLOWS_PATTERN = "FOLLOWS_PATTERN"
    """Component A follows pattern B."""

    DEVIATES_FROM = "DEVIATES_FROM"
    """Component A deviates from pattern B."""

    # Session relationships
    CREATED_IN = "CREATED_IN"
    """Memory A was created in session B."""

    MODIFIED_IN = "MODIFIED_IN"
    """Memory A was modified in session B."""

    # General relationships
    RELATED_TO = "RELATED_TO"
    """Generic relationship between two entities."""

    SIMILAR_TO = "SIMILAR_TO"
    """Entity A is semantically similar to entity B."""


class Relationship(BaseModel):
    """A relationship (edge) between two entities in the graph.

    Represents a directed edge from source to target with a specific type
    and optional properties.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )

    id: UUID = Field(default_factory=uuid4, description="Unique relationship identifier")
    type: RelationshipType = Field(..., description="Type of relationship")
    source_id: UUID = Field(..., description="Source entity ID")
    target_id: UUID = Field(..., description="Target entity ID")

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Relationship creation timestamp",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional relationship properties",
    )

    # Confidence/strength
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relationship strength/confidence (0.0-1.0)",
    )

    # Provenance
    source_label: str | None = Field(default=None, description="Neo4j label for source node")
    target_label: str | None = Field(default=None, description="Neo4j label for target node")

    def to_cypher_create(self, source_var: str = "a", target_var: str = "b") -> str:
        """Generate Cypher CREATE statement for this relationship.

        Args:
            source_var: Variable name for source node
            target_var: Variable name for target node

        Returns:
            Cypher CREATE clause
        """
        props = {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "weight": self.weight,
            **self.properties,
        }
        props_str = ", ".join(f"{k}: ${k}" for k in props.keys())
        return f"CREATE ({source_var})-[:{self.type} {{{props_str}}}]->({target_var})"

    def to_neo4j_properties(self) -> dict[str, Any]:
        """Convert to Neo4j relationship properties.

        Returns:
            Dictionary suitable for Neo4j relationship properties
        """
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "weight": self.weight,
            **self.properties,
        }

    @classmethod
    def code_call(
        cls,
        caller_id: UUID,
        callee_id: UUID,
        line: int | None = None,
    ) -> "Relationship":
        """Create a CALLS relationship between functions.

        Args:
            caller_id: ID of the calling function
            callee_id: ID of the called function
            line: Line number of the call

        Returns:
            CALLS relationship
        """
        props = {"line": line} if line else {}
        return cls(
            type=RelationshipType.CALLS,
            source_id=caller_id,
            target_id=callee_id,
            properties=props,
        )

    @classmethod
    def code_import(
        cls,
        importer_id: UUID,
        imported_id: UUID,
        import_name: str | None = None,
    ) -> "Relationship":
        """Create an IMPORTS relationship.

        Args:
            importer_id: ID of the importing module
            imported_id: ID of the imported module
            import_name: Specific name imported

        Returns:
            IMPORTS relationship
        """
        props = {"import_name": import_name} if import_name else {}
        return cls(
            type=RelationshipType.IMPORTS,
            source_id=importer_id,
            target_id=imported_id,
            properties=props,
        )

    @classmethod
    def inheritance(
        cls,
        child_id: UUID,
        parent_id: UUID,
    ) -> "Relationship":
        """Create an EXTENDS relationship for class inheritance.

        Args:
            child_id: ID of the child class
            parent_id: ID of the parent class

        Returns:
            EXTENDS relationship
        """
        return cls(
            type=RelationshipType.EXTENDS,
            source_id=child_id,
            target_id=parent_id,
        )

    @classmethod
    def containment(
        cls,
        container_id: UUID,
        contained_id: UUID,
    ) -> "Relationship":
        """Create a CONTAINS relationship.

        Args:
            container_id: ID of the container (class, module)
            contained_id: ID of the contained element (method, class)

        Returns:
            CONTAINS relationship
        """
        return cls(
            type=RelationshipType.CONTAINS,
            source_id=container_id,
            target_id=contained_id,
        )

    @classmethod
    def requirement_satisfaction(
        cls,
        requirement_id: UUID,
        component_id: UUID,
        coverage: float = 1.0,
    ) -> "Relationship":
        """Create a SATISFIED_BY relationship.

        Args:
            requirement_id: ID of the requirement
            component_id: ID of the satisfying component
            coverage: Coverage percentage (0.0-1.0)

        Returns:
            SATISFIED_BY relationship
        """
        return cls(
            type=RelationshipType.SATISFIED_BY,
            source_id=requirement_id,
            target_id=component_id,
            weight=coverage,
        )

    @classmethod
    def similarity(
        cls,
        entity_a_id: UUID,
        entity_b_id: UUID,
        similarity_score: float,
    ) -> "Relationship":
        """Create a SIMILAR_TO relationship.

        Args:
            entity_a_id: ID of first entity
            entity_b_id: ID of second entity
            similarity_score: Similarity score (0.0-1.0)

        Returns:
            SIMILAR_TO relationship
        """
        return cls(
            type=RelationshipType.SIMILAR_TO,
            source_id=entity_a_id,
            target_id=entity_b_id,
            weight=similarity_score,
            properties={"similarity_score": similarity_score},
        )
