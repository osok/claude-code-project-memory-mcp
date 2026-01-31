"""Factory classes for creating test data."""

import random
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from memory_service.models import (
    BaseMemory,
    CodePatternMemory,
    ComponentMemory,
    DesignMemory,
    FunctionMemory,
    MemoryType,
    RequirementsMemory,
    SessionMemory,
    SyncStatus,
    TestHistoryMemory,
    UserPreferenceMemory,
)


def generate_embedding(seed: int | None = None, dim: int = 1024) -> list[float]:
    """Generate a random embedding vector.

    Args:
        seed: Optional seed for reproducibility
        dim: Dimension of the embedding (default 1024 for Voyage-Code-3)

    Returns:
        List of floats representing the embedding
    """
    if seed is not None:
        random.seed(seed)
    return [random.random() for _ in range(dim)]


class MemoryFactory:
    """Base factory for creating memory objects."""

    _counter: int = 0

    @classmethod
    def _next_id(cls) -> int:
        """Get next sequence number."""
        cls._counter += 1
        return cls._counter

    @classmethod
    def reset(cls) -> None:
        """Reset the counter."""
        cls._counter = 0


class RequirementsMemoryFactory(MemoryFactory):
    """Factory for creating RequirementsMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        requirement_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        priority: str = "High",
        status: str = "Approved",
        source_document: str = "requirements.md",
        related_requirements: list[str] | None = None,
        **kwargs: Any,
    ) -> RequirementsMemory:
        """Create a RequirementsMemory instance with defaults."""
        seq = cls._next_id()
        return RequirementsMemory(
            id=id or uuid4(),
            type=MemoryType.REQUIREMENTS,
            content=content or f"The system shall provide feature {seq}",
            embedding=embedding or generate_embedding(seq),
            requirement_id=requirement_id or f"REQ-MEM-FN-{seq:03d}",
            title=title or f"Requirement {seq}",
            description=description or f"Description for requirement {seq}",
            priority=priority,
            status=status,
            source_document=source_document,
            related_requirements=related_requirements or [],
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[RequirementsMemory]:
        """Create multiple RequirementsMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class DesignMemoryFactory(MemoryFactory):
    """Factory for creating DesignMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        design_type: str = "ADR",
        title: str | None = None,
        decision: str | None = None,
        rationale: str | None = None,
        status: str = "Accepted",
        related_requirements: list[str] | None = None,
        alternatives_considered: list[str] | None = None,
        **kwargs: Any,
    ) -> DesignMemory:
        """Create a DesignMemory instance with defaults."""
        seq = cls._next_id()
        return DesignMemory(
            id=id or uuid4(),
            type=MemoryType.DESIGN,
            content=content or f"Design decision {seq} for component architecture",
            embedding=embedding or generate_embedding(seq + 1000),
            design_type=design_type,
            title=title or f"ADR-{seq:03d}: Design Decision {seq}",
            decision=decision or f"Use pattern {seq} for implementation",
            rationale=rationale or f"Rationale for decision {seq}",
            status=status,
            related_requirements=related_requirements or [f"REQ-MEM-FN-{seq:03d}"],
            alternatives_considered=alternatives_considered or [],
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[DesignMemory]:
        """Create multiple DesignMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class CodePatternMemoryFactory(MemoryFactory):
    """Factory for creating CodePatternMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        pattern_name: str | None = None,
        pattern_type: str = "Template",
        language: str = "Python",
        code_template: str | None = None,
        usage_context: str | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> CodePatternMemory:
        """Create a CodePatternMemory instance with defaults."""
        seq = cls._next_id()
        return CodePatternMemory(
            id=id or uuid4(),
            type=MemoryType.CODE_PATTERN,
            content=content or f"Code pattern {seq} for common operations",
            embedding=embedding or generate_embedding(seq + 2000),
            pattern_name=pattern_name or f"Pattern {seq}",
            pattern_type=pattern_type,
            language=language,
            code_template=code_template or f"def pattern_{seq}():\n    pass",
            usage_context=usage_context or f"Use pattern {seq} when handling common case",
            tags=tags or ["utility", "common"],
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[CodePatternMemory]:
        """Create multiple CodePatternMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class ComponentMemoryFactory(MemoryFactory):
    """Factory for creating ComponentMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        component_id: str | None = None,
        component_type: str = "Service",
        name: str | None = None,
        file_path: str | None = None,
        public_interface: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
        **kwargs: Any,
    ) -> ComponentMemory:
        """Create a ComponentMemory instance with defaults."""
        seq = cls._next_id()
        return ComponentMemory(
            id=id or uuid4(),
            type=MemoryType.COMPONENT,
            content=content or f"Component {seq} - Service for handling operations",
            embedding=embedding or generate_embedding(seq + 3000),
            component_id=component_id or f"component-{seq}",
            component_type=component_type,
            name=name or f"Component{seq}",
            file_path=file_path or f"src/components/component_{seq}.py",
            public_interface=public_interface or {
                "exports": [
                    {"name": f"Component{seq}", "type": "class"},
                    {"name": f"process_{seq}", "type": "function"},
                ]
            },
            dependencies=dependencies or [],
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[ComponentMemory]:
        """Create multiple ComponentMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class FunctionMemoryFactory(MemoryFactory):
    """Factory for creating FunctionMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        function_id: UUID | None = None,
        name: str | None = None,
        signature: str | None = None,
        file_path: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        language: str = "python",
        docstring: str | None = None,
        **kwargs: Any,
    ) -> FunctionMemory:
        """Create a FunctionMemory instance with defaults."""
        seq = cls._next_id()
        return FunctionMemory(
            id=id or uuid4(),
            type=MemoryType.FUNCTION,
            content=content or f"def function_{seq}(arg1: str, arg2: int) -> bool",
            embedding=embedding or generate_embedding(seq + 4000),
            function_id=function_id or uuid4(),
            name=name or f"function_{seq}",
            signature=signature or f"def function_{seq}(arg1: str, arg2: int) -> bool",
            file_path=file_path or f"src/module_{seq}.py",
            start_line=start_line or seq * 10,
            end_line=end_line or (seq * 10) + 15,
            language=language,
            docstring=docstring or f"Process function {seq} with given arguments.",
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[FunctionMemory]:
        """Create multiple FunctionMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class TestHistoryMemoryFactory(MemoryFactory):
    """Factory for creating TestHistoryMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        test_id: UUID | None = None,
        test_name: str | None = None,
        test_file: str | None = None,
        execution_time: datetime | None = None,
        status: str = "Passed",
        duration_ms: int | None = None,
        error_message: str | None = None,
        **kwargs: Any,
    ) -> TestHistoryMemory:
        """Create a TestHistoryMemory instance with defaults."""
        seq = cls._next_id()
        return TestHistoryMemory(
            id=id or uuid4(),
            type=MemoryType.TEST_HISTORY,
            content=content or f"test_function_{seq}_behavior",
            embedding=embedding or generate_embedding(seq + 5000),
            test_id=test_id or uuid4(),
            test_name=test_name or f"test_function_{seq}_behavior",
            test_file=test_file or f"tests/test_module_{seq}.py",
            execution_time=execution_time or datetime.now(timezone.utc),
            status=status,
            duration_ms=duration_ms or random.randint(10, 1000),
            error_message=error_message,
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[TestHistoryMemory]:
        """Create multiple TestHistoryMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_failed(cls, error_message: str = "Assertion failed", **kwargs: Any) -> TestHistoryMemory:
        """Create a failed test history."""
        return cls.create(status="Failed", error_message=error_message, **kwargs)


