# Context Management System

A context management system for AI development tools like Cursor, Claude Code, and Gemini CLI that enables leveraging previous context from chat sessions while maintaining dynamic workflows.

## Features

- **LOG**: Record reasoning steps as the AI works through problems
- **COMMIT**: Checkpoint important points in chat sessions
- **BRANCH**: Create new branches with easy access to previous branch context
- **MERGE**: Merge context from multiple branches into the current branch
- **INFO**: Get project information at different levels (project goals, branch summaries, detailed chat sessions)

## Installation

```bash
pip install -r requirements.txt
```

## Integration Options

### Option 1: MCP Server (Recommended)

The MCP (Model Context Protocol) server allows AI tools to call context management functions directly.

#### For Cursor

1. Copy the MCP config to your Cursor settings:

```bash
# Create/edit ~/.cursor/mcp.json (global) or .cursor/mcp.json (project)
```

Add this configuration:

```json
{
  "mcpServers": {
    "context-management": {
      "command": "python3",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/context-engineering"
    }
  }
}
```

2. Restart Cursor. The AI will now have access to context management tools.

#### For Gemini CLI

1. Edit `.gemini/settings.json` in your project:

```json
{
  "mcpServers": {
    "context-management": {
      "command": "python3",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/context-engineering"
    }
  }
}
```

2. The Gemini CLI will now have access to context management tools.

#### For Claude Desktop

1. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "context-management": {
      "command": "python3",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/context-engineering"
    }
  }
}
```

### Option 2: CLI Commands

Use the CLI directly or have the AI invoke shell commands:

```bash
# Log reasoning steps
python3 -m src.cli log "Investigating the auth module..."

# Commit progress
python3 -m src.cli commit --from-log all

# Create/switch branches
python3 -m src.cli branch fix-login-bug --empty

# Get info
python3 -m src.cli info --level branch
```

## MCP Tools

When using the MCP server, the AI has access to these tools:

| Tool | Description |
|------|-------------|
| `context_log` | Log a reasoning step during AI thought process |
| `context_commit` | Checkpoint progress by creating a commit |
| `context_branch` | Create a new branch or switch to existing one |
| `context_merge` | Merge context from other branches |
| `context_info` | Get project/branch/session information |
| `context_status` | Get current context status |

## Workflow Example

```
┌─────────────────────────────────────────────────────────────┐
│  AI Chat Session                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Start task                                              │
│     └─> context_branch("fix-login-bug", empty=True)         │
│                                                             │
│  2. AI reasons and logs each step                           │
│     └─> context_log("Investigating the auth module...")     │
│     └─> context_log("Found bug in password hashing...")     │
│     └─> context_log("Implemented fix in auth/utils.py...")  │
│                                                             │
│  3. Checkpoint progress                                     │
│     └─> context_commit(from_log="all")                      │
│                                                             │
│  4. Continue work or switch tasks...                        │
│                                                             │
│  5. Return later - AI reads context                         │
│     └─> context_info(level="branch")                        │
│     └─> context_status()                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
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

## Development

This tool is under active development. See TODO.md for implementation progress.
