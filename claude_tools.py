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
@click.option(
    "--location",
    "-l",
    default="San Francisco, CA",
    help="Location to check weather for",
)
@click.option(
    "--unit",
    "-u",
    type=click.Choice(["celsius", "fahrenheit"]),
    default="celsius",
    help="Temperature unit",
)
@click.option(
    "--model", "-m", default="claude-3-5-sonnet-20240620", help="Claude model to use"
)
def main(location, unit, model):
    """Demonstrate Claude's tool-calling capabilities with a weather example."""
    client = Anthropic()

    # Define the weather tool
    weather_tool = {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "The unit of temperature, either 'celsius' or 'fahrenheit'",
                },
            },
            "required": ["location"],
        },
    }

    print(f"Asking Claude about weather in {location} ({unit})...\n")

    # Initial prompt to get Claude to use the tool
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        tools=[weather_tool],
        messages=[
            {
                "role": "user",
                "content": f"What's the weather like in {location}? Please use {unit} units.",
            }
        ],
    )

    # Display Claude's response
    print("Claude's response:")
    for content in response.content:
        if content.type == "text":
            print(f"TEXT: {content.text}")
        elif content.type == "tool_use":
            print(f"TOOL USE: {content.name}")
            print(f"TOOL INPUT: {content.input}")

    print("\nThis is a simplified demo. In a real application, you would:")
    print("1. Handle the tool request from Claude")
    print("2. Call a real weather API")
    print("3. Return the results to Claude")
    print("4. Get Claude's final response")


if __name__ == "__main__":
    main()
