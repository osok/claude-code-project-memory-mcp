"""Unit tests for Schema Validation (UT-030 to UT-046)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

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
from memory_service.models.memories import (
    ComponentType,
    DesignStatus,
    DesignType,
    PatternType,
    PreferenceCategory,
    PreferenceScope,
    RequirementPriority,
    RequirementStatus,
    TestStatus,
)
from tests.fixtures.factories import (
    generate_embedding,
    reset_all_factories,
)


@pytest.fixture(autouse=True)
def reset_factories():
    """Reset factory counters before each test."""
    reset_all_factories()


@pytest.fixture
def valid_embedding() -> list[float]:
    """Generate valid 1024-dimensional embedding."""
    return generate_embedding(seed=42)


class TestRequirementsMemoryValidation:
    """Tests for RequirementsMemory schema validation (UT-030 to UT-032)."""

    def test_ut030_validate_requirement_id_pattern_valid(self, valid_embedding):
        """UT-030: Validate requirement_id pattern (REQ-XXX-NNN) - valid cases."""
        # Standard format
        memory = RequirementsMemory(
            content="Test requirement",
            embedding=valid_embedding,
            requirement_id="REQ-MEM-FN-001",
            title="Test",
            description="Test description",
            priority=RequirementPriority.HIGH,
            status=RequirementStatus.APPROVED,
            source_document="requirements.md",
        )
        assert memory.requirement_id == "REQ-MEM-FN-001"

        # With longer prefix
        memory2 = RequirementsMemory(
            content="Test requirement 2",
            embedding=valid_embedding,
            requirement_id="REQ-PROJECT-SECURITY-123",
            title="Test 2",
            description="Test description 2",
            priority=RequirementPriority.MEDIUM,
            status=RequirementStatus.DRAFT,
            source_document="requirements.md",
        )
        assert memory2.requirement_id == "REQ-PROJECT-SECURITY-123"

    def test_ut030_validate_requirement_id_pattern_invalid(self, valid_embedding):
        """UT-030: Validate requirement_id pattern (REQ-XXX-NNN) - invalid cases."""
        # Missing REQ prefix
        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
            )
        assert "requirement_id" in str(exc_info.value)

        # Too few parts
        with pytest.raises(ValidationError):
            RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
            )

    def test_ut031_validate_priority_enum_values(self, valid_embedding):
        """UT-031: Validate priority enum values."""
        # All valid priorities
        for priority in RequirementPriority:
            memory = RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=priority,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
            )
            assert memory.priority == priority.value

        # Invalid priority
        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority="Urgent",  # Invalid
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
            )
        assert "priority" in str(exc_info.value)

    def test_ut032_validate_status_enum_values(self, valid_embedding):
        """UT-032: Validate status enum values."""
        # All valid statuses
        for status in RequirementStatus:
            memory = RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=status,
                source_document="requirements.md",
            )
            assert memory.status == status.value

        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status="Completed",  # Invalid
                source_document="requirements.md",
            )
        assert "status" in str(exc_info.value)


class TestDesignMemoryValidation:
    """Tests for DesignMemory schema validation (UT-033 to UT-034)."""

    def test_ut033_validate_design_type_enum_values(self, valid_embedding):
        """UT-033: Validate design_type enum values."""
        # All valid design types
        for design_type in DesignType:
            memory = DesignMemory(
                content="Test design",
                embedding=valid_embedding,
                design_type=design_type,
                title="Test Design",
                status=DesignStatus.ACCEPTED,
            )
            assert memory.design_type == design_type.value

        # Invalid design type
        with pytest.raises(ValidationError) as exc_info:
            DesignMemory(
                content="Test",
                embedding=valid_embedding,
                design_type="Blueprint",  # Invalid
                title="Test",
                status=DesignStatus.ACCEPTED,
            )
        assert "design_type" in str(exc_info.value)

    def test_ut034_validate_design_status_enum_values(self, valid_embedding):
        """UT-034: Validate status enum values for Design."""
        # All valid statuses
        for status in DesignStatus:
            memory = DesignMemory(
                content="Test",
                embedding=valid_embedding,
                design_type=DesignType.ADR,
                title="Test",
                status=status,
            )
            assert memory.status == status.value

        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            DesignMemory(
                content="Test",
                embedding=valid_embedding,
                design_type=DesignType.ADR,
                title="Test",
                status="Approved",  # Invalid - should be "Accepted"
            )
        assert "status" in str(exc_info.value)


class TestCodePatternMemoryValidation:
    """Tests for CodePatternMemory schema validation (UT-035 to UT-036)."""

    def test_ut035_validate_pattern_type_enum_values(self, valid_embedding):
        """UT-035: Validate pattern_type enum values."""
        # All valid pattern types
        for pattern_type in PatternType:
            memory = CodePatternMemory(
                content="Test pattern",
                embedding=valid_embedding,
                pattern_name="Test Pattern",
                pattern_type=pattern_type,
                language="Python",
                code_template="def example(): pass",
                usage_context="Use for testing",
            )
            assert memory.pattern_type == pattern_type.value

        # Invalid pattern type
        with pytest.raises(ValidationError) as exc_info:
            CodePatternMemory(
                content="Test",
                embedding=valid_embedding,
                pattern_name="Test",
                pattern_type="Pattern",  # Invalid
                language="Python",
                code_template="def example(): pass",
                usage_context="Use for testing",
            )
        assert "pattern_type" in str(exc_info.value)

    def test_ut036_require_code_template_and_usage_context(self, valid_embedding):
        """UT-036: Require code_template and usage_context."""
        # Missing code_template
        with pytest.raises(ValidationError) as exc_info:
            CodePatternMemory(
                content="Test",
                embedding=valid_embedding,
                pattern_name="Test",
                pattern_type=PatternType.TEMPLATE,
                language="Python",
                usage_context="Use for testing",
                # code_template missing
            )
        assert "code_template" in str(exc_info.value)

        # Missing usage_context
        with pytest.raises(ValidationError) as exc_info:
            CodePatternMemory(
                content="Test",
                embedding=valid_embedding,
                pattern_name="Test",
                pattern_type=PatternType.TEMPLATE,
                language="Python",
                code_template="def example(): pass",
                # usage_context missing
            )
        assert "usage_context" in str(exc_info.value)

        # Empty strings should also fail
        with pytest.raises(ValidationError):
            CodePatternMemory(
                content="Test",
                embedding=valid_embedding,
                pattern_name="Test",
                pattern_type=PatternType.TEMPLATE,
                language="Python",
                code_template="",  # Empty
                usage_context="Use for testing",
            )


class TestComponentMemoryValidation:
    """Tests for ComponentMemory schema validation (UT-037 to UT-038)."""

    def test_ut037_validate_component_type_enum_values(self, valid_embedding):
        """UT-037: Validate component_type enum values."""
        # All valid component types
        for component_type in ComponentType:
            memory = ComponentMemory(
                content="Test component",
                embedding=valid_embedding,
                component_id="test-component",
                component_type=component_type,
                name="TestComponent",
                file_path="src/component.py",
            )
            assert memory.component_type == component_type.value

        # Invalid component type
        with pytest.raises(ValidationError) as exc_info:
            ComponentMemory(
                content="Test",
                embedding=valid_embedding,
                component_id="test",
                component_type="Module",  # Invalid
                name="Test",
                file_path="src/test.py",
            )
        assert "component_type" in str(exc_info.value)

    def test_ut038_require_component_id_and_file_path(self, valid_embedding):
        """UT-038: Require component_id and file_path."""
        # Missing component_id
        with pytest.raises(ValidationError) as exc_info:
            ComponentMemory(
                content="Test",
                embedding=valid_embedding,
                component_type=ComponentType.SERVICE,
                name="Test",
                file_path="src/test.py",
            )
        assert "component_id" in str(exc_info.value)

        # Missing file_path
        with pytest.raises(ValidationError) as exc_info:
            ComponentMemory(
                content="Test",
                embedding=valid_embedding,
                component_id="test",
                component_type=ComponentType.SERVICE,
                name="Test",
            )
        assert "file_path" in str(exc_info.value)

        # Empty strings should fail
        with pytest.raises(ValidationError):
            ComponentMemory(
                content="Test",
                embedding=valid_embedding,
                component_id="",  # Empty
                component_type=ComponentType.SERVICE,
                name="Test",
                file_path="src/test.py",
            )

    def test_component_version_pattern(self, valid_embedding):
        """Test version follows semantic versioning pattern."""
        # Valid version
        memory = ComponentMemory(
            content="Test",
            embedding=valid_embedding,
            component_id="test",
            component_type=ComponentType.SERVICE,
            name="Test",
            file_path="src/test.py",
            version="1.0.0",
        )
        assert memory.version == "1.0.0"

        # Invalid version format
        with pytest.raises(ValidationError):
            ComponentMemory(
                content="Test",
                embedding=valid_embedding,
                component_id="test",
                component_type=ComponentType.SERVICE,
                name="Test",
                file_path="src/test.py",
                version="1.0",  # Invalid - needs 3 parts
            )


class TestFunctionMemoryValidation:
    """Tests for FunctionMemory schema validation (UT-039 to UT-040)."""

    def test_ut039_require_name_signature_file_path(self, valid_embedding):
        """UT-039: Require name, signature, file_path."""
        # Missing name
        with pytest.raises(ValidationError) as exc_info:
            FunctionMemory(
                content="def test(): pass",
                embedding=valid_embedding,
                signature="def test(): pass",
                file_path="src/test.py",
                start_line=1,
                end_line=2,
                language="python",
            )
        assert "name" in str(exc_info.value)

        # Missing signature
        with pytest.raises(ValidationError) as exc_info:
            FunctionMemory(
                content="def test(): pass",
                embedding=valid_embedding,
                name="test",
                file_path="src/test.py",
                start_line=1,
                end_line=2,
                language="python",
            )
        assert "signature" in str(exc_info.value)

        # Missing file_path
        with pytest.raises(ValidationError) as exc_info:
            FunctionMemory(
                content="def test(): pass",
                embedding=valid_embedding,
                name="test",
                signature="def test(): pass",
                start_line=1,
                end_line=2,
                language="python",
            )
        assert "file_path" in str(exc_info.value)

    def test_ut040_validate_start_line_less_than_end_line(self, valid_embedding):
        """UT-040: Validate start_line < end_line."""
        # Valid: start_line < end_line
        memory = FunctionMemory(
            content="def test(): pass",
            embedding=valid_embedding,
            name="test",
            signature="def test(): pass",
            file_path="src/test.py",
            start_line=10,
            end_line=20,
            language="python",
        )
        assert memory.start_line == 10
        assert memory.end_line == 20

        # Valid: start_line == end_line (single line function)
        memory2 = FunctionMemory(
            content="def test(): pass",
            embedding=valid_embedding,
            name="test",
            signature="def test(): pass",
            file_path="src/test.py",
            start_line=10,
            end_line=10,
            language="python",
        )
        assert memory2.start_line == memory2.end_line

        # Invalid: end_line < start_line
        with pytest.raises(ValidationError) as exc_info:
            FunctionMemory(
                content="def test(): pass",
                embedding=valid_embedding,
                name="test",
                signature="def test(): pass",
                file_path="src/test.py",
                start_line=20,
                end_line=10,  # Less than start_line
                language="python",
            )
        assert "end_line" in str(exc_info.value)

    def test_function_line_numbers_positive(self, valid_embedding):
        """Test line numbers must be positive."""
        # start_line must be >= 1
        with pytest.raises(ValidationError):
            FunctionMemory(
                content="def test(): pass",
                embedding=valid_embedding,
                name="test",
                signature="def test(): pass",
                file_path="src/test.py",
                start_line=0,  # Invalid
                end_line=10,
                language="python",
            )


class TestTestHistoryMemoryValidation:
    """Tests for TestHistoryMemory schema validation (UT-041 to UT-042)."""

    def test_ut041_validate_status_enum_values(self, valid_embedding):
        """UT-041: Validate status enum values."""
        # All valid test statuses
        for status in TestStatus:
            memory = TestHistoryMemory(
                content="test_example",
                embedding=valid_embedding,
                test_name="test_example",
                test_file="tests/test_example.py",
                execution_time=datetime.now(timezone.utc),
                status=status,
            )
            assert memory.status == status.value

        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            TestHistoryMemory(
                content="test_example",
                embedding=valid_embedding,
                test_name="test_example",
                test_file="tests/test_example.py",
                execution_time=datetime.now(timezone.utc),
                status="Success",  # Invalid - should be "Passed"
            )
        assert "status" in str(exc_info.value)

    def test_ut042_validate_design_alignment_score_range(self, valid_embedding):
        """UT-042: Validate design_alignment_score range [0.0, 1.0]."""
        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            memory = TestHistoryMemory(
                content="test_example",
                embedding=valid_embedding,
                test_name="test_example",
                test_file="tests/test_example.py",
                execution_time=datetime.now(timezone.utc),
                status=TestStatus.PASSED,
                design_alignment_score=score,
            )
            assert memory.design_alignment_score == score

        # Invalid: below range
        with pytest.raises(ValidationError) as exc_info:
            TestHistoryMemory(
                content="test_example",
                embedding=valid_embedding,
                test_name="test_example",
                test_file="tests/test_example.py",
                execution_time=datetime.now(timezone.utc),
                status=TestStatus.PASSED,
                design_alignment_score=-0.1,
            )
        assert "design_alignment_score" in str(exc_info.value)

        # Invalid: above range
        with pytest.raises(ValidationError) as exc_info:
            TestHistoryMemory(
                content="test_example",
                embedding=valid_embedding,
                test_name="test_example",
                test_file="tests/test_example.py",
                execution_time=datetime.now(timezone.utc),
                status=TestStatus.PASSED,
                design_alignment_score=1.1,
            )
        assert "design_alignment_score" in str(exc_info.value)

    def test_fix_commit_pattern(self, valid_embedding):
        """Test fix_commit follows git SHA pattern."""
        # Valid short SHA
        memory = TestHistoryMemory(
            content="test_example",
            embedding=valid_embedding,
            test_name="test_example",
            test_file="tests/test_example.py",
            execution_time=datetime.now(timezone.utc),
            status=TestStatus.PASSED,
            fix_commit="abc1234",
        )
        assert memory.fix_commit == "abc1234"

        # Valid full SHA
        memory2 = TestHistoryMemory(
            content="test_example",
            embedding=valid_embedding,
            test_name="test_example",
            test_file="tests/test_example.py",
            execution_time=datetime.now(timezone.utc),
            status=TestStatus.PASSED,
            fix_commit="abc123def456789012345678901234567890abcd",
        )
        assert len(memory2.fix_commit) == 40

        # Invalid: too short
        with pytest.raises(ValidationError):
            TestHistoryMemory(
                content="test_example",
                embedding=valid_embedding,
                test_name="test_example",
                test_file="tests/test_example.py",
                execution_time=datetime.now(timezone.utc),
                status=TestStatus.PASSED,
                fix_commit="abc12",  # Too short
            )


class TestSessionMemoryValidation:
    """Tests for SessionMemory schema validation (UT-043)."""

    def test_ut043_require_start_time_and_summary(self, valid_embedding):
        """UT-043: Require start_time and summary."""
        # Missing start_time
        with pytest.raises(ValidationError) as exc_info:
            SessionMemory(
                content="Session content",
                embedding=valid_embedding,
                summary="Session summary",
            )
        assert "start_time" in str(exc_info.value)

        # Missing summary
        with pytest.raises(ValidationError) as exc_info:
            SessionMemory(
                content="Session content",
                embedding=valid_embedding,
                start_time=datetime.now(timezone.utc),
            )
        assert "summary" in str(exc_info.value)

        # Valid session
        memory = SessionMemory(
            content="Session content",
            embedding=valid_embedding,
            start_time=datetime.now(timezone.utc),
            summary="Completed feature implementation",
        )
        assert memory.summary == "Completed feature implementation"

        # Empty summary should fail
        with pytest.raises(ValidationError):
            SessionMemory(
                content="Session content",
                embedding=valid_embedding,
                start_time=datetime.now(timezone.utc),
                summary="",  # Empty
            )


class TestUserPreferenceMemoryValidation:
    """Tests for UserPreferenceMemory schema validation (UT-044)."""

    def test_ut044_validate_category_and_scope_enums(self, valid_embedding):
        """UT-044: Validate category and scope enums."""
        # All valid categories
        for category in PreferenceCategory:
            memory = UserPreferenceMemory(
                content="Test preference",
                embedding=valid_embedding,
                category=category,
                key="test_key",
                value={"setting": True},
                scope=PreferenceScope.GLOBAL,
            )
            assert memory.category == category.value

        # All valid scopes
        for scope in PreferenceScope:
            memory = UserPreferenceMemory(
                content="Test preference",
                embedding=valid_embedding,
                category=PreferenceCategory.CODING_STYLE,
                key="test_key",
                value={"setting": True},
                scope=scope,
            )
            assert memory.scope == scope.value

        # Invalid category
        with pytest.raises(ValidationError) as exc_info:
            UserPreferenceMemory(
                content="Test",
                embedding=valid_embedding,
                category="Style",  # Invalid
                key="test_key",
                value={"setting": True},
                scope=PreferenceScope.GLOBAL,
            )
        assert "category" in str(exc_info.value)

        # Invalid scope
        with pytest.raises(ValidationError) as exc_info:
            UserPreferenceMemory(
                content="Test",
                embedding=valid_embedding,
                category=PreferenceCategory.CODING_STYLE,
                key="test_key",
                value={"setting": True},
                scope="File",  # Invalid
            )
        assert "scope" in str(exc_info.value)


class TestBaseMemoryValidation:
    """Tests for BaseMemory schema validation (UT-045 to UT-046)."""

    def test_ut045_validate_importance_score_range(self, valid_embedding):
        """UT-045: Validate importance_score range [0.0, 1.0]."""
        # Valid scores at boundaries
        for score in [0.0, 0.5, 1.0]:
            memory = RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
                importance_score=score,
            )
            assert memory.importance_score == score

        # Invalid: below range
        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
                importance_score=-0.1,
            )
        assert "importance_score" in str(exc_info.value)

        # Invalid: above range
        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
                importance_score=1.1,
            )
        assert "importance_score" in str(exc_info.value)

    def test_ut046_validate_sync_status_enum_values(self, valid_embedding):
        """UT-046: Validate sync_status enum values."""
        # All valid sync statuses
        for status in SyncStatus:
            memory = RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
                sync_status=status,
            )
            assert memory.sync_status == status.value

        # Invalid sync status
        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="Test",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
                sync_status="complete",  # Invalid
            )
        assert "sync_status" in str(exc_info.value)


class TestEmbeddingValidation:
    """Tests for embedding dimension validation."""

    def test_embedding_must_be_1024_dimensions(self):
        """Test embedding vector must have 1024 dimensions."""
        valid_embedding = generate_embedding(seed=42, dim=1024)
        memory = RequirementsMemory(
            content="Test",
            embedding=valid_embedding,
            requirement_id="REQ-MEM-FN-001",
            title="Test",
            description="Test",
            priority=RequirementPriority.HIGH,
            status=RequirementStatus.APPROVED,
            source_document="requirements.md",
        )
        assert len(memory.embedding) == 1024

    def test_embedding_wrong_dimensions_rejected(self):
        """Test embedding with wrong dimensions is rejected."""
        wrong_embedding = [0.1] * 512  # Wrong size

        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="Test",
                embedding=wrong_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
            )
        assert "1024" in str(exc_info.value)

    def test_empty_embedding_allowed(self):
        """Test empty embedding is allowed (to be generated later)."""
        memory = RequirementsMemory(
            content="Test",
            embedding=[],
            requirement_id="REQ-MEM-FN-001",
            title="Test",
            description="Test",
            priority=RequirementPriority.HIGH,
            status=RequirementStatus.APPROVED,
            source_document="requirements.md",
        )
        assert memory.embedding == []


class TestContentValidation:
    """Tests for content field validation."""

    def test_content_cannot_be_empty(self, valid_embedding):
        """Test content field cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            RequirementsMemory(
                content="",
                embedding=valid_embedding,
                requirement_id="REQ-MEM-FN-001",
                title="Test",
                description="Test",
                priority=RequirementPriority.HIGH,
                status=RequirementStatus.APPROVED,
                source_document="requirements.md",
            )
        assert "content" in str(exc_info.value).lower()

    def test_content_whitespace_stripped(self, valid_embedding):
        """Test content whitespace is stripped."""
        memory = RequirementsMemory(
            content="  Test content with spaces  ",
            embedding=valid_embedding,
            requirement_id="REQ-MEM-FN-001",
            title="Test",
            description="Test",
            priority=RequirementPriority.HIGH,
            status=RequirementStatus.APPROVED,
            source_document="requirements.md",
        )
        assert memory.content == "Test content with spaces"
