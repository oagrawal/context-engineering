"""Default templates for context files"""


def get_main_md_template() -> str:
    """Template for main.md"""
    return """# Project Goals

<!-- High-level description of the project's purpose and objectives -->

## Key Milestones

<!-- Track major milestones and achievements -->

## TODO List

<!-- Shared TODO items across all branches -->

"""


def get_commit_json_template() -> str:
    """Template for commit.json (empty JSON array initially)"""
    return "[]\n"


def get_log_json_template() -> str:
    """Template for log.json (empty JSON array initially)"""
    return "[]\n"


def get_metadata_yaml_template(created_date: str = None) -> str:
    """Template for metadata.yaml"""
    import yaml
    data = {
        'file_structure': {},
        'env_config': {}
    }
    if created_date:
        data['created_date'] = created_date
    
    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
    return f"""# Branch Metadata

{yaml_str}
# Example file_structure:
# file_structure:
#   src/:
#     main.py: "Main entry point"
#     utils.py: "Utility functions"
#
# Example env_config:
# env_config:
#   python_version: "3.9+"
#   dependencies: ["click", "pyyaml"]
#
# Add custom metadata entries below as needed

"""

