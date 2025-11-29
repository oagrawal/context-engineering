"""CLI interface for context management system"""

import click
import subprocess
import sys
from typing import Optional, List
from .filesystem import (
    ensure_context_directory, get_current_branch, set_current_branch,
    branch_exists, create_branch_directory, initialize_branch_files,
    copy_branch_files, read_commits, write_commits, append_commit,
    read_logs, write_logs, append_log, clear_all_logs, clear_logs_range,
    clear_logs_count, read_metadata, write_metadata,
    read_main_md, write_main_md, list_branches
)
from .models import (
    CommitEntry, LogEntry, BranchMetadata, MetadataYAML,
    generate_commit_id, get_current_timestamp, validate_branch_name,
    compare_commits
)
from .validation import (
    validate_branch_metadata, validate_commit_entry, validate_log_entry
)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """Context Management System for AI Development Tools"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ensure_context_directory()


@cli.command()
@click.option('--message', '-m', help='Commit message/contribution')
@click.option('--from-log', help='Log range to include (e.g., "5" for last 5 entries, "10:20" for range)')
@click.option('--git-commit', is_flag=True, help='Also create a git commit (disabled by default)')
@click.pass_context
def commit(ctx, message, from_log, git_commit):
    """Create a commit checkpoint in the current branch"""
    verbose = ctx.obj['verbose']
    
    # Get current branch
    current_branch = get_current_branch()
    if not current_branch:
        click.echo("Error: No current branch. Create a branch first with 'context branch <name>'.", err=True)
        sys.exit(1)
    
    if verbose:
        click.echo(f"Current branch: {current_branch}")
    
    # Read existing commits and logs
    commits = read_commits(current_branch)
    logs = read_logs(current_branch)
    
    # Determine branch purpose (from first commit or use default)
    branch_purpose = "Track progress and reasoning"
    if commits:
        branch_purpose = commits[0].branch_purpose
    
    # Determine previous progress
    previous_progress = "Initial state"
    if commits:
        last_commit = commits[-1]
        previous_progress = f"{last_commit.previous_progress}\n\n{last_commit.commit_contribution}"
    
    # Generate commit contribution from logs or message
    commit_contribution = message or "Progress update"
    
    if from_log and logs:
        # Parse log range
        try:
            if ':' in from_log:
                start, end = map(int, from_log.split(':'))
                selected_logs = logs[start:end]
            else:
                count = int(from_log)
                selected_logs = logs[-count:] if count > 0 else logs
        except ValueError:
            click.echo(f"Error: Invalid log range format: {from_log}", err=True)
            sys.exit(1)
        
        # Combine selected log entries
        log_text = "\n\n".join([log.reasoning_step for log in selected_logs])
        commit_contribution = f"{commit_contribution}\n\nReasoning steps:\n{log_text}"
    elif logs:
        # If no --from-log specified, include all logs by default
        log_text = "\n\n".join([log.reasoning_step for log in logs])
        commit_contribution = f"{commit_contribution}\n\nReasoning steps:\n{log_text}"
    
    # Create commit entry
    commit_entry = CommitEntry(
        commit_id=generate_commit_id(),
        branch_purpose=branch_purpose,
        previous_progress=previous_progress,
        commit_contribution=commit_contribution,
        timestamp=get_current_timestamp()
    )
    
    # Validate commit
    is_valid, error = validate_commit_entry(commit_entry)
    if not is_valid:
        click.echo(f"Error: Invalid commit entry: {error}", err=True)
        sys.exit(1)
    
    # Append commit
    append_commit(current_branch, commit_entry)
    
    # Clear logs that were included in this commit
    logs_before_clear = len(logs)
    if from_log and logs:
        # Clear only the selected logs
        try:
            if ':' in from_log:
                start, end = map(int, from_log.split(':'))
                # Validate range before clearing
                if start < 0:
                    click.echo(f"Error: Start index must be >= 0, got {start}", err=True)
                    sys.exit(1)
                if end < start:
                    click.echo(f"Error: End index must be >= start, got end={end}, start={start}", err=True)
                    sys.exit(1)
                if start > logs_before_clear:
                    click.echo(f"Error: Start index {start} is out of bounds (only {logs_before_clear} logs available)", err=True)
                    sys.exit(1)
                
                clear_logs_range(current_branch, start, end)
                if verbose:
                    # Calculate actual cleared count
                    actual_end = min(end, logs_before_clear)
                    cleared_count = actual_end - start
                    click.echo(f"Cleared {cleared_count} log entries that were included in commit")
            else:
                count = int(from_log)
                if count <= 0:
                    click.echo(f"Error: Count must be > 0, got {count}", err=True)
                    sys.exit(1)
                if count > logs_before_clear:
                    click.echo(f"Warning: Requested {count} logs but only {logs_before_clear} available. Clearing all.", err=True)
                
                clear_logs_count(current_branch, count)
                if verbose:
                    cleared_count = min(count, logs_before_clear)
                    click.echo(f"Cleared {cleared_count} log entries that were included in commit")
        except ValueError as e:
            # Handle validation errors from clear functions
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    elif logs:
        # Clear all logs since they were all included in the commit
        clear_all_logs(current_branch)
        if verbose:
            click.echo(f"Cleared {logs_before_clear} log entries (included in commit)")
    
    if verbose:
        click.echo(f"Created commit: {commit_entry.commit_id}")
    else:
        click.echo(f"Commit created: {commit_entry.commit_id}")
    
    # Optionally create git commit (only if --git-commit flag is set)
    if git_commit:
        try:
            subprocess.run(['git', 'add', '.context/'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', f'Context commit: {commit_entry.commit_id}'], 
                          check=True, capture_output=True)
            if verbose:
                click.echo("Git commit created successfully")
        except FileNotFoundError:
            click.echo("Error: Git is not installed or not in PATH", err=True)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            click.echo(f"Error: Git commit failed (exit code {e.returncode}). Are you in a git repository?", err=True)
            sys.exit(1)


@cli.command()
@click.argument('reasoning_step', required=True)
@click.pass_context
def log(ctx, reasoning_step):
    """Add a reasoning step to the current branch's log"""
    verbose = ctx.obj['verbose']
    
    # Get current branch
    current_branch = get_current_branch()
    if not current_branch:
        click.echo("Error: No current branch. Create a branch first with 'context branch <name>'.", err=True)
        sys.exit(1)
    
    if verbose:
        click.echo(f"Current branch: {current_branch}")
    
    # Create log entry
    log_entry = LogEntry(
        timestamp=get_current_timestamp(),
        reasoning_step=reasoning_step
    )
    
    # Validate log entry
    is_valid, error = validate_log_entry(log_entry)
    if not is_valid:
        click.echo(f"Error: Invalid log entry: {error}", err=True)
        sys.exit(1)
    
    # Append log
    append_log(current_branch, log_entry)
    
    if verbose:
        click.echo(f"Added log entry to branch '{current_branch}' at {log_entry.timestamp}")
    else:
        click.echo(f"Log entry added to branch '{current_branch}'")


