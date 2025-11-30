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
                "description": """Log a reasoning step during AI thought process. Call this frequently as you work through problems to record your thinking.

### WHEN TO CALL (Required Behaviors)
- **AFTER** making any significant discovery or decision
- **AFTER** completing a file edit or code change
- **WHEN** encountering an error or unexpected behavior
- **WHEN** changing approach or strategy
- **EVERY 2-3 minutes** during active problem-solving (minimum)

### Examples
- "Investigating auth module - found session token not being refreshed"
- "Bug identified: race condition in user.save() on line 45"
- "Decision: Using Redis for session storage instead of memory"
- "Completed: Added input validation to API endpoints"

### Why This Matters
Logs create a recoverable trail of reasoning. If the session ends unexpectedly or you return later, these logs let you (or another AI) understand exactly what was being done and why.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reasoning_step": {
                            "type": "string",
                            "description": "The reasoning or thinking step to log. Be specific: include file names, line numbers, decisions made, and rationale."
                        }
                    },
                    "required": ["reasoning_step"]
                }
            },
            "context_commit": {
                "description": """Checkpoint progress by creating a commit. Call this at major milestones to save your progress.

### WHEN TO CALL (Required Behaviors)
- **AFTER** completing a feature, fix, or logical unit of work
- **BEFORE** switching to a different task or taking a break
- **AFTER** every 5-10 log entries (consolidate progress)
- **WHEN** the user indicates they're done for now
- **BEFORE** context_branch if switching tasks

### Best Practice
Use `from_log="all"` to automatically summarize your logged work. Only use explicit `message` when you need to override or add context beyond what's in the logs.

