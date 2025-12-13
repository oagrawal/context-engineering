"""File system operations for context management"""

import os
import subprocess
import threading
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
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


# Thread-local storage for workspace root (for concurrency safety)
_thread_local = threading.local()

def _get_thread_workspace() -> Optional[str]:
    return getattr(_thread_local, 'workspace_root', None)

def _get_thread_auto_detected() -> bool:
    return getattr(_thread_local, 'workspace_auto_detected', False)

# Constants (relative to workspace root)
CONTEXT_DIR_NAME = ".context"


def set_workspace_root(path: str) -> None:
    """Set the workspace root directory for context storage (thread-local)"""
    _thread_local.workspace_root = os.path.abspath(path)
    _thread_local.workspace_auto_detected = False


def _detect_git_root(start_path: Optional[str] = None) -> Optional[str]:
    """Detect git repository root directory"""
    try:
        cwd = start_path or os.getcwd()
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


def _find_existing_context_dir(start_path: Optional[str] = None) -> Optional[str]:
    """Walk up from start_path looking for an existing .context directory"""
    current = os.path.abspath(start_path or os.getcwd())
    
    # Limit search to prevent infinite loops
    for _ in range(20):
        context_path = os.path.join(current, CONTEXT_DIR_NAME)
        if os.path.isdir(context_path):
            return current
        
        parent = os.path.dirname(current)
        if parent == current:  # Reached root
            break
        current = parent
    
    return None


def auto_detect_workspace() -> Tuple[Optional[str], str]:
    """
    Auto-detect the workspace root directory.
    
    Returns:
        Tuple of (workspace_path, detection_method)
        detection_method is one of: 'existing_context', 'git_root', 'cwd', 'not_found'
    """
    # Priority 1: Look for existing .context directory
    existing = _find_existing_context_dir()
    if existing:
        return existing, 'existing_context'
    
    # Priority 2: Use git repository root
    git_root = _detect_git_root()
    if git_root:
        return git_root, 'git_root'
    
    # Priority 3: Fall back to current working directory
    return os.getcwd(), 'cwd'


def get_workspace_root() -> str:
    """Get the workspace root directory, auto-detecting if not explicitly set (thread-local)"""
    workspace = _get_thread_workspace()
    if workspace is None:
        detected, method = auto_detect_workspace()
        _thread_local.workspace_root = detected
        _thread_local.workspace_auto_detected = True
        return detected
    return workspace


def is_workspace_auto_detected() -> bool:
    """Check if workspace was auto-detected (vs explicitly set)"""
    return _get_thread_auto_detected()


def _get_context_dir() -> str:
    """Get the full path to the context directory"""
    return os.path.join(get_workspace_root(), CONTEXT_DIR_NAME)


def _get_branches_dir() -> str:
    """Get the full path to the branches directory"""
    return os.path.join(_get_context_dir(), "branches")


def _get_current_branch_file() -> str:
    """Get the full path to the current branch file"""
    return os.path.join(_get_context_dir(), ".current_branch")


def _get_main_md_file() -> str:
    """Get the full path to main.md"""
    return os.path.join(_get_context_dir(), "main.md")


# Legacy constants for backward compatibility (use functions above instead)
CONTEXT_DIR = ".context"
BRANCHES_DIR = os.path.join(CONTEXT_DIR, "branches")
CURRENT_BRANCH_FILE = os.path.join(CONTEXT_DIR, ".current_branch")
MAIN_MD_FILE = os.path.join(CONTEXT_DIR, "main.md")


def get_context_dir() -> str:
    """Get the context directory path"""
    return _get_context_dir()


def get_branches_dir() -> str:
    """Get the branches directory path"""
    return _get_branches_dir()


def initialize_context_directory() -> None:
    """Initialize .context/ directory structure if it doesn't exist"""
    branches_dir = _get_branches_dir()
    main_md_file = _get_main_md_file()
    
    os.makedirs(branches_dir, exist_ok=True)
    
    # Create main.md if it doesn't exist
    if not os.path.exists(main_md_file):
        with open(main_md_file, 'w', encoding='utf-8') as f:
            f.write(get_main_md_template())


def ensure_context_directory() -> None:
    """Ensure context directory exists, create if it doesn't"""
    context_dir = _get_context_dir()
    branches_dir = _get_branches_dir()
    
    if not os.path.exists(context_dir):
        initialize_context_directory()
    elif not os.path.exists(branches_dir):
        os.makedirs(branches_dir, exist_ok=True)


def get_main_md_path() -> str:
    """Get the path to main.md"""
    return _get_main_md_file()


def validate_main_md() -> bool:
    """Validate that main.md exists and has basic structure"""
    main_md_file = _get_main_md_file()
    
    if not os.path.exists(main_md_file):
        return False
    
    # Check if file has basic sections
    try:
        with open(main_md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check for key sections (basic validation)
            return '# Project Goals' in content or 'Project Goals' in content
    except Exception:
        return False


def create_main_md() -> None:
    """Create or recreate main.md with template"""
    ensure_context_directory()
    main_md_file = _get_main_md_file()
    with open(main_md_file, 'w', encoding='utf-8') as f:
        f.write(get_main_md_template())


def read_main_md() -> str:
    """Read main.md content"""
    main_md_file = _get_main_md_file()
    if not os.path.exists(main_md_file):
        create_main_md()
    
    with open(main_md_file, 'r', encoding='utf-8') as f:
        return f.read()


def write_main_md(content: str) -> None:
    """Write content to main.md"""
    ensure_context_directory()
    main_md_file = _get_main_md_file()
    with open(main_md_file, 'w', encoding='utf-8') as f:
        f.write(content)


def get_branch_dir(branch_name: str) -> str:
    """Get the directory path for a branch"""
    return os.path.join(_get_branches_dir(), branch_name)


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
    current_branch_file = _get_current_branch_file()
    
    if not os.path.exists(current_branch_file):
        return None
    
    try:
        with open(current_branch_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Parse format: "branch_name\ntimestamp" (timestamp is optional for backwards compat)
            lines = content.split('\n')
            branch_name = lines[0].strip() if lines else ""
            if branch_name and branch_exists(branch_name):
                return branch_name
            return None
    except Exception:
        return None


def get_current_branch_info() -> Optional[Tuple[str, Optional[str]]]:
    """
    Get current branch name and session timestamp.
    
    Returns:
        Tuple of (branch_name, timestamp) or None if no branch set.
        timestamp may be None for legacy .current_branch files.
    """
    current_branch_file = _get_current_branch_file()
    
    if not os.path.exists(current_branch_file):
        return None
    
    try:
        with open(current_branch_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            lines = content.split('\n')
            branch_name = lines[0].strip() if lines else ""
            timestamp = lines[1].strip() if len(lines) > 1 else None
            
            if branch_name and branch_exists(branch_name):
                return (branch_name, timestamp)
            return None
    except Exception:
        return None


def set_current_branch(branch_name: str) -> None:
    """Set the current branch with session timestamp"""
    if not branch_exists(branch_name):
        raise ValueError(f"Branch '{branch_name}' does not exist")
    
    ensure_context_directory()
    current_branch_file = _get_current_branch_file()
    timestamp = datetime.now().isoformat()
    with open(current_branch_file, 'w', encoding='utf-8') as f:
        f.write(f"{branch_name}\n{timestamp}")


def list_branches() -> List[str]:
    """List all existing branches"""
    branches_dir = _get_branches_dir()
    
    if not os.path.exists(branches_dir):
        return []
    
    branches = []
    for item in os.listdir(branches_dir):
        branch_path = os.path.join(branches_dir, item)
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
