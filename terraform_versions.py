#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "colorama",
# ]
# ///

import click
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

class TerraformFile:
    def __init__(self, path):
        self.path = Path(path)
        self.content = self.path.read_text()
        self.modified = False
        self.backup_path = None

    def backup(self):
        """Create a backup of the file"""
        backup_path = self.path.with_suffix(f"{self.path.suffix}.backup")
        shutil.copy2(self.path, backup_path)
        self.backup_path = backup_path
        return backup_path

    def update_terraform_version(self, version_constraint):
        """Update the Terraform required_version constraint"""
        pattern = r'(required_version\s*=\s*)"([^"]+)"'
        replacement = fr'\1"{version_constraint}"'
        new_content = re.sub(pattern, replacement, self.content)
        if new_content != self.content:
            self.content = new_content
            self.modified = True
            return True
        return False

    def update_provider_version(self, provider_name, version_constraint):
        """Update the provider version constraint"""
        # Pattern for standard provider block format
        pattern = fr'({provider_name}\s*=\s*\{{[^}}]*version\s*=\s*)"([^"]+)"([^}}]*\}})'
        replacement = fr'\1"{version_constraint}"\3'

        new_content = re.sub(pattern, replacement, self.content, flags=re.DOTALL)
        if new_content != self.content:
            self.content = new_content
            self.modified = True
            return True
        return False

    def save(self):
        """Save changes to the file"""
        if self.modified:
            self.path.write_text(self.content)
            return True
        return False

def is_inside_terraform_dir(path):
    """Check if a path is inside a .terraform directory"""
    return '.terraform' in path.parts

def find_terraform_files(path, recursive=False):
    """Find all .tf files in the given path, excluding those inside .terraform directories"""
    path = Path(path)
    if recursive:
        all_files = path.glob('**/*.tf')
        return [f for f in all_files if not is_inside_terraform_dir(f)]
    else:
        return [f for f in path.glob('*.tf') if not is_inside_terraform_dir(f)]

def find_lock_files(path, recursive=False):
    """Find all .terraform.lock.hcl files in the given path, excluding those inside .terraform directories"""
    path = Path(path)
    if recursive:
        all_files = path.glob('**/.terraform.lock.hcl')
        return [f for f in all_files if not is_inside_terraform_dir(f)]
    else:
        # For non-recursive mode, we still need to look in immediate subdirectories for lock files
        return [f for f in path.glob('*/.terraform.lock.hcl') if not is_inside_terraform_dir(f)]

def find_terraform_modules(path, recursive=False):
    """Find directories containing .tf files, excluding .terraform directories"""
    tf_files = find_terraform_files(path, recursive)
    # Get unique parent directories
    return set(file.parent for file in tf_files)

def find_terraform_dirs(path, recursive=False):
    """Find .terraform directories in the given path"""
    path = Path(path)
    if recursive:
        # Searching for .terraform directories
        return list(path.glob('**/.terraform'))
    else:
        # For non-recursive mode, look in the current directory and immediate subdirectories
        dirs = list(path.glob('.terraform'))
        dirs.extend(path.glob('*/.terraform'))
        return dirs

def has_lock_file(dir_path):
    """Check if a directory has a .terraform.lock.hcl file"""
    lock_file = dir_path / ".terraform.lock.hcl"
    return lock_file.exists()