### Examples
- After fixing a bug: commit(from_log="all") 
- Before break: commit(message="WIP: Authentication 70% complete, next: add password reset")
- Feature done: commit(from_log="all")""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message describing what was accomplished. Include: what was done, current state, and what's next."
                        },
                        "from_log": {
                            "type": "string",
                            "description": "Extract commit content from logs. Use 'all' for all logs since last commit, or 'last:N' for last N entries."
                        }
                    },
                    "required": []
                }
            },
            "context_branch": {
                "description": """Create a new context branch or switch to an existing one. Use at the start of a new task.

### WHEN TO CALL (Required Behaviors)
- **AT SESSION START**: Check context_status first, then switch to or create appropriate branch
- **WHEN** starting a new feature, bug fix, or distinct task
- **WHEN** user asks to work on something different
- **WHEN** you want to explore an alternative approach without losing current progress

### Branch Naming Convention
Use descriptive, kebab-case names: `fix-login-bug`, `add-user-auth`, `refactor-database`, `explore-redis-caching`

### Purpose Parameter (Important!)
Always provide a `purpose` - this helps future sessions understand what the branch is for.

### Examples
- New feature: branch(name="add-payment-processing", purpose="Implement Stripe payment integration")
- Bug fix: branch(name="fix-session-timeout", purpose="Fix session expiring prematurely on mobile")
- Exploration: branch(name="explore-graphql", empty=True, purpose="Evaluate GraphQL vs REST for new API")""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Branch name in kebab-case (e.g., 'fix-login-bug', 'add-user-auth')"
                        },
                        "from_branch": {
                            "type": "string",
                            "description": "Source branch to copy context from (defaults to current branch). Use to build on existing progress."
                        },
                        "empty": {
                            "type": "boolean",
                            "description": "Create empty branch with no prior context. Use for completely new tasks unrelated to current work."
                        },
                        "purpose": {
                            "type": "string",
                            "description": "RECOMMENDED: Clear description of the branch purpose (e.g., 'Implement user authentication with OAuth2')"
                        }
                    },
                    "required": ["name"]
                }
            },
            "context_merge": {
                "description": """Merge context from other branches into current branch. Use when combining work from parallel efforts.

### WHEN TO CALL
- **WHEN** completing a feature branch and merging back to main
- **WHEN** you need learnings from another branch
- **WHEN** consolidating work from multiple exploration branches

### Example
After completing a feature in branch 'add-auth', merge it into 'main':
1. branch(name="main") 
2. merge(branches=["add-auth"])""",
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
                "description": """Get project/branch/session information. Use this to understand current context and previous progress.

### WHEN TO CALL (Required Behaviors)
- **AT SESSION START**: ALWAYS call this first to understand what was done previously
- **WHEN** returning to work after a break
- **WHEN** you need to recall previous decisions or progress
- **BEFORE** making changes that might conflict with previous work

### Levels
- `project`: High-level goals, all branches, overall status
- `branch`: Current branch's commits and progress summary (DEFAULT - use this most often)
- `session`: Detailed logs from current session (use when you need specifics)

### Session Start Pattern
1. context_status() - see current state
2. context_info(level="branch") - understand recent progress
3. Then proceed with work""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["project", "branch", "session"],
                            "description": "project=goals/all branches, branch=current progress (default), session=detailed logs"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name to inspect (optional, defaults to current branch)"
                        }
                    },
                    "required": []
                }
            },
            "context_status": {
                "description": """Get current context status (current branch, recent activity).

### WHEN TO CALL (Required Behaviors)
- **AT EVERY SESSION START**: This is your first call to orient yourself
- **WHEN** you're unsure what branch you're on
- **WHEN** you need a quick overview without full details

### What It Returns
- Current workspace path
- Current branch name
- Available branches
- Commit/log counts
- Latest activity timestamp

### Session Start Pattern
This should be your FIRST context call in any new session.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "context_set_workspace": {
                "description": """Set the workspace directory for context storage. Call this at the start of each project session to ensure context is stored in the correct project folder. This creates a .context folder in the specified workspace.

### WHEN TO CALL
- **IF** context_status() indicates wrong workspace or no .context folder
- **WHEN** working on a new project for the first time
- **WHEN** the workspace path shown doesn't match your current project

### Note
In most cases, the workspace is auto-detected from git root or existing .context folder. Only call this if auto-detection fails or shows the wrong path.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_path": {
                            "type": "string",
                            "description": "Absolute path to the project/workspace directory where .context folder should be created"
                        }
                    },
                    "required": ["workspace_path"]
                }
            }
        }
    
    def handle_initialize(self, params: dict) -> dict:
        """Handle initialize request"""
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
                            "text": """# Context Management Protocol

You have access to context-management tools that maintain continuity across chat sessions. Follow these guidelines:

## 🚨 SESSION START (MANDATORY)
At the START of every conversation, BEFORE responding to the user:
1. `context_status()` - Orient yourself (workspace, branch, state)
2. `context_info(level="branch")` - Recall previous progress
3. Create/switch branch if needed for current task

## 🔄 DURING WORK
Log continuously with `context_log()`:
- After every discovery, decision, or finding
- After every file edit or code change
- When encountering errors
- Every 2-3 minutes minimum

Example: `context_log("Investigating user.py - found auth token issue on line 45")`

## 💾 CHECKPOINTS
Call `context_commit(from_log="all")`:
- After completing any feature/fix/unit of work
- Before switching tasks
- Every 5-10 log entries
- When user indicates they're done

## 🌿 BRANCHING
Create branches for different tasks:
`context_branch(name="fix-auth-bug", purpose="Fix OAuth token refresh")`

Always provide a `purpose` parameter.

## QUICK REFERENCE
| When | Action |
|------|--------|
| Session starts | `context_status()` → `context_info()` |
| New task | `context_branch(name="...", purpose="...")` |
| Made discovery | `context_log("Found: ...")` |
| Made decision | `context_log("Decision: ...")` |
| Completed work | `context_log("Completed: ...")` |
| Unit done | `context_commit(from_log="all")` |
| User leaving | `context_commit(message="WIP: current state")` |

Use these tools AUTOMATICALLY without being prompted."""
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
                        "text": """# Context Management Guidelines

## Session Start Protocol
1. `context_status()` - Check current state
2. `context_info(level="branch")` - Recall previous work
3. Create/switch branch if needed

## During Work
- `context_log("...")` - Log every discovery, decision, edit
- Call every 2-3 minutes minimum

## Save Progress  
- `context_commit(from_log="all")` - After completing work units
- Commit before switching tasks or ending session

## Branching
- `context_branch(name="task-name", purpose="description")`
- Always include purpose parameter

Use these tools AUTOMATICALLY throughout the session."""
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
        context_dir = filesystem.get_context_dir()
        
        # If .context already exists, we're good
        if os.path.isdir(context_dir):
            return None
        
        # Try auto-detection
        detected = auto_detect_workspace()
        if detected:
            filesystem.set_workspace_root(detected)
            # Check again if .context exists in detected workspace
            context_dir = filesystem.get_context_dir()
            if os.path.isdir(context_dir):
                return None
            # .context doesn't exist but we found a good workspace, that's OK
            return None
        
        # Can't auto-detect - return helpful message
        current_workspace = filesystem.get_workspace_root()
        return (
            f"⚠️ No .context folder found and couldn't auto-detect workspace.\n"
            f"Current workspace: {current_workspace}\n\n"
            f"Please call context_set_workspace with your project's absolute path first:\n"
            f"  context_set_workspace(workspace_path=\"/path/to/your/project\")\n\n"
            f"This will create a .context folder to store your development context."
        )
    
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

