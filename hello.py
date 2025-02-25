#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
# ]
# ///

import click

@click.command()
@click.option("--name", default="World", help="Who to greet")
def hello(name):
    """Simple CLI that prints a greeting message."""
    click.echo(f"Hello {name}!")

if __name__ == "__main__":
    hello()