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


def log_command(reasoning_step: str, log_type: str | None = None) -> None:
    """
    LOG command: Append a reasoning step to the current branch's log
    
    This is called by the AI during its reasoning process to record
    what it's thinking/doing. These logs are later used by COMMIT
    to create structured summaries.
    
    Args:
        reasoning_step: The reasoning/thinking step to log
        log_type: Optional type prefix (ACTION, RESULT, USER, THINKING, etc.)
    """
    # Ensure context directory exists
    filesystem.ensure_context_directory()
    
    # Get current branch
    current_branch = filesystem.get_current_branch()
    if not current_branch:
        raise ValueError("No current branch set. Use 'branch' command to create/switch branches.")
    
    # Format the log entry with type prefix if provided
    formatted_step = reasoning_step
    if log_type and not reasoning_step.startswith(f"{log_type}:"):
        formatted_step = f"{log_type}: {reasoning_step}"
    
    # Truncate very long entries to keep logs manageable
    # LLM should provide concise summaries, but cap at 800 chars as safety
    max_log_length = 800
    if len(formatted_step) > max_log_length:
        formatted_step = formatted_step[:max_log_length] + " [truncated]"
    
    # Create log entry
    log_entry = LogEntry(
        timestamp=get_current_timestamp(),
        reasoning_step=formatted_step,
        source_branch=None  # This is the original branch, not from a merge
    )
    
    # Append to log
    filesystem.append_log(current_branch, log_entry)
    
    # Auto-track files and keywords mentioned in the log
    files = _extract_files_from_text(reasoning_step)
    keywords = _extract_keywords_from_text(reasoning_step)
    if files or keywords:
        update_branch_tracking(files=files[:5], keywords=keywords[:5])
    
    # Also update main.md interaction log (but keep it brief)
    _update_interaction_log(formatted_step)
    
    print(f"✓ Logged to branch '{current_branch}'")


def _update_interaction_log(entry: str, max_entries: int = 20) -> None:
    """Update the interaction log section in main.md with recent activity."""
    try:
        main_content = filesystem.read_main_md()
        
        marker = "## Interaction Log"
        if marker not in main_content:
            return
        
        # Find the interaction log section
        marker_pos = main_content.find(marker)
        section_start = marker_pos + len(marker)
        
        # Find the next section or end
        next_section = main_content.find("\n## ", section_start)
        if next_section == -1:
            next_section = len(main_content)
        
        # Get current entries (skip comment lines)
        current_section = main_content[section_start:next_section].strip()
        lines = [l for l in current_section.split('\n') if l.strip() and not l.strip().startswith('<!--')]
        
        # Add new entry at the top (most recent first)
        timestamp = datetime.now().strftime('%H:%M:%S')
        new_entry = f"- `{timestamp}` {entry[:150]}{'...' if len(entry) > 150 else ''}"
        
        # Keep only last N entries
        lines = [new_entry] + lines[:max_entries - 1]
        
        # Rebuild section
        new_section = f"\n\n" + "\n".join(lines) + "\n"
        
        # Replace section in main.md
        new_content = main_content[:section_start] + new_section + main_content[next_section:]
        filesystem.write_main_md(new_content)
    except Exception:
        pass  # Non-critical, don't fail on logging errors


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
        workspace_root = filesystem.get_workspace_root()
        file_structure = _scan_file_structure(workspace_root, max_depth=2)
        metadata = filesystem.read_metadata(current_branch)
        metadata.file_structure = file_structure
        filesystem.write_metadata(current_branch, metadata)
    
    # Update main.md with recent progress
    update_main_md_with_progress(current_branch, new_commit)
    
    # Create git commit (turned off for now)
    # git_commit_context(current_branch, new_commit.commit_id)
    
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
    
    # Create git commit (turned off for now)
    # git_commit_context(current_branch, merge_commit.commit_id)
    
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


