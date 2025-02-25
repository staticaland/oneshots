# Oneshots

A collection of self-contained Python utility scripts.

## About

This repository contains standalone Python scripts that each solve a specific task. Each script is completely self-contained with its own dependencies managed through `uv`.

99% of the code is written by [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview).

## How it works

Every script in this repo follows the same pattern:

1. A shebang line that uses `uv run --script` to execute the script
2. A script metadata section that specifies Python version and dependencies
3. The actual script code

Example:

```python
#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "requests",
# ]
# ///

# Your script code here...
```

## Usage

Scripts can be run directly after making them executable:

```bash
# Make script executable (first time only)
chmod +x script.py

# Run the script
./script.py
```

Alternatively, you can run them using `uv`:

```bash
uv run script.py
```

## Available Scripts

- `hello.py` - A simple "Hello World" CLI demo
- `rename_files.py` - Utility to batch rename files based on a pattern

## Development

All scripts have corresponding test files that can be run directly:

```bash
./test_script.py
```

See CLAUDE.md for more details about coding standards and practices used in this repository.