@cli.command()
@click.argument('name')
@click.option('--from', 'source_branch', help='Copy context from this branch')
@click.option('--empty', is_flag=True, help='Create empty branch')
@click.pass_context
def branch(ctx, name, source_branch, empty):
    """Create a new branch"""
    verbose = ctx.obj['verbose']
    
    # Validate branch name
    if not validate_branch_name(name):
        click.echo(f"Error: Invalid branch name: {name}", err=True)
        sys.exit(1)
    
    # Check if branch already exists
    if branch_exists(name):
        click.echo(f"Error: Branch '{name}' already exists", err=True)
        sys.exit(1)
    
    # Determine source branch
    if not source_branch and not empty:
        source_branch = get_current_branch()
        if not source_branch:
            click.echo("Error: No current branch. Use --empty to create a new branch or specify --from.", err=True)
            sys.exit(1)
    
    # Create branch directory
    create_branch_directory(name)
    
    if empty:
        # Create empty branch
        initialize_branch_files(name, empty=True)
        if verbose:
            click.echo(f"Created empty branch: {name}")
    else:
        # Copy from source branch
        if not branch_exists(source_branch):
            click.echo(f"Error: Source branch '{source_branch}' does not exist", err=True)
            sys.exit(1)
        
        copy_branch_files(source_branch, name)
        if verbose:
            click.echo(f"Created branch '{name}' from '{source_branch}'")
    
    # Set as current branch
    set_current_branch(name)
    click.echo(f"Branch '{name}' created and set as current")