def summary_command() -> str:
    """
    SUMMARY command: Get a quick, AI-friendly summary of current progress.
    
    This is the primary command for the agent to recall where it is.
    Returns a concise summary with:
    - Current TODOs (most important!)
    - Key milestones achieved
    - Recent activity summary
    
    Returns:
        Formatted summary string
    """
    filesystem.ensure_context_directory()
    
    current_branch = filesystem.get_current_branch()
    if not current_branch:
        return "No active branch. Use context_branch to start tracking progress."
    
    commits = filesystem.read_commits(current_branch)
    logs = filesystem.read_logs(current_branch)
    
    lines = []
    lines.append(f"# Context Recovery - {current_branch}")
    lines.append("")
    
    # Branch purpose / task (first line) - show full, no truncation
    if commits:
        lines.append(f"**Task:** {commits[0].branch_purpose}")
        lines.append("")
    
    # TODOs - MOST IMPORTANT for recovery
    try:
        main_content = filesystem.read_main_md()
        todo_marker = "## TODO List"
        if todo_marker in main_content:
            todo_start = main_content.find(todo_marker)
            next_section = main_content.find("\n## ", todo_start + len(todo_marker))
            if next_section == -1:
                todo_section = main_content[todo_start:]
            else:
                todo_section = main_content[todo_start:next_section]
            
            # Parse TODOs
            pending = []
            completed = []
            for line in todo_section.split('\n'):
                line = line.strip()
                if line.startswith('- [ ]'):
                    pending.append(line[6:].strip())
                elif line.startswith('- [x]'):
                    completed.append(line[6:].strip())
            
            lines.append("## TODOs")
            if pending:
                lines.append(f"**Pending ({len(pending)}):**")
                for i, todo in enumerate(pending, 1):
                    lines.append(f"  {i}. {todo}")
            else:
                lines.append("**No pending TODOs.** Add some with `context_todos --add \"task\"`")
            
            if completed:
                lines.append(f"\n**Completed ({len(completed)}):**")
                # Show all completed TODOs for full context (or last 15 if many)
                todos_to_show = completed[-15:] if len(completed) > 15 else completed
                for todo in todos_to_show:
                    lines.append(f"  ✓ {todo}")
            lines.append("")
    except Exception:
        lines.append("## TODOs")
        lines.append("Could not read TODOs. Use `context_todos` to view them.")
        lines.append("")
    
    # Key milestones (commits) - show last 10 with full text, no truncation
    if commits and len(commits) > 1:  # Skip if only initial commit
        lines.append("## Milestones Achieved")
        # Show last 10 commits (or all if less) for better recovery context
        commits_to_show = commits[-10:] if len(commits) > 10 else commits[1:]  # Skip initial commit
        for c in commits_to_show:
            # Show first line of commit message fully - no truncation
            summary = c.commit_contribution.split('\n')[0]
            lines.append(f"  • {summary}")
        lines.append("")
    
    # Recent activity from logs - categorized
    if logs:
        lines.append(f"## Recent Activity ({len(logs)} entries)")
        
        # Show last 25 log entries for much better recovery context
        recent_logs = logs[-25:] if len(logs) > 25 else logs
        actions = []
        results = []
        findings = []
        
        for log in recent_logs:
            entry = log.reasoning_step
            if entry.startswith("ACTION:"):
                # Show full action - no truncation
                actions.append(entry[7:].strip())
            elif entry.startswith("RESULT:"):
                # Show full result - no truncation
                results.append(entry[7:].strip())
            elif any(kw in entry.lower() for kw in ['found', 'discovered', 'located', 'bug', 'error', 'fix', 'updated', 'changed', 'completed', 'verified']):
                # Show full finding - no truncation
                findings.append(entry)
        
        if findings:
            lines.append("**Key Findings:**")
            # Show last 10 findings for better context
            for f in findings[-10:]:
                lines.append(f"  • {f}")
        
        if actions:
            lines.append("**Recent Actions:**")
            # Show last 10 actions for better context
            for a in actions[-10:]:
                lines.append(f"  • {a}")
        
        lines.append("")
        lines.append("_Use `context_info --level session` for full log history._")
    else:
        lines.append("## Recent Activity")
        lines.append("No activity logged yet.")
    
    return "\n".join(lines)


