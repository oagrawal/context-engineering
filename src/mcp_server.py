#!/usr/bin/env python3
"""
MCP Server for Context Management System

This server exposes context management tools via the Model Context Protocol,
allowing AI assistants (Claude, Cursor, Gemini CLI) to manage development context.

Usage:
    python mcp_server.py [--workspace PATH]

Arguments:
    --workspace PATH    Set the workspace root directory for context storage.
                        If not provided, uses the current working directory.
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Optional

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import filesystem, commands
from src.models import get_current_timestamp
import subprocess


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="MCP Server for Context Management System"
    )
    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default=None,
        help="Workspace root directory for context storage (default: current working directory)"
    )
    return parser.parse_args()


def auto_detect_workspace() -> Optional[str]:
    """
    Auto-detect workspace by:
    1. Looking for .context folder walking up from CWD
    2. Finding git root
    Returns the detected workspace path or None
    """
    cwd = os.getcwd()
    
    # Strategy 1: Walk up looking for existing .context folder
    current = cwd
    while True:
        context_path = os.path.join(current, ".context")
        if os.path.isdir(context_path):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # Reached root
            break
        current = parent
    
    # Strategy 2: Try git root
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, Exception):
        pass
    
    return None


class MCPServer:
    """Simple MCP Server implementation using stdio JSON-RPC"""
    
    def __init__(self):
        self.tools = {
            "context_log": {
                "description": """Log a reasoning step to preserve your thinking for future sessions.

### Parameters
- `reasoning_step` (required): Your observation, decision, or finding

### What to Include
Be specific - include file names, line numbers, decisions made, and rationale:
- "Found: auth.py:45 - token refresh missing error handling"
- "Decision: Using Redis for session storage - faster than DB"
- "Edited: user.py:120-135 - added input validation"
- "Error: ImportError in test_auth.py - missing mock dependency"

