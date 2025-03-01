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
@click.argument("pattern", type=str)
@click.argument("replacement", type=str)
@click.option(
    "--dir",
    "-d",
    default=".",
    help="Directory containing files to rename (default: current directory)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Preview changes without actually renaming files",
)
def rename_files(pattern: str, replacement: str, dir: str, dry_run: bool) -> None:
    """
    Rename files by replacing PATTERN with REPLACEMENT in filenames.

    Examples:
        ./rename_files.py old new  # Replace 'old' with 'new' in all filenames
        ./rename_files.py .txt .md # Change file extension from .txt to .md
    """
    directory = Path(dir)
    if not directory.exists() or not directory.is_dir():
        click.echo(f"Error: {dir} is not a valid directory", err=True)
        return

    files = [f for f in directory.iterdir() if f.is_file()]
    if not files:
        click.echo(f"No files found in {dir}")
        return

    renamed = 0
    for file_path in files:
        if pattern in file_path.name:
            new_name = file_path.name.replace(pattern, replacement)
            new_path = file_path.parent / new_name

            if dry_run:
                click.echo(f"Would rename: {file_path.name} → {new_name}")
            else:
                try:
                    file_path.rename(new_path)
                    click.echo(f"Renamed: {file_path.name} → {new_name}")
                    renamed += 1
                except Exception as e:
                    click.echo(f"Error renaming {file_path.name}: {e}", err=True)

    if dry_run:
        click.echo(
            f"\nDry run complete. {len([f for f in files if pattern in f.name])} files would be renamed."
        )
    else:
        click.echo(f"\nRenamed {renamed} files.")


if __name__ == "__main__":
    rename_files()