def info_command(level: str = "project", branch_name: Optional[str] = None, format: str = "markdown", brief: bool = False) -> str:
    """
    INFO command: Get detailed information at different levels.
    
    For quick progress recall, use `context_summary` instead.
    
    Args:
        level: Information level - "project", "branch", or "session"
        branch_name: Optional branch name (defaults to current branch for branch/session levels)
        format: Output format - "markdown" or "yaml"
        brief: If True, return concise output (useful for limited context scenarios)
    
    Returns:
        Formatted info string
    """
    filesystem.ensure_context_directory()
    
    current_branch = filesystem.get_current_branch()
    branches = filesystem.list_branches()
    target = branch_name or current_branch or "none"
    
    output_lines = []
    output_lines.append(f"✓ Context INFO level='{level}' target='{target}' (current={current_branch}, {len(branches)} branches available)")
    
    if level == "project":
        output_lines.append(format_project_info(format, brief=brief))
    elif level == "branch":
        if branch_name is None:
            branch_name = current_branch
            if branch_name is None:
                raise ValueError("No branch specified and no current branch set")
        output_lines.append(format_branch_info(branch_name, format, brief=brief))
    elif level == "session":
        if branch_name is None:
            branch_name = current_branch
            if branch_name is None:
                raise ValueError("No branch specified and no current branch set")
        output_lines.append(format_session_info(branch_name, format, brief=brief))
    else:
        raise ValueError(f"Invalid level: {level}. Must be 'project', 'branch', or 'session'")
    
    return "\n".join(output_lines)


def format_project_info(format: str, brief: bool = False) -> str:
    """Format project-level information"""
    main_content = filesystem.read_main_md()
    branches = filesystem.list_branches()
    current_branch = filesystem.get_current_branch()
    
    lines = []
    
    if brief:
        lines.append(f"Branch: {current_branch} | All branches: {', '.join(branches)}")
        if "## TODO" in main_content:
            todo_start = main_content.find("## TODO")
            todo_section = main_content[todo_start:todo_start+500]
            lines.append(todo_section.split("\n## ")[0][:300])
        return "\n".join(lines)
    
    if format == "markdown":
        lines.append("=" * 60)
        lines.append("PROJECT INFORMATION")
        lines.append("=" * 60)
        lines.append("")
        lines.append(main_content)
        lines.append("")
        lines.append("=" * 60)
        lines.append("BRANCHES")
        lines.append("=" * 60)
        for branch in branches:
            marker = " (current)" if branch == current_branch else ""
            lines.append(f"  - {branch}{marker}")
    else:
        import yaml
        data = {
            'main_content': main_content,
            'branches': branches,
            'current_branch': current_branch
        }
        return yaml.dump(data, default_flow_style=False)
    
    return "\n".join(lines)


def format_branch_info(branch_name: str, format: str, brief: bool = False) -> str:
    """Format branch-level information with full commit history"""
    if not filesystem.branch_exists(branch_name):
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    commits = filesystem.read_commits(branch_name)
    logs = filesystem.read_logs(branch_name)
    metadata = filesystem.read_metadata(branch_name)
    
    lines = []
    
    if brief:
        lines.append(f"[{branch_name}] {len(commits)} commits, {len(logs)} logs")
        if commits:
            lines.append(f"Purpose: {commits[0].branch_purpose[:80]}")
            for c in commits[-3:]:
                summary = c.commit_contribution.replace('\n', ' ')[:60]
                lines.append(f"  • {summary}...")
        return "\n".join(lines)
    
    if format == "markdown":
        lines.append("=" * 60)
        lines.append(f"BRANCH: {branch_name} (FULL COMMIT HISTORY)")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Total Commits: {len(commits)}")
        
        if commits:
            lines.append(f"Branch Purpose: {commits[0].branch_purpose}")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("COMMIT HISTORY (oldest to newest):")
        lines.append("-" * 60)
        
        # Show ALL commits with their contributions
        for i, c in enumerate(commits, 1):
            lines.append("")
            lines.append(f"--- Commit {i}/{len(commits)} ---")
            lines.append(f"ID: {c.commit_id}")
            lines.append(f"Timestamp: {c.timestamp}")
            if c.parent_commit:
                lines.append(f"Parent: {c.parent_commit}")
            else:
                lines.append("Root commit")
            lines.append(f"Contribution:")
            lines.append(c.commit_contribution)
            lines.append("-" * 60)
        
        lines.append("")
        lines.append("Metadata:")
        lines.append(f"  File Structure: {len(metadata.file_structure)} entries")
        lines.append(f"  Environment Config: {len(metadata.env_config)} entries")
    else:
        import yaml
        data = {
            'branch_name': branch_name,
            'commit_count': len(commits),
            'branch_purpose': commits[0].branch_purpose if commits else None,
            'commits': [c.to_dict() for c in commits],
            'metadata': metadata.to_dict()
        }
        return yaml.dump(data, default_flow_style=False)
    
    return "\n".join(lines)


