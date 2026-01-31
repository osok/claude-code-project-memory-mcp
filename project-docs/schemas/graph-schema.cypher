// Neo4j Graph Schema for Claude Code Long-Term Memory System
// Version: 1.0
// Purpose: Define nodes, relationships, indexes, and constraints for code knowledge graph

// ==============================================================================
// NODE DEFINITIONS
// ==============================================================================

// ------------------------------------------------------------------------------
// Function Node
// ------------------------------------------------------------------------------
// Represents a function or method in the codebase
// Links to Qdrant function_index collection via memory_id

CREATE CONSTRAINT function_memory_id_unique IF NOT EXISTS
FOR (f:Function) REQUIRE f.memory_id IS UNIQUE;

CREATE INDEX function_name_idx IF NOT EXISTS
FOR (f:Function) ON (f.name);

CREATE INDEX function_file_path_idx IF NOT EXISTS
FOR (f:Function) ON (f.file_path);

CREATE INDEX function_language_idx IF NOT EXISTS
FOR (f:Function) ON (f.language);

// Properties:
// - memory_id: String (UNIQUE) - Reference to Qdrant memory
// - name: String (INDEXED) - Function name
// - file_path: String (INDEXED) - Source file path
// - signature: String - Full function signature
// - language: String (INDEXED) - Programming language

// ------------------------------------------------------------------------------
// Class Node
// ------------------------------------------------------------------------------
// Represents a class, struct, or interface in the codebase

CREATE CONSTRAINT class_memory_id_unique IF NOT EXISTS
FOR (c:Class) REQUIRE c.memory_id IS UNIQUE;

CREATE INDEX class_name_idx IF NOT EXISTS
FOR (c:Class) ON (c.name);

CREATE INDEX class_file_path_idx IF NOT EXISTS
FOR (c:Class) ON (c.file_path);

CREATE INDEX class_language_idx IF NOT EXISTS
FOR (c:Class) ON (c.language);

// Properties:
// - memory_id: String (UNIQUE) - Reference to Qdrant memory
// - name: String (INDEXED) - Class name
// - file_path: String (INDEXED) - Source file path
// - language: String (INDEXED) - Programming language

// ------------------------------------------------------------------------------
// Module Node
// ------------------------------------------------------------------------------
// Represents a module, package, or namespace

CREATE CONSTRAINT module_path_language_unique IF NOT EXISTS
FOR (m:Module) REQUIRE (m.file_path, m.language) IS UNIQUE;

CREATE INDEX module_name_idx IF NOT EXISTS
FOR (m:Module) ON (m.name);

CREATE INDEX module_file_path_idx IF NOT EXISTS
FOR (m:Module) ON (m.file_path);

// Properties:
// - name: String (INDEXED) - Module/package name
// - file_path: String (UNIQUE with language) - Module file or directory path
// - language: String - Programming language

// ------------------------------------------------------------------------------
// File Node
// ------------------------------------------------------------------------------
// Represents a source code file

CREATE CONSTRAINT file_path_unique IF NOT EXISTS
FOR (f:File) REQUIRE f.path IS UNIQUE;

CREATE INDEX file_language_idx IF NOT EXISTS
FOR (f:File) ON (f.language);

// Properties:
// - path: String (UNIQUE) - Absolute file path
// - language: String (INDEXED) - Programming language
// - content_hash: String - SHA-256 hash of file content
// - indexed_at: DateTime - Last indexing timestamp

// ------------------------------------------------------------------------------
// Component Node
// ------------------------------------------------------------------------------
// Represents a system component (frontend, backend, agent, etc.)
// Links to Qdrant component_registry collection via memory_id

CREATE CONSTRAINT component_memory_id_unique IF NOT EXISTS
FOR (c:Component) REQUIRE c.memory_id IS UNIQUE;

CREATE CONSTRAINT component_id_unique IF NOT EXISTS
FOR (c:Component) REQUIRE c.component_id IS UNIQUE;

CREATE INDEX component_name_idx IF NOT EXISTS
FOR (c:Component) ON (c.name);

CREATE INDEX component_type_idx IF NOT EXISTS
FOR (c:Component) ON (c.type);

// Properties:
// - memory_id: String (UNIQUE) - Reference to Qdrant memory
// - component_id: String (UNIQUE) - Component identifier
// - name: String (INDEXED) - Component name
// - type: String (INDEXED) - Component type (Frontend/Backend/Agent/etc.)

