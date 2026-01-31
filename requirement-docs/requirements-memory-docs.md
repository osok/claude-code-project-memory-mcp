# Claude Code Long-Term Memory System - Requirements Specification

**Document ID:** REQ-MEM-001
**Version:** 1.0
**Status:** Draft
**Classification:** Internal Use Only
**Compliance:** ISO/IEC/IEEE 29148:2018

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Stakeholder Requirements](#2-stakeholder-requirements)
3. [System Requirements](#3-system-requirements)
4. [Interface Requirements](#4-interface-requirements)
5. [Data Requirements](#5-data-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Verification Requirements](#7-verification-requirements)
8. [Deployment Requirements](#8-deployment-requirements)
9. [Document Control](#9-document-control)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the Claude Code Long-Term Memory System, a persistent memory infrastructure designed to enhance Claude Code's capabilities for complex, multi-session software development projects. The system addresses critical limitations in AI-assisted development including context loss across sessions, code duplication, inconsistent implementation patterns, and design drift during debugging. This specification defines the functional and non-functional requirements that the system shall satisfy and serves as the authoritative reference for implementation.

### 1.2 Scope

**Included Capabilities:**
- Multi-tiered memory architecture with episodic, semantic, and procedural memory layers
- Vector-based semantic search using Qdrant for code and documentation embeddings
- Graph-based relationship tracking using Neo4j for code structure, dependencies, and call graphs
- Letta/MemGPT-inspired self-editing memory management with autonomous consolidation
- MCP (Model Context Protocol) server providing memory query and update tools to Claude Code
- Requirements memory linking specifications to implementing code
- Design memory preserving architectural decisions and ADRs
- Code pattern memory capturing successful implementations and templates
- Component registry tracking all system components and their relationships
- Function index with duplicate detection using cosine similarity thresholds
- Test history memory correlating failures with fixes and design alignment
- Session history capturing key decisions and learnings across development sessions
- User preference memory for coding style, framework conventions, and patterns
- Memory normalization system for cleanup and optimization
- Voyage-Code-3 embeddings optimized for code semantic search

**Excluded Capabilities:**
- Modification of Claude Code's core functionality or system prompts
- Direct storage of memory content in CLAUDE.md files (CLAUDE.md references memory system only)
- Multi-user collaboration or shared memory across different developers
- Real-time synchronization with external version control systems
- Automated code generation based on memory (Claude Code retains this responsibility)
- Training or fine-tuning of language models

### 1.3 Definitions and Acronyms

**Definitions:**
- **ADR (Architecture Decision Record):** Structured document capturing an architectural decision, its context, rationale, and consequences
- **Agent Memory:** Memory scoped to a specific sub-agent type within the SDLC workflow, persisting across tasks assigned to that agent
- **Base Agent Pattern:** Common implementation template that multiple similar components (e.g., 12 agents) should follow for consistency
- **Code Pattern:** Reusable implementation approach or template extracted from successful code
- **Component Registry:** Catalog of all system components with their types, dependencies, interfaces, and relationships
- **Consolidation:** Process of merging related memories, resolving conflicts, and reducing redundancy while preserving essential information
- **Context Window:** The limited token capacity available to Claude Code for processing information in a single interaction
- **Cosine Similarity:** Mathematical measure of similarity between two vectors, used for duplicate detection and semantic search
- **Design Drift:** Gradual deviation from original design intent during implementation or debugging
- **Duplicate Detection:** Process of identifying semantically equivalent or highly similar code to prevent redundant implementations
- **Embedding:** Dense vector representation of text or code that captures semantic meaning for similarity comparisons
- **Episodic Memory:** Memory of specific events, sessions, and interactions with temporal context
- **Function Index:** Searchable catalog of all functions in the codebase with their embeddings, signatures, and locations
- **Knowledge Graph:** Graph structure representing entities (code elements) and their relationships (calls, imports, extends)
- **Late Detection:** Discovery of a memory-relevant event after the original context has been processed
- **Memory Normalization:** Process of cleaning, deduplicating, and optimizing memory storage by rebuilding into a fresh store
- **Memory Tier:** Level of memory organization (working, episodic, semantic, procedural) with different retention and access patterns
- **MCP (Model Context Protocol):** Standardized protocol for AI applications to connect with external data sources and tools
- **Procedural Memory:** Memory of how to perform tasks, including workflows, patterns, and best practices
- **Requirements Traceability:** Linkage between requirements, design elements, and implementing code
- **Self-Editing Memory:** Memory management approach where the AI system manages its own memory through tool calls
- **Semantic Memory:** Memory of facts, concepts, and general knowledge abstracted from specific episodes
- **Session:** A single Claude Code interaction session, from start to context reset or user termination
- **Test History:** Record of test executions, failures, fixes applied, and their alignment with design requirements
- **Vector Database:** Database optimized for storing and querying high-dimensional vector embeddings
- **Working Memory:** Immediate context available to Claude Code within the current context window

**Acronyms:**
- **ADR:** Architecture Decision Record
- **API:** Application Programming Interface
- **AST:** Abstract Syntax Tree
- **CRUD:** Create, Read, Update, Delete
- **DXA:** Document XML Architecture units (1440 DXA = 1 inch)
- **HNSW:** Hierarchical Navigable Small World (graph-based approximate nearest neighbor algorithm)
- **HTTP/HTTPS:** Hypertext Transfer Protocol (Secure)
- **JSON:** JavaScript Object Notation
- **JSONL:** JSON Lines format
- **LLM:** Large Language Model
- **MCP:** Model Context Protocol
- **NFR:** Non-Functional Requirement
- **RAG:** Retrieval-Augmented Generation
- **REST:** Representational State Transfer
- **SDLC:** Software Development Lifecycle
- **SQL:** Structured Query Language
- **TTL:** Time To Live
- **UUID:** Universally Unique Identifier
- **YAML:** YAML Ain't Markup Language

### 1.4 References

**Normative References:**
- ISO/IEC/IEEE 29148:2018 - Systems and software engineering — Life cycle processes — Requirements engineering
- Model Context Protocol Specification (https://modelcontextprotocol.io)
- Qdrant Vector Database Documentation (https://qdrant.tech/documentation)
- Neo4j Graph Database Documentation (https://neo4j.com/docs)
- Voyage-Code-3 Embedding Model Documentation

**Informative References:**
- Letta/MemGPT Architecture Documentation (https://docs.letta.com)
- Mem0 Memory Framework Documentation (https://mem0.ai)
- Claude Code Documentation (https://docs.anthropic.com/claude-code)
- "MemGPT: Towards LLMs as Operating Systems" (arXiv:2310.08560)
- "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory" (arXiv:2504.19413)
- "Cognitive Memory in Large Language Models" (arXiv:2504.02441)

---

## 2. Stakeholder Requirements

### 2.1 System Context

The Claude Code Long-Term Memory System serves as persistent memory infrastructure for Claude Code during complex, multi-session software development projects. It enables Claude Code to maintain context, recall past decisions, detect duplicate implementations, and ensure consistency across components developed over days or weeks.

**System Boundaries:**
- **Upstream:** Claude Code (primary consumer), Developer workstation file system, Project codebase
- **Downstream:** None (terminal system providing services to Claude Code)
- **External:** Voyage AI API (embeddings), Docker runtime environment

**Integration Points:**
- Claude Code via MCP Server tools
- CLAUDE.md via reference documentation (not storage)
- Project file system for codebase indexing
- Docker volumes for persistent storage

### 2.2 User Needs

- **Solo Developer:** Maintain project context across multiple development sessions spanning days or weeks without re-explaining project structure, decisions, or conventions (Priority: Critical)
- **Solo Developer:** Prevent Claude Code from recreating functionality that already exists in the codebase by providing semantic code search and duplicate detection (Priority: Critical)
- **Solo Developer:** Ensure consistent implementation patterns when building similar components (e.g., 12 agents extending a common base) developed at different times (Priority: Critical)
- **Solo Developer:** Keep test fixes aligned with original design requirements rather than introducing design drift during debugging (Priority: Critical)
- **Solo Developer:** Enable Claude Code to understand the full context of requirements documents, design documentation, and existing codebase to build cohesive applications (Priority: Critical)
- **Solo Developer:** Provide clear visibility into what the memory system knows and how it influences Claude Code's responses (Priority: High)
- **Solo Developer:** Support memory cleanup and normalization to maintain quality over long project lifecycles (Priority: High)

### 2.3 Constraints

**Operational Constraints:**
- The system shall operate on a single developer's workstation
- The system shall persist state across Claude Code sessions using Docker volumes
- The system shall support projects developed over days to weeks with unlimited sessions
- The system shall not modify CLAUDE.md content; CLAUDE.md shall only reference memory system usage
- The system shall integrate with existing SDLC sub-agent workflows defined in CLAUDE.md

**Technical Constraints:**
- Claude Code with Opus 4.5 via Max subscription (200K context window)
- Qdrant vector database for embedding storage and similarity search
- Neo4j graph database for relationship tracking
- Voyage-Code-3 embedding model for code semantic representations
- Docker containerization for all persistent services
- MCP protocol for Claude Code integration
- Letta/MemGPT architectural patterns for memory management

**Design Constraints:**
- Memory system shall be additive to Claude Code capabilities, not modify core behavior
- All memory operations shall be explicitly invokable via MCP tools
- Memory shall be organized by cognitive type (episodic, semantic, procedural) following Letta/MemGPT patterns
- Duplicate detection threshold shall be 0.85 cosine similarity (configurable)
- Memory shall be retained indefinitely with normalization for cleanup (no automatic deletion)

---

## 3. System Requirements

### 3.1 Functional Requirements

#### 3.1.1 Memory Architecture

**Intent:** Establish the foundational memory structure following Letta/MemGPT patterns with four cognitive tiers optimized for software development context.

**REQ-MEM-FN-001:** The system shall implement a four-tier memory architecture consisting of Working Memory (context window), Episodic Memory (session histories and specific events), Semantic Memory (facts, patterns, and abstractions), and Procedural Memory (workflows and rules).
- **Priority:** Critical
- **Verification:** Architecture review and integration test

**REQ-MEM-FN-002:** The system shall maintain Working Memory as a managed subset of content injected into Claude Code's context window via MCP tool responses, not exceeding 50,000 tokens per query response.
- **Priority:** Critical
- **Verification:** Token count validation test

**REQ-MEM-FN-003:** The system shall store Episodic Memory in Qdrant with temporal metadata enabling queries by time range, session identifier, and semantic similarity.
- **Priority:** Critical
- **Verification:** Temporal query test

**REQ-MEM-FN-004:** The system shall store Semantic Memory as a hybrid of Qdrant embeddings (for similarity search) and Neo4j nodes (for relationship traversal).
- **Priority:** Critical
- **Verification:** Hybrid query test

**REQ-MEM-FN-005:** The system shall store Procedural Memory as structured documents in Qdrant with associated Neo4j nodes linking procedures to applicable contexts and components.
- **Priority:** High
- **Verification:** Procedure retrieval test

#### 3.1.2 Memory Types

**Intent:** Define the eight specific memory types required to address the identified use cases for complex software development projects.

**REQ-MEM-FN-010:** The system shall maintain Requirements Memory containing parsed requirements documents with unique identifiers, bidirectional links to implementing code, verification status, and semantic embeddings for similarity search.
- **Priority:** Critical
- **Verification:** Requirements traceability test

**REQ-MEM-FN-011:** The system shall maintain Design Memory containing architecture decisions, ADRs, design documents, component specifications, and their relationships to requirements and code.
- **Priority:** Critical
- **Verification:** Design retrieval test

**REQ-MEM-FN-012:** The system shall maintain Code Pattern Memory containing successful implementation patterns, base class templates, and reusable code structures with context about when and how to apply them.
- **Priority:** Critical
- **Verification:** Pattern matching test

**REQ-MEM-FN-013:** The system shall maintain Component Registry Memory containing all system components with their types, file locations, public interfaces, dependencies, and relationship edges to other components.
- **Priority:** Critical
- **Verification:** Component lookup test

**REQ-MEM-FN-014:** The system shall maintain Function Index Memory containing all functions in the codebase with embeddings, signatures, file locations, and similarity scores for duplicate detection.
- **Priority:** Critical
- **Verification:** Duplicate detection test

**REQ-MEM-FN-015:** The system shall maintain Test History Memory containing test execution records, failure details, fixes applied, and correlation to design requirements and affected components.
- **Priority:** Critical
- **Verification:** Test history correlation test

**REQ-MEM-FN-016:** The system shall maintain Session History Memory containing key decisions, learnings, context summaries, and outcomes from each development session.
- **Priority:** High
- **Verification:** Session recall test

**REQ-MEM-FN-017:** The system shall maintain User Preferences Memory containing coding style preferences, framework conventions, naming patterns, and tool configurations.
- **Priority:** High
- **Verification:** Preference application test

#### 3.1.3 Self-Editing Memory Management

**Intent:** Implement Letta/MemGPT-inspired self-editing memory where Claude Code manages its own memory through MCP tools.

**REQ-MEM-FN-020:** The system shall provide MCP tools enabling Claude Code to add, update, search, and delete memories across all memory types.
- **Priority:** Critical
- **Verification:** CRUD operation test

**REQ-MEM-FN-021:** The system shall implement memory extraction that automatically identifies salient information from Claude Code interactions when explicitly triggered via MCP tool.
- **Priority:** Critical
- **Verification:** Extraction accuracy test

**REQ-MEM-FN-022:** The system shall implement conflict detection that identifies when new memories contradict or overlap with existing memories, returning conflict details to Claude Code for resolution.
- **Priority:** High
- **Verification:** Conflict detection test

**REQ-MEM-FN-023:** The system shall implement memory consolidation that merges related memories, resolves redundancy, and maintains referential integrity when triggered via MCP tool.
- **Priority:** High
- **Verification:** Consolidation test

**REQ-MEM-FN-024:** The system shall support memory importance scoring based on access frequency, recency, and explicit priority flags, used for retrieval ranking.
- **Priority:** High
- **Verification:** Scoring accuracy test

#### 3.1.4 Code Duplicate Detection

**Intent:** Prevent code duplication by identifying semantically similar existing implementations before new code is generated.

**REQ-MEM-FN-030:** The system shall compute embeddings for all indexed functions using Voyage-Code-3 and store them in Qdrant with function metadata.
- **Priority:** Critical
- **Verification:** Embedding generation test

**REQ-MEM-FN-031:** The system shall provide an MCP tool to search for similar functions given a function description or code snippet, returning matches above 0.85 cosine similarity threshold.
- **Priority:** Critical
- **Verification:** Similarity search test with known duplicates

**REQ-MEM-FN-032:** The system shall return existing function details (location, signature, documentation) when duplicates are detected, enabling Claude Code to suggest reuse.
- **Priority:** Critical
- **Verification:** Duplicate suggestion test

**REQ-MEM-FN-033:** The duplicate detection threshold shall be configurable between 0.70 and 0.95 with default value of 0.85.
- **Priority:** Medium
- **Verification:** Configuration test

#### 3.1.5 Consistency Enforcement

**Intent:** Ensure consistent implementation patterns across similar components developed at different times.

**REQ-MEM-FN-040:** The system shall identify base patterns and templates when a component is registered, storing them as Code Pattern Memory entries.
- **Priority:** Critical
- **Verification:** Pattern extraction test

**REQ-MEM-FN-041:** The system shall provide an MCP tool to retrieve applicable patterns given a component type, returning base class implementations, interface contracts, and coding conventions.
- **Priority:** Critical
- **Verification:** Pattern retrieval test

**REQ-MEM-FN-042:** The system shall track pattern deviations by comparing new implementations against stored patterns, flagging significant differences for review.
- **Priority:** High
- **Verification:** Deviation detection test

**REQ-MEM-FN-043:** The system shall maintain inheritance and extension relationships in Neo4j, enabling queries like "show all agents extending BaseAgent" or "find all implementations of interface X."
- **Priority:** Critical
- **Verification:** Relationship query test

#### 3.1.6 Design Alignment

**Intent:** Maintain alignment between implementations, fixes, and original design requirements.

**REQ-MEM-FN-050:** The system shall provide an MCP tool to retrieve design context for a given component, returning associated requirements, ADRs, and design specifications.
- **Priority:** Critical
- **Verification:** Design context retrieval test

**REQ-MEM-FN-051:** The system shall provide an MCP tool to validate a proposed fix against design requirements, returning alignment score and potential conflicts.
- **Priority:** Critical
- **Verification:** Fix validation test

**REQ-MEM-FN-052:** The system shall record test failures with links to affected requirements, design documents, and the eventual fix applied.
- **Priority:** Critical
- **Verification:** Failure linkage test

**REQ-MEM-FN-053:** The system shall detect when a proposed fix would violate architectural constraints stored in Design Memory, alerting Claude Code before implementation.
- **Priority:** High
- **Verification:** Constraint violation test

#### 3.1.7 Codebase Indexing

**Intent:** Maintain comprehensive index of the project codebase for semantic search and relationship tracking.

**REQ-MEM-FN-060:** The system shall provide an MCP tool to index a file or directory, parsing code to extract functions, classes, imports, and relationships.
- **Priority:** Critical
- **Verification:** Indexing completeness test

**REQ-MEM-FN-061:** The system shall use language-specific parsers (tree-sitter or equivalent) to accurately extract code structure respecting language semantics.
- **Priority:** Critical
- **Verification:** Parser accuracy test

**REQ-MEM-FN-062:** The system shall support incremental indexing, updating only changed files based on modification timestamps or content hashes.
- **Priority:** High
- **Verification:** Incremental update test

**REQ-MEM-FN-063:** The system shall support the following languages at minimum: Python, TypeScript, JavaScript, Java, Go, Rust, and C#.
- **Priority:** High
- **Verification:** Multi-language parsing test

**REQ-MEM-FN-064:** The system shall extract and store the following relationships in Neo4j: function calls, class inheritance, interface implementation, module imports, and file dependencies.
- **Priority:** Critical
- **Verification:** Relationship extraction test

#### 3.1.8 Memory Normalization

**Intent:** Provide cleanup and optimization capabilities to maintain memory quality over long project lifecycles.

**REQ-MEM-FN-070:** The system shall provide an MCP tool to initiate memory normalization, which creates a new temporary memory store, rebuilds from the existing store with cleanup, and swaps upon completion.
- **Priority:** High
- **Verification:** Normalization completion test

**REQ-MEM-FN-071:** During normalization, the system shall deduplicate memories with cosine similarity above 0.95, merging metadata and preserving the most complete version.
- **Priority:** High
- **Verification:** Deduplication test

**REQ-MEM-FN-072:** During normalization, the system shall remove orphaned references where linked entities no longer exist in the codebase.
- **Priority:** High
- **Verification:** Orphan cleanup test

**REQ-MEM-FN-073:** During normalization, the system shall recompute embeddings for memories whose source content has changed.
- **Priority:** High
- **Verification:** Embedding refresh test

**REQ-MEM-FN-074:** The system shall maintain the original memory store until normalization completes successfully, enabling rollback on failure.
- **Priority:** Critical
- **Verification:** Rollback test

**REQ-MEM-FN-075:** The system shall provide progress reporting during normalization via MCP tool status queries.
- **Priority:** Medium
- **Verification:** Progress reporting test

#### 3.1.9 Query and Retrieval

**Intent:** Provide comprehensive query capabilities for Claude Code to access relevant memories.

**REQ-MEM-FN-080:** The system shall provide semantic search across all memory types using Qdrant vector similarity with optional filters for memory type, time range, and metadata attributes.
- **Priority:** Critical
- **Verification:** Filtered search test

**REQ-MEM-FN-081:** The system shall provide graph traversal queries via Neo4j for relationship-based retrieval (e.g., "all callers of function X," "all components depending on module Y").
- **Priority:** Critical
- **Verification:** Graph traversal test

**REQ-MEM-FN-082:** The system shall provide hybrid queries combining semantic similarity with graph relationships for complex retrieval scenarios.
- **Priority:** High
- **Verification:** Hybrid query test

**REQ-MEM-FN-083:** The system shall support query result pagination with configurable page size (default 10, maximum 100).
- **Priority:** Medium
- **Verification:** Pagination test

**REQ-MEM-FN-084:** The system shall return query results ranked by relevance score combining similarity, importance, and recency factors.
- **Priority:** High
- **Verification:** Ranking accuracy test

---

## 4. Interface Requirements

### 4.1 MCP Server Interface

**Intent:** Define the MCP server interface through which Claude Code interacts with the memory system.

**REQ-MEM-INT-001:** The system shall expose an MCP server compliant with Model Context Protocol specification version 2025-11-25 or later.
- **Priority:** Critical
- **Verification:** MCP compliance test

**REQ-MEM-INT-002:** The MCP server shall expose the following tool categories: Memory CRUD (add, update, delete, get), Search (semantic, graph, hybrid), Index (file, directory, incremental), Analysis (duplicate detection, pattern matching, design validation), and Maintenance (normalize, status, statistics).
- **Priority:** Critical
- **Verification:** Tool availability test

**REQ-MEM-INT-003:** All MCP tool inputs and outputs shall use JSON schema validation with comprehensive error messages for invalid inputs.
- **Priority:** High
- **Verification:** Schema validation test

**REQ-MEM-INT-004:** The MCP server shall support concurrent tool invocations from Claude Code with proper request isolation.
- **Priority:** High
- **Verification:** Concurrency test

#### 4.1.1 Memory CRUD Tools

**REQ-MEM-INT-010:** The system shall provide `memory_add` tool accepting memory type, content, metadata, and optional relationships, returning the created memory ID.
- **Priority:** Critical
- **Verification:** Add operation test

**REQ-MEM-INT-011:** The system shall provide `memory_update` tool accepting memory ID, updated content, and metadata, returning success status and updated memory.
- **Priority:** Critical
- **Verification:** Update operation test

**REQ-MEM-INT-012:** The system shall provide `memory_delete` tool accepting memory ID, returning success status and handling cascading relationship cleanup.
- **Priority:** Critical
- **Verification:** Delete with cascade test

**REQ-MEM-INT-013:** The system shall provide `memory_get` tool accepting memory ID, returning full memory content with metadata and relationships.
- **Priority:** Critical
- **Verification:** Get operation test

**REQ-MEM-INT-014:** The system shall provide `memory_bulk_add` tool accepting array of memories for batch insertion with transactional semantics.
- **Priority:** High
- **Verification:** Bulk add test

#### 4.1.2 Search Tools

**REQ-MEM-INT-020:** The system shall provide `memory_search` tool accepting query text, optional memory type filter, optional time range, and limit, returning ranked results with relevance scores.
- **Priority:** Critical
- **Verification:** Search accuracy test

**REQ-MEM-INT-021:** The system shall provide `code_search` tool accepting code snippet or natural language description, returning similar functions with locations and similarity scores.
- **Priority:** Critical
- **Verification:** Code search test

**REQ-MEM-INT-022:** The system shall provide `graph_query` tool accepting Cypher query string, returning Neo4j query results as structured JSON.
- **Priority:** High
- **Verification:** Cypher execution test

**REQ-MEM-INT-023:** The system shall provide `find_duplicates` tool accepting function signature or code, returning potential duplicates above threshold with recommendations.
- **Priority:** Critical
- **Verification:** Duplicate finding test

**REQ-MEM-INT-024:** The system shall provide `get_related` tool accepting entity ID, relationship types, and depth, returning connected entities via graph traversal.
- **Priority:** High
- **Verification:** Relationship traversal test

#### 4.1.3 Index Tools

**REQ-MEM-INT-030:** The system shall provide `index_file` tool accepting file path, parsing and indexing its contents with appropriate language parser.
- **Priority:** Critical
- **Verification:** File indexing test

**REQ-MEM-INT-031:** The system shall provide `index_directory` tool accepting directory path and optional filters, recursively indexing all matching files.
- **Priority:** Critical
- **Verification:** Directory indexing test

**REQ-MEM-INT-032:** The system shall provide `index_status` tool returning current index statistics including file count, function count, last update time, and index health.
- **Priority:** High
- **Verification:** Status reporting test

**REQ-MEM-INT-033:** The system shall provide `reindex` tool accepting optional scope (full or changed-only), triggering reindexing with progress reporting.
- **Priority:** High
- **Verification:** Reindex test

#### 4.1.4 Analysis Tools

**REQ-MEM-INT-040:** The system shall provide `check_consistency` tool accepting component identifier, returning comparison against base patterns with deviation details.
- **Priority:** Critical
- **Verification:** Consistency check test

**REQ-MEM-INT-041:** The system shall provide `validate_fix` tool accepting proposed fix description and affected component, returning design alignment analysis.
- **Priority:** Critical
- **Verification:** Fix validation test

**REQ-MEM-INT-042:** The system shall provide `get_design_context` tool accepting component identifier, returning associated requirements, ADRs, and design specifications.
- **Priority:** Critical
- **Verification:** Context retrieval test

**REQ-MEM-INT-043:** The system shall provide `trace_requirements` tool accepting requirement ID, returning all implementing code, tests, and design documents.
- **Priority:** High
- **Verification:** Traceability test

#### 4.1.5 Maintenance Tools

**REQ-MEM-INT-050:** The system shall provide `normalize_memory` tool initiating the normalization process, returning job ID for status tracking.
- **Priority:** High
- **Verification:** Normalization initiation test

**REQ-MEM-INT-051:** The system shall provide `normalize_status` tool accepting job ID, returning progress percentage, current phase, and any errors.
- **Priority:** High
- **Verification:** Status query test

**REQ-MEM-INT-052:** The system shall provide `memory_statistics` tool returning counts by memory type, storage utilization, index health, and performance metrics.
- **Priority:** Medium
- **Verification:** Statistics accuracy test

**REQ-MEM-INT-053:** The system shall provide `export_memory` tool accepting optional filters, exporting matching memories to JSONL format for backup.
- **Priority:** Medium
- **Verification:** Export completeness test

**REQ-MEM-INT-054:** The system shall provide `import_memory` tool accepting JSONL file path, importing memories with conflict detection and resolution options.
- **Priority:** Medium
- **Verification:** Import with conflict test

### 4.2 Qdrant Interface

**REQ-MEM-INT-060:** The system shall connect to Qdrant using the official Python client (qdrant-client) via HTTP on configurable host and port.
- **Priority:** Critical
- **Verification:** Connection test

**REQ-MEM-INT-061:** The system shall create separate Qdrant collections for each memory type with appropriate vector dimensions matching Voyage-Code-3 output (1024 dimensions).
- **Priority:** Critical
- **Verification:** Collection creation test

**REQ-MEM-INT-062:** The system shall configure Qdrant collections with HNSW indexing parameters optimized for recall (ef_construct: 200, m: 16).
- **Priority:** High
- **Verification:** Index configuration test

**REQ-MEM-INT-063:** The system shall implement connection pooling and retry logic for Qdrant operations with exponential backoff.
- **Priority:** High
- **Verification:** Resilience test

### 4.3 Neo4j Interface

**REQ-MEM-INT-070:** The system shall connect to Neo4j using the official Python driver (neo4j) via Bolt protocol on configurable host and port.
- **Priority:** Critical
- **Verification:** Connection test

**REQ-MEM-INT-071:** The system shall implement the code knowledge graph schema with node types: Function, Class, Module, File, Component, Requirement, Design, Pattern, and Test.
- **Priority:** Critical
- **Verification:** Schema validation test

**REQ-MEM-INT-072:** The system shall implement the code knowledge graph schema with relationship types: CALLS, IMPORTS, EXTENDS, IMPLEMENTS, DEPENDS_ON, IMPLEMENTS_REQ, FOLLOWS_DESIGN, USES_PATTERN, and TESTS.
- **Priority:** Critical
- **Verification:** Relationship type test

**REQ-MEM-INT-073:** The system shall maintain bidirectional references between Qdrant memory IDs and Neo4j node IDs for hybrid queries.
- **Priority:** Critical
- **Verification:** Reference integrity test

**REQ-MEM-INT-074:** The system shall implement Neo4j vector index for embeddings stored on nodes, enabling combined graph and vector queries.
- **Priority:** High
- **Verification:** Vector index test

### 4.4 Voyage-Code-3 Interface

**REQ-MEM-INT-080:** The system shall integrate with Voyage AI API for Voyage-Code-3 embeddings via HTTP REST interface.
- **Priority:** Critical
- **Verification:** API integration test

**REQ-MEM-INT-081:** The system shall batch embedding requests to Voyage AI with maximum batch size of 128 texts per request.
- **Priority:** High
- **Verification:** Batching test

**REQ-MEM-INT-082:** The system shall implement local caching of embeddings to minimize API calls for previously embedded content.
- **Priority:** High
- **Verification:** Cache hit rate test

**REQ-MEM-INT-083:** The system shall handle Voyage AI rate limits with exponential backoff and request queuing.
- **Priority:** High
- **Verification:** Rate limit handling test

**REQ-MEM-INT-084:** The system shall support fallback to local embedding model (configurable) when Voyage AI is unavailable.
- **Priority:** Medium
- **Verification:** Fallback test

### 4.5 File System Interface

**REQ-MEM-INT-090:** The system shall read project files from the mounted project directory with configurable base path.
- **Priority:** Critical
- **Verification:** File read test

**REQ-MEM-INT-091:** The system shall respect .gitignore patterns when indexing directories, excluding ignored files and directories.
- **Priority:** High
- **Verification:** Gitignore respect test

**REQ-MEM-INT-092:** The system shall detect file changes using modification timestamps and content hashes (SHA-256) for incremental indexing.
- **Priority:** High
- **Verification:** Change detection test

**REQ-MEM-INT-093:** The system shall support configurable file extension filters for indexing (default includes common code file extensions).
- **Priority:** Medium
- **Verification:** Filter configuration test

---

## 5. Data Requirements

### 5.1 Memory Schemas

#### 5.1.1 Base Memory Schema

**REQ-MEM-DATA-001:** All memories shall include the following base fields: id (UUID), type (enum), content (text), embedding (vector), created_at (timestamp), updated_at (timestamp), access_count (integer), importance_score (float 0.0-1.0), and metadata (JSON).
- **Priority:** Critical
- **Verification:** Schema validation test

**REQ-MEM-DATA-002:** Memory IDs shall be UUID v4 format ensuring global uniqueness across all memory types.
- **Priority:** Critical
- **Verification:** UUID generation test

#### 5.1.2 Requirements Memory Schema

**REQ-MEM-DATA-010:** Requirements Memory shall include additional fields: requirement_id (string matching REQ-XXX-NNN pattern), title (text), description (text), priority (enum: Critical/High/Medium/Low), status (enum: Draft/Approved/Implemented/Verified), source_document (file path), and implementing_components (array of component IDs).
- **Priority:** Critical
- **Verification:** Requirements schema test

#### 5.1.3 Design Memory Schema

**REQ-MEM-DATA-011:** Design Memory shall include additional fields: design_type (enum: ADR/Specification/Architecture/Interface), title (text), decision (text for ADRs), rationale (text), consequences (text), related_requirements (array of requirement IDs), affected_components (array of component IDs), and status (enum: Proposed/Accepted/Deprecated/Superseded).
- **Priority:** Critical
- **Verification:** Design schema test

#### 5.1.4 Code Pattern Memory Schema

**REQ-MEM-DATA-012:** Code Pattern Memory shall include additional fields: pattern_name (text), pattern_type (enum: Template/Convention/Idiom/Architecture), language (string), code_template (text), usage_context (text), applicable_components (array of component types), and example_implementations (array of file paths).
- **Priority:** Critical
- **Verification:** Pattern schema test

#### 5.1.5 Component Registry Schema

**REQ-MEM-DATA-013:** Component Registry entries shall include: component_id (string), component_type (enum: Frontend/Backend/Agent/Library/Service/Database), name (text), file_path (text), public_interface (JSON describing exports), dependencies (array of component IDs), dependents (array of component IDs), base_pattern (pattern ID if applicable), and version (string).
- **Priority:** Critical
- **Verification:** Component schema test

#### 5.1.6 Function Index Schema

**REQ-MEM-DATA-014:** Function Index entries shall include: function_id (UUID), name (text), signature (text), file_path (text), start_line (integer), end_line (integer), language (string), docstring (text), embedding (vector), containing_class (class ID if applicable), calls (array of function IDs), and called_by (array of function IDs).
- **Priority:** Critical
- **Verification:** Function schema test

#### 5.1.7 Test History Schema

**REQ-MEM-DATA-015:** Test History entries shall include: test_id (UUID), test_name (text), test_file (file path), execution_time (timestamp), status (enum: Passed/Failed/Skipped/Error), failure_message (text if failed), affected_component (component ID), related_requirements (array of requirement IDs), fix_applied (text if fixed), fix_commit (string if applicable), and design_alignment_score (float 0.0-1.0).
- **Priority:** Critical
- **Verification:** Test history schema test

#### 5.1.8 Session History Schema

**REQ-MEM-DATA-016:** Session History entries shall include: session_id (UUID), start_time (timestamp), end_time (timestamp), summary (text), key_decisions (array of text), components_modified (array of component IDs), memories_created (array of memory IDs), and outcome (text).
- **Priority:** High
- **Verification:** Session schema test

#### 5.1.9 User Preferences Schema

**REQ-MEM-DATA-017:** User Preferences entries shall include: preference_id (UUID), category (enum: CodingStyle/Naming/Framework/Tool/Convention), key (text), value (JSON), scope (enum: Global/Language/Project/Component), and examples (array of code snippets).
- **Priority:** High
- **Verification:** Preferences schema test

### 5.2 Graph Schema

**REQ-MEM-DATA-020:** Neo4j nodes shall include a unique `memory_id` property linking to corresponding Qdrant memory entries where applicable.
- **Priority:** Critical
- **Verification:** Cross-reference integrity test

**REQ-MEM-DATA-021:** All Neo4j relationships shall include `created_at` timestamp and optional `metadata` JSON property.
- **Priority:** High
- **Verification:** Relationship metadata test

**REQ-MEM-DATA-022:** Neo4j shall maintain indexes on: Function(name), Class(name), Module(name), File(path), Component(component_id), and Requirement(requirement_id).
- **Priority:** High
- **Verification:** Index presence test

### 5.3 Data Integrity

**REQ-MEM-DATA-030:** The system shall enforce referential integrity between Qdrant memories and Neo4j nodes, preventing orphaned references.
- **Priority:** Critical
- **Verification:** Integrity constraint test

**REQ-MEM-DATA-031:** The system shall validate all memory content against defined schemas before storage, rejecting invalid data with descriptive errors.
- **Priority:** Critical
- **Verification:** Validation rejection test

**REQ-MEM-DATA-032:** The system shall implement optimistic concurrency control for memory updates using version timestamps.
- **Priority:** High
- **Verification:** Concurrent update test

### 5.4 Data Retention

**REQ-MEM-DATA-040:** The system shall retain all memories indefinitely unless explicitly deleted via MCP tool.
- **Priority:** Critical
- **Verification:** Retention verification test

**REQ-MEM-DATA-041:** The system shall maintain full audit trail of memory modifications including previous values, modification time, and operation type.
- **Priority:** High
- **Verification:** Audit trail test

**REQ-MEM-DATA-042:** Deleted memories shall be soft-deleted (marked inactive) and retained for 30 days before permanent removal during normalization.
- **Priority:** Medium
- **Verification:** Soft delete test

---

## 6. Non-Functional Requirements

### 6.1 Performance Requirements

**REQ-MEM-PERF-001:** Semantic search queries shall return results within 500ms for databases containing up to 100,000 memories.
- **Priority:** Critical
- **Verification:** Search latency test under load

**REQ-MEM-PERF-002:** Graph traversal queries shall return results within 200ms for traversals up to 3 hops depth.
- **Priority:** Critical
- **Verification:** Graph query latency test

**REQ-MEM-PERF-003:** Memory add operations shall complete within 100ms excluding embedding generation time.
- **Priority:** High
- **Verification:** Write latency test

**REQ-MEM-PERF-004:** Embedding generation shall batch efficiently to achieve throughput of at least 100 embeddings per second for cached content.
- **Priority:** High
- **Verification:** Embedding throughput test

**REQ-MEM-PERF-005:** Full codebase indexing shall process at least 1,000 files per minute for typical source files.
- **Priority:** High
- **Verification:** Indexing throughput test

**REQ-MEM-PERF-006:** Duplicate detection shall return results within 300ms for comparison against function index of 10,000 functions.
- **Priority:** Critical
- **Verification:** Duplicate detection latency test

### 6.2 Security Requirements

**REQ-MEM-SEC-001:** All API keys (Voyage AI) shall be stored as environment variables, never in code or configuration files within the repository.
- **Priority:** Critical
- **Verification:** Secret scanning test

**REQ-MEM-SEC-002:** The MCP server shall only accept connections from localhost (127.0.0.1) by default.
- **Priority:** Critical
- **Verification:** Network binding test

**REQ-MEM-SEC-003:** Docker containers shall run as non-root user with minimal required capabilities.
- **Priority:** High
- **Verification:** Container security scan

**REQ-MEM-SEC-004:** Database connections (Qdrant, Neo4j) shall use authentication when configured, with credentials stored as environment variables.
- **Priority:** High
- **Verification:** Authentication test

**REQ-MEM-SEC-005:** The system shall not transmit memory content to external services except Voyage AI for embedding generation, with option to use local embedding model for air-gapped environments.
- **Priority:** High
- **Verification:** Network traffic audit

### 6.3 Reliability Requirements

**REQ-MEM-REL-001:** The system shall persist all data to Docker volumes, surviving container restarts without data loss.
- **Priority:** Critical
- **Verification:** Restart recovery test

**REQ-MEM-REL-002:** The system shall implement transaction semantics for operations spanning Qdrant and Neo4j, with rollback on partial failure.
- **Priority:** Critical
- **Verification:** Transaction rollback test

**REQ-MEM-REL-003:** The system shall handle Qdrant or Neo4j unavailability gracefully, queuing operations for retry and returning appropriate error responses.
- **Priority:** High
- **Verification:** Degradation test

**REQ-MEM-REL-004:** The system shall implement health checks for all external dependencies (Qdrant, Neo4j, Voyage AI) with configurable thresholds.
- **Priority:** High
- **Verification:** Health check test

**REQ-MEM-REL-005:** Memory normalization shall be atomic, completing fully or rolling back to previous state on any failure.
- **Priority:** Critical
- **Verification:** Normalization atomicity test

### 6.4 Scalability Requirements

**REQ-MEM-SCAL-001:** The system shall support projects with up to 100,000 source files without degradation below performance requirements.
- **Priority:** High
- **Verification:** Large project test

**REQ-MEM-SCAL-002:** The system shall support up to 1,000,000 total memories across all types without degradation below performance requirements.
- **Priority:** High
- **Verification:** Memory scale test

**REQ-MEM-SCAL-003:** The system shall support function index of up to 500,000 functions for duplicate detection.
- **Priority:** High
- **Verification:** Function index scale test

**REQ-MEM-SCAL-004:** Docker resource limits shall be configurable with recommended minimums: Memory Service 2GB RAM, Qdrant 4GB RAM, Neo4j 2GB RAM.
- **Priority:** High
- **Verification:** Resource configuration test

### 6.5 Maintainability Requirements

**REQ-MEM-MAINT-001:** All code shall include type hints and docstrings for public interfaces following Google Python Style Guide.
- **Priority:** High
- **Verification:** Code style check

**REQ-MEM-MAINT-002:** The system shall implement structured logging with JSON format including timestamp, level, component, operation, and context fields.
- **Priority:** High
- **Verification:** Log format test

**REQ-MEM-MAINT-003:** All configuration shall be externalized via environment variables with sensible defaults documented.
- **Priority:** High
- **Verification:** Configuration documentation review

**REQ-MEM-MAINT-004:** The system shall provide comprehensive API documentation for all MCP tools including input/output schemas and examples.
- **Priority:** High
- **Verification:** Documentation completeness review

**REQ-MEM-MAINT-005:** Unit test coverage shall exceed 80% for core memory management logic.
- **Priority:** High
- **Verification:** Coverage report

### 6.6 Observability Requirements

**REQ-MEM-OBS-001:** The system shall expose metrics endpoint (Prometheus format) including: query latency histograms, operation counts by type, memory counts by type, embedding cache hit rate, and error rates.
- **Priority:** High
- **Verification:** Metrics endpoint test

**REQ-MEM-OBS-002:** The system shall log all MCP tool invocations with input parameters (sanitized), execution time, and result status.
- **Priority:** High
- **Verification:** Invocation logging test

**REQ-MEM-OBS-003:** The system shall provide memory statistics via MCP tool including: total memories by type, storage utilization, index health, and recent activity summary.
- **Priority:** Medium
- **Verification:** Statistics accuracy test

**REQ-MEM-OBS-004:** Error conditions shall be logged with full context including stack traces, input parameters, and system state.
- **Priority:** High
- **Verification:** Error logging test

### 6.7 Usability Requirements

**REQ-MEM-USE-001:** MCP tool error messages shall be actionable, describing what went wrong and suggesting corrective action.
- **Priority:** High
- **Verification:** Error message review

**REQ-MEM-USE-002:** The system shall provide a CLI utility for administrative operations (backup, restore, statistics, health check) independent of MCP interface.
- **Priority:** Medium
- **Verification:** CLI functionality test

**REQ-MEM-USE-003:** CLAUDE.md integration documentation shall provide clear examples of when and how Claude Code should invoke memory tools within SDLC workflows.
- **Priority:** High
- **Verification:** Documentation usability review

---

## 7. Verification Requirements

### 7.1 Unit Testing

- **Memory CRUD Operations:** 80% coverage - add, update, delete, get for all memory types
- **Schema Validation:** 80% coverage - all memory schemas with valid and invalid inputs
- **Embedding Management:** 80% coverage - generation, caching, batching
- **Query Building:** 80% coverage - semantic search, graph queries, hybrid queries
- **Duplicate Detection:** 80% coverage - similarity calculation, threshold application
- **Normalization Logic:** 80% coverage - deduplication, orphan cleanup, embedding refresh

### 7.2 Integration Testing

**REQ-MEM-VER-001:** Integration tests shall verify complete memory lifecycle from creation through search to deletion with proper persistence.
- **Scope:** End-to-end memory lifecycle
- **Success Criteria:** Memory created, searchable, retrievable, deletable with audit trail

**REQ-MEM-VER-002:** Integration tests shall verify Qdrant and Neo4j consistency after operations spanning both stores.
- **Scope:** Cross-store consistency
- **Success Criteria:** Matching records in both stores, referential integrity maintained

**REQ-MEM-VER-003:** Integration tests shall verify duplicate detection accuracy using known duplicate and non-duplicate function pairs.
- **Scope:** Duplicate detection accuracy
- **Success Criteria:** 95% precision, 90% recall on test dataset

**REQ-MEM-VER-004:** Integration tests shall verify design alignment validation correctly identifies conforming and non-conforming fixes.
- **Scope:** Design alignment accuracy
- **Success Criteria:** Correct classification of test fix scenarios

**REQ-MEM-VER-005:** Integration tests shall verify normalization completes successfully and improves memory quality metrics.
- **Scope:** Normalization effectiveness
- **Success Criteria:** Duplicate count reduced, orphans removed, embeddings refreshed

**REQ-MEM-VER-006:** Integration tests shall verify MCP server handles concurrent requests correctly without data corruption.
- **Scope:** Concurrency safety
- **Success Criteria:** 100 concurrent operations complete without errors or data inconsistency

**REQ-MEM-VER-007:** Integration tests shall verify codebase indexing correctly extracts functions, classes, and relationships for supported languages.
- **Scope:** Indexing accuracy
- **Success Criteria:** All public functions indexed, relationships correctly identified

**REQ-MEM-VER-008:** Integration tests shall verify recovery after container restart with no data loss.
- **Scope:** Persistence durability
- **Success Criteria:** All memories retrievable after restart

### 7.3 Acceptance Criteria

- **Memory Persistence:** Given memory added via MCP tool, memory is retrievable in new Claude Code session after container restart
- **Duplicate Detection:** Given function similar to existing indexed function (>0.85 similarity), system returns existing function as potential duplicate
- **Consistency Enforcement:** Given new agent implementation, system returns applicable base patterns and flags significant deviations
- **Design Alignment:** Given proposed test fix, system returns design context and alignment score with specific concerns if any
- **Requirements Traceability:** Given requirement ID, system returns all implementing code, related design documents, and test coverage
- **Semantic Search:** Given natural language query, system returns relevant memories ranked by relevance within 500ms
- **Graph Traversal:** Given component ID, system returns all dependencies and dependents within 200ms
- **Normalization:** Given normalization trigger, system completes cleanup, reports progress, and swaps to normalized store without data loss

---

## 8. Deployment Requirements

### 8.1 Container Configuration

**Memory Service Container:**
- **Base Image:** python:3.12-slim
- **Memory Limit:** 2GB (recommended), 1GB (minimum)
- **CPU Limit:** 1 core (recommended), 0.5 core (minimum)
- **Health Endpoint:** /health (HTTP 200 when healthy)
- **Metrics Endpoint:** /metrics (Prometheus format)
- **MCP Endpoint:** stdio or HTTP on configurable port (default 8765)

**Qdrant Container:**
- **Image:** qdrant/qdrant:latest
- **Memory Limit:** 4GB (recommended), 2GB (minimum)
- **Storage:** Docker volume mounted at /qdrant/storage
- **Port:** 6333 (HTTP), 6334 (gRPC)

**Neo4j Container (Optional - can be embedded):**
- **Image:** neo4j:5-community
- **Memory Limit:** 2GB (recommended), 1GB (minimum)
- **Storage:** Docker volume mounted at /data
- **Ports:** 7474 (HTTP), 7687 (Bolt)

### 8.2 Environment Variables

**Memory Service:**
- **MCP_HOST** (Optional, default 127.0.0.1): MCP server bind address
- **MCP_PORT** (Optional, default 8765): MCP server port
- **QDRANT_HOST** (Required): Qdrant server host
- **QDRANT_PORT** (Optional, default 6333): Qdrant server port
- **QDRANT_API_KEY** (Optional): Qdrant API key if authentication enabled
- **NEO4J_URI** (Required): Neo4j Bolt URI (e.g., bolt://localhost:7687)
- **NEO4J_USER** (Optional, default neo4j): Neo4j username
- **NEO4J_PASSWORD** (Required if auth enabled): Neo4j password
- **VOYAGE_API_KEY** (Required): Voyage AI API key for embeddings
- **VOYAGE_MODEL** (Optional, default voyage-code-3): Voyage embedding model
- **EMBEDDING_CACHE_SIZE** (Optional, default 10000): Maximum cached embeddings
- **DUPLICATE_THRESHOLD** (Optional, default 0.85): Cosine similarity threshold
- **LOG_LEVEL** (Optional, default INFO): Logging level
- **LOG_FORMAT** (Optional, default json): Log format (json or text)
- **PROJECT_PATH** (Required): Path to mounted project directory
- **METRICS_ENABLED** (Optional, default true): Enable Prometheus metrics
- **METRICS_PORT** (Optional, default 9090): Metrics endpoint port

**Qdrant:**
- **QDRANT__SERVICE__GRPC_PORT** (Optional, default 6334): gRPC port
- **QDRANT__SERVICE__HTTP_PORT** (Optional, default 6333): HTTP port

**Neo4j:**
- **NEO4J_AUTH** (Optional): Authentication in user/password format
- **NEO4J_PLUGINS** (Optional): Comma-separated plugin list
- **NEO4J_dbms_memory_heap_max__size** (Optional, default 1G): Heap size

### 8.3 Docker Compose Configuration

**REQ-MEM-DEP-001:** The system shall provide docker-compose.yml defining all services with appropriate networking, volumes, and dependencies.
- **Priority:** Critical
- **Verification:** Compose deployment test

**REQ-MEM-DEP-002:** Docker volumes shall be named for persistence: memory-qdrant-data, memory-neo4j-data, memory-service-cache.
- **Priority:** Critical
- **Verification:** Volume persistence test

**REQ-MEM-DEP-003:** Services shall be configured with health checks and restart policies (restart: unless-stopped).
- **Priority:** High
- **Verification:** Health check and restart test

**REQ-MEM-DEP-004:** The system shall provide .env.example documenting all environment variables with descriptions and example values.
- **Priority:** High
- **Verification:** Documentation completeness review

### 8.4 Claude Code Integration

**REQ-MEM-DEP-010:** The system shall provide MCP server configuration for Claude Code's .mcp.json or settings.json.
- **Priority:** Critical
- **Verification:** MCP configuration test

**REQ-MEM-DEP-011:** The system shall provide CLAUDE.md section template documenting memory system usage within SDLC workflows.
- **Priority:** Critical
- **Verification:** Documentation review

**REQ-MEM-DEP-012:** The CLAUDE.md section shall specify when each sub-agent should invoke memory tools (query before implementation, record after decisions, validate before fixes).
- **Priority:** Critical
- **Verification:** Workflow coverage review

### 8.5 Dependencies

**Python Dependencies:**
- **qdrant-client:** >=1.7.0 - Qdrant Python client
- **neo4j:** >=5.0.0 - Neo4j Python driver
- **voyageai:** >=0.2.0 - Voyage AI client
- **pydantic:** >=2.0.0 - Data validation
- **fastapi:** >=0.100.0 - HTTP server (if HTTP MCP transport)
- **uvicorn:** >=0.23.0 - ASGI server
- **tree-sitter:** >=0.20.0 - Code parsing
- **tree-sitter-languages:** >=1.8.0 - Language grammars
- **httpx:** >=0.24.0 - HTTP client
- **structlog:** >=23.0.0 - Structured logging
- **prometheus-client:** >=0.17.0 - Metrics

**External Services:**
- Qdrant vector database (containerized)
- Neo4j graph database (containerized or embedded)
- Voyage AI API (external, requires API key)

---

## 9. Document Control

**Revision History:**
- **Version 1.0:** Initial requirements specification based on research findings and stakeholder decisions

**Document Owner:** Project Lead
**Distribution:** Development team
**Classification:** Internal Use Only

**Stakeholder Decisions Incorporated:**
- Graph Database: Qdrant + Neo4j (full relationship tracking)
- Memory Framework: Letta/MemGPT architectural patterns
- Integration Architecture: MCP Server only (CLAUDE.md references, not stores)
- Embedding Model: Voyage-Code-3
- Memory Scope: All 8 memory types enabled
- Duplicate Threshold: 0.85 (moderate)
- Docker Architecture: 2+ containers (Qdrant separate, Memory Service)
- Retention Policy: Keep everything with normalization for cleanup

**Research Sources:**
- Mem0 architecture and conflict resolution patterns
- Letta/MemGPT self-editing memory and tiered hierarchy
- Qdrant vector database capabilities and HNSW configuration
- Neo4j knowledge graph patterns for code relationships
- Voyage-Code-3 embedding model specifications
- Model Context Protocol specification
- Claude Code documentation and CLAUDE.md patterns
- Academic research on LLM memory systems (2023-2025)

---

*End of Requirements Specification Document*