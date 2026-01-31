"""Memory type implementations for all 8 memory types."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from memory_service.models.base import BaseMemory, MemoryType


# =============================================================================
# Requirements Memory
# =============================================================================


class RequirementPriority(str, Enum):
    """Requirement priority levels."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RequirementStatus(str, Enum):
    """Requirement implementation status."""

    DRAFT = "Draft"
    APPROVED = "Approved"
    IMPLEMENTED = "Implemented"
    VERIFIED = "Verified"


class RequirementsMemory(BaseMemory):
    """Memory type for storing parsed requirements documents with traceability.

    Stores requirements from ISO 29148-style requirement documents,
    enabling traceability from requirements to code and tests.
    """

    type: MemoryType = Field(default=MemoryType.REQUIREMENTS, frozen=True)

    requirement_id: str = Field(
        ...,
        pattern=r"^REQ-[A-Z]{2,}(-[A-Z]{2,})*-\d{3,}$",
        description="Requirement identifier (e.g., REQ-MEM-FN-001 or REQ-AUTH-001)",
    )
    title: str = Field(..., min_length=1, description="Requirement title")
    description: str = Field(..., min_length=1, description="Full requirement text")
    priority: RequirementPriority = Field(..., description="Requirement priority level")
    status: RequirementStatus = Field(..., description="Implementation status")
    source_document: str = Field(..., description="Source file path (relative to project root)")
    implementing_components: list[UUID] = Field(
        default_factory=list,
        description="Component IDs that implement this requirement",
    )

    @field_validator("requirement_id")
    @classmethod
    def validate_requirement_id(cls, v: str) -> str:
        """Validate requirement ID format."""
        parts = v.split("-")
        if len(parts) < 4:
            raise ValueError(f"Invalid requirement ID format: {v}")
        return v


# =============================================================================
# Design Memory
# =============================================================================


class DesignType(str, Enum):
    """Types of design documents."""

    ADR = "ADR"
    SPECIFICATION = "Specification"
    ARCHITECTURE = "Architecture"
    INTERFACE = "Interface"


class DesignStatus(str, Enum):
    """Design decision status."""

    PROPOSED = "Proposed"
    ACCEPTED = "Accepted"
    DEPRECATED = "Deprecated"
    SUPERSEDED = "Superseded"


class DesignMemory(BaseMemory):
    """Memory type for storing architectural decisions, ADRs, and design documents.

    Stores design decisions and their rationale, enabling validation that
    implementations align with intended architecture.
    """

    type: MemoryType = Field(default=MemoryType.DESIGN, frozen=True)

    design_type: DesignType = Field(..., description="Type of design document")
    title: str = Field(..., min_length=1, description="Design document title")
    decision: str | None = Field(default=None, description="ADR decision text (required for ADR type)")
    rationale: str | None = Field(default=None, description="Reasoning for the design decision")
    consequences: str | None = Field(default=None, description="Trade-offs and implications")
    related_requirements: list[str] = Field(
        default_factory=list,
        description="Requirement IDs this design addresses",
    )
    affected_components: list[UUID] = Field(
        default_factory=list,
        description="Component IDs affected by this design",
    )
    status: DesignStatus = Field(..., description="Design decision status")


# =============================================================================
# Code Pattern Memory
# =============================================================================


class PatternType(str, Enum):
    """Categories of code patterns."""

    TEMPLATE = "Template"
    CONVENTION = "Convention"
    IDIOM = "Idiom"
    ARCHITECTURE = "Architecture"


class CodePatternMemory(BaseMemory):
    """Memory type for storing reusable implementation templates and conventions.

    Enables consistency checking against established patterns and provides
    templates for code generation.
    """

    type: MemoryType = Field(default=MemoryType.CODE_PATTERN, frozen=True)

    pattern_name: str = Field(..., min_length=1, description="Human-readable pattern name")
    pattern_type: PatternType = Field(..., description="Category of code pattern")
    language: str = Field(..., description="Programming language (e.g., Python, TypeScript)")
    code_template: str = Field(..., min_length=1, description="Template code with placeholders")
    usage_context: str = Field(..., min_length=1, description="When and how to apply this pattern")
    applicable_components: list[str] = Field(
        default_factory=list,
        description="Component types this pattern applies to",
    )
    example_implementations: list[str] = Field(
        default_factory=list,
        description="File paths of example implementations",
    )


# =============================================================================
# Component Memory
# =============================================================================


class ComponentType(str, Enum):
    """Categories of system components."""

    FRONTEND = "Frontend"
    BACKEND = "Backend"
    AGENT = "Agent"
    LIBRARY = "Library"
    SERVICE = "Service"
    DATABASE = "Database"


class ComponentMemory(BaseMemory):
    """Memory type for tracking all system components and their relationships.

    Provides a registry of components for dependency tracking and
    impact analysis.
    """

    type: MemoryType = Field(default=MemoryType.COMPONENT, frozen=True)

    component_id: str = Field(..., min_length=1, description="Unique component identifier")
    component_type: ComponentType = Field(..., description="Category of component")
    name: str = Field(..., min_length=1, description="Component name")
    file_path: str = Field(..., min_length=1, description="Primary file location (relative to project root)")
    public_interface: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON describing exported functions/classes",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Component IDs this component depends on",
    )
    dependents: list[str] = Field(
        default_factory=list,
        description="Component IDs depending on this component",
    )
    base_pattern: UUID | None = Field(
        default=None,
        description="Pattern ID if component extends a base pattern",
    )
    version: str | None = Field(
        default=None,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic version (e.g., 1.0.0)",
    )


