# Context Management System

A context management system for AI development tools like Cursor and Claude Code that enables leveraging previous context from chat sessions while maintaining dynamic workflows.

## Features

- **COMMIT**: Checkpoint important points in chat sessions and increment branch pointer
- **BRANCH**: Create new branches with easy access to previous branch context
- **MERGE**: Merge context from multiple branches into the current branch
- **INFO**: Get project information at different levels (project goals, branch summaries, detailed chat sessions)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Commit current progress
context commit [--message MESSAGE] [--from-log RANGE]

# Create a new branch
context branch <name> [--from BRANCH] [--empty]

# Merge branches
context merge <branch1> [<branch2> ...]

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
        ├── commit.md    # Structured commit history
        ├── log.md       # Fine-grained reasoning cycles
        └── metadata.yaml # Structured meta-level information
```

## Development

This tool is under active development. See TODO.md for implementation progress.