### Output
Returns confirmation with current branch name.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reasoning_step": {
                            "type": "string",
                            "description": "The reasoning step to log. Be specific: include file names, line numbers, decisions, rationale."
                        }
                    },
                    "required": ["reasoning_step"]
                }
            },
            "context_commit": {
                "description": """Create a checkpoint to save progress. Consolidates recent logs into a commit.

### Parameters
- `message` (optional): Explicit commit message
- `from_log` (optional): Auto-generate from logs - use "all" for all logs since last commit, or "last:N" for last N entries

### Usage Patterns
- Auto-summarize: `context_commit(from_log="all")` - recommended for most cases
- Manual message: `context_commit(message="WIP: Auth 70% done, next: password reset")`
- Combined: `context_commit(message="...", from_log="all")` - adds your message plus log summary

### Output
Returns confirmation with branch name and commit ID.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message. Describe: what was done, current state, what's next."
                        },
                        "from_log": {
                            "type": "string",
                            "description": "Auto-generate from logs. Use 'all' for all since last commit, 'last:N' for last N entries."
                        }
                    },
                    "required": []
                }
            },
            "context_branch": {
                "description": """Create or switch to a context branch. Organizes work into separate contexts.

### Parameters  
- `name` (required): Branch name in kebab-case (e.g., "fix-auth-bug")
- `purpose` (recommended): Why this branch exists - helps future recall
- `from_branch` (optional): Copy context from this branch (default: current)
- `empty` (optional): Start with no context (for unrelated tasks)

### Behavior
- If branch exists: switches to it
- If branch doesn't exist: creates it and switches

### Examples
```
context_branch(name="fix-login-bug", purpose="Fix OAuth token refresh")
context_branch(name="explore-redis", empty=True, purpose="Evaluate Redis vs Memcached")
context_branch(name="feature-v2", from_branch="main", purpose="Build on main's progress")
```

### Output  
Returns confirmation: created new or switched to existing.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Branch name in kebab-case (e.g., 'fix-login-bug', 'add-user-auth')"
                        },
                        "from_branch": {
                            "type": "string",
                            "description": "Source branch to copy context from (defaults to current branch)"
                        },
                        "empty": {
                            "type": "boolean",
                            "description": "Create empty branch with no prior context"
                        },
                        "purpose": {
                            "type": "string",
                            "description": "Clear description of branch purpose (recommended)"
                        }
                    },
                    "required": ["name"]
                }
            },
            "context_merge": {
                "description": """Merge context from other branches into current branch.

### Parameters
- `branches` (required): List of branch names to merge from

### How It Works
- Copies commits and logs from source branches into current branch
- Deduplicates entries (won't create duplicates if already merged)
- Preserves source branch attribution in merged entries

### Example
After completing feature work, merge back to main:
```
context_branch(name="main")
context_merge(branches=["add-auth", "fix-session"])
```

### Output
Returns confirmation with count of merged branches.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "branches": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of branch names to merge from"
                        }
                    },
                    "required": ["branches"]
                }
            },
            "context_info": {
                "description": """Retrieve detailed context information at different levels.

### Parameters
- `level` (optional): Detail level - "project", "branch" (default), or "session"
- `branch` (optional): Specific branch to inspect (defaults to current)

### Levels Explained
- `project`: High-level overview - all branches, goals, overall status
- `branch`: Current branch's commits and progress (DEFAULT - use most often)
- `session`: Detailed log entries from current session

### Output (Markdown formatted)
- Project level: branch list, purposes, commit counts
- Branch level: commits with messages, timestamps, progress summary
- Session level: individual log entries with timestamps

### Typical Use
Call with `level="branch"` at session start to recall what was done.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["project", "branch", "session"],
                            "description": "Detail level: project (overview), branch (commits), session (logs)"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch to inspect (optional, defaults to current)"
                        }
                    },
                    "required": []
                }
            },
            "context_status": {
                "description": """Quick status check - workspace, branch, and counts.

### Parameters
None required.

### Output
Returns plain text with:
- Workspace path
- Context folder location  
- Current branch name
- Available branches
- Commit and log counts
- Branch purpose (if set)
- Latest activity timestamp

### Use Case
First call in any session to orient yourself quickly.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "context_set_workspace": {
                "description": """Set workspace directory for context storage. Creates .context folder.

### Parameters
- `workspace_path` (required): Absolute path to project directory

### When Needed
Usually not needed - workspace auto-detects from:
1. Existing .context folder (walks up from cwd)
2. Git repository root

Only call if:
- `context_status()` shows wrong workspace
- Working on a new project with no .context yet
- Auto-detection picked wrong directory

### Output
Returns confirmation with workspace and .context folder paths.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_path": {
                            "type": "string",
                            "description": "Absolute path to project directory where .context should be created"
                        }
                    },
                    "required": ["workspace_path"]
                }
            },
            "context_todos": {
                "description": """Manage TODO list - view, add, or complete items. TODOs are your roadmap!

### Parameters
- `action` (optional): "list" (default), "add", or "complete"
- `item` (optional): TODO text when action="add"
- `todo_id` (optional): TODO number (1-indexed) when action="complete"

### Usage Patterns
- View TODOs: `context_todos()` or `context_todos(action="list")`
- Add TODO: `context_todos(action="add", item="Implement user authentication")`
- Complete: `context_todos(action="complete", todo_id=1)`

### Best Practices
1. **AT SESSION START**: Check TODOs first to see pending work
2. Create specific, actionable TODOs (not vague like "fix bug")
3. Work on ONE TODO at a time
4. Mark complete when done - this auto-creates a checkpoint commit

### Good TODO Examples
- "Find __getattr__ method in sky_coordinate.py causing AttributeError"
- "Create minimal reproduction script for the session timeout bug"
- "Update validators to use regex anchors \\A and \\Z"

### Output
Returns formatted TODO list or confirmation message.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "add", "complete"],
                            "description": "Action to perform: list (view), add (new TODO), complete (mark done)"
                        },
                        "item": {
                            "type": "string",
                            "description": "TODO text (required for action='add')"
                        },
                        "todo_id": {
                            "type": "integer",
                            "description": "TODO number to complete, 1-indexed (required for action='complete')"
                        }
                    },
                    "required": []
                }
            },
            "context_summary": {
                "description": """Get a quick summary of current progress - TODOs, milestones, and recent activity.

### Parameters
None required.

### What It Returns
- **Task**: The branch purpose / what you're working on
- **TODOs**: Pending and completed items (most important!)
- **Milestones**: Recent commits / checkpoints achieved
- **Recent Activity**: Key findings and actions from logs

### When to Use
- **AT SESSION START**: After context_status, call this to recall progress
- **WHEN LOST**: If context was truncated, this recovers your state
- **BEFORE DECIDING**: To recall what's been tried and what's pending

### Why This Matters
This is your PRIMARY RECOVERY tool. When you feel lost or the conversation
seems incomplete, context_summary tells you exactly where you left off.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "context_detect_branch": {
                "description": """Detect which branch best matches the current work context. Use this for SMART BRANCHING.

### Parameters
- `context_hint` (required): Description of what you're working on, OR file paths being worked on

### What It Does
- Analyzes your context hint (files mentioned, keywords, topics)
- Compares against all existing branches (their tracked files, keywords, purpose)
- Returns the best matching branch with a similarity score

### When to Use (CRITICAL!)
- **BEFORE starting work on something new**: Check if an existing branch matches
- **WHEN user asks about unrelated topic**: Detect if you should switch branches
- **WHEN returning to previous work**: Find the right branch to continue

### Example
User says "let's work on the authentication system" but you're on branch "fix-ui-bug".
Call: `context_detect_branch(context_hint="authentication system login user session")`
Result might say: Switch to branch 'add-auth' (score: 25.0)

### Output
Returns recommendation: stay on current branch, switch to existing branch, or create new one.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "context_hint": {
                            "type": "string",
                            "description": "Description of current work: file paths, topics, or what the user wants to do"
                        }
                    },
                    "required": ["context_hint"]
                }
            }
        }
    
    def handle_initialize(self, params: dict) -> dict:
        """Handle initialize request"""
        # Try to get workspace root from client info
        # Cursor sends this in various ways - check all possibilities
        root_uri = params.get("rootUri")
        root_path = params.get("rootPath")
        
        # Check for workspace folders (newer protocol)
        workspace_folders = params.get("workspaceFolders", [])
        if workspace_folders and len(workspace_folders) > 0:
            first_folder = workspace_folders[0]
            if isinstance(first_folder, dict):
                root_uri = first_folder.get("uri") or root_uri
        
        # Check capabilities.roots (some clients use this)
        capabilities = params.get("capabilities", {})
        roots = capabilities.get("roots", {})
        if isinstance(roots, dict) and roots.get("listChanged"):
            # Client supports roots, but we need to get them separately
            pass
        
        # Convert file:// URI to path
        workspace_path = None
        if root_uri and root_uri.startswith("file://"):
            workspace_path = root_uri[7:]  # Remove 'file://'
            # Handle URL encoding (spaces as %20, etc.)
            import urllib.parse
            workspace_path = urllib.parse.unquote(workspace_path)
        elif root_path:
            workspace_path = root_path
        
        # Set workspace if we got one
        if workspace_path and os.path.isdir(workspace_path):
            filesystem.set_workspace_root(workspace_path)
        
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "prompts": {},
                "resources": {}
            },
            "serverInfo": {
                "name": "context-management",
                "version": "0.1.0"
            }
        }
    
    def handle_list_prompts(self, params: dict) -> dict:
        """Handle prompts/list request - expose context management guidelines"""
        return {
            "prompts": [
                {
                    "name": "context-management-protocol",
                    "description": "IMPORTANT: Read this at session start. Guidelines for using context management tools to maintain continuity across chat sessions.",
                    "arguments": []
                }
            ]
        }
    
    def handle_get_prompt(self, params: dict) -> dict:
        """Handle prompts/get request"""
        prompt_name = params.get("name", "")
        
        if prompt_name == "context-management-protocol":
            return {
                "description": "Context Management Protocol - Guidelines for AI assistants",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": """# Arbor Context Management - TODO-Driven Workflow with Smart Branching

You have access to `context_*` MCP tools. **Use them automatically without being prompted.**

## 🚨 SESSION START (MANDATORY)

1. `context_status()` - Check workspace is correct (not home dir!)
2. If workspace wrong: `context_set_workspace(workspace_path="/path/to/project")`
3. `context_summary()` - See TODOs and progress

## 🌿 SMART BRANCHING (CRITICAL!)

**BEFORE working on anything new, check if you're on the right branch:**

```
context_detect_branch(context_hint="<describe the task, include file names>")
```

Call this when:
- User asks about something different from current work
- You're about to create/edit new, unrelated files
- Returning to previous work

**DO NOT pile unrelated work into one branch!**

## 📋 TODO-DRIVEN WORKFLOW

1. `context_todos()` - Check pending TODOs
2. `context_todos(action="add", item="...")` - Add specific TODOs
3. Work ONE TODO at a time
4. `context_log(reasoning_step="...")` - Log discoveries
5. `context_todos(action="complete", todo_id=N)` - Mark done (auto-commits!)

## QUICK REFERENCE

| When | Action |
|------|--------|
| Session starts | `context_status()` → `context_summary()` |
| Wrong workspace | `context_set_workspace(workspace_path="...")` |
| New/different task | `context_detect_branch(context_hint="...")` |
| Need to plan | `context_todos(action="add", item="...")` |
| Made discovery | `context_log(reasoning_step="Found: ...")` |
| TODO done | `context_todos(action="complete", todo_id=N)` |
| Create branch | `context_branch(name="...", purpose="...")` |

**Use these tools AUTOMATICALLY throughout every session.**"""
                        }
                    }
                ]
            }
        
        return {"error": f"Unknown prompt: {prompt_name}"}
    
    def handle_list_resources(self, params: dict) -> dict:
        """Handle resources/list request"""
        return {
            "resources": [
                {
                    "uri": "context://guidelines",
                    "name": "Context Management Guidelines",
                    "description": "Read this FIRST at session start - instructions for using context tools",
                    "mimeType": "text/markdown"
                },
                {
                    "uri": "context://status",
                    "name": "Current Context Status",
                    "description": "Current workspace, branch, and recent activity",
                    "mimeType": "text/plain"
                }
            ]
        }
    
    def handle_read_resource(self, params: dict) -> dict:
        """Handle resources/read request"""
        uri = params.get("uri", "")
        
        if uri == "context://guidelines":
            return {
                "contents": [
                    {
                        "uri": "context://guidelines",
                        "mimeType": "text/markdown",
                        "text": """# Arbor Context Management Guidelines

## Session Start (MANDATORY)
1. `context_status()` - Check workspace correct
2. `context_summary()` - See TODOs and progress

## Smart Branching (CRITICAL!)
BEFORE new work: `context_detect_branch(context_hint="...")`
- Checks if current branch matches your task
- Suggests switching or creating new branch
- DO NOT pile unrelated work into one branch!

## TODO-Driven Workflow
1. `context_todos()` - Check pending
2. `context_todos(action="add", item="...")` - Add specific TODOs
3. Work ONE TODO at a time
4. `context_log(reasoning_step="...")` - Log discoveries
5. `context_todos(action="complete", todo_id=N)` - Mark done (auto-commits!)

## When to Branch
`context_detect_branch(context_hint="...")` first, then:
`context_branch(name="...", purpose="...")` if needed

**Use these tools AUTOMATICALLY.**"""
                    }
                ]
            }
        
        elif uri == "context://status":
            # Return actual current status
            try:
                filesystem.ensure_context_directory()
                current_branch = filesystem.get_current_branch()
                branches = filesystem.list_branches()
                
                status_lines = [
                    f"Workspace: {filesystem.get_workspace_root()}",
                    f"Current branch: {current_branch or 'None'}",
                    f"Available branches: {', '.join(branches) if branches else 'None'}"
                ]
                
                if current_branch:
                    commits = filesystem.read_commits(current_branch)
                    logs = filesystem.read_logs(current_branch)
                    status_lines.append(f"Commits: {len(commits)}")
                    status_lines.append(f"Log entries: {len(logs)}")
                
                return {
                    "contents": [
                        {
                            "uri": "context://status",
                            "mimeType": "text/plain",
                            "text": "\n".join(status_lines)
                        }
                    ]
                }
            except Exception as e:
                return {
                    "contents": [
                        {
                            "uri": "context://status",
                            "mimeType": "text/plain",
                            "text": f"Error getting status: {str(e)}"
                        }
                    ]
                }
    
    def handle_list_tools(self, params: dict) -> dict:
        """Handle tools/list request"""
        tools = []
        for name, spec in self.tools.items():
            tools.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"]
            })
        return {"tools": tools}
    
    def handle_call_tool(self, params: dict) -> dict:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            result = self._execute_tool(tool_name, arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    def _ensure_workspace_set(self) -> Optional[str]:
        """
        Ensure workspace is properly set. Returns error message if not set and can't auto-detect.
        Returns None if workspace is ready.
        """
        current_workspace = filesystem.get_workspace_root()
        context_dir = filesystem.get_context_dir()
        
        # Check if workspace looks like a home directory (likely wrong)
        home_dir = os.path.expanduser("~")
        is_home_dir = os.path.normpath(current_workspace) == os.path.normpath(home_dir)
        
        # If .context already exists and it's not in home dir, we're good
        if os.path.isdir(context_dir) and not is_home_dir:
            return None
        
        # Try auto-detection
        detected, method = auto_detect_workspace()
        
        # If detection found something other than cwd or home dir, use it
        if detected and method in ['existing_context', 'git_root']:
            detected_normalized = os.path.normpath(detected)
            if detected_normalized != os.path.normpath(home_dir):
                filesystem.set_workspace_root(detected)
                context_dir = filesystem.get_context_dir()
                if os.path.isdir(context_dir):
                    return None
                # .context doesn't exist but we found a good workspace, that's OK
                return None
        
        # Workspace is home directory or couldn't detect properly - require explicit set
        if is_home_dir or (detected and os.path.normpath(detected) == os.path.normpath(home_dir)):
            return (
                f"⚠️ Workspace detected as home directory ({home_dir}) - this is incorrect.\n\n"
                f"**REQUIRED**: Call context_set_workspace with your project's path FIRST:\n"
                f"  context_set_workspace(workspace_path=\"/path/to/your/project\")\n\n"
                f"This ensures .context is created in your project, not your home folder.\n"
                f"Look at the file paths in this conversation to determine the correct project path."
            )
        
        # Have a workspace, but no .context yet - that's OK, will be created
        return None
    
    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool and return the result"""
        
        # context_set_workspace doesn't need workspace check
        if tool_name != "context_set_workspace":
            workspace_error = self._ensure_workspace_set()
            if workspace_error:
                return workspace_error
        
        if tool_name == "context_log":
            reasoning_step = arguments.get("reasoning_step", "")
            if not reasoning_step:
                return "Error: reasoning_step is required"
            
            commands.log_command(reasoning_step=reasoning_step)
            branch = filesystem.get_current_branch() or "unknown"
            return f"✓ Logged to branch '{branch}'"
        
        elif tool_name == "context_commit":
            message = arguments.get("message")
            from_log = arguments.get("from_log")
            
            commands.commit_command(message=message, from_log_range=from_log)
            branch = filesystem.get_current_branch() or "unknown"
            return f"✓ Committed to branch '{branch}'"
        
        elif tool_name == "context_branch":
            name = arguments.get("name", "")
            if not name:
                return "Error: branch name is required"
            
            from_branch = arguments.get("from_branch")
            empty = arguments.get("empty", False)
            purpose = arguments.get("purpose")
            
            # Check if branch exists - switch to it
            if filesystem.branch_exists(name):
                filesystem.set_current_branch(name)
                return f"✓ Switched to existing branch '{name}'"
            else:
                commands.branch_command(branch_name=name, from_branch=from_branch, empty=empty, purpose=purpose)
                purpose_msg = f" (Purpose: {purpose})" if purpose else ""
                return f"✓ Created and switched to branch '{name}'{purpose_msg}"
        
        elif tool_name == "context_merge":
            branches = arguments.get("branches", [])
            if not branches:
                return "Error: at least one branch name is required"
            
            commands.merge_command(source_branches=branches)
            current = filesystem.get_current_branch() or "unknown"
            return f"✓ Merged {len(branches)} branch(es) into '{current}'"
        
        elif tool_name == "context_info":
            level = arguments.get("level", "branch")
            branch_name = arguments.get("branch")
            
            # Capture output
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                commands.info_command(level=level, branch_name=branch_name, format="markdown")
            
            return f.getvalue()
        
        elif tool_name == "context_status":
            filesystem.ensure_context_directory()
            current_branch = filesystem.get_current_branch()
            branches = filesystem.list_branches()
            
            status = []
            status.append(f"Workspace: {filesystem.get_workspace_root()}")
            status.append(f"Context folder: {filesystem.get_context_dir()}")
            status.append(f"Current branch: {current_branch or 'None'}")
            status.append(f"Available branches: {', '.join(branches) if branches else 'None'}")
            
            if current_branch:
                commits = filesystem.read_commits(current_branch)
                logs = filesystem.read_logs(current_branch)
                status.append(f"Commits in current branch: {len(commits)}")
                status.append(f"Log entries in current branch: {len(logs)}")
                
                if commits:
                    status.append(f"Branch purpose: {commits[0].branch_purpose}")
                    status.append(f"Latest commit: {commits[-1].timestamp}")
            
            return "\n".join(status)
        
        elif tool_name == "context_set_workspace":
            workspace_path = arguments.get("workspace_path", "")
            if not workspace_path:
                return "Error: workspace_path is required"
            
            # Validate the path exists
            if not os.path.isdir(workspace_path):
                return f"Error: Directory does not exist: {workspace_path}"
            
            # Set the workspace root
            abs_path = os.path.abspath(workspace_path)
            filesystem.set_workspace_root(abs_path)
            
            # Initialize the context directory
            filesystem.ensure_context_directory()
            
            context_dir = filesystem.get_context_dir()
            return f"✓ Workspace set to: {abs_path}\n✓ Context folder: {context_dir}"
        
        elif tool_name == "context_todos":
            action = arguments.get("action", "list")
            item = arguments.get("item")
            todo_id = arguments.get("todo_id")
            
            return commands.todos_command(action=action, item=item, todo_id=todo_id)
        
        elif tool_name == "context_summary":
            return commands.summary_command()
        
        elif tool_name == "context_detect_branch":
            context_hint = arguments.get("context_hint", "")
            if not context_hint:
                return "Error: context_hint is required"
            
            result = commands.detect_matching_branch(context_hint)
            
            # Format the result nicely
            lines = []
            lines.append(f"## Branch Detection Results")
            lines.append(f"**Current branch:** {result['current_branch'] or 'None'}")
            lines.append(f"**Extracted files:** {', '.join(result['extracted_files']) if result['extracted_files'] else 'None'}")
            lines.append(f"**Extracted keywords:** {', '.join(result['extracted_keywords'][:5]) if result['extracted_keywords'] else 'None'}")
            lines.append("")
            lines.append(f"### Recommendation")
            lines.append(result['suggestion'])
            lines.append("")
            
            if result['all_branches']:
                lines.append("### Branch Scores")
                for branch, score in result['all_branches'][:5]:
                    marker = " ← current" if branch == result['current_branch'] else ""
                    marker += " ★ recommended" if branch == result['recommended_branch'] else ""
                    lines.append(f"  - {branch}: {score:.1f}{marker}")
            
            return "\n".join(lines)
        
        else:
            return f"Error: Unknown tool '{tool_name}'"
    
    async def run(self):
        """Run the MCP server using stdio"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())
        
        while True:
            try:
                line = await reader.readline()
                if not line:
                    break
                
                request = json.loads(line.decode())
                response = self.handle_request(request)
                
                # Only send response if it's not None (notifications don't get responses)
                if response is not None:
                    response_line = json.dumps(response) + "\n"
                    writer.write(response_line.encode())
                    await writer.drain()
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                # Only send error response if we have a request id
                # Otherwise it's a notification and we shouldn't respond
                pass
    
    def handle_request(self, request: dict) -> Optional[dict]:
        """Handle a JSON-RPC request. Returns None for notifications (no id)."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Check if this is a notification (no id field means notification)
        is_notification = "id" not in request
        
        result = None
        error = None
        
        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "initialized":
                # This is always a notification, no response needed
                return None
            elif method == "notifications/initialized":
                # Alternative notification format
                return None
            elif method == "tools/list":
                result = self.handle_list_tools(params)
            elif method == "tools/call":
                result = self.handle_call_tool(params)
            elif method == "prompts/list":
                result = self.handle_list_prompts(params)
            elif method == "prompts/get":
                result = self.handle_get_prompt(params)
            elif method == "resources/list":
                result = self.handle_list_resources(params)
            elif method == "resources/read":
                result = self.handle_read_resource(params)
            elif method == "ping":
                result = {}
            elif method.startswith("notifications/"):
                # All notifications - no response
                return None
            else:
                error = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
        except Exception as e:
            error = {
                "code": -32603,
                "message": str(e)
            }
        
        # Don't respond to notifications
        if is_notification:
            return None
        
        response = {"jsonrpc": "2.0", "id": request_id}
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        return response


def main():
    """Entry point for MCP server"""
    args = parse_args()
    
    # Set workspace root if provided, otherwise use current working directory
    if args.workspace:
        workspace_path = os.path.abspath(args.workspace)
    else:
        workspace_path = os.getcwd()
    
    filesystem.set_workspace_root(workspace_path)
    
    server = MCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