# =============================================================================
# Function Memory
# =============================================================================


class FunctionMemory(BaseMemory):
    """Memory type for indexing all functions in the codebase for duplicate detection.

    Enables duplicate detection and semantic search across all functions
    in the codebase.
    """

    type: MemoryType = Field(default=MemoryType.FUNCTION, frozen=True)

    function_id: UUID = Field(default_factory=uuid4, description="Unique function identifier")
    name: str = Field(..., min_length=1, description="Function or method name")
    signature: str = Field(..., min_length=1, description="Full signature with types")
    file_path: str = Field(..., min_length=1, description="Source file location (relative to project root)")
    start_line: int = Field(..., ge=1, description="Starting line number")
    end_line: int = Field(..., ge=1, description="Ending line number")
    language: str = Field(..., description="Programming language")
    docstring: str | None = Field(default=None, description="Documentation string")
    containing_class: UUID | None = Field(default=None, description="Parent class ID (if method)")
    calls: list[UUID] = Field(default_factory=list, description="Function IDs this function calls")
    called_by: list[UUID] = Field(default_factory=list, description="Function IDs that call this function")

    @field_validator("end_line")
    @classmethod
    def validate_end_line(cls, v: int, info) -> int:
        """Validate end_line is >= start_line."""
        start_line = info.data.get("start_line")
        if start_line and v < start_line:
            raise ValueError(f"end_line ({v}) must be >= start_line ({start_line})")
        return v


# =============================================================================
# Test History Memory
# =============================================================================


class TestStatus(str, Enum):
    """Test execution result status."""

    PASSED = "Passed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    ERROR = "Error"


class TestHistoryMemory(BaseMemory):
    """Memory type for tracking test executions, failures, and fixes.

    Enables learning from past failures and tracking design alignment
    of fixes.
    """

    type: MemoryType = Field(default=MemoryType.TEST_HISTORY, frozen=True)

    test_id: UUID = Field(default_factory=uuid4, description="Unique test identifier")
    test_name: str = Field(..., min_length=1, description="Test function or method name")
    test_file: str = Field(..., min_length=1, description="Test file path (relative to project root)")
    execution_time: datetime = Field(..., description="When the test was executed (ISO8601)")
    status: TestStatus = Field(..., description="Test execution result")
    failure_message: str | None = Field(default=None, description="Error message if test failed")
    affected_component: UUID | None = Field(default=None, description="Component ID under test")
    related_requirements: list[str] = Field(
        default_factory=list,
        description="Requirement IDs this test verifies",
    )
    fix_applied: str | None = Field(default=None, description="Description of fix applied (if test was fixed)")
    fix_commit: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{7,40}$",
        description="Git commit SHA of fix",
    )
    design_alignment_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="How well the fix aligns with original design (0.0-1.0)",
    )


# =============================================================================
# Session Memory
# =============================================================================


class SessionMemory(BaseMemory):
    """Memory type for capturing key decisions and learnings from development sessions.

    Provides context continuity across development sessions.
    """

    type: MemoryType = Field(default=MemoryType.SESSION, frozen=True)

    session_id: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    start_time: datetime = Field(..., description="Session start timestamp (ISO8601)")
    end_time: datetime | None = Field(default=None, description="Session end timestamp (ISO8601)")
    summary: str = Field(..., min_length=1, description="Brief session summary")
    key_decisions: list[str] = Field(
        default_factory=list,
        description="Important decisions made during session",
    )
    components_modified: list[UUID] = Field(
        default_factory=list,
        description="Component IDs modified in this session",
    )
    memories_created: list[UUID] = Field(
        default_factory=list,
        description="Memory IDs created during this session",
    )
    outcome: str | None = Field(default=None, description="Session outcome description")


# =============================================================================
# User Preference Memory
# =============================================================================


class PreferenceCategory(str, Enum):
    """Preference categories."""

    CODING_STYLE = "CodingStyle"
    NAMING = "Naming"
    FRAMEWORK = "Framework"
    TOOL = "Tool"
    CONVENTION = "Convention"


class PreferenceScope(str, Enum):
    """Preference application scope."""

    GLOBAL = "Global"
    LANGUAGE = "Language"
    PROJECT = "Project"
    COMPONENT = "Component"


class UserPreferenceMemory(BaseMemory):
    """Memory type for storing coding style preferences and conventions.

    Enables consistent code generation aligned with user preferences.
    """

    type: MemoryType = Field(default=MemoryType.USER_PREFERENCE, frozen=True)

    preference_id: UUID = Field(default_factory=uuid4, description="Unique preference identifier")
    category: PreferenceCategory = Field(..., description="Preference category")
    key: str = Field(..., min_length=1, description="Preference key (e.g., 'indent_style', 'quote_style')")
    value: Any = Field(..., description="Preference value (flexible JSON structure)")
    scope: PreferenceScope = Field(..., description="Where this preference applies")
    examples: list[str] = Field(
        default_factory=list,
        description="Code snippets demonstrating the preference",
    )
