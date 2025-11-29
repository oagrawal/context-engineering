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


class MCPServer:
    """Simple MCP Server implementation using stdio JSON-RPC"""
    
    def __init__(self):
        self.tools = {
            "context_log": {
                "description": "Log a reasoning step during AI thought process. Call this frequently as you work through problems to record your thinking.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reasoning_step": {
                            "type": "string",
                            "description": "The reasoning or thinking step to log (e.g., 'Investigating auth module...', 'Found bug in line 45...')"
                        }
                    },
                    "required": ["reasoning_step"]
                }
            },
            "context_commit": {
                "description": "Checkpoint progress by creating a commit. Call this at major milestones to save your progress.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message describing what was accomplished (optional if using from_log)"
                        },
                        "from_log": {
                            "type": "string",
                            "description": "Extract commit content from logs. Use 'all' for all logs, or 'last:N' for last N entries"
                        }
                    },
                    "required": []
                }
            },
            "context_branch": {
                "description": "Create a new context branch or switch to an existing one. Use at the start of a new task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Branch name (e.g., 'fix-login-bug', 'add-user-auth')"
                        },
                        "from_branch": {
                            "type": "string",
                            "description": "Source branch to copy from (optional, defaults to current branch)"
                        },
                        "empty": {
                            "type": "boolean",
                            "description": "Create empty branch with no prior context (default: false)"
                        }
                    },
                    "required": ["name"]
                }
            },
            "context_merge": {
                "description": "Merge context from other branches into current branch.",
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
                "description": "Get project/branch/session information. Use this to understand current context and previous progress.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["project", "branch", "session"],
                            "description": "Information level: 'project' for high-level goals, 'branch' for branch progress, 'session' for detailed logs"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name (optional, defaults to current branch)"
                        }
                    },
                    "required": []
                }
            },
            "context_status": {
                "description": "Get current context status (current branch, recent activity).",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "context_set_workspace": {
                "description": "Set the workspace directory for context storage. Call this at the start of each project session to ensure context is stored in the correct project folder. This creates a .context folder in the specified workspace.",
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
                "tools": {}
            },
            "serverInfo": {
                "name": "context-management",
                "version": "0.1.0"
            }
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
    
    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool and return the result"""
        
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
            
            # Check if branch exists - switch to it
            if filesystem.branch_exists(name):
                filesystem.set_current_branch(name)
                return f"✓ Switched to existing branch '{name}'"
            else:
                commands.branch_command(branch_name=name, from_branch=from_branch, empty=empty)
                return f"✓ Created and switched to branch '{name}'"
        
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

