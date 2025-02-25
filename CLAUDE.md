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

## Build Commands

- Preferred: Make script executable and run directly: `chmod +x <script.py>` then `./<script.py>`
- Alternative: `uv run <name of python file>`

## Test Commands

- Add test runner commands once testing framework is established.

## Lint Commands

- Add linting commands when a linter is configured.

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