class SessionMemoryFactory(MemoryFactory):
    """Factory for creating SessionMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        session_id: UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        summary: str | None = None,
        key_decisions: list[str] | None = None,
        files_modified: list[str] | None = None,
        **kwargs: Any,
    ) -> SessionMemory:
        """Create a SessionMemory instance with defaults."""
        seq = cls._next_id()
        return SessionMemory(
            id=id or uuid4(),
            type=MemoryType.SESSION,
            content=content or f"Development session {seq} - Implemented feature X",
            embedding=embedding or generate_embedding(seq + 6000),
            session_id=session_id or uuid4(),
            start_time=start_time or datetime.now(timezone.utc),
            end_time=end_time,
            summary=summary or f"Session {seq}: Implemented and tested feature",
            key_decisions=key_decisions or [f"Decision {seq}.1", f"Decision {seq}.2"],
            files_modified=files_modified or [f"src/file_{seq}.py"],
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[SessionMemory]:
        """Create multiple SessionMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class UserPreferenceMemoryFactory(MemoryFactory):
    """Factory for creating UserPreferenceMemory test objects."""

    @classmethod
    def create(
        cls,
        id: UUID | None = None,
        content: str | None = None,
        embedding: list[float] | None = None,
        preference_id: UUID | None = None,
        category: str = "CodingStyle",
        key: str | None = None,
        value: Any | None = None,
        scope: str = "Global",
        **kwargs: Any,
    ) -> UserPreferenceMemory:
        """Create a UserPreferenceMemory instance with defaults."""
        seq = cls._next_id()
        return UserPreferenceMemory(
            id=id or uuid4(),
            type=MemoryType.USER_PREFERENCE,
            content=content or f"User preference {seq} for coding style",
            embedding=embedding or generate_embedding(seq + 7000),
            preference_id=preference_id or uuid4(),
            category=category,
            key=key or f"preference_{seq}",
            value=value or {"enabled": True, "level": seq},
            scope=scope,
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs: Any) -> list[UserPreferenceMemory]:
        """Create multiple UserPreferenceMemory instances."""
        return [cls.create(**kwargs) for _ in range(count)]


def reset_all_factories() -> None:
    """Reset all factory counters."""
    RequirementsMemoryFactory.reset()
    DesignMemoryFactory.reset()
    CodePatternMemoryFactory.reset()
    ComponentMemoryFactory.reset()
    FunctionMemoryFactory.reset()
    TestHistoryMemoryFactory.reset()
    SessionMemoryFactory.reset()
    UserPreferenceMemoryFactory.reset()
