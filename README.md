# Context Management System

A context management system for AI development tools like Cursor, Claude Code, and Gemini CLI that enables leveraging previous context from chat sessions while maintaining dynamic workflows.

## 🚀 Quick Start (5 Minutes)

**Get up and running immediately:**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # Or install in development mode:
   pip install -e .
   ```

2. **Set up MCP integration** (choose your tool):
   - **Cursor**: Copy `mcp-config-cursor.json` to `~/.cursor/mcp.json` or `.cursor/mcp.json` in your project
   - **Gemini CLI**: Copy `mcp-config-gemini.json` to `.gemini/settings.json` in your project
   - **Claude Desktop**: Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

3. **Restart your AI tool** - The context management tools are now available!

4. **Start using it** - The AI will automatically:
   - Create context branches for different tasks
   - Log reasoning steps as it works
   - Create checkpoints when you make progress
   - Remember context across sessions

**That's it!** The system auto-detects your project workspace and creates a `.context/` directory automatically.

## ✨ What You Get

Once set up, your AI assistant can:

- **Remember across sessions**: Pick up exactly where you left off, even days later
- **Organize by task**: Automatically branch context for different features/bugs
- **Track progress**: See what's been done, what's pending, and what's next
- **Smart context switching**: Automatically detect which branch matches your current work
- **No manual work**: The AI handles all context management automatically

## Features

- **LOG**: Record reasoning steps as the AI works through problems
- **COMMIT**: Checkpoint important points in chat sessions
- **BRANCH**: Create new branches with easy access to previous branch context
- **MERGE**: Merge context from multiple branches into the current branch
- **INFO**: Get project information at different levels (project goals, branch summaries, detailed chat sessions)
- **TODO Management**: Track and manage TODO items across branches
- **Smart Branch Detection**: Automatically suggest the right branch for your work

## Installation

### Option 1: Development Install (Recommended)

```bash
# Clone or download this repository
cd context-engineering

# Install in development mode
pip install -e .
```

### Option 2: Direct Install

```bash
pip install -r requirements.txt
```

## Integration Options

### Option 1: MCP Server (Recommended)

The MCP (Model Context Protocol) server allows AI tools to call context management functions directly. This is the recommended approach as it enables seamless integration.

#### For Cursor

**Quick Setup:**

1. **Copy the config file:**
   ```bash
   # For project-specific setup (recommended):
   cp mcp-config-cursor.json .cursor/mcp.json
   
   # Or for global setup:
   mkdir -p ~/.cursor
   cp mcp-config-cursor.json ~/.cursor/mcp.json
   ```

2. **Edit the `cwd` path** in the config file to point to this repository:
   ```json
   {
     "mcpServers": {
       "context-management": {
         "command": "python3",
         "args": ["-m", "src.mcp_server"],
         "cwd": "/absolute/path/to/context-engineering"
       }
     }
   }
   ```
   > **Note**: Use `${workspaceFolder}` for project-specific configs (Cursor will auto-replace it)

3. **Restart Cursor** - The AI will now have access to context management tools!

**What happens next:**
- When you start a new chat, the AI can call `context_status()` to check your workspace
- The AI will automatically create a `.context/` directory in your project root
- All context management happens automatically - no manual intervention needed

#### For Gemini CLI

1. **Create the config directory:**
   ```bash
   mkdir -p .gemini
   cp mcp-config-gemini.json .gemini/settings.json
   ```

2. **Edit `.gemini/settings.json`** and update the `cwd` path:
   ```json
   {
     "mcpServers": {
       "context-management": {
         "command": "python3",
         "args": ["-m", "src.mcp_server"],
         "cwd": "/absolute/path/to/context-engineering"
       }
     }
   }
   ```

3. **Restart Gemini CLI** - Context management tools are now available!

#### For Claude Desktop

1. **Edit the config file:**
   ```bash
   # On macOS:
   open ~/Library/Application\ Support/Claude/claude_desktop_config.json
   
   # On Windows:
   # %APPDATA%\Claude\claude_desktop_config.json
   
   # On Linux:
   # ~/.config/Claude/claude_desktop_config.json
   ```

2. **Add or merge this configuration:**
   ```json
   {
     "mcpServers": {
       "context-management": {
         "command": "python3",
         "args": ["-m", "src.mcp_server"],
         "cwd": "/absolute/path/to/context-engineering"
       }
     }
   }
   ```

3. **Restart Claude Desktop** - You're all set!

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

## 🎯 First Steps After Setup

Once you've configured MCP and restarted your AI tool, here's what to expect:

### 1. Automatic Workspace Detection

When you start a new chat session, the AI will:
- Automatically detect your project workspace (via git root or existing `.context/` directory)
- Create a `.context/` directory structure if it doesn't exist
- Initialize the main context file with your project goals

### 2. Start Working Normally

Just work with your AI as usual! The system will:
- **Automatically branch** when you switch to different tasks
- **Log reasoning steps** as the AI thinks through problems
- **Create checkpoints** when significant progress is made
- **Track TODOs** across your work sessions

### 3. Example: Your First Session

```
You: "Help me add user authentication to my app"

AI: [Automatically calls context_detect_branch()]
    → Creates branch "add-user-auth"
    → Logs: "Starting authentication feature implementation"
    → Works on the task...

