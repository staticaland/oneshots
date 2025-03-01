.PHONY: format lint test all

format:
	uvx ruff format .

lint:
	uvx ruff check --select I --fix .

test:
	./test_rename_files.py
	./test_hello.py

all: format lint test
