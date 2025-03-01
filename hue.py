#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "phue",
# ]
# ///

import json
import os
import sys
from pathlib import Path

import click
from phue import Bridge, Group, Light, PhueRegistrationException, PhueRequestTimeout

# Configuration file path
CONFIG_PATH = Path.home() / ".hue-control.json"


def get_bridge(ip_address=None):
    """
    Connect to the Hue bridge. If no IP address is provided,
    try to load from the config file, or prompt the user.
    """
    try:
        # If IP address provided, use it
        if ip_address:
            bridge = Bridge(ip_address)
            # Save the IP to config
            save_config({"bridge_ip": ip_address})
            return bridge

        # Try to load from config
        config = load_config()
        if config and "bridge_ip" in config:
            try:
                bridge = Bridge(config["bridge_ip"])
                return bridge
            except Exception as e:
                click.echo(f"Error connecting to saved bridge: {e}", err=True)

        # No valid connection, prompt user
        click.echo("No bridge IP specified or saved.")
        click.echo("Please press the link button on your Hue bridge and then run:")
        click.echo("  ./hue.py --ip <bridge_ip> list")
        sys.exit(1)
    except PhueRegistrationException:
        click.echo("Please press the link button on your Hue bridge and try again.")
        sys.exit(1)
    except PhueRequestTimeout:
        click.echo("Connection to the bridge timed out. Please verify the IP address.")
        sys.exit(1)


def load_config():
    """Load configuration from file if it exists"""
    if not CONFIG_PATH.exists():
        return None

    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        return None


def save_config(config_data):
    """Save configuration to file"""
    # Merge with existing config if it exists
    existing_config = load_config() or {}
    existing_config.update(config_data)

    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(existing_config, f)
    except Exception as e:
        click.echo(f"Error saving config: {e}", err=True)


@click.group()
@click.option("--ip", help="IP address of your Hue Bridge")
@click.pass_context
def cli(ctx, ip):
    """Control your Philips Hue lights from the command line"""
    ctx.ensure_object(dict)
    ctx.obj["ip"] = ip


@cli.command()
@click.pass_context
def list(ctx):
    """List all available lights"""
    bridge = get_bridge(ctx.obj["ip"])
    lights = bridge.get_light_objects("id")

    click.echo("\n=== Available Lights ===")
    for light_id, light in lights.items():
        status = "ON" if light.on else "OFF"
        click.echo(f"{light_id}. {light.name} - {status}")
        click.echo(f"   Brightness: {light.brightness}/254")
        if light.colormode:
            if light.colormode == "xy":
                click.echo(f"   Color (xy): {light.xy}")
            elif light.colormode == "ct":
                click.echo(f"   Color Temperature: {light.colortemp_k}K")
            elif light.colormode == "hs":
                click.echo(f"   Hue: {light.hue}, Saturation: {light.saturation}")
    click.echo("")


@cli.command()
@click.argument("light_id")
@click.pass_context
def on(ctx, light_id):
    """Turn a light on (use name or ID)"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Try to interpret as name if not a number
        if not light_id.isdigit():
            light = bridge.get_light_objects("name").get(light_id)
            if light:
                light.on = True
                click.echo(f"Light '{light_id}' turned on")
                return

        # Otherwise treat as ID
        bridge.set_light(light_id, "on", True)
        click.echo(f"Light {light_id} turned on")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("light_id")
@click.pass_context
def off(ctx, light_id):
    """Turn a light off (use name or ID)"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Try to interpret as name if not a number
        if not light_id.isdigit():
            light = bridge.get_light_objects("name").get(light_id)
            if light:
                light.on = False
                click.echo(f"Light '{light_id}' turned off")
                return

        # Otherwise treat as ID
        bridge.set_light(light_id, "on", False)
        click.echo(f"Light {light_id} turned off")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("light_id")