// ------------------------------------------------------------------------------
// Requirement Node
// ------------------------------------------------------------------------------
// Represents a requirements specification
// Links to Qdrant requirements_memory collection via memory_id

CREATE CONSTRAINT requirement_memory_id_unique IF NOT EXISTS
FOR (r:Requirement) REQUIRE r.memory_id IS UNIQUE;

CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS
FOR (r:Requirement) REQUIRE r.requirement_id IS UNIQUE;

CREATE INDEX requirement_priority_idx IF NOT EXISTS
FOR (r:Requirement) ON (r.priority);

// Properties:
// - memory_id: String (UNIQUE) - Reference to Qdrant memory
// - requirement_id: String (UNIQUE) - REQ-XXX-NNN pattern
// - title: String - Requirement title
// - priority: String (INDEXED) - Critical/High/Medium/Low

// ------------------------------------------------------------------------------
// Design Node
// ------------------------------------------------------------------------------
// Represents a design document or ADR
// Links to Qdrant design_memory collection via memory_id

CREATE CONSTRAINT design_memory_id_unique IF NOT EXISTS
FOR (d:Design) REQUIRE d.memory_id IS UNIQUE;

CREATE INDEX design_title_idx IF NOT EXISTS
FOR (d:Design) ON (d.title);

CREATE INDEX design_type_idx IF NOT EXISTS
FOR (d:Design) ON (d.design_type);

// Properties:
// - memory_id: String (UNIQUE) - Reference to Qdrant memory
// - title: String (INDEXED) - Design document title
// - design_type: String (INDEXED) - ADR/Specification/Architecture/Interface

// ------------------------------------------------------------------------------
// Pattern Node
// ------------------------------------------------------------------------------
// Represents a code pattern or template
// Links to Qdrant code_patterns collection via memory_id

CREATE CONSTRAINT pattern_memory_id_unique IF NOT EXISTS
FOR (p:Pattern) REQUIRE p.memory_id IS UNIQUE;

CREATE INDEX pattern_name_idx IF NOT EXISTS
FOR (p:Pattern) ON (p.pattern_name);

CREATE INDEX pattern_type_idx IF NOT EXISTS
FOR (p:Pattern) ON (p.pattern_type);

// Properties:
// - memory_id: String (UNIQUE) - Reference to Qdrant memory
// - pattern_name: String (INDEXED) - Pattern name
// - pattern_type: String (INDEXED) - Template/Convention/Idiom/Architecture

// ------------------------------------------------------------------------------
// Test Node
// ------------------------------------------------------------------------------
// Represents a test case
// Links to Qdrant test_history collection via memory_id

CREATE CONSTRAINT test_memory_id_unique IF NOT EXISTS
FOR (t:Test) REQUIRE t.memory_id IS UNIQUE;

CREATE INDEX test_name_idx IF NOT EXISTS
FOR (t:Test) ON (t.test_name);

CREATE INDEX test_file_idx IF NOT EXISTS
FOR (t:Test) ON (t.test_file);

// Properties:
// - memory_id: String (UNIQUE) - Reference to Qdrant memory
// - test_name: String (INDEXED) - Test name
// - test_file: String (INDEXED) - Test file path

// ==============================================================================
// RELATIONSHIP DEFINITIONS
// ==============================================================================

// ------------------------------------------------------------------------------
// CALLS Relationship
// ------------------------------------------------------------------------------
// Function calls another function
// Direction: Caller -> Callee

// CREATE INDEX rel_calls_created_at IF NOT EXISTS
// FOR ()-[r:CALLS]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created
// - line_number: Integer (optional) - Line where call occurs

// ------------------------------------------------------------------------------
// IMPORTS Relationship
// ------------------------------------------------------------------------------
// File or module imports another module or file
// Direction: Importer -> Imported

// CREATE INDEX rel_imports_created_at IF NOT EXISTS
// FOR ()-[r:IMPORTS]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created
// - items: List[String] (optional) - Specific items imported

// ------------------------------------------------------------------------------
// EXTENDS Relationship
// ------------------------------------------------------------------------------
// Class extends (inherits from) another class
// Direction: Child -> Parent

// CREATE INDEX rel_extends_created_at IF NOT EXISTS
// FOR ()-[r:EXTENDS]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created

// ------------------------------------------------------------------------------
// IMPLEMENTS Relationship
// ------------------------------------------------------------------------------
// Class implements an interface
// Direction: Implementor -> Interface

// CREATE INDEX rel_implements_created_at IF NOT EXISTS
// FOR ()-[r:IMPLEMENTS]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created

