# REQ-MEM-007: Browser Details Enhancements

## Document Information

| Field | Value |
|-------|-------|
| **Sequence** | 007 |
| **Status** | Approved |
| **Component** | inspector-ui |

## 1. Introduction

### 1.1 Purpose

This document specifies requirements for enhancements to the Details Panel in the Memory Inspector UI, focusing on improved content display and expandability.

### 1.2 Scope

Enhancements to existing functionality:
- **Inspector UI (`inspector-ui/`):**
  - Expandable/maximizable Details Panel
  - Language-aware syntax highlighting for code content
  - Markdown rendering with raw/formatted toggle
  - Project switching auto-refresh
  - Memory Browser table columns and resizing
  - Memory Browser pagination controls fix
  - Graph tab memory type filter fix
- **MCP Server (`mcp-server/`):**
  - Test result cleanup (suite-based)
  - Automated function extraction during file indexing

### 1.3 Definitions

| Term | Definition |
|------|------------|
| Details Panel | The panel showing full memory content and metadata when a memory is selected |
| Syntax Highlighting | Color-coded display of code based on language grammar |
| Markdown Rendering | Converting markdown syntax to formatted HTML display |

## 2. Stakeholder Requirements

| ID | Requirement | Priority | Rationale |
|----|-------------|----------|-----------|
| STK-007-001 | As a developer, I need to see memory content in a larger view so I can read and understand long content without scrolling in a small panel | High | Current fixed-size panel limits visibility of large memories |
| STK-007-002 | As a developer, I need code content to be syntax highlighted based on language so I can read code patterns more easily | High | Plain text code is hard to parse visually |
| STK-007-003 | As a developer, I need markdown content to render properly with option to see raw source so I can verify formatting and read content naturally | Medium | Current display shows raw markdown which is harder to read |
| STK-007-004 | As a developer, I need the expanded view to show content and metadata in separate scrollable regions so I can view large content while keeping metadata accessible | High | Long content pushes metadata out of view |
| STK-007-005 | As a developer, I need the UI to automatically refresh when I switch projects so I can interact with the new project data without manual browser refresh | High | Current behavior requires manual refresh after project switch, causes errors |
| STK-007-006 | As a developer, I need additional metadata columns in the Browser table (component, language) so I can quickly identify relevant memories | Medium | Current columns don't show enough context |
| STK-007-007 | As a developer, I need to resize table columns so I can adjust column widths to see content that matters to me | Medium | Fixed column widths may truncate important data |
| STK-007-008 | As a developer, I need the Graph tab memory type filters to work correctly so I can filter the graph by specific memory types | High | Current filters show no results when individual types are selected (defect) |
| STK-007-009 | As a developer, I need old test_result memories to be automatically cleaned up when new results are stored for the same test suite so I don't accumulate stale test data | Medium | Test results from previous runs clutter the memory store |
| STK-007-010 | As a developer, I need individual functions to be automatically extracted and stored when files are indexed so I can search and browse at the function level | High | Currently function memories require manual creation |
| STK-007-011 | As a developer, I need visible pagination controls in the Memory Browser so I can navigate through pages of results | High | Pagination controls are not displaying (defect) |

## 3. Functional Requirements

### 3.1 Details Panel Expansion

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-001 | The system shall provide an expand button on the Details Panel that maximizes the panel to full viewport width | High | STK-007-001 |
| REQ-007-FN-002 | The expanded Details Panel shall include a collapse button to return to normal size | High | STK-007-001 |
| REQ-007-FN-003 | The expanded view shall preserve all existing functionality (edit, delete, copy, relationships) | High | STK-007-001 |
| REQ-007-FN-004 | The expansion state shall not persist across memory selections (each new selection starts collapsed) | Low | STK-007-001 |
| REQ-007-FN-005 | The expanded view shall display content in the upper region (~75% of height) and metadata in the lower region (~25% of height) | High | STK-007-004 |
| REQ-007-FN-006 | The content region shall be independently scrollable when content exceeds visible area | High | STK-007-004 |
| REQ-007-FN-007 | The metadata region shall be independently scrollable and always visible (not pushed off-screen by content) | High | STK-007-004 |
| REQ-007-FN-008 | The boundary between content and metadata regions shall be resizable via drag handle | Medium | STK-007-004 |

### 3.2 Syntax Highlighting

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-010 | The system shall detect the programming language of code content based on memory metadata or content analysis | High | STK-007-002 |
| REQ-007-FN-011 | The system shall apply syntax highlighting to code content using language-appropriate grammar rules | High | STK-007-002 |
| REQ-007-FN-012 | Supported languages shall include at minimum: JavaScript, TypeScript, Python, JSON, YAML, SQL, Bash, HTML, CSS | High | STK-007-002 |
| REQ-007-FN-013 | For `function` and `code_pattern` memory types, the system shall use the `language` metadata field to determine highlighting | High | STK-007-002 |
| REQ-007-FN-014 | If language cannot be determined, the system shall fall back to plain text display | Medium | STK-007-002 |

