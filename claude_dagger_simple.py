#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "dagger-io",
#     "anthropic",
#     "click",
# ]
# ///

import json
import sys
from typing import Any, Dict, List, Optional

import anyio
import click
import dagger
from anthropic import Anthropic

# Constants
DEFAULT_MODEL = "claude-3-7-sonnet-latest"
BASE_IMAGE = "ubuntu:22.04"


# Dagger utilities
async def _get_toilet_container(client: dagger.Client) -> dagger.Container:
    """Create a Dagger container with toilet installed."""
    return (
        client.container()
        .from_(BASE_IMAGE)
        .with_exec(["apt-get", "update"])
        .with_exec(["apt-get", "install", "-y", "toilet"])
    )


async def run_toilet(
    client: dagger.Client, text: str, font: Optional[str] = None
) -> str:
    """Format text using toilet CLI via Dagger."""
    container = await _get_toilet_container(client)
    cmd = ["toilet"]
    if font:
        cmd.extend(["-f", font])
    cmd.append(text)
    return await container.with_exec(cmd).stdout()


async def list_toilet_fonts(client: dagger.Client) -> List[str]:
    """List available toilet fonts via Dagger by checking font directory."""
    container = await _get_toilet_container(client)
    # List .tlf files in /usr/share/figlet/, strip path and extension
    output = await container.with_exec(["ls", "/usr/share/figlet"]).stdout()
    print("Raw font directory output:\n", output)  # Debug peek
    fonts = [
        f.strip().removesuffix(".tlf") for f in output.split() if f.endswith(".tlf")
    ]
    return fonts


# Tool definitions
def _create_tools() -> List[Dict[str, Any]]:
    """Define tools for Claude integration."""
    return [
        {
            "name": "format_text",
            "description": "Format text into ASCII art using toilet. Use this to transform text into decorative ASCII art with an optional font.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to format"},
                    "font": {
                        "type": "string",
                        "description": "Optional font (e.g., 'big', 'standard')",
                    },
                },
                "required": ["text"],
            },
        },
        {
            "name": "list_fonts",
            "description": "List available toilet fonts for ASCII art formatting.",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]


# Claude integration
async def _process_tool_call(
    tool_call: Dict[str, Any],
    client: Anthropic,
    model: str,
    prompt: str,
    defaults: Dict[str, Any],
) -> Any:
    """Handle tool calls and return Claude's response."""
    try:
        if tool_call["name"] == "format_text":
            text = tool_call["input"].get("text", defaults.get("text"))
            font = tool_call["input"].get("font", defaults.get("font"))
            result = await run_toilet(text, font)
        elif tool_call["name"] == "list_fonts":
            result = "\n".join(await list_toilet_fonts())
        else:
            raise ValueError(f"Unknown tool: {tool_call['name']}")

        return client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": [{"type": "tool_use", **tool_call}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call["id"],
                            "content": result,
                        }
                    ],
                },
            ],
        )
    except Exception as e:
        return client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": [{"type": "tool_use", **tool_call}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call["id"],
                            "content": f"Error: {e}",
                            "is_error": True,
                        }
                    ],
                },
            ],
        )


# CLI commands
@click.group()
def cli():
    """Claude-powered ASCII art generator using Dagger."""
    pass


@cli.command()
@click.argument("text")
@click.option("--font", "-f", help="Font for formatting")
@click.option("--model", "-m", default=DEFAULT_MODEL, help="Claude model to use")
@click.option("--raw", is_flag=True, help="Output raw ASCII art")
@click.option("--debug", is_flag=True, help="Show debug info")
def format(text: str, font: Optional[str], model: str, raw: bool, debug: bool):
    """Format TEXT into ASCII art."""
    if raw:
        print(anyio.run(run_toilet, text, font))
        return

    client = Anthropic()
    prompt = f"Format this text as ASCII art: {text}" + (
        f" Use the {font} font." if font else ""
    )
    if debug:
        print(f"Prompt: {prompt}")

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        tools=_create_tools(),
        tool_choice={"type": "tool", "name": "format_text"},
        messages=[{"role": "user", "content": prompt}],
    )

    if debug:
        print(f"Response: {response}")

    for content in response.content:
        if content.type == "text":
            print(content.text)
        elif content.type == "tool_use":
            tool_call = {"id": content.id, "name": content.name, "input": content.input}
            if debug:
                print(f"Tool call: {tool_call}")
            final_response = anyio.run(
                _process_tool_call,
                tool_call,
                client,
                model,
                prompt,
                {"text": text, "font": font},
            )
            if debug:
                print(f"Final response: {final_response}")
            for final_content in final_response.content:
                if final_content.type == "text":
                    print(final_content.text)


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def fonts(json_output: bool):
    """List available toilet fonts."""

    async def run_fonts():
        async with dagger.connection(dagger.Config(log_output=sys.stderr)):
            client = dagger.dag
            font_list = await list_toilet_fonts(client)
            if json_output:
                print(json.dumps({"fonts": font_list}, indent=2))
            else:
                print("Available fonts:\n  " + "\n  ".join(font_list))

    anyio.run(run_fonts)


@cli.command()
@click.argument("text")
@click.option("--model", "-m", default=DEFAULT_MODEL, help="Claude model to use")
def suggest(text: str, model: str):
    """Get font suggestions from Claude."""
    client = Anthropic()
    prompt = f"Suggest 3 toilet fonts for: {text}. Use list_fonts to check options and explain why each fits."

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        tools=_create_tools(),
        messages=[{"role": "user", "content": prompt}],
    )

    for content in response.content:
        if content.type == "text":
            print(content.text)
        elif content.type == "tool_use":
            tool_call = {"id": content.id, "name": content.name, "input": content.input}
            final_response = anyio.run(
                _process_tool_call, tool_call, client, model, prompt, {"text": text}
            )
            for final_content in final_response.content:
                if final_content.type == "text":
                    print(final_content.text)


@cli.command()
@click.argument("text")
@click.option("--fonts", "-f", type=int, default=3, help="Number of font examples")
def examples(text: str, fonts: int):
    """Generate examples with different fonts."""

    async def run_examples():
        async with dagger.connection(dagger.Config(log_output=sys.stderr)):
            client = dagger.dag
            font_list = await list_toilet_fonts(client)
            if not font_list:
                print("No fonts found! Something’s off with the container.")
                return
            selected_fonts = font_list[: min(fonts, len(font_list))]
            print(f"Generating {len(selected_fonts)} examples for: {text}\n")
            for font in selected_fonts:
                try:
                    output = await run_toilet(client, text, font)
                    print(f"Font: {font}\n{output}\n")
                except Exception as e:
                    print(f"Error with font '{font}': {e}")

    anyio.run(run_examples)


if __name__ == "__main__":
    cli()