def format_session_info(branch_name: str, format: str, brief: bool = False) -> str:
    """Format session-level (log) information with FULL history"""
    if not filesystem.branch_exists(branch_name):
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    logs = filesystem.read_logs(branch_name)
    
    lines = []
    
    if brief:
        # Concise output - recent logs with truncation
        lines.append(f"[{branch_name}] {len(logs)} logs. Recent 8:")
        for log in logs[-8:]:
            summary = log.reasoning_step.replace('\n', ' ')[:300]
            lines.append(f"  • {log.timestamp[:16]}: {summary}...")
        return "\n".join(lines)
    
    if format == "markdown":
        lines.append("=" * 60)
        lines.append(f"SESSION LOGS: {branch_name} (FULL HISTORY)")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Total log entries: {len(logs)}")
        lines.append("")
        lines.append("-" * 60)
        
        # Show ALL logs - this is the detailed history recovery
        for i, log in enumerate(logs, 1):
            lines.append("")
            lines.append(f"--- Log {i}/{len(logs)} ---")
            lines.append(f"Timestamp: {log.timestamp}")
            if log.source_branch:
                lines.append(f"Source: {log.source_branch}")
            lines.append("Content:")
            lines.append(log.reasoning_step)
            lines.append("-" * 60)
    else:
        import yaml
        data = {
            'branch_name': branch_name,
            'total_logs': len(logs),
            'logs': [log.to_dict() for log in logs]
        }
        return yaml.dump(data, default_flow_style=False)
    
    return "\n".join(lines)


def todos_command(action: str = "list", item: Optional[str] = None, todo_id: Optional[int] = None) -> str:
    """
    TODOS command: Manage TODO items
    
    Args:
        action: "list", "add", or "complete"
        item: TODO item text (for "add" action)
        todo_id: TODO item number to complete (for "complete" action, 1-indexed)
    
    Returns:
        Formatted TODO list or confirmation message
    """
    filesystem.ensure_context_directory()
    
    main_content = filesystem.read_main_md()
    
    # Find TODO section
    todo_marker = "## TODO List"
    if todo_marker not in main_content:
        # Add TODO section if it doesn't exist
        main_content += f"\n\n{todo_marker}\n\n"
        filesystem.write_main_md(main_content)
    
    # Parse existing TODOs
    todo_start = main_content.find(todo_marker)
    todo_section_start = todo_start + len(todo_marker)
    
    # Find next section or end of file
    next_section = main_content.find("\n## ", todo_section_start)
    if next_section == -1:
        todo_section = main_content[todo_section_start:]
    else:
        todo_section = main_content[todo_section_start:next_section]
    
    # Parse TODO items (lines starting with - [ ] or - [x])
    lines = todo_section.strip().split('\n')
    todos = []
    other_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- [ ]') or stripped.startswith('- [x]'):
            completed = stripped.startswith('- [x]')
            text = stripped[6:].strip()  # Remove '- [ ] ' or '- [x] '
            todos.append({'text': text, 'completed': completed})
        elif stripped and not stripped.startswith('<!--'):
            other_lines.append(line)
    
    if action == "list":
        if not todos:
            return "No TODOs. Use `context_todos --add \"task description\"` to add one."
        
        result = ["## Current TODOs", ""]
        for i, todo in enumerate(todos, 1):
            status = "✓" if todo['completed'] else " "
            result.append(f"  {i}. [{status}] {todo['text']}")
        return "\n".join(result)
    
    elif action == "add":
        if not item:
            return "Error: Please provide a TODO item with --add \"description\""
        
        todos.append({'text': item, 'completed': False})
        _save_todos(main_content, todo_marker, todos, other_lines)
        return f"✓ Added TODO: {item}"
    
    elif action == "complete":
        if todo_id is None:
            return "Error: Please provide a TODO number with --complete N"
        if todo_id < 1 or todo_id > len(todos):
            return f"Error: Invalid TODO number. Valid range: 1-{len(todos)}"
        
        todos[todo_id - 1]['completed'] = True
        completed_text = todos[todo_id - 1]['text']
        _save_todos(main_content, todo_marker, todos, other_lines)
        
        # Also create a commit noting the completed TODO
        current_branch = filesystem.get_current_branch()
        if current_branch:
            new_commit = CommitEntry(
                commit_id=generate_commit_id(),
                branch_purpose=filesystem.read_commits(current_branch)[0].branch_purpose if filesystem.read_commits(current_branch) else "Development",
                commit_contribution=f"Completed TODO: {completed_text}",
                timestamp=get_current_timestamp(),
                parent_commit=filesystem.read_commits(current_branch)[-1].commit_id if filesystem.read_commits(current_branch) else None
            )
            filesystem.append_commit(current_branch, new_commit)
        
        return f"✓ Completed TODO #{todo_id}: {completed_text}"
    
    else:
        return f"Error: Unknown action '{action}'. Use 'list', 'add', or 'complete'."


