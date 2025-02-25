#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "pytest",
# ]
# ///

import os
import sys
import pytest
from pathlib import Path
from click.testing import CliRunner
from rename_files import rename_files


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory with test files."""
    # Create test files
    test_files = [
        "test_old_file1.txt",
        "test_old_file2.txt",
        "other_file.txt",
        "test_old_file.pdf",
    ]

    for filename in test_files:
        (tmp_path / filename).touch()

    return tmp_path


def test_rename_files_dry_run(temp_dir):
    """Test dry run mode doesn't change files."""
    runner = CliRunner()
    result = runner.invoke(
        rename_files, ["old", "new", "-d", str(temp_dir), "--dry-run"]
    )

    assert result.exit_code == 0
    assert "Would rename: test_old_file1.txt → test_new_file1.txt" in result.output
    assert "Would rename: test_old_file2.txt → test_new_file2.txt" in result.output
    assert "Would rename: test_old_file.pdf → test_new_file.pdf" in result.output

    # Verify files weren't actually renamed
    assert (temp_dir / "test_old_file1.txt").exists()
    assert (temp_dir / "test_old_file2.txt").exists()
    assert (temp_dir / "test_old_file.pdf").exists()
    assert not (temp_dir / "test_new_file1.txt").exists()


def test_rename_files_actual_run(temp_dir):
    """Test actual renaming in a temporary directory."""
    runner = CliRunner()
    result = runner.invoke(rename_files, ["old", "new", "-d", str(temp_dir)])

    assert result.exit_code == 0
    assert "Renamed: test_old_file1.txt → test_new_file1.txt" in result.output
    assert "Renamed: test_old_file2.txt → test_new_file2.txt" in result.output
    assert "Renamed: test_old_file.pdf → test_new_file.pdf" in result.output

    # Verify files were renamed
    assert not (temp_dir / "test_old_file1.txt").exists()
    assert not (temp_dir / "test_old_file2.txt").exists()
    assert not (temp_dir / "test_old_file.pdf").exists()
    assert (temp_dir / "test_new_file1.txt").exists()
    assert (temp_dir / "test_new_file2.txt").exists()
    assert (temp_dir / "test_new_file.pdf").exists()

    # Verify untouched files
    assert (temp_dir / "other_file.txt").exists()


def test_rename_files_file_extension(temp_dir):
    """Test changing file extensions."""
    runner = CliRunner()
    result = runner.invoke(rename_files, [".txt", ".md", "-d", str(temp_dir)])

    assert result.exit_code == 0
    assert "Renamed: test_old_file1.txt → test_old_file1.md" in result.output
    assert "Renamed: test_old_file2.txt → test_old_file2.md" in result.output
    assert "Renamed: other_file.txt → other_file.md" in result.output

    # Verify extensions were changed
    assert not (temp_dir / "test_old_file1.txt").exists()
    assert (temp_dir / "test_old_file1.md").exists()
    assert (temp_dir / "test_old_file.pdf").exists()  # Unchanged


def test_invalid_directory():
    """Test behavior with invalid directory."""
    runner = CliRunner()
    result = runner.invoke(
        rename_files, ["old", "new", "-d", "/nonexistent_directory_12345"]
    )

    assert result.exit_code == 0
    assert (
        "Error: /nonexistent_directory_12345 is not a valid directory" in result.output
    )


if __name__ == "__main__":
    # Run pytest when this script is executed directly
    sys.exit(pytest.main(["-v", __file__]))
