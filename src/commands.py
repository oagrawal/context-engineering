"""Command implementations for context management"""

import subprocess
import os
from typing import Optional, List, Set
from datetime import datetime
from . import filesystem
from .models import (
    CommitEntry, LogEntry, MetadataYAML,
    generate_commit_id, get_current_timestamp,
    validate_branch_name, compare_commits, find_divergence_point
)


def _scan_file_structure(root_path: str, max_depth: int = 3) -> dict:
    """
    Scan directory structure and return a simplified file tree.
    
    Args:
        root_path: Root directory to scan
        max_depth: Maximum depth to scan (default 3)
    
    Returns:
        Dictionary with file structure
    """
    structure = {}
    root_path = os.path.abspath(root_path)
    
    # Directories to skip
    skip_dirs = {'.git', '.context', 'node_modules', '__pycache__', '.venv', 'venv', 
                 '.env', 'dist', 'build', '.next', '.cache', 'coverage'}
    
    def scan_dir(path: str, depth: int) -> dict:
        if depth > max_depth:
            return {}
        
        result = {}
        try:
            for entry in os.scandir(path):
                if entry.name.startswith('.') and entry.name not in ['.gitignore']:
                    continue
                if entry.is_dir() and entry.name in skip_dirs:
                    continue
                
                rel_path = os.path.relpath(entry.path, root_path)
                
                if entry.is_file():
                    result[rel_path] = 'file'
                elif entry.is_dir():
                    sub_result = scan_dir(entry.path, depth + 1)
                    if sub_result:
                        result[rel_path] = sub_result
                    else:
                        result[rel_path] = 'dir'
        except PermissionError:
            pass
        
        return result
    
    return scan_dir(root_path, 0)


def log_command(reasoning_step: str) -> None:
    """
    LOG command: Append a reasoning step to the current branch's log
    
    This is called by the AI during its reasoning process to record
    what it's thinking/doing. These logs are later used by COMMIT
    to create structured summaries.
    
    Args:
        reasoning_step: The reasoning/thinking step to log
    """
    # Ensure context directory exists
    filesystem.ensure_context_directory()
    
    # Get current branch
    current_branch = filesystem.get_current_branch()
    if not current_branch:
        raise ValueError("No current branch set. Use 'branch' command to create/switch branches.")
    
    # Create log entry
    log_entry = LogEntry(
        timestamp=get_current_timestamp(),
        reasoning_step=reasoning_step,
        source_branch=None  # This is the original branch, not from a merge
    )
    
    # Append to log
    filesystem.append_log(current_branch, log_entry)
    
    print(f"✓ Logged to branch '{current_branch}'")


def commit_command(message: Optional[str] = None, from_log_range: Optional[str] = None, 
                   update_metadata: bool = True) -> None:
    """
    COMMIT command: Checkpoint important points in chat session
    
    Args:
        message: Optional commit message/contribution description
        from_log_range: Optional log range to extract from (e.g., "last:5" or "all")
        update_metadata: Whether to auto-update file structure in metadata (default True)
    """
    # Ensure context directory exists
    filesystem.ensure_context_directory()
    
    # Get current branch
    current_branch = filesystem.get_current_branch()
    if not current_branch:
        raise ValueError("No current branch set. Use 'branch' command to create/switch branches.")
    
    # Read existing commits
    commits = filesystem.read_commits(current_branch)
    
    # Get branch purpose from first commit or use default
    branch_purpose = "Development branch"
    if commits:
        branch_purpose = commits[0].branch_purpose
    
    # Get parent commit ID (for chain reference instead of bloated previous_progress)
    parent_commit = commits[-1].commit_id if commits else None
    
    # Generate commit contribution
    commit_contribution = message or "Progress checkpoint"
    
    # If from_log_range is specified, extract from logs
    if from_log_range:
        logs = filesystem.read_logs(current_branch)
        if logs:
            # Parse range (simple implementation: "last:N" or "all")
            if from_log_range.startswith("last:"):
                try:
                    n = int(from_log_range.split(":")[1])
                    relevant_logs = logs[-n:] if n > 0 else logs
                except ValueError:
                    relevant_logs = logs
            elif from_log_range == "all":
                relevant_logs = logs
            else:
                relevant_logs = logs
            
            # Extract reasoning steps from logs
            log_summaries = [log.reasoning_step for log in relevant_logs]
            if log_summaries:
                commit_contribution = "\n\n".join(log_summaries)
    
    # Create new commit entry with parent reference (no bloated previous_progress)
    new_commit = CommitEntry(
        commit_id=generate_commit_id(),
        branch_purpose=branch_purpose,
        commit_contribution=commit_contribution,
        timestamp=get_current_timestamp(),
        parent_commit=parent_commit
    )
    
    # Append commit
    filesystem.append_commit(current_branch, new_commit)
    
    # Update metadata with file structure
    if update_metadata:
        try:
            workspace_root = filesystem.get_workspace_root()
            file_structure = _scan_file_structure(workspace_root, max_depth=2)
            metadata = filesystem.read_metadata(current_branch)
            metadata.file_structure = file_structure
            filesystem.write_metadata(current_branch, metadata)
        except Exception:
            pass  # Non-critical, continue even if metadata update fails
    
    # Update main.md with recent progress
    update_main_md_with_progress(current_branch, new_commit)
    
    # Create git commit
    git_commit_context(current_branch, new_commit.commit_id)
    
    print(f"✓ Committed to branch '{current_branch}' (commit: {new_commit.commit_id})")


