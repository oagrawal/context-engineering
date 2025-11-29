# Context Management System

A context management system for AI development tools like Cursor and Claude Code that enables leveraging previous context from chat sessions while maintaining dynamic workflows.

## Features

- **COMMIT**: Checkpoint important points in chat sessions and increment branch pointer
- **BRANCH**: Create new branches with easy access to previous branch context
- **MERGE**: Merge context from multiple branches into the current branch
- **INFO**: Get project information at different levels (project goals, branch summaries, detailed chat sessions)

## Installation

### Development Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install the package in editable mode
pip install -e .
```

After installation, the `context` command will be available in your terminal.

### Alternative: Run as Module

If you don't want to install globally, you can run it as a Python module:

```bash
python -m src
```

## Usage

```bash
# Add a reasoning step to the current branch's log
context log "REASONING_STEP"

# Commit current progress
context commit [--message MESSAGE] [--from-log RANGE] [--git-commit]

# Create a new branch
context branch <name> [--from BRANCH] [--empty]

# Merge branches
context merge <branch1> [<branch2> ...] [--git-commit]

# Get information
context info [--level LEVEL] [--branch BRANCH] [--format FORMAT]
```

## Project Structure

```
.context/
├── main.md              # High-level project goals, milestones, TODO
├── .current_branch      # Current branch pointer
└── branches/
    └── <branch-name>/
        ├── commits.yaml # Structured commit history (YAML)
        ├── log.yaml     # Fine-grained reasoning cycles (YAML)
        └── metadata.yaml # Structured meta-level information (YAML)
```

## Examples

```bash
# Initialize and create your first branch
context branch main --empty

# Add reasoning steps as you work
context log "Analyzed requirements and decided to use a factory pattern"
context log "Identified potential race condition in authentication flow"

# Create a commit with a message (includes all logs by default)
context commit --message "Implemented core functionality"

# Or commit with specific log range
context commit --message "Auth work" --from-log 5  # Last 5 log entries

# Commit and also create a git commit (optional)
context commit --message "Feature done" --git-commit

# Create a new branch from main
context branch feature-auth --from main

# Add logs on the feature branch
context log "Started implementing OAuth integration"

# Merge a branch back
context merge feature-auth

# Merge and also create a git commit (optional)
context merge feature-auth --git-commit

# View project information
context info --level project

# View branch details
context info --level branch --branch feature-auth

# View session logs
context info --level session
```

## Testing

See [TESTS.md](TESTS.md) for comprehensive test cases covering all commands, edge cases, and integration scenarios.

## Development

This tool is under active development. See TODO.md for implementation progress.