### 3.3 Markdown Rendering

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-020 | The system shall detect markdown content based on memory type or content patterns | Medium | STK-007-003 |
| REQ-007-FN-021 | For markdown content, the system shall provide a toggle to switch between raw and rendered views | High | STK-007-003 |
| REQ-007-FN-022 | The rendered markdown view shall support standard markdown elements: headings, lists, code blocks, links, emphasis, tables | High | STK-007-003 |
| REQ-007-FN-023 | Code blocks within rendered markdown shall have syntax highlighting applied | Medium | STK-007-003, STK-007-002 |
| REQ-007-FN-024 | The default view for markdown content shall be rendered (with toggle visible to switch to raw) | Low | STK-007-003 |

### 3.4 Project Switching

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-030 | When the project ID changes in configuration, the system shall automatically invalidate all cached data | High | STK-007-005 |
| REQ-007-FN-031 | After project switch, the Memory Browser shall reload data for the new project without requiring manual page refresh | High | STK-007-005 |
| REQ-007-FN-032 | The system shall clear the current memory selection when project changes | High | STK-007-005 |
| REQ-007-FN-033 | The system shall display a loading state while fetching data for the new project | Medium | STK-007-005 |

### 3.5 Memory Browser Table Enhancements

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-040 | The Memory Browser table shall include a "Component" column displaying the component_name from metadata | Medium | STK-007-006 |
| REQ-007-FN-041 | The Memory Browser table shall include a "Language" column displaying the language from metadata | Medium | STK-007-006 |
| REQ-007-FN-042 | All table columns shall be resizable via drag handles on column borders | Medium | STK-007-007 |
| REQ-007-FN-043 | Column width adjustments shall persist within the session | Low | STK-007-007 |
| REQ-007-FN-044 | The Memory Browser shall display visible pagination controls (next, previous, page numbers) | High | STK-007-011 |
| REQ-007-FN-045 | The Memory Browser shall display the current page number and total page count | Medium | STK-007-011 |
| REQ-007-FN-046 | The Memory Browser shall provide a page size selector (10/25/50/100 items per page) | Medium | STK-007-011 |

### 3.6 Graph Tab Filter Fix

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-050 | The Graph tab memory type filter shall correctly filter displayed nodes when one or more types are selected | High | STK-007-008 |
| REQ-007-FN-051 | The Graph tab shall display nodes matching the selected memory types and their relationships | High | STK-007-008 |
| REQ-007-FN-052 | When "All" types are selected, the Graph tab shall display all memory nodes | High | STK-007-008 |

### 3.7 Test Result Cleanup

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-060 | The system shall provide a mechanism to identify test_result memories belonging to the same test suite (e.g., via suite_name or suite_id metadata) | Medium | STK-007-009 |
| REQ-007-FN-061 | When storing new test_result memories for a suite, the system shall delete existing test_result memories for that same suite | Medium | STK-007-009 |
| REQ-007-FN-062 | The Inspector UI shall provide a manual "Clean Test Results" action to delete old test results for a selected suite | Low | STK-007-009 |

### 3.8 Automated Function Extraction

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-FN-070 | When indexing a source file, the system shall parse and extract individual function/method definitions | High | STK-007-010 |
| REQ-007-FN-071 | Each extracted function shall be stored as a `function` memory type with metadata: function_name, file_path, language, start_line, end_line | High | STK-007-010 |
| REQ-007-FN-072 | Function extraction shall support at minimum: JavaScript/TypeScript (function, arrow, method), Python (def, async def), and class methods | High | STK-007-010 |
| REQ-007-FN-073 | When re-indexing a file, existing function memories for that file shall be removed before storing new extractions | Medium | STK-007-010 |
| REQ-007-FN-074 | The function memory content shall include the complete function body with proper formatting | High | STK-007-010 |

## 4. Interface Requirements

### 4.1 User Interface

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-INT-UI-001 | The expand button shall be positioned in the Details Panel header, visually distinct from other actions | High | REQ-007-FN-001 |
| REQ-007-INT-UI-002 | The raw/rendered toggle for markdown shall be positioned near the content area with clear labels | High | REQ-007-FN-021 |
| REQ-007-INT-UI-003 | Syntax highlighting colors shall be consistent with the application's existing theme (light/dark mode aware) | Medium | REQ-007-FN-011 |
| REQ-007-INT-UI-004 | The expanded panel shall use a modal or overlay pattern that doesn't navigate away from the current page | High | REQ-007-FN-001 |
| REQ-007-INT-UI-005 | The resizable splitter shall have a visible drag handle with hover/active states | Medium | REQ-007-FN-008 |
| REQ-007-INT-UI-006 | The content and metadata regions shall have clear visual separation | Medium | REQ-007-FN-005 |

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-NFR-PERF-001 | Syntax highlighting shall render within 200ms for content up to 10,000 characters | Medium | REQ-007-FN-011 |
| REQ-007-NFR-PERF-002 | Markdown rendering shall complete within 100ms for typical memory content | Medium | REQ-007-FN-022 |