def branch_command(branch_name: str, from_branch: Optional[str] = None, empty: bool = False,
                   purpose: Optional[str] = None) -> None:
    """
    BRANCH command: Create a new branch
    
    Args:
        branch_name: Name of the new branch
        from_branch: Optional source branch to copy from (defaults to current branch)
        empty: If True, create empty branch (empty commits.yaml and log.yaml)
        purpose: Optional description of the branch purpose
    """
    # Ensure context directory exists
    filesystem.ensure_context_directory()
    
    # Validate branch name
    if not validate_branch_name(branch_name):
        raise ValueError(f"Invalid branch name: {branch_name}")
    
    # Check if branch already exists
    if filesystem.branch_exists(branch_name):
        raise ValueError(f"Branch '{branch_name}' already exists")
    
    # Determine source branch
    if from_branch is None:
        from_branch = filesystem.get_current_branch()
        if from_branch is None:
            # No current branch, create empty branch
            empty = True
    
    # Create branch directory and files
    if empty:
        filesystem.initialize_branch_files(branch_name, empty=True)
        print(f"✓ Created empty branch '{branch_name}'")
    else:
        # Copy from source branch
        if not filesystem.branch_exists(from_branch):
            raise ValueError(f"Source branch '{from_branch}' does not exist")
        
        filesystem.copy_branch_files(from_branch, branch_name)
        print(f"✓ Created branch '{branch_name}' from '{from_branch}'")
    
    # Switch to new branch
    filesystem.set_current_branch(branch_name)
    
    # If purpose is provided, create initial commit with that purpose
    if purpose:
        initial_commit = CommitEntry(
            commit_id=generate_commit_id(),
            branch_purpose=purpose,
            commit_contribution=f"Created branch '{branch_name}': {purpose}",
            timestamp=get_current_timestamp(),
            parent_commit=None
        )
        filesystem.append_commit(branch_name, initial_commit)
        print(f"✓ Set branch purpose: {purpose}")
    
    print(f"✓ Switched to branch '{branch_name}'")


