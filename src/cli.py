"""Command-line interface for context management system"""

import click
from . import commands


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Context Management System for AI Development Tools"""
    pass


@cli.command()
@click.argument('reasoning_step')
def log(reasoning_step):
    """Log a reasoning step (called by AI during its thought process)"""
    try:
        commands.log_command(reasoning_step=reasoning_step)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--message', '-m', help='Commit message/contribution description')
@click.option('--from-log', help='Extract commit contribution from log range (e.g., "last:5" or "all")')
def commit(message, from_log):
    """Checkpoint important points in chat session"""
    try:
        commands.commit_command(message=message, from_log_range=from_log)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('name')
@click.option('--from', 'from_branch', help='Source branch to copy from (defaults to current branch)')
@click.option('--empty', is_flag=True, help='Create empty branch (empty commits.yaml and log.yaml)')
def branch(name, from_branch, empty):
    """Create a new branch or switch to existing branch"""
    try:
        # Check if branch exists - if so, switch to it
        from . import filesystem
        if filesystem.branch_exists(name):
            filesystem.set_current_branch(name)
            click.echo(f"✓ Switched to branch '{name}'")
        else:
            # Create new branch
            commands.branch_command(branch_name=name, from_branch=from_branch, empty=empty)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('branches', nargs=-1, required=True)
def merge(branches):
    """Merge context from multiple branches into current branch"""
    try:
        commands.merge_command(source_branches=list(branches))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--level', type=click.Choice(['project', 'branch', 'session'], case_sensitive=False),
              default='project', help='Information level to display')
@click.option('--branch', 'branch_name', help='Branch name (required for branch/session levels)')
@click.option('--format', type=click.Choice(['markdown', 'yaml'], case_sensitive=False),
              default='markdown', help='Output format')
def info(level, branch_name, format):
    """Get project information at different levels"""
    try:
        commands.info_command(level=level.lower(), branch_name=branch_name, format=format.lower())
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


def main():
    """Entry point for the CLI"""
    cli()


if __name__ == '__main__':
    main()

