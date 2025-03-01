#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
# ]
# ///

import os
from pathlib import Path

import click


@click.command()
@click.option(
    "--target-dir",
    "-t",
    default="~/.local/bin",
    help="Target directory for symlinks (default: ~/.local/bin)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Override existing symlinks",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would be done without making changes",
)
def install_links(target_dir, force, dry_run):
    """Create symlinks to all executable Python scripts in this repo.

    Scripts will be linked without the .py extension for cleaner commands.
    Test files (starting with test_) are excluded.
    """
    # Get repo directory, resolving symlinks
    repo_dir = Path(os.path.realpath(__file__)).parent.resolve()

    # Expand target directory
    target_path = Path(os.path.expanduser(target_dir)).resolve()

    # Ensure target directory exists
    if not target_path.exists():
        click.echo(f"Creating directory: {target_path}")
        if not dry_run:
            target_path.mkdir(parents=True, exist_ok=True)

    # Check if target is in PATH
    if str(target_path) not in os.environ.get("PATH", ""):
        click.echo(f"Warning: {target_path} is not in your PATH.")
        click.echo(f'Add to your shell profile: export PATH="$PATH:{target_path}"')

    # Find all executable Python scripts (excluding tests)
    scripts = []
    for script in repo_dir.glob("*.py"):
        if (
            script.is_file()
            and os.access(script, os.X_OK)
            and not script.name.startswith("test_")
        ):
            scripts.append(script)

    if not scripts:
        click.echo("No executable Python scripts found")
        return

    installed = 0
    skipped = 0

    # Create symlinks
    for script in scripts:
        # Use script name without .py extension
        link_name = script.stem
        link_path = target_path / link_name

        if link_path.exists() and not force:
            click.echo(f"Skipping {link_name} (already exists)")
            skipped += 1
            continue

        if link_path.exists() and force:
            if dry_run:
                click.echo(f"Would remove existing symlink: {link_name}")
            else:
                link_path.unlink()

        try:
            if dry_run:
                click.echo(f"Would create symlink: {link_name} -> {script}")
                installed += 1
            else:
                link_path.symlink_to(script)
                click.echo(f"Created symlink: {link_name} -> {script}")
                installed += 1
        except Exception as e:
            click.echo(f"Error creating symlink for {link_name}: {e}")

    if dry_run:
        click.echo(
            f"\nDry run complete: would create {installed} symlinks, {skipped} skipped"
        )
    else:
        click.echo(f"\nComplete: {installed} symlinks created, {skipped} skipped")


if __name__ == "__main__":
    install_links()