def merge_command(source_branches: List[str]) -> None:
    """
    MERGE command: Merge context from multiple branches into current branch
    
    Only merges unique commits and logs (deduplication based on commit_id and timestamp+reasoning_step).
    
    Args:
        source_branches: List of branch names to merge from
    """
    # Ensure context directory exists
    filesystem.ensure_context_directory()
    
    # Get current branch
    current_branch = filesystem.get_current_branch()
    if not current_branch:
        raise ValueError("No current branch set. Use 'branch' command to create/switch branches.")
    
    # Read current branch commits
    current_commits = filesystem.read_commits(current_branch)
    current_logs = filesystem.read_logs(current_branch)
    current_metadata = filesystem.read_metadata(current_branch)
    
    # Build sets for deduplication
    existing_commit_ids: Set[str] = {c.commit_id for c in current_commits}
    existing_log_keys: Set[tuple] = {(log.timestamp, log.reasoning_step) for log in current_logs}
    
    # Process each source branch
    merged_commits = []
    merged_logs = []
    merged_branch_names = []
    
    for source_branch in source_branches:
        if not filesystem.branch_exists(source_branch):
            raise ValueError(f"Source branch '{source_branch}' does not exist")
        
        if source_branch == current_branch:
            print(f"⚠ Skipping '{source_branch}' (same as current branch)")
            continue
        
        # Read source branch data
        source_commits = filesystem.read_commits(source_branch)
        source_logs = filesystem.read_logs(source_branch)
        source_metadata = filesystem.read_metadata(source_branch)
        
        # Only merge commits that don't already exist (by commit_id)
        for commit in source_commits:
            if commit.commit_id not in existing_commit_ids:
                merged_commits.append(commit)
                existing_commit_ids.add(commit.commit_id)
        
        # Only merge logs that don't already exist (by timestamp + reasoning_step)
        for log in source_logs:
            log_key = (log.timestamp, log.reasoning_step)
            if log_key not in existing_log_keys:
                # Set source_branch if not already set
                if not log.source_branch:
                    log.source_branch = source_branch
                merged_logs.append(log)
                existing_log_keys.add(log_key)
        
        # Merge metadata (simple merge - combine file structures and env configs)
        if source_metadata.file_structure:
            current_metadata.file_structure.update(source_metadata.file_structure)
        if source_metadata.env_config:
            current_metadata.env_config.update(source_metadata.env_config)
        
        merged_branch_names.append(source_branch)
    
    # Append merged commits to current branch
    if merged_commits:
        current_commits.extend(merged_commits)
        filesystem.write_commits(current_branch, current_commits)
    
    # Append merged logs to current branch
    if merged_logs:
        current_logs.extend(merged_logs)
        filesystem.write_logs(current_branch, current_logs)
    
    # Write updated metadata
    filesystem.write_metadata(current_branch, current_metadata)
    
    # Create merge commit entry (using parent_commit reference)
    parent_commit_id = current_commits[-1].commit_id if current_commits else None
    merge_commit = CommitEntry(
        commit_id=generate_commit_id(),
        branch_purpose=current_commits[0].branch_purpose if current_commits else "Merged branch",
        commit_contribution=f"Merged branches: {', '.join(merged_branch_names)}",
        timestamp=get_current_timestamp(),
        parent_commit=parent_commit_id
    )
    filesystem.append_commit(current_branch, merge_commit)
    
    # Update main.md with merge summary
    update_main_md_with_merge(merged_branch_names, current_branch)
    
    # Create git commit
    git_commit_context(current_branch, merge_commit.commit_id)
    
    print(f"✓ Merged {len(merged_branch_names)} branch(es) into '{current_branch}'")


def update_main_md_with_merge(merged_branches: List[str], target_branch: str) -> None:
    """Update main.md with merge summary"""
    main_content = filesystem.read_main_md()
    
    # Add merge summary section if it doesn't exist
    if "## Merge History" not in main_content:
        main_content += "\n\n## Merge History\n\n"
    
    merge_entry = f"- **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**: Merged {', '.join(merged_branches)} into {target_branch}\n"
    main_content += merge_entry
    
    filesystem.write_main_md(main_content)


def update_main_md_with_progress(branch_name: str, commit: CommitEntry) -> None:
    """Update main.md with commit progress in the TODO/milestones section"""
    main_content = filesystem.read_main_md()
    
    # Find the TODO List section and add the milestone there
    todo_marker = "## TODO List"
    milestones_marker = "## Key Milestones"
    
    # Create a milestone entry
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    # Truncate long contributions for the milestone
    contribution_summary = commit.commit_contribution[:100]
    if len(commit.commit_contribution) > 100:
        contribution_summary += "..."
    
    milestone_entry = f"- [{timestamp}] **{branch_name}**: {contribution_summary}\n"
    
    # Try to insert after Key Milestones section
    if milestones_marker in main_content:
        # Find the position after the marker line
        marker_pos = main_content.find(milestones_marker)
        # Find the end of the marker line
        newline_pos = main_content.find('\n', marker_pos)
        if newline_pos != -1:
            # Skip any HTML comment lines
            insert_pos = newline_pos + 1
            remaining = main_content[insert_pos:]
            # Skip empty lines and comment lines
            lines = remaining.split('\n')
            skip_count = 0
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('<!--') or stripped == '' or stripped.endswith('-->'):
                    skip_count += len(line) + 1  # +1 for newline
                else:
                    break
            insert_pos += skip_count
            
            main_content = main_content[:insert_pos] + milestone_entry + main_content[insert_pos:]
    else:
        # If no milestones section, add one
        if todo_marker in main_content:
            marker_pos = main_content.find(todo_marker)
            main_content = main_content[:marker_pos] + f"{milestones_marker}\n\n{milestone_entry}\n" + main_content[marker_pos:]
        else:
            # Append at the end
            main_content += f"\n\n{milestones_marker}\n\n{milestone_entry}"
    
    filesystem.write_main_md(main_content)


