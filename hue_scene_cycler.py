#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
# ]
# ///

import datetime
import subprocess
import time

import click


@click.command()
@click.option("--ip", default="192.168.10.121", help="IP address of Hue Bridge")
@click.option("--group", default="Nede", help="Hue group name")
@click.option("--delay", default=5, help="Delay in seconds between scene changes")
@click.option(
    "--scenes",
    default="relax,concentrate,energize,reading",
    help="Comma-separated list of scenes to cycle through",
)
def scene_cycler(ip, group, delay, scenes):
    """Cycles through different Hue scenes with a configurable delay."""
    # Parse scenes into a list
    scene_list = scenes.split(",")

    # Display script info
    click.echo("Hue Scene Cycler")
    click.echo("----------------")
    click.echo(f"IP Address: {ip}")
    click.echo(f"Group: {group}")
    click.echo(f"Scenes: {', '.join(scene_list)}")
    click.echo(f"Delay: {delay} seconds between scenes")
    click.echo("")
    click.echo("Press Ctrl+C to stop")
    click.echo("")

    try:
        # Main loop
        while True:
            for scene in scene_list:
                apply_scene(ip, group, scene)
                time.sleep(delay)
    except KeyboardInterrupt:
        click.echo("\nScene cycling stopped by user.")


def apply_scene(ip, group, scene):
    """Apply a scene to a Hue group."""
    click.echo(f"Applying scene: {scene}")

    # Execute the hue.py command to apply the scene
    subprocess.run(["./hue.py", "--ip", ip, "group-scene", group, scene])

    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    click.echo(f"Applied at {current_time}")
    click.echo("")


if __name__ == "__main__":
    scene_cycler()