def run_terraform_command(command, cwd=None, capture_output=True):
    """Run a terraform command and return the result"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return True, result.stdout if capture_output else ""
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}" if capture_output else f"Error: Command failed with code {e.returncode}"

def validate_terraform_file(file_path):
    """Validate a Terraform file using terraform validate"""
    cwd = file_path.parent
    success, output = run_terraform_command(["terraform", "fmt", "-check", file_path.name], cwd=cwd)
    return success

@click.group()
def cli():
    """Terraform version updater and lock file manager."""
    pass

@cli.command()
@click.option('--path', '-p', default='.', help='Path to the Terraform files directory')
@click.option('--recursive', '-r', is_flag=True, help='Search for Terraform files recursively')
@click.option('--tf-version', default='>= 1.7.0', help='Terraform version constraint to use')
@click.option('--aws-version', default='>= 5.70.0', help='AWS provider version constraint to use')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying them')
@click.option('--backup', is_flag=True, help='Create backups before making changes')
@click.option('--validate', is_flag=True, help='Validate files after modification')
def update(path, recursive, tf_version, aws_version, dry_run, backup, validate):
    """Update Terraform version constraints in .tf files."""
    tf_files = find_terraform_files(path, recursive)

    if not tf_files:
        click.echo(f"{Fore.YELLOW}No Terraform files found in {path}" +
                  (f" and its subdirectories" if recursive else ""))
        return

    click.echo(f"{Fore.CYAN}Found {len(tf_files)} Terraform files")

    modified_files = []

    for file_path in tf_files:
        try:
            tf_file = TerraformFile(file_path)
            terraform_updated = tf_file.update_terraform_version(tf_version)
            aws_updated = tf_file.update_provider_version("aws", aws_version)

            if terraform_updated or aws_updated:
                if dry_run:
                    click.echo(f"{Fore.GREEN}Would update: {file_path}")
                    continue

                if backup:
                    backup_path = tf_file.backup()
                    click.echo(f"{Fore.BLUE}Created backup: {backup_path}")

                tf_file.save()
                modified_files.append(file_path)

                updates = []
                if terraform_updated:
                    updates.append(f"Terraform version to {tf_version}")
                if aws_updated:
                    updates.append(f"AWS provider version to {aws_version}")

                click.echo(f"{Fore.GREEN}Updated {file_path}: {', '.join(updates)}")

                if validate:
                    if validate_terraform_file(file_path):
                        click.echo(f"{Fore.GREEN}✓ Validation passed for {file_path}")
                    else:
                        click.echo(f"{Fore.RED}✗ Validation failed for {file_path}")

        except Exception as e:
            click.echo(f"{Fore.RED}Error processing {file_path}: {str(e)}")

    click.echo(f"{Fore.CYAN}Summary: Modified {len(modified_files)} files")

@cli.command()
@click.option('--path', '-p', default='.', help='Path to the Terraform files directory')
@click.option('--recursive', '-r', is_flag=True, help='Search for lock files recursively')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying them')
@click.option('--backup', is_flag=True, help='Create backups before deletion')
@click.confirmation_option(prompt='Are you sure you want to remove the lock files?')
def clean_locks(path, recursive, dry_run, backup):
    """Remove Terraform lock files."""
    lock_files = find_lock_files(path, recursive)

    if not lock_files:
        click.echo(f"{Fore.YELLOW}No lock files found in {path}" +
                  (f" and its subdirectories" if recursive else ""))
        return

    click.echo(f"{Fore.CYAN}Found {len(lock_files)} lock files")

    removed_files = []

    for file_path in lock_files:
        try:
            if dry_run:
                click.echo(f"{Fore.GREEN}Would remove: {file_path}")
                continue

            if backup:
                backup_path = file_path.with_suffix('.hcl.backup')
                shutil.copy2(file_path, backup_path)
                click.echo(f"{Fore.BLUE}Created backup: {backup_path}")

            file_path.unlink()
            removed_files.append(file_path)
            click.echo(f"{Fore.GREEN}Removed: {file_path}")

        except Exception as e:
            click.echo(f"{Fore.RED}Error removing {file_path}: {str(e)}")

    click.echo(f"{Fore.CYAN}Summary: Removed {len(removed_files)} lock files")

@cli.command()
@click.option('--path', '-p', default='.', help='Path to search for .terraform directories')
@click.option('--recursive', '-r', is_flag=True, help='Search for directories recursively')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying them')
@click.confirmation_option(prompt='Are you sure you want to remove the .terraform directories?')
def clean_dirs(path, recursive, dry_run):
    """Remove .terraform directories."""
    tf_dirs = find_terraform_dirs(path, recursive)

    if not tf_dirs:
        click.echo(f"{Fore.YELLOW}No .terraform directories found in {path}" +
                  (f" and its subdirectories" if recursive else ""))
        return

    click.echo(f"{Fore.CYAN}Found {len(tf_dirs)} .terraform directories")

    removed_dirs = []
    failed_dirs = []

    for dir_path in tf_dirs:
        try:
            if dry_run:
                click.echo(f"{Fore.GREEN}Would remove: {dir_path}")
                continue

            # Calculate directory size before removal
            total_size = sum(f.stat().st_size for f in dir_path.glob('**/*') if f.is_file())
            size_mb = total_size / (1024 * 1024)

            # Remove the directory
            shutil.rmtree(dir_path)

            removed_dirs.append((dir_path, size_mb))
            click.echo(f"{Fore.GREEN}Removed: {dir_path} ({size_mb:.2f} MB)")

        except Exception as e:
            failed_dirs.append((dir_path, str(e)))
            click.echo(f"{Fore.RED}Error removing {dir_path}: {str(e)}")

    # Print summary
    click.echo(f"\n{Fore.CYAN}Summary:")

    total_size_removed = sum(size for _, size in removed_dirs)
    click.echo(f"{Fore.GREEN}Successfully removed {len(removed_dirs)} directories ({total_size_removed:.2f} MB total)")

    if failed_dirs:
        click.echo(f"{Fore.RED}Failed to remove {len(failed_dirs)} directories")
        for dir_path, error in failed_dirs:
            click.echo(f"{Fore.RED}  - {dir_path}: {error}")

@cli.command()
@click.option('--path', '-p', default='.', help='Path to Terraform root modules')
@click.option('--recursive', '-r', is_flag=True, help='Search for Terraform modules recursively')
@click.option('--platforms', default="darwin_amd64,darwin_arm64,linux_amd64,windows_amd64",
              help='Comma-separated list of platforms to lock')
@click.option('--force', '-f', is_flag=True, help='Force regeneration even if lock files already exist')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed error messages')
def regen_locks(path, recursive, platforms, force, verbose):
    """Regenerate Terraform lock files with specific platforms."""
    # Convert path to absolute path
    path = Path(path).absolute()

    # Find directories containing .tf files
    tf_dirs = find_terraform_modules(path, recursive)

    if not tf_dirs:
        click.echo(f"{Fore.YELLOW}No Terraform module directories found in {path}" +
                  (f" and its subdirectories" if recursive else ""))
        return

    click.echo(f"{Fore.CYAN}Found {len(tf_dirs)} Terraform module directories")

    # Create platform arguments for the terraform providers lock command
    platform_list = platforms.split(',')
    platform_args = []
    for p in platform_list:
        platform_args.extend(["-platform", p.strip()])

    successful_dirs = []
    skipped_dirs = []
    failed_dirs = []

    for dir_path in tf_dirs:
        # Check if lockfile exists and decide whether to process this directory
        if has_lock_file(dir_path) and not force:
            skipped_dirs.append(dir_path)
            click.echo(f"{Fore.YELLOW}Skipping {dir_path}: Lock file already exists (use --force to override)")
            continue

        click.echo(f"{Fore.CYAN}Processing: {dir_path}")

        # Run terraform providers lock with the specified platforms
        command = ["terraform", "providers", "lock"]
        command.extend(platform_args)

        click.echo(f"{Fore.BLUE}Running: {' '.join(command)}")
        success, output = run_terraform_command(command, cwd=dir_path, capture_output=True)

        if success:
            successful_dirs.append(dir_path)
            click.echo(f"{Fore.GREEN}Successfully regenerated lock file in {dir_path}")
            if verbose and output.strip():
                click.echo(f"{Fore.GREEN}Output: \n{output.strip()}")
        else:
            # Show the error output if verbose mode is enabled
            if verbose:
                click.echo(f"{Fore.RED}Error output: \n{output}")

            click.echo(f"{Fore.YELLOW}Failed to regenerate lock file. Trying to initialize first...")

            # Try initialization with verbose output if requested
            success_init, output_init = run_terraform_command(["terraform", "init", "-backend=false"], cwd=dir_path, capture_output=True)

            if not success_init:
                failed_dirs.append((dir_path, f"Initialization failed: {output_init}"))
                click.echo(f"{Fore.RED}Failed to initialize Terraform in {dir_path}")
                if verbose:
                    click.echo(f"{Fore.RED}Initialization error output: \n{output_init}")
                continue

            # Show initialization output if verbose
            if verbose and output_init.strip():
                click.echo(f"{Fore.GREEN}Initialization output: \n{output_init.strip()}")

            # Try again after initialization
            success_retry, output_retry = run_terraform_command(command, cwd=dir_path, capture_output=True)

            if success_retry:
                successful_dirs.append(dir_path)
                click.echo(f"{Fore.GREEN}Successfully regenerated lock file in {dir_path} after initialization")
                if verbose and output_retry.strip():
                    click.echo(f"{Fore.GREEN}Output: \n{output_retry.strip()}")
            else:
                failed_dirs.append((dir_path, output_retry))
                click.echo(f"{Fore.RED}Failed to regenerate lock file in {dir_path} even after initialization")
                if verbose:
                    click.echo(f"{Fore.RED}Error output: \n{output_retry}")

    # Print summary
    click.echo(f"\n{Fore.CYAN}Summary:")
    click.echo(f"{Fore.GREEN}Successfully regenerated lock files in {len(successful_dirs)} directories")
    click.echo(f"{Fore.YELLOW}Skipped {len(skipped_dirs)} directories with existing lock files")
    if failed_dirs:
        click.echo(f"{Fore.RED}Failed to regenerate lock files in {len(failed_dirs)} directories")
        for dir_path, error in failed_dirs[:5]:  # Show first 5 errors to avoid overwhelming output
            error_summary = error.split('\n')[0] if '\n' in error else error
            click.echo(f"{Fore.RED}  - {dir_path}: {error_summary}")

        if len(failed_dirs) > 5:
            click.echo(f"{Fore.RED}  ... and {len(failed_dirs) - 5} more (use --verbose for full error details)")

@cli.command()
@click.option('--path', '-p', default='.', help='Path to the Terraform files directory')
@click.option('--recursive', '-r', is_flag=True, help='Search recursively')
@click.option('--tf-version', default='>= 1.7.0', help='Terraform version constraint to use')
@click.option('--aws-version', default='>= 5.70.0', help='AWS provider version constraint to use')
@click.option('--backup', is_flag=True, help='Create backups before making changes')
@click.option('--platforms', default="darwin_amd64,darwin_arm64,linux_amd64,windows_amd64",
              help='Comma-separated list of platforms to lock')
@click.option('--force-regen', is_flag=True, help='Force regeneration of lock files even if they already exist')
@click.option('--clean-tf-dirs', is_flag=True, help='Also clean .terraform directories')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed command output and error messages')
@click.confirmation_option(prompt='This will update version constraints, remove lock files, and regenerate them. Continue?')
def run_all(path, recursive, tf_version, aws_version, backup, platforms, force_regen, clean_tf_dirs, verbose):
    """Execute all steps: update versions, clean .terraform directories (optional), clean locks, and regenerate locks."""
    click.echo(f"{Fore.CYAN}Step 1: Updating version constraints")
    ctx = click.Context(update, info_name='update')
    update.callback(path, recursive, tf_version, aws_version, False, backup, False)

    if clean_tf_dirs:
        click.echo(f"\n{Fore.CYAN}Step 2: Cleaning .terraform directories")
        ctx = click.Context(clean_dirs, info_name='clean-dirs')
        clean_dirs.callback(path, recursive, False)

    click.echo(f"\n{Fore.CYAN}Step {'3' if clean_tf_dirs else '2'}: Cleaning lock files")
    ctx = click.Context(clean_locks, info_name='clean-locks')
    clean_locks.callback(path, recursive, False, backup)

    click.echo(f"\n{Fore.CYAN}Step {'4' if clean_tf_dirs else '3'}: Regenerating lock files")
    ctx = click.Context(regen_locks, info_name='regen-locks')
    regen_locks.callback(path, recursive, platforms, force_regen, verbose)

    click.echo(f"\n{Fore.GREEN}All steps completed!")

if __name__ == '__main__':
    cli()