def info_command(level: str = "project", branch_name: Optional[str] = None, format: str = "markdown") -> None:
    """
    INFO command: Get project information at different levels
    
    Args:
        level: Information level - "project", "branch", or "session"
        branch_name: Optional branch name (defaults to current branch for branch/session levels)
        format: Output format - "markdown" or "yaml"
    """
    filesystem.ensure_context_directory()
    
    if level == "project":
        show_project_info(format)
    elif level == "branch":
        if branch_name is None:
            branch_name = filesystem.get_current_branch()
            if branch_name is None:
                raise ValueError("No branch specified and no current branch set")
        show_branch_info(branch_name, format)
    elif level == "session":
        if branch_name is None:
            branch_name = filesystem.get_current_branch()
            if branch_name is None:
                raise ValueError("No branch specified and no current branch set")
        show_session_info(branch_name, format)
    else:
        raise ValueError(f"Invalid level: {level}. Must be 'project', 'branch', or 'session'")


def show_project_info(format: str) -> None:
    """Show project-level information"""
    main_content = filesystem.read_main_md()
    branches = filesystem.list_branches()
    current_branch = filesystem.get_current_branch()
    
    if format == "markdown":
        print("=" * 60)
        print("PROJECT INFORMATION")
        print("=" * 60)
        print("\n" + main_content)
        print("\n" + "=" * 60)
        print("BRANCHES")
        print("=" * 60)
        for branch in branches:
            marker = " (current)" if branch == current_branch else ""
            print(f"  - {branch}{marker}")
    else:
        import yaml
        data = {
            'main_content': main_content,
            'branches': branches,
            'current_branch': current_branch
        }
        print(yaml.dump(data, default_flow_style=False))


def show_branch_info(branch_name: str, format: str) -> None:
    """Show branch-level information"""
    if not filesystem.branch_exists(branch_name):
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    commits = filesystem.read_commits(branch_name)
    metadata = filesystem.read_metadata(branch_name)
    
    if format == "markdown":
        print("=" * 60)
        print(f"BRANCH: {branch_name}")
        print("=" * 60)
        print(f"\nCommits: {len(commits)}")
        if commits:
            print(f"\nBranch Purpose: {commits[0].branch_purpose}")
            print(f"\nLatest Commit: {commits[-1].commit_id}")
            print(f"  Timestamp: {commits[-1].timestamp}")
            print(f"  Contribution: {commits[-1].commit_contribution[:100]}...")
        
        print(f"\nMetadata:")
        print(f"  File Structure: {len(metadata.file_structure)} entries")
        print(f"  Environment Config: {len(metadata.env_config)} entries")
    else:
        import yaml
        data = {
            'branch_name': branch_name,
            'commit_count': len(commits),
            'branch_purpose': commits[0].branch_purpose if commits else None,
            'latest_commit': commits[-1].to_dict() if commits else None,
            'metadata': metadata.to_dict()
        }
        print(yaml.dump(data, default_flow_style=False))


def show_session_info(branch_name: str, format: str) -> None:
    """Show session-level (log) information"""
    if not filesystem.branch_exists(branch_name):
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    logs = filesystem.read_logs(branch_name)
    
    if format == "markdown":
        print("=" * 60)
        print(f"SESSION LOGS: {branch_name}")
        print("=" * 60)
        print(f"\nTotal log entries: {len(logs)}")
        print("\n" + "-" * 60)
        
        # Show recent logs (last 10)
        recent_logs = logs[-10:] if len(logs) > 10 else logs
        for log in recent_logs:
            source_tag = f" [from {log.source_branch}]" if log.source_branch else ""
            print(f"\n{log.timestamp}{source_tag}")
            print(log.reasoning_step[:200] + "..." if len(log.reasoning_step) > 200 else log.reasoning_step)
            print("-" * 60)
    else:
        import yaml
        data = {
            'branch_name': branch_name,
            'total_logs': len(logs),
            'recent_logs': [log.to_dict() for log in logs[-10:]]
        }
        print(yaml.dump(data, default_flow_style=False))


def git_commit_context(branch_name: str, commit_id: str) -> None:
    """Create a git commit to checkpoint the context state"""
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode != 0:
            # Not a git repository, skip git commit
            return
        
        # Stage .context directory
        subprocess.run(
            ['git', 'add', '.context/'],
            check=False,  # Don't fail if nothing to add
            cwd=os.getcwd()
        )
        
        # Create commit
        commit_message = f"Context checkpoint: {branch_name} - {commit_id}"
        subprocess.run(
            ['git', 'commit', '-m', commit_message],
            check=False,  # Don't fail if nothing to commit
            cwd=os.getcwd(),
            capture_output=True
        )
    except FileNotFoundError:
        # Git not installed, skip
        pass
    except Exception:
        # Any other error, skip git commit (non-critical)
        pass