def _save_todos(main_content: str, todo_marker: str, todos: list, other_lines: list) -> None:
    """Helper to save TODOs back to main.md"""
    todo_start = main_content.find(todo_marker)
    todo_section_start = todo_start + len(todo_marker)
    
    # Find next section or end of file  
    next_section = main_content.find("\n## ", todo_section_start)
    
    # Build new TODO section
    new_todo_section = "\n\n"
    for todo in todos:
        checkbox = "[x]" if todo['completed'] else "[ ]"
        new_todo_section += f"- {checkbox} {todo['text']}\n"
    
    # Add any other preserved lines
    if other_lines:
        new_todo_section += "\n" + "\n".join(other_lines) + "\n"
    
    # Reconstruct main.md
    if next_section == -1:
        new_content = main_content[:todo_section_start] + new_todo_section
    else:
        new_content = main_content[:todo_section_start] + new_todo_section + main_content[next_section:]
    
    filesystem.write_main_md(new_content)


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


def _extract_files_from_text(text: str) -> List[str]:
    """Extract file paths mentioned in text"""
    import re
    # Match common file patterns
    patterns = [
        r'[\w/.-]+\.(?:py|js|ts|jsx|tsx|go|rs|java|c|cpp|h|hpp|rb|php|swift|kt|scala|yaml|yml|json|toml|md|txt|html|css|scss|sql)',
        r'(?:src|lib|app|test|tests|spec|docs)/[\w/.-]+',
    ]
    files = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            # Clean up and normalize
            cleaned = m.strip().lstrip('./')
            if cleaned and len(cleaned) > 2:
                files.add(cleaned)
    return list(files)


def _extract_keywords_from_text(text: str) -> List[str]:
    """Extract meaningful keywords from text"""
    import re
    # Remove common words and extract meaningful terms
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'to', 'of',
                  'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
                  'during', 'before', 'after', 'above', 'below', 'between', 'under',
                  'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
                  'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
                  'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
                  'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
                  'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me', 'my', 'we',
                  'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'they', 'them',
                  'their', 'what', 'which', 'who', 'whom', 'file', 'code', 'function',
                  'method', 'class', 'found', 'error', 'fix', 'bug', 'added', 'updated',
                  'changed', 'created', 'deleted', 'removed', 'modified'}
    
    # Extract words (alphanumeric with underscores)
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Count frequency and return top keywords
    from collections import Counter
    counts = Counter(keywords)
    return [kw for kw, _ in counts.most_common(20)]


