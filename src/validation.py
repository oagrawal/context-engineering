"""Validation functions for data structures"""

from typing import Optional
from .models import (
    BranchMetadata, CommitEntry, LogEntry, MetadataYAML,
    validate_branch_name, get_current_timestamp
)


def validate_branch_metadata(metadata: BranchMetadata) -> tuple[bool, Optional[str]]:
    """
    Validate branch metadata.
    Returns: (is_valid, error_message)
    """
    if not metadata.name:
        return False, "Branch name cannot be empty"
    
    if not validate_branch_name(metadata.name):
        return False, f"Invalid branch name: {metadata.name}"
    
    if not metadata.created_date:
        return False, "Created date cannot be empty"
    
    # Basic ISO format check
    try:
        from datetime import datetime
        datetime.fromisoformat(metadata.created_date.replace('Z', '+00:00'))
    except ValueError:
        return False, f"Invalid date format: {metadata.created_date}"
    
    return True, None


def validate_commit_entry(commit: CommitEntry) -> tuple[bool, Optional[str]]:
    """
    Validate commit entry.
    Returns: (is_valid, error_message)
    """
    if not commit.commit_id:
        return False, "Commit ID cannot be empty"
    
    if not commit.timestamp:
        return False, "Timestamp cannot be empty"
    
    # Validate timestamp format
    try:
        from datetime import datetime
        datetime.fromisoformat(commit.timestamp.replace('Z', '+00:00'))
    except ValueError:
        return False, f"Invalid timestamp format: {commit.timestamp}"
    
    if not commit.branch_purpose:
        return False, "Branch purpose cannot be empty"
    
    if not commit.previous_progress:
        return False, "Previous progress cannot be empty"
    
    if not commit.commit_contribution:
        return False, "Commit contribution cannot be empty"
    
    return True, None


def validate_log_entry(log: LogEntry) -> tuple[bool, Optional[str]]:
    """
    Validate log entry.
    Returns: (is_valid, error_message)
    """
    if not log.timestamp:
        return False, "Timestamp cannot be empty"
    
    # Validate timestamp format
    try:
        from datetime import datetime
        datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
    except ValueError:
        return False, f"Invalid timestamp format: {log.timestamp}"
    
    if not log.reasoning_step:
        return False, "Reasoning step cannot be empty"
    
    return True, None


def validate_metadata_yaml(metadata: MetadataYAML) -> tuple[bool, Optional[str]]:
    """
    Validate metadata YAML.
    Returns: (is_valid, error_message)
    """
    # Basic validation - file_structure and env_config should be dicts
    if not isinstance(metadata.file_structure, dict):
        return False, "file_structure must be a dictionary"
    
    if not isinstance(metadata.env_config, dict):
        return False, "env_config must be a dictionary"
    
    return True, None