You: "Actually, let's fix the login bug first"

AI: [Automatically calls context_detect_branch()]
    → Switches to branch "fix-login-bug" (or creates it)
    → Has access to previous login-related context
    → Continues from where you left off
```

### 4. Returning Later

When you come back days or weeks later:
```
You: "What were we working on?"

AI: [Calls context_summary()]
    → Shows: Current branch, pending TODOs, recent progress
    → Picks up exactly where you left off
```

**No manual context management needed** - it all happens automatically!

## MCP Tools

When using the MCP server, the AI has access to these tools:

**`context_status()`** - Check workspace path and current branch. Used at session start.

**`context_set_workspace(workspace_path)`** - Set the project workspace directory. Used if auto-detection fails.

**`context_summary()`** - Get quick overview of TODOs and progress. Used at session start and when checking status.

**`context_detect_branch(context_hint)`** - Smart branching: find the right branch for current work. Used before starting new tasks.

**`context_todos(action, item, todo_id)`** - View, add, or complete TODO items. Used throughout the session.

**`context_log(reasoning_step)`** - Log a reasoning step during AI thought process. Used as the AI works through problems.

**`context_commit(message, from_log)`** - Checkpoint progress by creating a commit. Used when significant progress is made.

**`context_branch(name, purpose, from_branch, empty)`** - Create a new branch or switch to existing one. Used when switching tasks.

**`context_merge(branches)`** - Merge context from other branches. Used when combining work from multiple branches.

**`context_info(level, branch)`** - Get detailed project/branch/session information. Used when you need detailed context.

**Note**: The AI uses these tools automatically - you don't need to call them manually!

## Workflow Example

Here's a real-world example of how the system works across multiple sessions:

**Day 1: Starting a New Feature**

You ask: "Let's add user authentication"

The AI automatically:
- Detects this is a new task and calls `context_detect_branch("user authentication")`
- Creates a new branch called "add-user-auth"
- Logs: "Starting auth implementation..."
- Works on the feature, logging steps like "Created User model..." and "Implemented login endpoint..."
- Creates a checkpoint with `context_commit(from_log="all")`

**Day 2: Switching Tasks**

You say: "Actually, let's fix the login bug first"

The AI automatically:
- Detects the task switch and calls `context_detect_branch("login bug fix")`
- Switches to (or creates) the "fix-login-bug" branch
- Logs: "Investigating login issue..."
- Finds and fixes the bug
- Commits: "Fixed password validation"

**Day 5: Returning to Previous Work**

You ask: "What were we working on?"

The AI automatically:
- Calls `context_summary()` to load your context
- Shows you're on branch "add-user-auth"
- Shows pending TODO: "Add password reset"
- Shows last commit: "Implemented login endpoint"
- Picks up exactly where you left off

**Key Benefits:**
- No context loss between sessions
- Automatic task organization
- Seamless switching between features
- Progress tracking and TODO management

## Project Structure

The system creates a `.context/` directory in your project root:

```
your-project/
├── .context/                    # Context management directory
│   ├── main.md                  # Project goals, milestones, shared TODOs
│   ├── .current_branch          # Current branch pointer (hidden file)
│   └── branches/
│       └── <branch-name>/       # One directory per branch
│           ├── commits.yaml     # Checkpoint history (structured)
│           ├── log.yaml         # Detailed reasoning steps (append-only)
│           └── metadata.yaml    # Branch metadata (file structure, env, etc.)
├── src/                         # Your actual project code
└── ...
```

**Important**: The `.context/` directory should be committed to git so context is shared across machines and team members.

## Troubleshooting

### MCP Server Not Working

**Problem**: AI doesn't have access to context tools

**Solutions**:
1. **Check the config file path** - Make sure you edited the correct config file for your tool
2. **Verify the `cwd` path** - Use absolute paths, not relative ones
3. **Check Python path** - Ensure `python3` is in your PATH
4. **Restart your AI tool** - MCP configs are only loaded on startup
5. **Check for errors** - Look in your AI tool's logs/console for MCP errors

### Workspace Not Detected

**Problem**: `context_status()` shows wrong workspace or "not found"

**Solutions**:
1. **Set workspace manually**: The AI can call `context_set_workspace(workspace_path="/path/to/project")`
2. **Ensure git repository**: The system auto-detects via git root
3. **Create `.context/` manually**: If needed, create `.context/` in your project root

### Branch Detection Not Working

**Problem**: AI creates new branches instead of switching to existing ones

**Solutions**:
1. **Use descriptive hints**: When the AI calls `context_detect_branch()`, provide clear context
2. **Check branch names**: Existing branches are matched by name similarity
3. **Manual switch**: You can ask the AI to switch branches explicitly

### Context Not Persisting

**Problem**: Context is lost between sessions

**Solutions**:
1. **Check `.context/` exists**: The directory should be in your project root
2. **Verify git commit**: Make sure `.context/` is committed to git
3. **Check branch**: Ensure you're on the same branch as before

## Development

This tool is under active development. See `TODO.md` for implementation progress.

### Contributing

Contributions are welcome! The system is designed to be extensible and modular.

### Requirements

- Python 3.8+
- See `requirements.txt` for dependencies
