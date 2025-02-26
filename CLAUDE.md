# CLAUDE.md

## Python Script Structure

Each script starts with this header:

```
#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# ///
```

When dependencies are needed, include them in the header:

```
#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "sqlite-utils",
# ]
# ///
```

Command-line interface (CLI) tools should accept standard input (stdin) by default whenever this functionality is appropriate for the tool's purpose.

## Build Commands

- Preferred: Make script executable and run directly: `chmod +x <script.py>` then `./<script.py>`
- Alternative: `uv run <name of python file>`

## Test Commands

Testing with pytest:

```
pytest                               # Run all tests
pytest test_filename.py              # Run tests in a specific file
pytest test_filename.py::test_func   # Run a specific test function
pytest -v                            # Run tests with verbose output
pytest -k "keyword"                  # Run tests containing keyword in name
```

Testing approaches:

Unit testing functions:

- Test pure functions with various inputs and expected outputs
- Use fixtures to set up test data
- Use parametrize to run same test with different inputs

Testing Click applications:

- Use CliRunner to simulate CLI commands
- Check exit codes and command output
- Test with various command-line options

Integration testing:

- Test interactions between components
- Use tmp_path fixture for file operations
- Mock external dependencies as needed

## Lint Commands

Linting with Ruff:

```
ruff check                          # Lint all files in the current directory (and subdirectories)
ruff check path/to/code/            # Lint all files in a specific directory (and subdirectories)
ruff check path/to/code/*.py        # Lint all .py files in a specific directory
ruff check path/to/code/to/file.py  # Lint a specific file
ruff check --fix                    # Lint files and fix any fixable errors
```

Formatting with Ruff (Python files):

```
ruff format                          # Format all files in the current directory (and subdirectories)
ruff format path/to/code/            # Format all files in a specific directory (and subdirectories)
ruff format path/to/code/*.py        # Format all .py files in a specific directory
ruff format path/to/code/to/file.py  # Format a specific file
```

Formatting with Prettier (Markdown files):

```
prettier --write *.md               # Format all Markdown files in the current directory
prettier --write path/to/*.md       # Format all Markdown files in a specific directory
prettier --write path/to/file.md    # Format a specific Markdown file
```

## Code Style Guidelines

- Format: Follow consistent indentation (4 spaces) and line length limits (88 chars)
- Naming: Use descriptive snake_case names for functions and variables
- Imports: Group imports by standard library, third-party, local. Sort alphabetically within groups
- Types: Use type hints for function parameters and return values
- Error handling: Use try/except blocks with specific exception types
- Comments: Write docstrings for modules and functions

## Project Organization

- Keep related files in the same directory
- Each tool should be a standalone Python file with proper uv header
- Follow established patterns when adding new code

## Version Control

- Use git CLI to commit changes: `git add <files>` then `git commit -m "message"`
- Follow conventional commits format:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `test:` for adding/modifying tests
  - `refactor:` for code changes that don't add features or fix bugs
  - `chore:` for maintenance tasks
- Write descriptive commit messages with a short summary line and detailed body

### Create PR with title and description

```sh
gh pr create --title "Your PR title" --body "Description of changes"
```

### Merging PRs

When merging pull requests:

- Use rebase merge if commits are well-structured and meaningful:
  ```sh
  gh pr merge --rebase
  ```
- Use squash merge if commits need cleanup or consolidation:
  ```sh
  gh pr merge --squash
  ```