@cli.command()
@click.argument('branches', nargs=-1, required=True)
@click.option('--git-commit', is_flag=True, help='Also create a git commit (disabled by default)')
@click.pass_context
def merge(ctx, branches, git_commit):
    """Merge context from one or more branches into the current branch"""
    verbose = ctx.obj['verbose']
    
    # Get current branch
    current_branch = get_current_branch()
    if not current_branch:
        click.echo("Error: No current branch. Create a branch first with 'context branch <name>'.", err=True)
        sys.exit(1)
    
    if verbose:
        click.echo(f"Merging into branch: {current_branch}")
    
    # Validate source branches
    for branch_name in branches:
        if not branch_exists(branch_name):
            click.echo(f"Error: Branch '{branch_name}' does not exist", err=True)
            sys.exit(1)
        if branch_name == current_branch:
            click.echo(f"Error: Cannot merge branch into itself", err=True)
            sys.exit(1)
    
    # Read current branch data
    current_commits = read_commits(current_branch)
    current_logs = read_logs(current_branch)
    current_metadata = read_metadata(current_branch)
    
    # Merge each source branch
    merged_branches = []
    for source_branch in branches:
        if verbose:
            click.echo(f"Merging from branch: {source_branch}")
        
        # Read source branch data
        source_commits = read_commits(source_branch)
        source_logs = read_logs(source_branch)
        source_metadata = read_metadata(source_branch)
        
        # Find divergence point and unique commits
        common_commits, unique_to_current, unique_to_source = compare_commits(
            current_commits, source_commits
        )
        
        # Add unique commits from source (after divergence point)
        for commit in unique_to_source:
            # Tag commit with source branch
            commit.branch_purpose = f"{commit.branch_purpose} [merged from {source_branch}]"
            current_commits.append(commit)
        
        # Create merge commit entry
        branch_purpose = current_commits[0].branch_purpose if current_commits else "Merged branch"
        if not current_commits:
            # If no commits in current branch, use source branch's purpose
            branch_purpose = source_commits[0].branch_purpose if source_commits else "Merged branch"
        
        merge_commit = CommitEntry(
            commit_id=generate_commit_id(),
            branch_purpose=branch_purpose,
            previous_progress=f"Merged branch '{source_branch}' into '{current_branch}'",
            commit_contribution=f"Merged {len(unique_to_source)} commits from branch '{source_branch}'",
            timestamp=get_current_timestamp()
        )
        current_commits.append(merge_commit)
        
        # Merge logs with origin tags
        for log in source_logs:
            # Check if log already exists (by timestamp and content)
            if not any(l.timestamp == log.timestamp and l.reasoning_step == log.reasoning_step 
                      for l in current_logs):
                log.source_branch = source_branch
                current_logs.append(log)
        
        # Merge metadata (simple merge - current takes precedence)
        if source_metadata.file_structure:
            current_metadata.file_structure.update(source_metadata.file_structure)
        if source_metadata.env_config:
            current_metadata.env_config.update(source_metadata.env_config)
        current_metadata.custom_entries.update(source_metadata.custom_entries)
        
        merged_branches.append(source_branch)
    
    # Write merged data
    write_commits(current_branch, current_commits)
    write_logs(current_branch, current_logs)
    write_metadata(current_branch, current_metadata)
    
    # Update main.md with merge summary
    main_content = read_main_md()
    merge_summary = f"\n## Merge Summary\n\nMerged branches: {', '.join(merged_branches)} into {current_branch}\n"
    main_content += merge_summary
    write_main_md(main_content)
    
    click.echo(f"Successfully merged {len(branches)} branch(es) into '{current_branch}'")
    
    # Optionally create git commit (only if --git-commit flag is set)
    if git_commit:
        try:
            subprocess.run(['git', 'add', '.context/'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', f'Context merge: {", ".join(merged_branches)} into {current_branch}'], 
                          check=True, capture_output=True)
            if verbose:
                click.echo("Git commit created successfully")
        except FileNotFoundError:
            click.echo("Error: Git is not installed or not in PATH", err=True)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            click.echo(f"Error: Git commit failed (exit code {e.returncode}). Are you in a git repository?", err=True)
            sys.exit(1)


@cli.command()
@click.option('--level', type=click.Choice(['project', 'branch', 'session'], case_sensitive=False), 
              default='project', help='Information level to display')
@click.option('--branch', 'branch_name', help='Branch name (for branch/session level)')
@click.option('--format', type=click.Choice(['markdown', 'yaml', 'text'], case_sensitive=False),
              default='text', help='Output format')
@click.pass_context
def info(ctx, level, branch_name, format):
    """Get project information at different levels"""
    verbose = ctx.obj['verbose']
    
    if level == 'project':
        # Project-level info
        main_content = read_main_md()
        branches = list_branches()
        current_branch = get_current_branch()
        
        if format == 'markdown':
            click.echo(main_content)
            click.echo(f"\n## Branches\n\nCurrent: {current_branch or 'None'}\n")
            for branch in branches:
                click.echo(f"- {branch}")
        elif format == 'yaml':
            import yaml
            data = {
                'main': main_content,
                'branches': branches,
                'current_branch': current_branch
            }
            click.echo(yaml.dump(data, default_flow_style=False))
        else:  # text
            click.echo("=== Project Information ===\n")
            click.echo(main_content)
            click.echo(f"\nBranches: {', '.join(branches) if branches else 'None'}")
            click.echo(f"Current branch: {current_branch or 'None'}")
    
    elif level == 'branch':
        # Branch-level info
        target_branch = branch_name or get_current_branch()
        if not target_branch:
            click.echo("Error: No branch specified and no current branch", err=True)
            sys.exit(1)
        
        if not branch_exists(target_branch):
            click.echo(f"Error: Branch '{target_branch}' does not exist", err=True)
            sys.exit(1)
        
        commits = read_commits(target_branch)
        metadata = read_metadata(target_branch)
        
        if format == 'markdown':
            click.echo(f"# Branch: {target_branch}\n")
            click.echo(f"Commits: {len(commits)}\n")
            for commit in commits:
                click.echo(commit.to_markdown())
        elif format == 'yaml':
            import yaml
            data = {
                'branch': target_branch,
                'commit_count': len(commits),
                'commits': [c.to_dict() for c in commits],
                'metadata': metadata.to_dict()
            }
            click.echo(yaml.dump(data, default_flow_style=False))
        else:  # text
            click.echo(f"=== Branch: {target_branch} ===\n")
            click.echo(f"Commits: {len(commits)}")
            if commits:
                click.echo(f"Branch Purpose: {commits[0].branch_purpose}")
                click.echo(f"\nRecent commits:")
                for commit in commits[-5:]:  # Show last 5
                    click.echo(f"  - {commit.commit_id}: {commit.commit_contribution[:50]}...")
    
    elif level == 'session':
        # Session-level info
        target_branch = branch_name or get_current_branch()
        if not target_branch:
            click.echo("Error: No branch specified and no current branch", err=True)
            sys.exit(1)
        
        if not branch_exists(target_branch):
            click.echo(f"Error: Branch '{target_branch}' does not exist", err=True)
            sys.exit(1)
        
        logs = read_logs(target_branch)
        
        if format == 'markdown':
            click.echo(f"# Session Log: {target_branch}\n")
            for log in logs:
                click.echo(log.to_markdown())
        elif format == 'yaml':
            import yaml
            data = {
                'branch': target_branch,
                'log_count': len(logs),
                'logs': [l.to_dict() for l in logs]
            }
            click.echo(yaml.dump(data, default_flow_style=False))
        else:  # text
            click.echo(f"=== Session Log: {target_branch} ===\n")
            click.echo(f"Log entries: {len(logs)}\n")
            for log in logs[-10:]:  # Show last 10
                click.echo(f"[{log.timestamp}] {log.reasoning_step[:100]}...")
                if log.source_branch:
                    click.echo(f"  (from {log.source_branch})")


def main():
    """Entry point for the CLI"""
    cli(auto_envvar_prefix='CONTEXT')


if __name__ == '__main__':
    main()