### 5.2 Usability

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-NFR-USE-001 | The expand/collapse interaction shall be keyboard accessible (Enter/Escape) | Medium | REQ-007-FN-001 |
| REQ-007-NFR-USE-002 | The raw/rendered toggle state shall be visually clear (which mode is active) | Medium | REQ-007-FN-021 |

## 6. Verification Requirements

| ID | Requirement | Priority | Traces To |
|----|-------------|----------|-----------|
| REQ-007-VER-001 | Verify expand button maximizes Details Panel and collapse returns to original size | High | REQ-007-FN-001, REQ-007-FN-002 |
| REQ-007-VER-002 | Verify syntax highlighting applies correctly for each supported language | High | REQ-007-FN-011, REQ-007-FN-012 |
| REQ-007-VER-003 | Verify markdown toggle switches between raw and rendered views | High | REQ-007-FN-021 |
| REQ-007-VER-004 | Verify code blocks in markdown receive syntax highlighting | Medium | REQ-007-FN-023 |
| REQ-007-VER-005 | Verify expanded view displays content (75%) and metadata (25%) in separate scrollable regions | High | REQ-007-FN-005, REQ-007-FN-006, REQ-007-FN-007 |
| REQ-007-VER-006 | Verify the splitter between content and metadata is draggable to resize regions | Medium | REQ-007-FN-008 |
| REQ-007-VER-007 | Verify changing project ID automatically refreshes Memory Browser with new project data | High | REQ-007-FN-030, REQ-007-FN-031 |
| REQ-007-VER-008 | Verify memory selection is cleared after project switch | High | REQ-007-FN-032 |
| REQ-007-VER-009 | Verify Component and Language columns are visible in Memory Browser table | Medium | REQ-007-FN-040, REQ-007-FN-041 |
| REQ-007-VER-010 | Verify table columns can be resized by dragging column borders | Medium | REQ-007-FN-042 |
| REQ-007-VER-016 | Verify pagination controls are visible and functional in Memory Browser | High | REQ-007-FN-044 |
| REQ-007-VER-011 | Verify Graph tab displays correct nodes when filtering by one memory type | High | REQ-007-FN-050 |
| REQ-007-VER-012 | Verify Graph tab displays correct nodes when filtering by multiple memory types | High | REQ-007-FN-050, REQ-007-FN-051 |
| REQ-007-VER-013 | Verify storing new test_result for a suite removes old results for that suite | Medium | REQ-007-FN-061 |
| REQ-007-VER-014 | Verify indexing a file creates function memories for each function/method | High | REQ-007-FN-070, REQ-007-FN-071 |
| REQ-007-VER-015 | Verify re-indexing removes old function memories for the file before adding new ones | Medium | REQ-007-FN-073 |

## 7. Traceability Matrix

| Stakeholder Req | Functional Req | Interface Req | NFR | Verification |
|-----------------|----------------|---------------|-----|--------------|
| STK-007-001 | REQ-007-FN-001 to FN-004 | REQ-007-INT-UI-001, INT-UI-004 | REQ-007-NFR-USE-001 | REQ-007-VER-001 |
| STK-007-002 | REQ-007-FN-010 to FN-014 | REQ-007-INT-UI-003 | REQ-007-NFR-PERF-001 | REQ-007-VER-002 |
| STK-007-003 | REQ-007-FN-020 to FN-024 | REQ-007-INT-UI-002 | REQ-007-NFR-PERF-002, NFR-USE-002 | REQ-007-VER-003, VER-004 |
| STK-007-004 | REQ-007-FN-005 to FN-008 | REQ-007-INT-UI-005, INT-UI-006 | - | REQ-007-VER-005, VER-006 |
| STK-007-005 | REQ-007-FN-030 to FN-033 | - | - | REQ-007-VER-007, VER-008 |
| STK-007-006 | REQ-007-FN-040, FN-041 | - | - | REQ-007-VER-009 |
| STK-007-007 | REQ-007-FN-042, FN-043 | - | - | REQ-007-VER-010 |
| STK-007-008 | REQ-007-FN-050 to FN-052 | - | - | REQ-007-VER-011, VER-012 |
| STK-007-009 | REQ-007-FN-060 to FN-062 | - | - | REQ-007-VER-013 |
| STK-007-010 | REQ-007-FN-070 to FN-074 | - | - | REQ-007-VER-014, VER-015 |
| STK-007-011 | REQ-007-FN-044 to FN-046 | - | - | REQ-007-VER-016 |
