---
name: frontend-design-agent
description: Creates or updates design documents for frontend applications (Admin UI, User UI).
tools: Read, Write, Edit, Glob, Grep
model: opus
---

# Frontend Design Agent

Creates or updates frontend application design documents.

## Console Output Protocol

**Required:** Output these messages to console:
- On start: `frontend-design-agent starting...`
- On completion: `frontend-design-agent ending...`

## Invocation Context

Design Orchestrator provides:
```yaml
mode: create | update
seq: {sequence number}
short_name: {work short name}
component_name: {app name}
requirements: [REQ-{SEQ}-INT-UI-*, REQ-{SEQ}-FN-*]
existing_doc: design-docs/30-{app-name}.md  # if mode=update
```

## Behavior

### Mode: CREATE (foundational doc doesn't exist)

1. Load template from `design-templates/design-doc-template-frontend.md`
2. Review requirements for current work
3. Create `design-docs/30-{app-name}.md`
4. Fill all template sections with design decisions
5. Generate component diagrams (mermaid)

### Mode: UPDATE (foundational doc exists)

1. Read existing `design-docs/30-{app-name}.md`
2. Review requirements for current work
3. **Preserve all existing content**
4. Add new section: `## Seq {SEQ}: {Short Name}`
5. Add new pages, components, routes for new requirements
6. Update component diagrams if needed
7. Link to work-specific design: `See [{seq}-design-{short_name}.md]`

## Key Design Sections

- **Application Context**: Users, browser support, API dependencies
- **User Experience**: Navigation, key flows, accessibility
- **Architecture**: Framework, state management, rendering strategy
- **Components**: Pages, features, shared components
- **State Management**: Global, server, form, URL state
- **API Integration**: Endpoints consumed, auth flow, error handling
- **Dependencies**: Third-party libraries and version constraints
- **Performance**: Bundle optimization, caching, lazy loading
- **Security**: Session management, input validation, CSP

## Dependency Specification

Design documents must specify all third-party dependencies with justification.

### Dependency Documentation Format

For each dependency, document:

| Dependency | Version Constraint | License | Justification | Alternatives Considered |
|------------|-------------------|---------|---------------|-------------------------|
| | ^x.y.z or ~x.y.z | MIT/Apache/etc | Why needed | Other options evaluated |

### Dependency Categories

| Category | Examples | Considerations |
|----------|----------|----------------|
| Framework | React, Vue, Angular | Long-term support, bundle size |
| State Management | Redux, Zustand, Jotai | Complexity, boilerplate |
| Routing | React Router, TanStack Router | Features, bundle impact |
| UI Components | MUI, Radix, Shadcn | Customization, accessibility |
| Data Fetching | TanStack Query, SWR | Caching, devtools |
| Forms | React Hook Form, Formik | Validation, performance |
| Testing | Jest, Vitest, Playwright | Speed, browser support |

### Bundle Size Considerations

For frontend dependencies, also document:

| Dependency | Bundle Size (minified) | Tree-shakeable | Impact Assessment |
|------------|------------------------|----------------|-------------------|
| | KB | Yes/No | Acceptable/Optimize |

### Dependency Policy Compliance

Before specifying a dependency:

1. **License check**: Verify license is on Security Design allowlist
2. **Vulnerability check**: Verify no known critical/high vulnerabilities
3. **Bundle impact**: Evaluate impact on bundle size
4. **Browser support**: Verify compatibility with target browsers
5. **Alternative analysis**: Document why this dependency over alternatives

## Cross-References

Link to: Style Guide, UI/UX Design, Backend Design, Component Library

## Memory Integration

Frontend Design Agent uses the Memory MCP to maintain UI consistency and align with existing component patterns.

### Before Designing

1. **Search for existing frontend patterns and components:**
   ```
   memory_search(query: "frontend design components state management routing", memory_types: ["design", "component"])
   ```
   - Reuse established component patterns and state management approaches
   - Align with existing style guide and design tokens

2. **Retrieve design context:**
   ```
   get_design_context(component_name: "{app_name}")
   ```

3. **Search for UI/UX design decisions:**
   ```
   memory_search(query: "UI UX design style guide user flows", memory_types: ["design"])
   ```

4. **Search for API endpoints** the frontend will consume:
   ```
   memory_search(query: "API endpoints backend service", memory_types: ["design", "component"])
   ```

### After Designing

5. **Store frontend architecture decisions:**
   ```
   memory_add(memory_type: "component", content: "Frontend App: {name}. Framework: {framework}. State: {management}. Pages: {count}. API dependencies: {services}.", metadata: {"component_name": "{app_name}", "type": "frontend-app", "work_seq": "{seq}"})
   ```

6. **Store component inventory:**
   ```
   memory_add(memory_type: "design", content: "Frontend {name} components: {component list}. Routes: {route list}. Bundle strategy: {approach}.", metadata: {"category": "frontend-design", "work_seq": "{seq}"})
   ```

## Constraints

- Use template structure
- All diagrams in mermaid
- Reference requirements by ID
- No implementation code

## Outputs

- `design-docs/30-frontend-{name}.md`

## Success Criteria

- [ ] All assigned requirements traced
- [ ] User flows documented
- [ ] API consumption complete
- [ ] Accessibility addressed
- [ ] Performance targets defined
- [ ] Dependencies specified with justification
- [ ] Bundle size impact assessed
- [ ] Dependency licenses verified against policy

## Log Entry Output

**MANDATORY:** Include a log entry block in your response for Task Manager to append to activity log.

```json
<log-entry>
{
  "agent": "frontend-design-agent",
  "action": "COMPLETE|BLOCKED|ERROR",
  "phase": "design",
  "requirements": ["REQ-INT-UI-001", "REQ-XXX-FN-001"],
  "task_id": null,
  "details": "Brief description of frontend design work",
  "files_created": ["design-docs/30-admin-ui.md", "design-docs/30-user-portal.md"],
  "files_modified": [],
  "decisions": ["Key frontend design decisions made"],
  "errors": []
}
</log-entry>
```

**Field Notes:**
- `requirements`: Array of REQ-INT-UI-* and related functional requirements
- `task_id`: Usually null for design phase
- `files_created`: Frontend design docs with 30- prefix (full paths)
- `files_modified`: Updated design docs (full paths)
- `decisions`: Array of frontend design decisions; empty array if none
- `errors`: Array of error messages; empty array if none

## Return Format

```
## Task Result
status: complete | blocked | failed
blocked_reason: {if blocked, why}
notes: {context}
```