// ------------------------------------------------------------------------------
// CONTAINS Relationship
// ------------------------------------------------------------------------------
// File or class contains functions or classes
// Direction: Container -> Contained

// CREATE INDEX rel_contains_created_at IF NOT EXISTS
// FOR ()-[r:CONTAINS]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created

// ------------------------------------------------------------------------------
// DEPENDS_ON Relationship
// ------------------------------------------------------------------------------
// Component depends on another component
// Direction: Dependent -> Dependency

// CREATE INDEX rel_depends_on_created_at IF NOT EXISTS
// FOR ()-[r:DEPENDS_ON]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created
// - dependency_type: String (optional) - Runtime/Build/Optional

// ------------------------------------------------------------------------------
// IMPLEMENTS_REQ Relationship
// ------------------------------------------------------------------------------
// Code implements a requirement
// Direction: Code (Component/Function/Class) -> Requirement

// CREATE INDEX rel_implements_req_created_at IF NOT EXISTS
// FOR ()-[r:IMPLEMENTS_REQ]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created
// - completeness: Float (optional) - Implementation completeness (0.0-1.0)

// ------------------------------------------------------------------------------
// FOLLOWS_DESIGN Relationship
// ------------------------------------------------------------------------------
// Code follows a design document
// Direction: Code (Component/Function/Class) -> Design

// CREATE INDEX rel_follows_design_created_at IF NOT EXISTS
// FOR ()-[r:FOLLOWS_DESIGN]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created

// ------------------------------------------------------------------------------
// USES_PATTERN Relationship
// ------------------------------------------------------------------------------
// Code uses a pattern
// Direction: Code (Component/Class) -> Pattern

// CREATE INDEX rel_uses_pattern_created_at IF NOT EXISTS
// FOR ()-[r:USES_PATTERN]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created

// ------------------------------------------------------------------------------
// TESTS Relationship
// ------------------------------------------------------------------------------
// Test tests code
// Direction: Test -> Tested (Component/Function/Class)

// CREATE INDEX rel_tests_created_at IF NOT EXISTS
// FOR ()-[r:TESTS]-() ON (r.created_at);

// Properties:
// - created_at: DateTime - When relationship was created
// - last_result: String (optional) - Passed/Failed/Skipped

// ==============================================================================
// EXAMPLE QUERIES
// ==============================================================================

// Find all functions that call a specific function
// MATCH (caller:Function)-[:CALLS]->(target:Function {name: 'authenticate'})
// RETURN caller.name, caller.file_path;

// Find all components that depend on a specific component
// MATCH (dependent:Component)-[:DEPENDS_ON]->(component:Component {component_id: 'auth-service'})
// RETURN dependent.name, dependent.component_id;

// Find all code implementing a requirement
// MATCH (code)-[:IMPLEMENTS_REQ]->(req:Requirement {requirement_id: 'REQ-MEM-FN-001'})
// RETURN DISTINCT labels(code)[0] AS type, code.name;

// Find inheritance hierarchy for a class
// MATCH path = (child:Class {name: 'SpecializedAgent'})-[:EXTENDS*1..5]->(parent:Class)
// RETURN nodes(path);

// Find all tests for a component
// MATCH (test:Test)-[:TESTS]->(component:Component {component_id: 'auth-service'})
// RETURN test.test_name, test.test_file;

// Find transitive dependencies (up to 3 levels deep)
// MATCH path = (c:Component {component_id: 'frontend'})-[:DEPENDS_ON*1..3]->(dep:Component)
// RETURN DISTINCT dep.component_id, dep.name, length(path) AS depth
// ORDER BY depth;

// Find all components using a specific pattern
// MATCH (component:Component)-[:USES_PATTERN]->(pattern:Pattern {pattern_name: 'BaseAgent'})
// RETURN component.name, component.component_id;

// ==============================================================================
// SCHEMA VALIDATION QUERIES
// ==============================================================================

// Show all constraints
// SHOW CONSTRAINTS;

// Show all indexes
// SHOW INDEXES;

// Count nodes by type
// MATCH (n)
// RETURN DISTINCT labels(n) AS NodeType, count(n) AS Count
// ORDER BY Count DESC;

// Count relationships by type
// MATCH ()-[r]->()
// RETURN type(r) AS RelationshipType, count(r) AS Count
// ORDER BY Count DESC;

// ==============================================================================
// END OF SCHEMA
// ==============================================================================
