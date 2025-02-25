# Oneshots

A collection of self-contained Python utility scripts.

## About

This repository contains standalone Python scripts that each solve a specific task. Each script is completely self-contained with its own dependencies managed through `uv`.

The repo includes `install_links.py` to easily make all scripts available on your PATH as commands without the .py extension.

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

### Adding to PATH

To make all scripts available as commands without the .py extension:

```bash
# Run the installer (creates symlinks in ~/.local/bin)
./install_links.py

# Now you can run any script from anywhere
hello
rename-files --help
aws_config_merge --help
```

Use `--dry-run` to preview changes and `--force` to recreate existing links.

## Available Scripts

- `hello.py` - A simple "Hello World" CLI demo
- `rename_files.py` - Utility to batch rename files based on a pattern
- `aws_config_merge.py` - Tool to merge AWS configuration files
- `install_links.py` - Makes scripts available on your PATH

## Development

All scripts have corresponding test files that can be run directly:

```bash
./test_script.py
```

See CLAUDE.md for more details about coding standards and practices used in this repository.
