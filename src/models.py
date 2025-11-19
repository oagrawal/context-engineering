"""Data models and schemas for the context management system"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import yaml


@dataclass
class CommitEntry:
    """A single commit entry stored in commit.json"""
    commit_id: str  # Unique identifier (timestamp or UUID)
    branch_purpose: str  # Reiteration of branch purpose
    previous_progress: str  # Combined previous progress + contribution
    commit_contribution: str  # What this commit adds
    timestamp: str  # ISO format datetime string
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'commit_id': self.commit_id,
            'branch_purpose': self.branch_purpose,
            'previous_progress': self.previous_progress,
            'commit_contribution': self.commit_contribution,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommitEntry':
        """Create from dictionary"""
        return cls(
            commit_id=data['commit_id'],
            branch_purpose=data['branch_purpose'],
            previous_progress=data['previous_progress'],
            commit_contribution=data['commit_contribution'],
            timestamp=data['timestamp']
        )
    
    def to_json(self) -> str:
        """Convert to JSON string for storage"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_content: str) -> 'CommitEntry':
        """Create from JSON string"""
        data = json.loads(json_content)
        return cls.from_dict(data)
    
    def to_markdown(self) -> str:
        """Convert to markdown format for LLM consumption"""
        return f"""## Commit {self.commit_id}

**Timestamp:** {self.timestamp}

### Branch Purpose
{self.branch_purpose}

### Previous Progress
{self.previous_progress}

### Commit Contribution
{self.commit_contribution}

---

"""


@dataclass
class LogEntry:
    """A single log entry stored in log.json"""
    timestamp: str  # ISO format datetime string
    reasoning_step: str  # The reasoning/thinking step
    source_branch: Optional[str] = None  # Track which branch this came from (for merges)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'timestamp': self.timestamp,
            'reasoning_step': self.reasoning_step
        }
        if self.source_branch:
            result['source_branch'] = self.source_branch
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        return cls(
            timestamp=data['timestamp'],
            reasoning_step=data['reasoning_step'],
            source_branch=data.get('source_branch')
        )
    
    def to_json(self) -> str:
        """Convert to JSON string for storage"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_content: str) -> 'LogEntry':
        """Create from JSON string"""
        data = json.loads(json_content)
        return cls.from_dict(data)
    
    def to_markdown(self) -> str:
        """Convert to markdown format for LLM consumption"""
        header = f"## {self.timestamp}"
        if self.source_branch:
            header += f" (from branch: {self.source_branch})"
        
        return f"""{header}

{self.reasoning_step}

---

