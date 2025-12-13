"""Default templates for context files"""


def get_main_md_template(project_goal: str = "") -> str:
    """Template for main.md"""
    goal_text = project_goal if project_goal else "_No project goal set yet._"
    return f"""# Project Goal

{goal_text}

## TODO List

## Interaction Log

"""


def get_commits_yaml_template() -> str:
    """Template for commits.yaml (empty initially, first commit will define branch purpose)"""
    return """# Branch Commit History
# Commits will be added here as the branch progresses

commits: []

"""


def get_log_yaml_template() -> str:
    """Template for log.yaml (empty initially)"""
    return """# Reasoning Log
# Fine-grained reasoning cycles will be logged here

logs: []

"""


def get_metadata_yaml_template() -> str:
    """Template for metadata.yaml"""
    return """# Branch Metadata

file_structure: {}

env_config: {}

# Files this branch works on (for smart branch detection)
tracked_files: []

# Keywords/topics for this branch
keywords: []

"""
