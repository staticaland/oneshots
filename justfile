set dotenv-load

# Format the code with ruff
format:
    uvx ruff format .

# Fix import order issues with ruff
lint:
    uvx ruff check --select I --fix .

# Run pytest
test:
    ./test_rename_files.py
    ./test_hello.py

# Run all tasks: format, lint and test
all: format lint test
