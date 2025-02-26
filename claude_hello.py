#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anthropic",
#     "click",
# ]
# ///

import click
from anthropic import Anthropic


@click.command()
@click.option("--name", default="Claude", help="Name to greet in the message")
@click.option("--model", default="claude-3-5-haiku-latest", help="Claude model to use")
def hello(name, model):
    """Send a greeting to Claude and get a response."""
    client = Anthropic()  # Uses ANTHROPIC_API_KEY from environment by default

    message = client.messages.create(
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"Hello, {name}",
            }
        ],
        model=model,
    )
    print(message.content)


if __name__ == "__main__":
    hello()
