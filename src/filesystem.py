"""File system operations for context management"""

import os
import yaml
from pathlib import Path
from typing import Optional, List
from .models import (
    CommitEntry, LogEntry, MetadataYAML,
    commits_to_yaml, commits_from_yaml,
    logs_to_yaml, logs_from_yaml
)
from .templates import (
    get_main_md_template,
    get_commits_yaml_template,
    get_log_yaml_template,
    get_metadata_yaml_template
)


# Constants
CONTEXT_DIR = ".context"
BRANCHES_DIR = os.path.join(CONTEXT_DIR, "branches")
CURRENT_BRANCH_FILE = os.path.join(CONTEXT_DIR, ".current_branch")
MAIN_MD_FILE = os.path.join(CONTEXT_DIR, "main.md")


def get_context_dir() -> str:
    """Get the context directory path"""
    return CONTEXT_DIR


def get_branches_dir() -> str:
    """Get the branches directory path"""
    return BRANCHES_DIR


def initialize_context_directory() -> None:
    """Initialize .context/ directory structure if it doesn't exist"""
    os.makedirs(BRANCHES_DIR, exist_ok=True)
    
    # Create main.md if it doesn't exist
    if not os.path.exists(MAIN_MD_FILE):
        with open(MAIN_MD_FILE, 'w', encoding='utf-8') as f:
            f.write(get_main_md_template())


def ensure_context_directory() -> None:
    """Ensure context directory exists, create if it doesn't"""
    if not os.path.exists(CONTEXT_DIR):
        initialize_context_directory()
    elif not os.path.exists(BRANCHES_DIR):
        os.makedirs(BRANCHES_DIR, exist_ok=True)


def get_main_md_path() -> str:
    """Get the path to main.md"""
    return MAIN_MD_FILE


