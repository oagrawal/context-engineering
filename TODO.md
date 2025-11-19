# Context Management System - TODO List

## Phase 1: Project Setup & Foundation

### 1.1 Project Structure Setup
- [ ] Create project directory structure
- [ ] Set up Python project with appropriate dependencies (e.g., pyyaml for YAML parsing, click/argparse for CLI)
- [ ] Create `.context/` directory structure:
  - [ ] `.context/main.md` template
  - [ ] `.context/branches/` directory
- [ ] Set up basic project documentation (README.md)

### 1.2 Core Data Models & Schemas
- [ ] Define data structures for:
  - [ ] Branch metadata (name, created date, etc.) - minimal metadata since branch directory contains all context
  - [ ] Commit entry structure (branch purpose, previous progress, commit contribution, commit timestamp/ID)
  - [ ] Log entry structure (timestamp, reasoning step)
  - [ ] Metadata.yaml schema (file structure, env config, custom entries)
- [ ] Create validation functions for each data structure
- [ ] Define default templates for each file type
- [ ] Design commit comparison logic to handle common prefix problem (compare commit lists to find divergence point)

## Phase 2: File System Operations

### 2.1 Context Directory Management
- [ ] Implement function to initialize `.context/` directory if it doesn't exist
- [ ] Implement function to create/validate `main.md` structure
- [ ] Implement function to create new branch directory structure
- [ ] Implement function to check if branch exists
- [ ] Implement function to get current branch (store in `.context/.current_branch` file)
- [ ] Implement function to switch current branch pointer

### 2.2 File Read/Write Operations
- [ ] Implement reading/writing `main.md` (markdown parsing)
- [ ] Implement reading/writing `commit.md` (structured markdown with entries)
- [ ] Implement reading/writing `log.md` (append-only log entries)
- [ ] Implement reading/writing `metadata.yaml` (YAML parsing with validation)
- [ ] Handle file locking/conflicts for concurrent access

## Phase 3: Core Command Implementations

### 3.1 COMMIT Command
- [ ] Parse command arguments (optional message, optional log range)
- [ ] Read current branch's `commit.md` to get last commit entry
- [ ] Read current branch's `log.md` to extract relevant reasoning steps
- [ ] Generate "previous progress" by combining previous commit's progress + contribution
- [ ] Generate "commit contribution" from log entries or user input
- [ ] Read branch purpose from branch metadata or first commit
- [ ] Append new commit entry to `commit.md` with unique commit ID/timestamp
- [ ] Optionally update `metadata.yaml` if structural changes detected
- [ ] Create git commit to checkpoint this memory state (commit .context/ directory)

### 3.2 BRANCH Command
- [ ] Parse command arguments (branch name, optional `--from BRANCH`, optional `--empty` flag)
- [ ] Validate branch name (no conflicts, valid characters)
- [ ] Create new branch directory structure
- [ ] Handle two branch creation modes:
  - [ ] `--empty`: Create branch with empty `log.md` and `commit.md` (user/agent writes branch purpose)
  - [ ] Default or `--from BRANCH`: Copy context from specified branch (or current branch)
- [ ] When copying from existing branch:
  - [ ] Copy `commit.md`, `log.md`, `metadata.yaml` from source branch
  - [ ] Last commit in copied `commit.md` becomes the branch pointer (no separate tracking needed)
- [ ] Update branch metadata (creation date only - branch directory contains all context)
- [ ] Switch current branch pointer to new branch

### 3.3 MERGE Command
- [ ] Parse command arguments (source branch(es))
- [ ] Read commit entries from source branch(es)
- [ ] Read commit entries from current branch
- [ ] Handle common prefix problem:
  - [ ] Compare commit lists to find last common commit (branch point)
  - [ ] Only merge commits that occurred AFTER branch point (unique to each branch)
  - [ ] Track which commits came from which branch in merge commit
- [ ] Merge commit entries into current branch's `commit.md`:
  - [ ] Append commits from source branch(es) that are after branch point
  - [ ] Create merge commit entry indicating which branch(es) were merged into current branch
- [ ] Merge log entries into current branch's `log.md`:
  - [ ] Append log entries from source branch(es) with origin tags (e.g., `== Branch A ==`)
  - [ ] Preserve traceability of reasoning steps
- [ ] Merge metadata.yaml entries (simple merge, no conflict resolution for now)
- [ ] Update `main.md`:
  - [ ] Add summary of merged branch's outcome and impact on broader roadmap
  - [ ] Update TODO list if branch contributed to TODO items
- [ ] Create git commit to checkpoint this merge state

### 3.4 INFO Command
- [ ] Parse command arguments (level: project/branch/session, optional branch name)
- [ ] Implement project-level info:
  - [ ] Read and display `main.md` content (goals, milestones, TODO)
  - [ ] List all branches
  - [ ] Show branch tree/structure
- [ ] Implement branch-level info:
  - [ ] Read and display branch `commit.md` summaries
  - [ ] Show branch metadata (creation date, commit count)
  - [ ] Show branch purpose and progress summary
- [ ] Implement session-level info:
  - [ ] Read and display recent `log.md` entries
  - [ ] Show detailed reasoning cycles
  - [ ] Filter by date range or entry count

## Phase 4: CLI Interface

### 4.1 CLI Framework Setup
- [ ] Choose CLI framework (click, argparse, or typer)
- [ ] Set up command structure:
  - [ ] `commit [--message MESSAGE] [--from-log RANGE]`
  - [ ] `branch <name> [--from BRANCH] [--empty]`
  - [ ] `merge <branch1> [<branch2> ...]`
  - [ ] `info [--level LEVEL] [--branch BRANCH] [--format FORMAT]`
- [ ] Implement help text for each command
- [ ] Add global options (--verbose, --dry-run, etc.)

### 4.2 Error Handling & Validation
- [ ] Implement error handling for:
  - [ ] Invalid branch names
  - [ ] Missing files/directories
  - [ ] Corrupted YAML/markdown files
  - [ ] Git repository not initialized
  - [ ] Git commit failures
- [ ] Add validation for command arguments
- [ ] Provide helpful error messages