"""


class MetadataYAML:
    """Structured metadata stored in metadata.yaml"""
    
    def __init__(self, file_structure: Optional[Dict[str, Any]] = None,
                 env_config: Optional[Dict[str, Any]] = None,
                 created_date: Optional[str] = None,
                 custom_entries: Optional[Dict[str, Any]] = None):
        self.file_structure = file_structure or {}
        self.env_config = env_config or {}
        self.created_date = created_date  # Branch creation date
        self.custom_entries = custom_entries or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        result = {
            'file_structure': self.file_structure,
            'env_config': self.env_config
        }
        if self.created_date:
            result['created_date'] = self.created_date
        result.update(self.custom_entries)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataYAML':
        """Create from dictionary"""
        file_structure = data.get('file_structure', {})
        env_config = data.get('env_config', {})
        created_date = data.get('created_date')
        custom_entries = {k: v for k, v in data.items() 
                         if k not in ['file_structure', 'env_config', 'created_date']}
        
        return cls(
            file_structure=file_structure,
            env_config=env_config,
            created_date=created_date,
            custom_entries=custom_entries
        )
    
    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'MetadataYAML':
        """Create from YAML string"""
        data = yaml.safe_load(yaml_content) or {}
        return cls.from_dict(data)


def validate_branch_name(name: str) -> bool:
    """Validate branch name"""
    if not name:
        return False
    # Check for invalid characters (basic validation)
    invalid_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    for char in invalid_chars:
        if char in name:
            return False
    return True


def generate_commit_id() -> str:
    """Generate a unique commit ID"""
    return datetime.now().isoformat().replace(':', '-').replace('.', '-')


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()


def compare_commits(commits_a: List[CommitEntry], commits_b: List[CommitEntry]) -> tuple[List[CommitEntry], List[CommitEntry], List[CommitEntry]]:
    """
    Compare two commit lists to find:
    - common_commits: Commits present in both branches (common prefix)
    - unique_to_a: Commits only in branch A (after divergence)
    - unique_to_b: Commits only in branch B (after divergence)
    
    Returns: (common_commits, unique_to_a, unique_to_b)
    """
    # Create sets of commit IDs for quick lookup
    ids_a = {c.commit_id for c in commits_a}
    ids_b = {c.commit_id for c in commits_b}
    
    # Find common commit IDs
    common_ids = ids_a & ids_b
    
    # Find commits unique to each branch
    unique_ids_a = ids_a - ids_b
    unique_ids_b = ids_b - ids_a
    
    # Convert back to commit lists, preserving order
    common_commits = [c for c in commits_a if c.commit_id in common_ids]
    unique_to_a = [c for c in commits_a if c.commit_id in unique_ids_a]
    unique_to_b = [c for c in commits_b if c.commit_id in unique_ids_b]
    
    # Sort common commits by timestamp to find the last common commit
    common_commits.sort(key=lambda x: x.timestamp)
    
    return common_commits, unique_to_a, unique_to_b


def find_divergence_point(commits_a: List[CommitEntry], commits_b: List[CommitEntry]) -> Optional[str]:
    """
    Find the commit ID where two branches diverged.
    Returns the commit ID of the last common commit, or None if no common history.
    """
    common_commits, _, _ = compare_commits(commits_a, commits_b)
    
    if not common_commits:
        return None
    
    # Return the last common commit ID
    return common_commits[-1].commit_id


def commits_to_json(commits: List[CommitEntry]) -> str:
    """Convert a list of commits to JSON array string"""
    return json.dumps([c.to_dict() for c in commits], indent=2, ensure_ascii=False)


def commits_from_json(json_content: str) -> List[CommitEntry]:
    """Parse a list of commits from JSON array string"""
    if not json_content.strip():
        return []
    data_list = json.loads(json_content)
    return [CommitEntry.from_dict(item) for item in data_list]


def commits_to_markdown(commits: List[CommitEntry]) -> str:
    """Convert a list of commits to markdown for LLM consumption"""
    if not commits:
        return "# Branch Commit History\n\nNo commits yet.\n"
    
    markdown = "# Branch Commit History\n\n"
    for commit in commits:
        markdown += commit.to_markdown()
    return markdown


def logs_to_json(logs: List[LogEntry]) -> str:
    """Convert a list of log entries to JSON array string"""
    return json.dumps([l.to_dict() for l in logs], indent=2, ensure_ascii=False)


def logs_from_json(json_content: str) -> List[LogEntry]:
    """Parse a list of log entries from JSON array string"""
    if not json_content.strip():
        return []
    data_list = json.loads(json_content)
    return [LogEntry.from_dict(item) for item in data_list]


def logs_to_markdown(logs: List[LogEntry], include_branch_tags: bool = False) -> str:
    """Convert a list of log entries to markdown for LLM consumption"""
    if not logs:
        return "# Reasoning Log\n\nNo log entries yet.\n"
    
    markdown = "# Reasoning Log\n\n"
    current_branch = None
    
    for log in logs:
        # Add branch tag if branch changed and include_branch_tags is True
        if include_branch_tags and log.source_branch and log.source_branch != current_branch:
            markdown += f"\n== {log.source_branch} ==\n\n"
            current_branch = log.source_branch
        
        markdown += log.to_markdown()
    
    return markdown