def _calculate_branch_similarity(branch_name: str, files: List[str], keywords: List[str]) -> float:
    """Calculate how similar a branch is to given files and keywords"""
    metadata = filesystem.read_metadata(branch_name)
    commits = filesystem.read_commits(branch_name)
    logs = filesystem.read_logs(branch_name)
    
    score = 0.0
    
    # Check tracked files overlap
    if metadata.tracked_files and files:
        tracked_set = set(f.lower() for f in metadata.tracked_files)
        files_set = set(f.lower() for f in files)
        file_overlap = len(tracked_set & files_set)
        if file_overlap > 0:
            score += file_overlap * 10  # High weight for file matches
    
    # Check keywords overlap
    if metadata.keywords and keywords:
        kw_set = set(metadata.keywords)
        new_kw_set = set(keywords)
        kw_overlap = len(kw_set & new_kw_set)
        score += kw_overlap * 2
    
    # Check branch purpose for keyword matches
    if commits:
        purpose = commits[0].branch_purpose.lower()
        for kw in keywords:
            if kw in purpose:
                score += 5
    
    # Check recent logs for file mentions
    recent_logs = logs[-10:] if len(logs) > 10 else logs
    log_text = ' '.join(log.reasoning_step for log in recent_logs)
    log_files = _extract_files_from_text(log_text)
    if log_files and files:
        log_files_set = set(f.lower() for f in log_files)
        files_set = set(f.lower() for f in files)
        log_file_overlap = len(log_files_set & files_set)
        score += log_file_overlap * 5
    
    return score


def detect_matching_branch(context_hint: str) -> dict:
    """
    Detect which branch best matches the given context.
    
    Args:
        context_hint: Text describing what the user wants to work on,
                     or file paths being worked on
    
    Returns:
        Dictionary with:
        - match_found: bool
        - recommended_branch: str or None
        - similarity_score: float
        - all_branches: list of (branch_name, score) tuples
        - suggestion: str describing what to do
    """
    filesystem.ensure_context_directory()
    
    branches = filesystem.list_branches()
    current_branch = filesystem.get_current_branch()
    
    # Extract files and keywords from context hint
    files = _extract_files_from_text(context_hint)
    keywords = _extract_keywords_from_text(context_hint)
    
    result = {
        'match_found': False,
        'recommended_branch': None,
        'similarity_score': 0.0,
        'all_branches': [],
        'current_branch': current_branch,
        'extracted_files': files[:5],  # Top 5
        'extracted_keywords': keywords[:10],  # Top 10
        'suggestion': ''
    }
    
    if not branches:
        result['suggestion'] = "No branches exist. Create one with context_branch(name='...', purpose='...')"
        return result
    
    # Calculate similarity for each branch
    branch_scores = []
    for branch in branches:
        score = _calculate_branch_similarity(branch, files, keywords)
        branch_scores.append((branch, score))
    
    # Sort by score descending
    branch_scores.sort(key=lambda x: x[1], reverse=True)
    result['all_branches'] = branch_scores
    
    best_branch, best_score = branch_scores[0]
    
    # Determine recommendation
    if best_score >= 10:
        result['match_found'] = True
        result['recommended_branch'] = best_branch
        result['similarity_score'] = best_score
        
        if best_branch == current_branch:
            result['suggestion'] = f"✓ Already on the best matching branch '{best_branch}' (score: {best_score:.1f})"
        else:
            result['suggestion'] = f"⚠️ Switch to branch '{best_branch}' (score: {best_score:.1f}). Current branch '{current_branch}' may not be related."
    else:
        # No good match - suggest creating new branch
        result['suggestion'] = f"No matching branch found. Consider creating a new branch for this work."
        if keywords:
            suggested_name = '-'.join(keywords[:3])
            result['suggestion'] += f"\n  Suggested: context_branch(name='{suggested_name}', purpose='...')"
    
    return result


def update_branch_tracking(files: List[str] = None, keywords: List[str] = None) -> None:
    """Update current branch's tracked files and keywords"""
    current_branch = filesystem.get_current_branch()
    if not current_branch:
        return
    
    metadata = filesystem.read_metadata(current_branch)
    
    if files:
        for f in files:
            metadata.add_tracked_file(f)
    
    if keywords:
        for kw in keywords:
            metadata.add_keyword(kw)
    
    filesystem.write_metadata(current_branch, metadata)
