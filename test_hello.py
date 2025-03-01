#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "pytest",
# ]
# ///

import sys

import pytest
from click.testing import CliRunner

from hello import hello


def test_hello_default():
    """Test hello with default parameters."""
    runner = CliRunner()
    result = runner.invoke(hello)
    assert result.exit_code == 0
    assert "Hello World!" in result.output


def test_hello_with_name():
    """Test hello with custom name parameter."""
    runner = CliRunner()
    result = runner.invoke(hello, ["--name", "Claude"])
    assert result.exit_code == 0
    assert "Hello Claude!" in result.output


@pytest.mark.parametrize(
    "name,expected",
    [
        ("User", "Hello User!"),
        ("Python", "Hello Python!"),
        ("", "Hello !"),  # Empty name test
    ],
)
def test_hello_parametrized(name, expected):
    """Test hello with multiple name parameters."""
    runner = CliRunner()
    result = runner.invoke(hello, ["--name", name])
    assert result.exit_code == 0
    assert expected in result.output


if __name__ == "__main__":
    # Run pytest when this script is executed directly
    sys.exit(pytest.main(["-v", __file__]))
