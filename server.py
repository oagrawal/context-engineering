"""
Context Engineering Tool MCP Server

A Python MCP server that implements Git-like context management for LLM agents
using a local ./context/ folder structure.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Context Engineering Tool")

# Base context directory
CONTEXT_DIR = Path("./context")
BRANCHES_DIR = CONTEXT_DIR / "branches"
MAIN_MD = CONTEXT_DIR / "main.md"


def ensure_context_structure() -> None:
    """Ensure the context directory structure exists."""
    CONTEXT_DIR.mkdir(exist_ok=True)
    BRANCHES_DIR.mkdir(exist_ok=True)
    if not MAIN_MD.exists():
        MAIN_MD.write_text("# Global Project Roadmap\n\nThis is the main context file for the project.\n")


def validate_branch_name(branch_name: str) -> bool:
    """Validate branch name to prevent issues with filesystem."""
    if not branch_name or len(branch_name) == 0:
        return False
    # Prevent problematic characters
    invalid_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    return not any(char in branch_name for char in invalid_chars)


def get_branch_dir(branch_name: str) -> Path:
    """Get the directory path for a branch."""
    return BRANCHES_DIR / branch_name


def get_commits_dir(branch_name: str) -> Path:
    """Get the commits directory for a branch."""
    return get_branch_dir(branch_name) / "commits"


def get_branch_metadata_path(branch_name: str) -> Path:
    """Get the metadata file path for a branch."""
    return get_branch_dir(branch_name) / "metadata.json"


async def read_branch_metadata(branch_name: str) -> dict[str, Any]:
    """Read branch metadata from file."""
    metadata_path = get_branch_metadata_path(branch_name)
    if metadata_path.exists():
        content = await asyncio.to_thread(metadata_path.read_text)
        return json.loads(content)
    return {
        "name": branch_name,
        "created_at": datetime.now().isoformat(),
        "parent": None,
        "commits": []
    }


async def write_branch_metadata(branch_name: str, metadata: dict[str, Any]) -> None:
    """Write branch metadata to file."""
    metadata_path = get_branch_metadata_path(branch_name)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(metadata_path.write_text, json.dumps(metadata, indent=2))


@mcp.tool()
async def context_commit(
    branch: str,
    message: str,
    content: str,
    metadata: Optional[str] = None
) -> dict[str, Any]:
    """
    Save current state as a timestamped commit in the specified branch.
    
    Args:
        branch: The branch name to commit to
        message: Commit message describing the changes
        content: The content to save in this commit
        metadata: Optional JSON string with additional metadata
    
    Returns:
        Dictionary with commit information including commit_id and path
    """
    if not validate_branch_name(branch):
        return {"error": "Invalid branch name"}
    
    ensure_context_structure()
    
    # Read or create branch metadata
    branch_metadata = await read_branch_metadata(branch)
    
    # Create commit
    commit_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    commits_dir = get_commits_dir(branch)
    commits_dir.mkdir(parents=True, exist_ok=True)
    
    commit_file = commits_dir / f"{commit_id}.md"
    
    # Prepare commit content
    commit_content = f"# Commit: {message}\n\n"
    commit_content += f"**Timestamp**: {datetime.now().isoformat()}\n"
    commit_content += f"**Branch**: {branch}\n\n"
    if metadata:
        commit_content += f"**Metadata**: {metadata}\n\n"
    commit_content += "---\n\n"
    commit_content += content
    
    await asyncio.to_thread(commit_file.write_text, commit_content)
    
    # Update branch metadata
    commit_info = {
        "id": commit_id,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "file": str(commit_file.relative_to(CONTEXT_DIR))
    }
    
    branch_metadata["commits"].append(commit_info)
    branch_metadata["last_commit"] = commit_info
    branch_metadata["updated_at"] = datetime.now().isoformat()
    
    await write_branch_metadata(branch, branch_metadata)
    
    return {
        "success": True,
        "commit_id": commit_id,
        "branch": branch,
        "message": message,
        "path": str(commit_file.relative_to(CONTEXT_DIR))
    }


@mcp.tool()
async def context_branch(
    name: str,
    parent: Optional[str] = None
) -> dict[str, Any]:
    """
    Create a new branch folder copying from parent, initialize branch-specific tracking file.
    
    Args:
        name: The name of the new branch
        parent: Optional parent branch name to copy from. If not provided, creates from main
    
    Returns:
        Dictionary with branch creation information
    """
    if not validate_branch_name(name):
        return {"error": "Invalid branch name"}
    
    ensure_context_structure()
    
    branch_dir = get_branch_dir(name)
    if branch_dir.exists():
        return {"error": f"Branch '{name}' already exists"}
    
    # Create branch directory structure
    branch_dir.mkdir(parents=True, exist_ok=True)
    commits_dir = get_commits_dir(name)
    commits_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize metadata
    branch_metadata = {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "parent": parent or "main",
        "commits": []
    }
    
    # If parent exists, copy commits
    if parent:
        parent_metadata = await read_branch_metadata(parent)
        if parent_metadata.get("commits"):
            branch_metadata["parent_commits"] = parent_metadata["commits"]
    
    await write_branch_metadata(name, branch_metadata)
    
    return {
        "success": True,
        "branch": name,
        "parent": parent or "main",
        "created_at": branch_metadata["created_at"]
    }


@mcp.tool()
async def context_merge(
    source_branch: str,
    target_branch: str,
    merge_message: Optional[str] = None
) -> dict[str, Any]:
    """
    Combine two branch histories, write synthesis to target branch.
    
    Args:
        source_branch: The branch to merge from
        target_branch: The branch to merge into
        merge_message: Optional message describing the merge
    
    Returns:
        Dictionary with merge information
    """
    if not validate_branch_name(source_branch) or not validate_branch_name(target_branch):
        return {"error": "Invalid branch name"}
    
    ensure_context_structure()
    
    # Read both branch metadata
    source_metadata = await read_branch_metadata(source_branch)
    target_metadata = await read_branch_metadata(target_branch)
    
    if not source_metadata.get("commits"):
        return {"error": f"Source branch '{source_branch}' has no commits"}
    
    # Read source commits
    source_commits_dir = get_commits_dir(source_branch)
    source_commits_content = []
    
    for commit_info in source_metadata.get("commits", []):
        commit_file = CONTEXT_DIR / commit_info["file"]
        if commit_file.exists():
            content = await asyncio.to_thread(commit_file.read_text)
            source_commits_content.append({
                "id": commit_info["id"],
                "message": commit_info["message"],
                "content": content
            })
    
    # Read target commits
    target_commits_dir = get_commits_dir(target_branch)
    target_commits_content = []
    
    for commit_info in target_metadata.get("commits", []):
        commit_file = CONTEXT_DIR / commit_info["file"]
        if commit_file.exists():
            content = await asyncio.to_thread(commit_file.read_text)
            target_commits_content.append({
                "id": commit_info["id"],
                "message": commit_info["message"],
                "content": content
            })
    
    # Create merge commit
    merge_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    commits_dir = get_commits_dir(target_branch)
    commits_dir.mkdir(parents=True, exist_ok=True)
    
    merge_file = commits_dir / f"{merge_id}.md"
    
    merge_content = f"# Merge: {source_branch} into {target_branch}\n\n"
    merge_content += f"**Timestamp**: {datetime.now().isoformat()}\n"
    merge_content += f"**Source Branch**: {source_branch}\n"
    merge_content += f"**Target Branch**: {target_branch}\n\n"
    
    if merge_message:
        merge_content += f"**Merge Message**: {merge_message}\n\n"
    
    merge_content += "---\n\n"
    merge_content += "## Source Branch Commits\n\n"
    for commit in source_commits_content:
        merge_content += f"### {commit['message']} ({commit['id']})\n\n"
        merge_content += commit['content'] + "\n\n---\n\n"
    
    merge_content += "## Target Branch Commits\n\n"
    for commit in target_commits_content:
        merge_content += f"### {commit['message']} ({commit['id']})\n\n"
        merge_content += commit['content'] + "\n\n---\n\n"
    
    merge_content += "## Synthesis\n\n"
    merge_content += "This merge combines the histories of both branches.\n"
    
    await asyncio.to_thread(merge_file.write_text, merge_content)
    
    # Update target branch metadata
    merge_commit_info = {
        "id": merge_id,
        "message": merge_message or f"Merge {source_branch} into {target_branch}",
        "timestamp": datetime.now().isoformat(),
        "file": str(merge_file.relative_to(CONTEXT_DIR)),
        "merge_from": source_branch
    }
    
    target_metadata["commits"].append(merge_commit_info)
    target_metadata["last_commit"] = merge_commit_info
    target_metadata["updated_at"] = datetime.now().isoformat()
    target_metadata["merged_from"] = source_branch
    
    await write_branch_metadata(target_branch, target_metadata)
    
    return {
        "success": True,
        "merge_id": merge_id,
        "source_branch": source_branch,
        "target_branch": target_branch,
        "merge_file": str(merge_file.relative_to(CONTEXT_DIR))
    }


@mcp.tool()
async def context_retrieve(
    branch: str,
    query: Optional[str] = None,
    limit: int = 10
) -> dict[str, Any]:
    """
    Read commit history and return relevant context based on query.
    
    Args:
        branch: The branch to retrieve context from
        query: Optional search query to filter commits
        limit: Maximum number of commits to return (default: 10)
    
    Returns:
        Dictionary with retrieved context information
    """
    if not validate_branch_name(branch):
        return {"error": "Invalid branch name"}
    
    ensure_context_structure()
    
    # Read branch metadata
    branch_metadata = await read_branch_metadata(branch)
    
    commits = branch_metadata.get("commits", [])
    
    # Filter commits if query provided
    if query:
        query_lower = query.lower()
        filtered_commits = [
            c for c in commits
            if query_lower in c.get("message", "").lower()
        ]
        commits = filtered_commits
    
    # Limit results
    commits = commits[-limit:] if limit > 0 else commits
    
    # Read commit contents
    commit_contents = []
    for commit_info in commits:
        commit_file = CONTEXT_DIR / commit_info["file"]
        if commit_file.exists():
            content = await asyncio.to_thread(commit_file.read_text)
            commit_contents.append({
                "id": commit_info["id"],
                "message": commit_info["message"],
                "timestamp": commit_info["timestamp"],
                "content": content
            })
    
    return {
        "success": True,
        "branch": branch,
        "query": query,
        "commits_found": len(commit_contents),
        "commits": commit_contents
    }


@mcp.resource("context://main.md")
async def get_main_context() -> str:
    """Get the main context file content."""
    ensure_context_structure()
    if MAIN_MD.exists():
        return await asyncio.to_thread(MAIN_MD.read_text)
    return "# Global Project Roadmap\n\nThis is the main context file for the project.\n"


@mcp.resource("context://branches/{name}")
async def get_branch_resource(name: str) -> str:
    """Get branch metadata and recent commits as a resource."""
    ensure_context_structure()
    
    if not validate_branch_name(name):
        return json.dumps({"error": "Invalid branch name"})
    
    branch_metadata = await read_branch_metadata(name)
    
    # Include recent commits content
    commits_summary = []
    for commit_info in branch_metadata.get("commits", [])[-5:]:  # Last 5 commits
        commit_file = CONTEXT_DIR / commit_info["file"]
        if commit_file.exists():
            content = await asyncio.to_thread(commit_file.read_text)
            commits_summary.append({
                "id": commit_info["id"],
                "message": commit_info["message"],
                "timestamp": commit_info["timestamp"],
                "content": content[:500]  # First 500 chars
            })
    
    result = {
        "branch": branch_metadata,
        "recent_commits": commits_summary
    }
    
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    ensure_context_structure()
    mcp.run()

