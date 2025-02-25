#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
# ]
# ///

import configparser
import os
import sys
import click

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.aws/config")


def load_aws_config(config_path):
    """Load an AWS config file into a ConfigParser object."""
    if not os.path.exists(config_path):
        click.echo(f"Error: Config file not found: {config_path}", err=True)
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def load_config_from_string(config_str):
    """Load config from a string into a ConfigParser object."""
    config = configparser.ConfigParser()
    config.read_string(config_str)
    return config


def merge_configs(base_config, new_config):
    """Merge two ConfigParser objects, with new_config taking precedence."""
    merged_config = configparser.ConfigParser()

    # Copy all sections from base_config
    for section in base_config.sections():
        if not merged_config.has_section(section):
            merged_config.add_section(section)
        for key, value in base_config[section].items():
            merged_config[section][key] = value

    # Copy and override with new_config
    for section in new_config.sections():
        if not merged_config.has_section(section):
            merged_config.add_section(section)
        for key, value in new_config[section].items():
            merged_config[section][key] = value

    return merged_config


def write_config(config, file_path=None):
    """Write config to stdout or to a file if file_path is provided."""
    if file_path:
        with open(file_path, "w") as f:
            config.write(f)
        click.echo(f"Config written to {file_path}")
    else:
        # Write to stdout in the same format as the original
        for section in config.sections():
            click.echo(f"[{section}]")
            for key, value in config[section].items():
                click.echo(f"{key} = {value}")
            click.echo()  # Empty line between sections


@click.command(help="Merge AWS config files")
@click.argument(
    "new_config_path",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=False,
)
@click.option(
    "--aws-config",
    "-c",
    default=DEFAULT_CONFIG_PATH,
    help=f"Path to AWS config file (default: {DEFAULT_CONFIG_PATH})",
)
@click.option(
    "--in-place/--no-in-place",
    "-i/-n",
    default=True,
    help="Edit AWS config in place (default: True)",
)
@click.option(
    "--stdin", "-s", is_flag=True, help="Read new config from stdin instead of a file"
)
def main(new_config_path, aws_config, in_place, stdin):
    """Merge a new config with the AWS config file.

    The new config can be provided as a file or via stdin.
    """
    # Load base config
    try:
        base_config = load_aws_config(aws_config)
    except Exception as e:
        click.echo(f"Error loading base config: {e}", err=True)
        sys.exit(1)

    # Load new config from stdin or file
    try:
        if stdin:
            if new_config_path:
                click.echo(
                    "Error: Cannot specify both --stdin and a config file path",
                    err=True,
                )
                sys.exit(1)

            # Read from stdin
            stdin_content = sys.stdin.read()
            if not stdin_content:
                click.echo("Error: No input received from stdin", err=True)
                sys.exit(1)

            new_config = load_config_from_string(stdin_content)
        else:
            if not new_config_path:
                click.echo(
                    "Error: Must specify either a config file path or --stdin", err=True
                )
                sys.exit(1)

            new_config = load_aws_config(new_config_path)
    except Exception as e:
        click.echo(f"Error loading new config: {e}", err=True)
        sys.exit(1)

    # Merge the configs
    merged_config = merge_configs(base_config, new_config)

    # Write the merged config
    if in_place:
        write_config(merged_config, aws_config)
    else:
        write_config(merged_config)  # Write to stdout


if __name__ == "__main__":
    main()
