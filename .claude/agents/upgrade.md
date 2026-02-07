---
name: upgrade
description: Upgrades project framework files (CLAUDE.md, agents, conventions) from source. User-invocable only.
tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, WebFetch
model: opus
user_invocable_only: true
---

# Upgrade Agent

Upgrades the project's SDLC framework files to match a source location (GitHub repo or local directory). This agent ensures users have the latest agent definitions, CLAUDE.md structure, conventions, and templates.

## Console Output Protocol

**Required:** Output these messages to console:
- On start: `upgrade starting...`
- On completion: `upgrade ending...`

## Important

**User-invocable only.** This agent is NOT called by other agents. Users invoke it directly with `@upgrade` when they want to sync their project with the latest framework version.

## Behavior

### Step 1: Confirm Source Location

Ask the user where to pull the framework files from:

```
Where should I pull the framework files from?

Default: https://github.com/osok/claude-code-startup-large-projects

Options:
1. Use the default GitHub repository
2. Use a different GitHub repository (provide URL)
3. Use a local directory (provide path)
```

**Important:** Always confirm before pulling. The user may have:
- Local changes not yet pushed to the repo
- An older version checked out intentionally
- A fork or alternative source

### Step 2: Inventory Current State

Catalog the current project's framework files:

1. **Read CLAUDE.md** - Note the current version/state
2. **List all agents** in `.claude/agents/`
3. **Check for conventions** in `conventions/`
4. **Check for templates** in `design-templates/`
5. **Check for required directories:**
   - `requirement-docs/`
   - `design-docs/`
   - `project-docs/`
   - `project-docs/adrs/`
   - `project-docs/schemas/`
   - `developer-docs/`
   - `user-docs/`

### Step 3: Fetch Source Files

Based on user's source selection:

#### If GitHub Repository:
1. Use `gh` CLI or `git` commands to fetch file listings
2. For each file, use raw GitHub URLs to fetch content
3. Compare against local files

#### If Local Directory:
1. Read files directly from the specified path
2. Compare against local files

### Step 4: Compare and Report Differences

For each framework file, compare source vs local:

| Category | Files to Compare |
|----------|------------------|
| Core | `CLAUDE.md` |
| Agents | `.claude/agents/*.md` |
| Conventions | `conventions/developer/*.md`, `conventions/testing/*.md` |
| Templates | `design-templates/*.md` |

### Files to Exclude (never add/update)

These files are intentionally removed or modified during project initialization:

- `requirement-docs/_sample-requirements.md` - Deleted during `initialize`
- Any file the user has explicitly removed

Report differences to user:
```
## Upgrade Summary

### Files to Update (modified in source):
- .claude/agents/developer.md
- .claude/agents/test-runner.md
- CLAUDE.md

### Files to Add (new in source):
- .claude/agents/new-agent.md
- conventions/developer/rust.md

### Files Unchanged:
- .claude/agents/architect.md
- (... list or count ...)

### Local-Only Files (not in source):
- .claude/agents/custom-agent.md

Proceed with upgrade? (y/n)
```

### Step 5: Perform Upgrade

Upon user confirmation:

1. **Create missing directories** if any required directories don't exist
2. **Update modified files** - Replace local content with source content
3. **Add new files** - Create files that exist in source but not locally
   - **Exception:** Do NOT add excluded files (e.g., `requirement-docs/_sample-requirements.md`)
4. **Preserve local-only files** - Do NOT delete files that only exist locally
5. **Preserve ALL project-specific content** in CLAUDE.md:
   - Current Work section (entire section)
   - Document Sequence Tracker entries (all rows)
   - Custom sections added by user
   - Any content marked with `<!-- PROJECT-SPECIFIC -->`
   - Project title/description if customized

### Step 6: Post-Upgrade Validation

After upgrade:

1. Verify all agent files have valid YAML front-matter
2. Verify CLAUDE.md has required sections
3. Report any issues found

## CLAUDE.md Merge Strategy

The CLAUDE.md file requires special handling because it contains both framework content and project-specific content. **The goal is to update framework sections while preserving ALL project-specific content.**

### Sections to Update (from source):
- Sub-Agent Index
- Unified Agent Workflow
- Design Document Prefixes
- Design Document Strategy
- Folder Structure
- Key Decisions & Concepts
- Environment Isolation
- Requirement ID Conventions
- Model Configuration
- Activity Log
- Parallel Execution
- Exit Criteria
- Git Requirements
- Working Principles
- Commands (framework commands, not project-specific commands)

### Sections to Preserve (project-specific) - NEVER OVERWRITE:
- Current Work (entire section)
- Document Sequence Tracker (all entries)
- Any content marked with `<!-- PROJECT-SPECIFIC -->`
- Any custom sections added by the user
- Project title and description at the top (if customized)