@click.argument("brightness", type=int)
@click.option(
    "--transition",
    "-t",
    type=int,
    help="Transition time in tenths of a second (deciseconds)",
)
@click.pass_context
def brightness(ctx, light_id, brightness, transition):
    """Set the brightness of a light (0-254)"""
    if not 0 <= brightness <= 254:
        click.echo("Brightness must be between 0 and 254", err=True)
        return

    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Try to interpret as name if not a number
        if not light_id.isdigit():
            light = bridge.get_light_objects("name").get(light_id)
            if light:
                if transition:
                    light.transitiontime = transition
                light.brightness = brightness
                click.echo(f"Light '{light_id}' brightness set to {brightness}")
                return

        # Otherwise treat as ID
        kwargs = {}
        if transition:
            kwargs["transitiontime"] = transition
        bridge.set_light(light_id, "bri", brightness, **kwargs)
        click.echo(f"Light {light_id} brightness set to {brightness}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("light_id")
@click.argument("temperature", type=int)
@click.option(
    "--transition",
    "-t",
    type=int,
    help="Transition time in tenths of a second (deciseconds)",
)
@click.pass_context
def temperature(ctx, light_id, temperature, transition):
    """Set the color temperature of a light (2000-6500K)"""
    if not 2000 <= temperature <= 6500:
        click.echo("Temperature must be between 2000K and 6500K", err=True)
        return

    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Try to interpret as name if not a number
        if not light_id.isdigit():
            light = bridge.get_light_objects("name").get(light_id)
            if light:
                if transition:
                    light.transitiontime = transition
                light.colortemp_k = temperature
                click.echo(f"Light '{light_id}' temperature set to {temperature}K")
                return

        # Otherwise treat as ID
        # Convert Kelvin to mireds (Hue uses mireds internally)
        mired = int(1000000 / temperature)

        kwargs = {}
        if transition:
            kwargs["transitiontime"] = transition
        bridge.set_light(light_id, "ct", mired, **kwargs)
        click.echo(f"Light {light_id} temperature set to {temperature}K")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("light_id")
@click.argument("color", type=str)
@click.option(
    "--transition",
    "-t",
    type=int,
    help="Transition time in tenths of a second (deciseconds)",
)
@click.pass_context
def color(ctx, light_id, color, transition):
    """Set the color of a light (by name or hex)"""
    # Define some basic colors
    color_map = {
        "red": (0.675, 0.322),
        "green": (0.408, 0.517),
        "blue": (0.167, 0.04),
        "yellow": (0.508, 0.474),
        "orange": (0.611, 0.382),
        "pink": (0.452, 0.261),
        "purple": (0.244, 0.091),
        "white": (0.33, 0.33),
    }

    xy_color = None

    # Check if it's a named color
    if color.lower() in color_map:
        xy_color = color_map[color.lower()]
    # Check if it's a hex color
    elif color.startswith("#") and len(color) == 7:
        try:
            # Convert hex to RGB
            r = int(color[1:3], 16) / 255.0
            g = int(color[3:5], 16) / 255.0
            b = int(color[5:7], 16) / 255.0

            # Convert RGB to XY (simplified)
            r_adj = (r > 0.04045) and ((r + 0.055) / 1.055) ** 2.4 or (r / 12.92)
            g_adj = (g > 0.04045) and ((g + 0.055) / 1.055) ** 2.4 or (g / 12.92)
            b_adj = (b > 0.04045) and ((b + 0.055) / 1.055) ** 2.4 or (b / 12.92)

            X = r_adj * 0.664511 + g_adj * 0.154324 + b_adj * 0.162028
            Y = r_adj * 0.283881 + g_adj * 0.668433 + b_adj * 0.047685
            Z = r_adj * 0.000088 + g_adj * 0.072310 + b_adj * 0.986039

            sum_XYZ = X + Y + Z
            if sum_XYZ == 0:
                xy_color = (0.33, 0.33)
            else:
                xy_color = (X / sum_XYZ, Y / sum_XYZ)
        except Exception as e:
            click.echo(f"Invalid hex color: {e}", err=True)
            return
    else:
        click.echo(
            "Invalid color. Use a color name (red, green, blue, etc.) or hex value (#RRGGBB)",
            err=True,
        )
        return

    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Try to interpret as name if not a number
        if not light_id.isdigit():
            light = bridge.get_light_objects("name").get(light_id)
            if light:
                if transition:
                    light.transitiontime = transition
                light.xy = xy_color
                click.echo(f"Light '{light_id}' color set to {color}")
                return

        # Otherwise treat as ID
        kwargs = {}
        if transition:
            kwargs["transitiontime"] = transition
        bridge.set_light(light_id, "xy", xy_color, **kwargs)
        click.echo(f"Light {light_id} color set to {color}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("light_id")
@click.argument(
    "scene", type=click.Choice(["relax", "concentrate", "energize", "reading"])
)
@click.option(
    "--transition",
    "-t",
    type=int,
    help="Transition time in tenths of a second (deciseconds)",
)
@click.pass_context
def scene(ctx, light_id, scene, transition):
    """Apply a predefined scene to a light"""
    bridge = get_bridge(ctx.obj["ip"])

    scenes = {
        "relax": {"bri": 144, "ct": 447},  # Warm, dimmed light
        "concentrate": {"bri": 219, "ct": 233},  # Cool, bright light
        "energize": {"bri": 254, "ct": 156},  # Very cool, very bright
        "reading": {"bri": 240, "ct": 346},  # Neutral white, bright
    }

    try:
        settings = scenes[scene].copy()

        # Add transition time if specified
        if transition:
            settings["transitiontime"] = transition

        # Try to interpret as name if not a number
        if not light_id.isdigit():
            light = bridge.get_light_objects("name").get(light_id)
            if light:
                # Apply settings one by one to properly use the Light object
                for key, value in settings.items():
                    if key == "transitiontime":
                        light.transitiontime = value
                    elif key == "bri":
                        light.brightness = value
                    elif key == "ct":
                        light.colortemp = value
                click.echo(f"Scene '{scene}' applied to light '{light_id}'")
                return

        # Otherwise treat as ID
        bridge.set_light(light_id, settings)
        click.echo(f"Scene '{scene}' applied to light {light_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def groups(ctx):
    """List all light groups"""
    bridge = get_bridge(ctx.obj["ip"])
    groups = bridge.get_group()

    click.echo("\n=== Light Groups ===")
    for group_id, group in groups.items():
        status = (
            "ON"
            if group.get("state", {}).get("all_on")
            else "PARTIAL"
            if group.get("state", {}).get("any_on")
            else "OFF"
        )
        click.echo(f"{group_id}. {group['name']} - {status}")
        click.echo(f"   Lights: {', '.join(str(l) for l in group['lights'])}")
    click.echo("")


@cli.command()
@click.argument("group_id")
@click.option(
    "--transition",
    "-t",
    type=int,
    help="Transition time in tenths of a second (deciseconds)",
)
@click.pass_context
def group_on(ctx, group_id, transition):
    """Turn all lights in a group on (use name or ID)"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Check if group_id is a name
        if not group_id.isdigit():
            group_id = bridge.get_group_id_by_name(group_id)
            if not group_id:
                click.echo(f"Group '{group_id}' not found", err=True)
                return

        kwargs = {}
        if transition:
            kwargs["transitiontime"] = transition
        bridge.set_group(group_id, "on", True, **kwargs)
        click.echo(f"Group {group_id} turned on")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("group_id")
@click.option(
    "--transition",
    "-t",
    type=int,
    help="Transition time in tenths of a second (deciseconds)",
)
@click.pass_context
def group_off(ctx, group_id, transition):
    """Turn all lights in a group off (use name or ID)"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Check if group_id is a name
        if not group_id.isdigit():
            group_id = bridge.get_group_id_by_name(group_id)
            if not group_id:
                click.echo(f"Group '{group_id}' not found", err=True)
                return

        kwargs = {}
        if transition:
            kwargs["transitiontime"] = transition
        bridge.set_group(group_id, "on", False, **kwargs)
        click.echo(f"Group {group_id} turned off")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("group_id")
@click.argument(
    "scene", type=click.Choice(["relax", "concentrate", "energize", "reading"])
)
@click.option(
    "--transition",
    "-t",
    type=int,
    help="Transition time in tenths of a second (deciseconds)",
)
@click.pass_context
def group_scene(ctx, group_id, scene, transition):
    """Apply a scene to all lights in a group"""
    bridge = get_bridge(ctx.obj["ip"])

    scenes = {
        "relax": {"bri": 144, "ct": 447},
        "concentrate": {"bri": 219, "ct": 233},
        "energize": {"bri": 254, "ct": 156},
        "reading": {"bri": 240, "ct": 346},
    }

    try:
        # Check if group_id is a name
        if not group_id.isdigit():
            group_id = bridge.get_group_id_by_name(group_id)
            if not group_id:
                click.echo(f"Group '{group_id}' not found", err=True)
                return

        settings = scenes[scene].copy()
        if transition:
            settings["transitiontime"] = transition

        bridge.set_group(group_id, settings)
        click.echo(f"Scene '{scene}' applied to group {group_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("name")
@click.argument("lights", nargs=-1, type=int)
@click.pass_context
def create_group(ctx, name, lights):
    """Create a new group with specified lights"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        result = bridge.create_group(name, lights)
        success = next((item for item in result if "success" in item), None)
        if success:
            group_id = success["success"]["id"]
            click.echo(f"Created group '{name}' with ID {group_id}")
        else:
            click.echo(f"Failed to create group: {result}", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("group_id")
@click.pass_context
def delete_group(ctx, group_id):
    """Delete a group"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Check if group_id is a name
        if not group_id.isdigit():
            group_id = bridge.get_group_id_by_name(group_id)
            if not group_id:
                click.echo(f"Group '{group_id}' not found", err=True)
                return

        result = bridge.delete_group(group_id)
        click.echo(f"Group {group_id} deleted")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("light_id")
@click.pass_context
def alert(ctx, light_id):
    """Flash a light once to help identify it"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        # Try to interpret as name if not a number
        if not light_id.isdigit():
            light = bridge.get_light_objects("name").get(light_id)
            if light:
                light.alert = "select"
                click.echo(f"Light '{light_id}' flashed")
                return

        bridge.set_light(light_id, "alert", "select")
        click.echo(f"Light {light_id} flashed")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def bridge_info(ctx):
    """Get information about the Hue bridge"""
    bridge = get_bridge(ctx.obj["ip"])
    try:
        config = bridge.request("GET", "/api/" + bridge.username + "/config")
        click.echo("\n=== Bridge Information ===")
        click.echo(f"Name: {config.get('name', 'Unknown')}")
        click.echo(f"Model: {config.get('modelid', 'Unknown')}")
        click.echo(f"Software Version: {config.get('swversion', 'Unknown')}")
        click.echo(f"API Version: {config.get('apiversion', 'Unknown')}")
        click.echo(f"Bridge ID: {config.get('bridgeid', 'Unknown')}")
        click.echo(f"ZigBee Channel: {config.get('zigbeechannel', 'Unknown')}")
        click.echo(f"IP Address: {bridge.ip}")
        click.echo("")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    cli(obj={})
