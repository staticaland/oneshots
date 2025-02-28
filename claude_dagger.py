#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "dagger-io",
#     "click",
# ]
# ///

import sys
from typing import Optional

import anyio
import click
import dagger
from dagger import dag


async def run_toilet(text: str, font: Optional[str] = None) -> str:
    """Run toilet CLI program via Dagger to format text."""
    async with dagger.connection(dagger.Config(log_output=sys.stderr)):
        # Create a container with toilet installed
        container = (
            dag.container()
            .from_("ubuntu:22.04")
            .with_exec(["apt-get", "update"])
            .with_exec(["apt-get", "install", "-y", "toilet"])
        )

        # Build the command
        cmd = ["toilet"]
        if font:
            cmd.extend(["-f", font])
        cmd.append(text)

        # Run toilet command and capture the output
        result = container.with_exec(cmd)

        # Get the stdout from the command
        output = await result.stdout()

        return output


@click.command()
@click.argument("text")
@click.option("--font", "-f", help="Font to use for toilet program")
def main(text: str, font: Optional[str] = None) -> None:
    """Format TEXT using the toilet CLI program via Dagger.

    This tool uses Dagger to run the toilet program in a container
    and returns the formatted output.
    """
    result = anyio.run(run_toilet, text, font)
    print(result)


if __name__ == "__main__":
    main()
