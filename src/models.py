"""Data models and schemas for the context management system"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import yaml


@dataclass
class BranchMetadata:
    """Minimal metadata for a branch"""
    name: str
    created_date: str  # ISO format datetime string
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        return {
            'name': self.name,
            'created_date': self.created_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BranchMetadata':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            created_date=data['created_date']
        )


@dataclass
class CommitEntry:
    """A single commit entry stored in commits.yaml"""
    commit_id: str  # Unique identifier (timestamp or UUID)
    branch_purpose: str  # Reiteration of branch purpose
    commit_contribution: str  # What this commit adds
    timestamp: str  # ISO format datetime string
    parent_commit: Optional[str] = None  # Reference to parent commit ID (None for first commit)
    # Deprecated: previous_progress is kept for backwards compatibility but not used for new commits
    previous_progress: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        result = {
            'commit_id': self.commit_id,
            'timestamp': self.timestamp,
            'branch_purpose': self.branch_purpose,
            'commit_contribution': self.commit_contribution
        }
        if self.parent_commit:
            result['parent_commit'] = self.parent_commit
        # Don't write previous_progress for new commits (storage optimization)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommitEntry':
        """Create from dictionary"""
        return cls(
            commit_id=data['commit_id'],
            timestamp=data['timestamp'],
            branch_purpose=data['branch_purpose'],
            commit_contribution=data['commit_contribution'],
            parent_commit=data.get('parent_commit'),
            # Support legacy previous_progress for backwards compatibility
            previous_progress=data.get('previous_progress')
        )
    
    def to_markdown(self) -> str:
        """Convert to markdown format for LLM consumption"""
        parent_info = f"\n**Parent:** {self.parent_commit}" if self.parent_commit else ""
        return f"""## Commit {self.commit_id}

**Timestamp:** {self.timestamp}{parent_info}

### Branch Purpose
{self.branch_purpose}

### Commit Contribution
{self.commit_contribution}

---

"""


@dataclass
class LogEntry:
    """A single log entry stored in log.yaml"""
    timestamp: str  # ISO format datetime string
    reasoning_step: str  # The reasoning/thinking step
    source_branch: Optional[str] = None  # Track which branch this came from (for merges)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
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
    
    def to_markdown(self) -> str:
        """Convert to markdown format for LLM consumption"""
        source_tag = f" *[from {self.source_branch}]*" if self.source_branch else ""
        return f"""## {self.timestamp}{source_tag}

{self.reasoning_step}

---

"""


class MetadataYAML:
    """Structured metadata stored in metadata.yaml"""
    
    def __init__(self, file_structure: Optional[Dict[str, Any]] = None,
                 env_config: Optional[Dict[str, Any]] = None,
                 custom_entries: Optional[Dict[str, Any]] = None):
        self.file_structure = file_structure or {}
        self.env_config = env_config or {}
        self.custom_entries = custom_entries or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        result = {
            'file_structure': self.file_structure,
            'env_config': self.env_config
        }
        result.update(self.custom_entries)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataYAML':
        """Create from dictionary"""
        file_structure = data.get('file_structure', {})
        env_config = data.get('env_config', {})
        custom_entries = {k: v for k, v in data.items() 
                         if k not in ['file_structure', 'env_config']}
        
        return cls(
            file_structure=file_structure,
            env_config=env_config,
            custom_entries=custom_entries
        )
    
    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'MetadataYAML':
        """Create from YAML string"""
        data = yaml.safe_load(yaml_content) or {}
        return cls.from_dict(data)


def commits_to_yaml(commits: List[CommitEntry]) -> str:
    """Convert list of commits to YAML string"""
    commits_dict = {'commits': [c.to_dict() for c in commits]}
    return yaml.dump(commits_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)


def commits_from_yaml(yaml_content: str) -> List[CommitEntry]:
    """Parse list of commits from YAML string"""
    data = yaml.safe_load(yaml_content) or {}
    commits_data = data.get('commits', [])
    return [CommitEntry.from_dict(c) for c in commits_data]


def logs_to_yaml(logs: List[LogEntry]) -> str:
    """Convert list of logs to YAML string"""
    logs_dict = {'logs': [l.to_dict() for l in logs]}
    return yaml.dump(logs_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)


def logs_from_yaml(yaml_content: str) -> List[LogEntry]:
    """Parse list of logs from YAML string"""
    data = yaml.safe_load(yaml_content) or {}
    logs_data = data.get('logs', [])
    return [LogEntry.from_dict(l) for l in logs_data]


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