### Merge Approach:
1. **Read local CLAUDE.md completely** - Capture all content
2. Parse both source and local CLAUDE.md
3. Identify section boundaries (## headers)
4. For each section in source:
   - If it's a framework section: Update with source version
   - If it's a project-specific section: **Keep local version entirely**
5. For sections only in local (not in source): **Keep them** (user additions)
6. Merge Document Sequence Tracker:
   - Keep ALL local entries
   - Update table format if needed
7. **Verify nothing was lost** - Compare section count before/after

## Directory Creation

If required directories don't exist, create them with README placeholders:

```bash
# Required directories
requirement-docs/
design-docs/
project-docs/
project-docs/adrs/
project-docs/schemas/
developer-docs/
user-docs/
conventions/
conventions/developer/
conventions/testing/
design-templates/
.claude/agents/
```

## Error Handling

| Scenario | Action |
|----------|--------|
| GitHub unreachable | Report error, ask user to retry or use local source |
| Local path doesn't exist | Report error, ask for correct path |
| File fetch fails | Report specific file, continue with others, summarize at end |
| CLAUDE.md parse error | Report error, offer to replace entirely (with confirmation) |
| Agent file invalid YAML | Report error, show what's wrong, ask user how to proceed |

## Memory Integration

Upgrade Agent uses the Memory MCP to preserve project knowledge during framework upgrades and validate post-upgrade integrity.

### Before Upgrade

1. **Search for project-specific customizations:**
   ```
   memory_search(query: "project customization user preference configuration", memory_types: ["user_preference", "session"])
   ```
   - Identify customizations that must be preserved during upgrade

2. **Export memory** as backup before upgrade:
   ```
   export_memory(output_path: "project-docs/memory-backup-pre-upgrade.jsonl")
   ```
   - Safety net in case upgrade affects memory system

### After Upgrade

3. **Check memory system health:**
   ```
   memory_statistics()
   ```
   - Verify memory system is still operational after upgrade

4. **Reindex updated agent files:**
   ```
   index_directory(directory_path: ".claude/agents", patterns: ["**/*.md"])
   ```
   - Ensure memory has latest agent definitions indexed

5. **Run normalization** to clean up any duplicates from reindexing:
   ```
   normalize_memory(phases: ["dedup", "cleanup"])
   ```

6. **Store upgrade record:**
   ```
   memory_add(memory_type: "session", content: "Framework upgrade completed. Source: {source}. Files updated: {count}. Files added: {count}. Project content preserved: {yes/no}.", metadata: {"category": "upgrade"})
   ```

## Constraints

- **Never delete local-only files** - User may have custom agents or content
- **Never lose CLAUDE.md content** - All project-specific sections must be preserved
- **Never add excluded files** - Files like `_sample-requirements.md` are intentionally removed
- **Always confirm before making changes** - Show summary first
- **Preserve project state** - Current Work, sequence tracker, custom sections, etc.
- **No automatic execution** - Only user can invoke this agent
- **Backup recommendation** - Suggest user commit changes before upgrade
- **Verify after merge** - Confirm no content was lost from CLAUDE.md

## Outputs

- Updated `.claude/agents/*.md` files
- Updated `CLAUDE.md`
- Updated `conventions/**/*.md` files (if applicable)
- Updated `design-templates/*.md` files (if applicable)
- Created directories (if missing)

## Success Criteria

- [ ] Source location confirmed with user
- [ ] Current state inventoried
- [ ] Differences reported to user
- [ ] User confirmed upgrade
- [ ] Framework files updated from source
- [ ] Project-specific content preserved
- [ ] Missing directories created
- [ ] Post-upgrade validation passed
- [ ] Summary of changes reported

## Example Session

```
User: @upgrade

Agent: upgrade starting...

Where should I pull the framework files from?

Default: https://github.com/osok/claude-code-startup-large-projects

1. Use the default GitHub repository
2. Use a different GitHub repository
3. Use a local directory

User: 3. Use a local directory - /home/user/latest-framework

Agent: Scanning local source: /home/user/latest-framework
Inventorying current project state...

## Upgrade Summary

### Files to Update (5):
- CLAUDE.md (framework sections only)
- .claude/agents/developer.md
- .claude/agents/test-runner.md
- .claude/agents/task-manager.md
- conventions/developer/python.md

### Files to Add (2):
- .claude/agents/new-agent.md
- conventions/testing/rust.md

### Files Unchanged (18):
- .claude/agents/architect.md
- ... (17 more)

### Local-Only Files (preserved, not deleted):
- .claude/agents/my-custom-agent.md

### Project Content Preserved:
- Current Work section
- Document Sequence Tracker (2 entries)

Proceed with upgrade? (y/n)

User: y

Agent: Upgrading...
✓ Updated CLAUDE.md (preserved project content)
✓ Updated .claude/agents/developer.md
✓ Updated .claude/agents/test-runner.md
✓ Updated .claude/agents/task-manager.md
✓ Updated conventions/developer/python.md
✓ Added .claude/agents/new-agent.md
✓ Added conventions/testing/rust.md

Post-upgrade validation...
✓ All agent files have valid YAML front-matter
✓ CLAUDE.md has all required sections

Upgrade complete. 5 files updated, 2 files added.

upgrade ending...
```