def validate_main_md() -> bool:
    """Validate that main.md exists and has basic structure"""
    if not os.path.exists(MAIN_MD_FILE):
        return False
    
    # Check if file has basic sections
    try:
        with open(MAIN_MD_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for key sections (basic validation)
            return '# Project Goals' in content or 'Project Goals' in content
    except Exception:
        return False


def create_main_md() -> None:
    """Create or recreate main.md with template"""
    ensure_context_directory()
    with open(MAIN_MD_FILE, 'w', encoding='utf-8') as f:
        f.write(get_main_md_template())


def read_main_md() -> str:
    """Read main.md content"""
    if not os.path.exists(MAIN_MD_FILE):
        create_main_md()
    
    with open(MAIN_MD_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def write_main_md(content: str) -> None:
    """Write content to main.md"""
    ensure_context_directory()
    with open(MAIN_MD_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def get_branch_dir(branch_name: str) -> str:
    """Get the directory path for a branch"""
    return os.path.join(BRANCHES_DIR, branch_name)


def branch_exists(branch_name: str) -> bool:
    """Check if a branch exists"""
    branch_dir = get_branch_dir(branch_name)
    return os.path.exists(branch_dir) and os.path.isdir(branch_dir)


def create_branch_directory(branch_name: str) -> str:
    """Create directory structure for a new branch"""
    branch_dir = get_branch_dir(branch_name)
    os.makedirs(branch_dir, exist_ok=True)
    return branch_dir


def get_branch_commits_path(branch_name: str) -> str:
    """Get the path to commits.yaml for a branch"""
    return os.path.join(get_branch_dir(branch_name), "commits.yaml")


def get_branch_log_path(branch_name: str) -> str:
    """Get the path to log.yaml for a branch"""
    return os.path.join(get_branch_dir(branch_name), "log.yaml")


def get_branch_metadata_path(branch_name: str) -> str:
    """Get the path to metadata.yaml for a branch"""
    return os.path.join(get_branch_dir(branch_name), "metadata.yaml")


def get_current_branch() -> Optional[str]:
    """Get the current branch name from .current_branch file"""
    if not os.path.exists(CURRENT_BRANCH_FILE):
        return None
    
    try:
        with open(CURRENT_BRANCH_FILE, 'r', encoding='utf-8') as f:
            branch_name = f.read().strip()
            if branch_name and branch_exists(branch_name):
                return branch_name
            return None
    except Exception:
        return None


def set_current_branch(branch_name: str) -> None:
    """Set the current branch"""
    if not branch_exists(branch_name):
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    ensure_context_directory()
    with open(CURRENT_BRANCH_FILE, 'w', encoding='utf-8') as f:
        f.write(branch_name)


def list_branches() -> List[str]:
    """List all existing branches"""
    if not os.path.exists(BRANCHES_DIR):
        return []
    
    branches = []
    for item in os.listdir(BRANCHES_DIR):
        branch_path = os.path.join(BRANCHES_DIR, item)
        if os.path.isdir(branch_path):
            branches.append(item)
    
    return sorted(branches)


def read_commits(branch_name: str) -> List[CommitEntry]:
    """Read commits from a branch's commits.yaml"""
    commits_path = get_branch_commits_path(branch_name)
    
    if not os.path.exists(commits_path):
        return []
    
    try:
        with open(commits_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return commits_from_yaml(content)
    except Exception as e:
        raise IOError(f"Failed to read commits from {commits_path}: {e}")


def write_commits(branch_name: str, commits: List[CommitEntry]) -> None:
    """Write commits to a branch's commits.yaml"""
    commits_path = get_branch_commits_path(branch_name)
    
    # Ensure branch directory exists
    create_branch_directory(branch_name)
    
    try:
        yaml_content = commits_to_yaml(commits)
        with open(commits_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
    except Exception as e:
        raise IOError(f"Failed to write commits to {commits_path}: {e}")


def append_commit(branch_name: str, commit: CommitEntry) -> None:
    """Append a single commit to a branch's commits.yaml"""
    commits = read_commits(branch_name)
    commits.append(commit)
    write_commits(branch_name, commits)


def read_logs(branch_name: str) -> List[LogEntry]:
    """Read logs from a branch's log.yaml"""
    log_path = get_branch_log_path(branch_name)
    
    if not os.path.exists(log_path):
        return []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return logs_from_yaml(content)
    except Exception as e:
        raise IOError(f"Failed to read logs from {log_path}: {e}")


def write_logs(branch_name: str, logs: List[LogEntry]) -> None:
    """Write logs to a branch's log.yaml"""
    log_path = get_branch_log_path(branch_name)
    
    # Ensure branch directory exists
    create_branch_directory(branch_name)
    
    try:
        yaml_content = logs_to_yaml(logs)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
    except Exception as e:
        raise IOError(f"Failed to write logs to {log_path}: {e}")


def append_log(branch_name: str, log_entry: LogEntry) -> None:
    """Append a single log entry to a branch's log.yaml"""
    logs = read_logs(branch_name)
    logs.append(log_entry)
    write_logs(branch_name, logs)


def clear_all_logs(branch_name: str) -> None:
    """Clear all logs from a branch's log.yaml"""
    write_logs(branch_name, [])


def clear_logs_range(branch_name: str, start: int, end: int) -> None:
    """Clear logs in a specific range (start inclusive, end exclusive)
    
    Args:
        branch_name: Name of the branch
        start: Start index (inclusive), must be >= 0
        end: End index (exclusive), must be >= start
    
    Raises:
        ValueError: If start < 0, end < start, or indices are out of bounds
    """
    if start < 0:
        raise ValueError(f"Start index must be >= 0, got {start}")
    if end < start:
        raise ValueError(f"End index must be >= start, got end={end}, start={start}")
    
    logs = read_logs(branch_name)
    if start > len(logs):
        raise ValueError(f"Start index {start} is out of bounds (only {len(logs)} logs available)")
    
    # Clamp end to available logs (don't error, just use what's available)
    end = min(end, len(logs))
    
    remaining_logs = logs[:start] + logs[end:]
    write_logs(branch_name, remaining_logs)


def clear_logs_count(branch_name: str, count: int) -> None:
    """Clear the last N log entries"""
    if count <= 0:
        return
    logs = read_logs(branch_name)
    remaining_logs = logs[:-count] if count < len(logs) else []
    write_logs(branch_name, remaining_logs)


def read_metadata(branch_name: str) -> MetadataYAML:
    """Read metadata from a branch's metadata.yaml"""
    metadata_path = get_branch_metadata_path(branch_name)
    
    if not os.path.exists(metadata_path):
        # Return default metadata if file doesn't exist
        return MetadataYAML()
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return MetadataYAML.from_yaml(content)
    except Exception as e:
        raise IOError(f"Failed to read metadata from {metadata_path}: {e}")


def write_metadata(branch_name: str, metadata: MetadataYAML) -> None:
    """Write metadata to a branch's metadata.yaml"""
    metadata_path = get_branch_metadata_path(branch_name)
    
    # Ensure branch directory exists
    create_branch_directory(branch_name)
    
    try:
        yaml_content = metadata.to_yaml()
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
    except Exception as e:
        raise IOError(f"Failed to write metadata to {metadata_path}: {e}")


def initialize_branch_files(branch_name: str, empty: bool = False) -> None:
    """Initialize branch files (commits.yaml, log.yaml, metadata.yaml)"""
    branch_dir = create_branch_directory(branch_name)
    
    if empty:
        # Create empty files
        commits_path = get_branch_commits_path(branch_name)
        log_path = get_branch_log_path(branch_name)
        metadata_path = get_branch_metadata_path(branch_name)
        
        with open(commits_path, 'w', encoding='utf-8') as f:
            f.write(get_commits_yaml_template())
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(get_log_yaml_template())
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(get_metadata_yaml_template())
    else:
        # Initialize with templates (will be populated later)
        commits_path = get_branch_commits_path(branch_name)
        log_path = get_branch_log_path(branch_name)
        metadata_path = get_branch_metadata_path(branch_name)
        
        if not os.path.exists(commits_path):
            with open(commits_path, 'w', encoding='utf-8') as f:
                f.write(get_commits_yaml_template())
        
        if not os.path.exists(log_path):
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(get_log_yaml_template())
        
        if not os.path.exists(metadata_path):
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(get_metadata_yaml_template())


def copy_branch_files(source_branch: str, target_branch: str) -> None:
    """Copy branch files from source branch to target branch"""
    if not branch_exists(source_branch):
        raise ValueError(f"Source branch '{source_branch}' does not exist")
    
    # Create target branch directory
    create_branch_directory(target_branch)
    
    # Copy commits.yaml
    source_commits = get_branch_commits_path(source_branch)
    target_commits = get_branch_commits_path(target_branch)
    if os.path.exists(source_commits):
        with open(source_commits, 'r', encoding='utf-8') as src:
            with open(target_commits, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
    
    # Copy log.yaml
    source_log = get_branch_log_path(source_branch)
    target_log = get_branch_log_path(target_branch)
    if os.path.exists(source_log):
        with open(source_log, 'r', encoding='utf-8') as src:
            with open(target_log, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
    
    # Copy metadata.yaml
    source_metadata = get_branch_metadata_path(source_branch)
    target_metadata = get_branch_metadata_path(target_branch)
    if os.path.exists(source_metadata):
        with open(source_metadata, 'r', encoding='utf-8') as src:
            with open(target_metadata, 'w', encoding='utf-8') as dst:
                dst.write(src.read())

