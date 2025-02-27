#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "rich",
#     "boto3",
#     "python-dateutil",
# ]
# ///

import datetime
import sys
from typing import List, Optional, Dict, Tuple

import boto3
import click
from dateutil import parser
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel


def get_aws_clusters(ecs_client) -> List[str]:
    """Get a list of all ECS clusters."""
    clusters = []
    paginator = ecs_client.get_paginator("list_clusters")

    for page in paginator.paginate():
        cluster_arns = page["clusterArns"]
        # Extract cluster name from ARN
        for arn in cluster_arns:
            cluster_name = arn.split("/")[-1]
            clusters.append(cluster_name)

    return clusters


def get_services_for_cluster(ecs_client, cluster: str) -> List[str]:
    """Get all services for a specific ECS cluster."""
    services = []
    paginator = ecs_client.get_paginator("list_services")

    for page in paginator.paginate(cluster=cluster):
        service_arns = page["serviceArns"]
        # Extract service name from ARN
        for arn in service_arns:
            service_name = arn.split("/")[-1]
            services.append(service_name)

    return services


def get_successful_service_deployments(
    ecs_client,
    cluster: str,
    service: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    debug: bool = False,
) -> Tuple[int, List[str]]:
    """Get count of successful deployment events for a service within the specified date range."""
    response = ecs_client.describe_services(cluster=cluster, services=[service])

    if not response["services"]:
        return 0, []

    service_data = response["services"][0]
    successful_deployments = 0
    sample_messages = []

    # Check for actual deployments within timeframe
    deployment_ids = set()
    for deployment in service_data.get("deployments", []):
        created_at = deployment.get("createdAt")
        if created_at and start_date <= created_at <= end_date:
            # Track this deployment ID
            deployment_ids.add(deployment.get("id", ""))

    # Count successful deployments from events
    for event in service_data.get("events", []):
        created_at = event.get("createdAt")
        message = event.get("message", "")

        # Collect sample messages for debugging
        if created_at and start_date <= created_at <= end_date:
            if "deployment" in message.lower() or "task" in message.lower():
                if len(sample_messages) < 3:  # Limit to 3 sample messages
                    sample_messages.append(message)

        # Try different patterns for successful deployments
        message_lower = message.lower()
        if created_at and start_date <= created_at <= end_date:
            # Various patterns that could indicate a successful deployment
            if any(
                [
                    # Original strict criteria
                    (
                        "has reached a steady state" in message_lower
                        and "deployment completed" in message_lower
                    ),
                    # Common steady state message
                    ("has reached a steady state" in message_lower),
                    # Deployment completion message
                    ("deployment completed" in message_lower),
                    # Task set completed message
                    ("has completed" in message_lower and "taskset" in message_lower),
                    # Primary task set message
                    (
                        "primary taskset" in message_lower
                        and "complete" in message_lower
                    ),
                    # Service stable message
                    ("service became stable" in message_lower),
                ]
            ):
                successful_deployments += 1
                if debug and len(sample_messages) < 5:
                    sample_messages.append(f"MATCHED: {message}")

    return successful_deployments, sample_messages


def print_deployment_summary(
    deployment_counts: Dict[str, int], total_count: int, console: Console
):
    """Print a summary table of successful deployments per service."""
    if not deployment_counts:
        console.print(
            "No successful deployments found in the specified time range.",
            style="yellow",
        )
        return

    # Create and configure table
    table = Table(title="ECS Successful Deployments Summary")
    table.add_column("Service", style="cyan")
    table.add_column("Successful Deployments", style="green", justify="right")

    # Add rows for each service
    for service, count in sorted(
        deployment_counts.items(), key=lambda x: x[1], reverse=True
    ):
        table.add_row(service, str(count))

    # Add total row
    table.add_section()
    table.add_row("TOTAL", f"[bold]{total_count}[/bold]")

    console.print(table)


@click.command()
@click.option(
    "--cluster",
    "-c",
    help="ECS cluster name (if not provided, will list available clusters)",
)
@click.option(
    "--service",
    "-s",
    help="ECS service name (if not provided, will show all services in the cluster)",
)
@click.option(
    "--profile",
    "-p",
    help="AWS profile to use",
)
@click.option(
    "--region",
    "-r",
    default="eu-west-1",
    help="AWS region (default: eu-west-1)",
)
@click.option(
    "--start-date",
    "-sd",
    help="Start date (YYYY-MM-DD) - defaults to 7 days ago",
)
@click.option(
    "--end-date",
    "-ed",
    help="End date (YYYY-MM-DD) - defaults to today",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Show debug information including sample event messages",
)
def main(
    cluster: Optional[str],
    service: Optional[str],
    profile: Optional[str],
    region: str,
    start_date: Optional[str],
    end_date: Optional[str],
    debug: bool,
):
    """
    Count successful ECS service deployments within a specified time period.

    If cluster is not specified, you'll be prompted to choose from available clusters.
    If service is not specified, deployments for all services in the cluster will be shown.
    """
    console = Console()

    # Setup AWS session
    session_kwargs = {"region_name": region}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    ecs_client = session.client("ecs")

    # Get or select cluster
    if not cluster:
        console.print("[bold blue]Fetching available ECS clusters...[/bold blue]")
        try:
            clusters = get_aws_clusters(ecs_client)
            console.print("[bold green]Done fetching clusters.[/bold green]")

            if not clusters:
                console.print(
                    Panel(
                        "No ECS clusters found in this region.",
                        title="Error",
                        border_style="red",
                    )
                )
                return

            # Interactive selection with Rich
            if sys.stdout.isatty():
                console.print(
                    Panel(
                        "Available ECS clusters",
                        title="Cluster Selection",
                        border_style="green",
                    )
                )

                # List clusters with numbers
                for i, c in enumerate(clusters, 1):
                    console.print(f"  [cyan]{i}.[/cyan] [bold green]{c}[/bold green]")

                console.print()  # Add space

                # Get selection with validation
                while True:
                    try:
                        selection = console.input(
                            "[bold cyan]Enter cluster number[/bold cyan] [default=1]: "
                        )

                        # Default to first option if empty input
                        if not selection.strip():
                            selection = "1"

                        idx = int(selection)
                        if 1 <= idx <= len(clusters):
                            cluster = clusters[idx - 1]
                            console.print(
                                f"\nSelected: [bold green]{cluster}[/bold green]"
                            )
                            break
                        else:
                            console.print(
                                f"[bold red]Please enter a number between 1 and {len(clusters)}[/bold red]"
                            )
                    except ValueError:
                        console.print(
                            "[bold red]Please enter a valid number[/bold red]"
                        )
            else:
                # Fallback to simple prompt if not in a terminal
                console.print(
                    Panel(
                        "Available clusters:",
                        title="Select a cluster",
                        border_style="green",
                    )
                )
                for i, c in enumerate(clusters, 1):
                    console.print(f"  [cyan]{i}.[/cyan] [green]{c}[/green]")

                selected = Prompt.ask(
                    "Select cluster by number",
                    choices=[str(i) for i in range(1, len(clusters) + 1)],
                    default="1",
                )
                cluster = clusters[int(selected) - 1]
        except Exception as e:
            console.print(
                Panel(
                    f"Error fetching clusters: {e}", title="Error", border_style="red"
                )
            )
            return

    console.print(f"Using cluster: [bold cyan]{cluster}[/bold cyan]")

    # Parse dates
    today = datetime.datetime.now(datetime.timezone.utc)
    default_start = today - datetime.timedelta(days=7)

    try:
        if start_date:
            start_date_parsed = parser.parse(start_date)
            if not start_date_parsed.tzinfo:
                start_date_parsed = start_date_parsed.replace(
                    tzinfo=datetime.timezone.utc
                )
        else:
            start_date_parsed = default_start

        if end_date:
            end_date_parsed = parser.parse(end_date)
            if not end_date_parsed.tzinfo:
                end_date_parsed = end_date_parsed.replace(tzinfo=datetime.timezone.utc)
            # Set end of day
            end_date_parsed = end_date_parsed.replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        else:
            end_date_parsed = today
    except Exception as e:
        console.print(f"Error parsing dates: {e}", style="red")
        return

    console.print(
        f"Time period: [bold]{start_date_parsed.strftime('%Y-%m-%d')}[/bold] to "
        f"[bold]{end_date_parsed.strftime('%Y-%m-%d')}[/bold]"
    )

    # Get services
    try:
        if service:
            services = [service]
        else:
            console.print(f"Fetching services for cluster {cluster}...", style="blue")
            services = get_services_for_cluster(ecs_client, cluster)
            if not services:
                console.print(
                    f"No services found in cluster {cluster}.", style="yellow"
                )
                return
    except Exception as e:
        console.print(f"Error fetching services: {e}", style="red")
        return

    # Process each service and count deployments
    deployment_counts = {}
    total_successful_deployments = 0
    all_sample_messages = {}

    with console.status("[bold blue]Counting successful deployments...[/bold blue]"):
        for service_name in services:
            try:
                count, sample_messages = get_successful_service_deployments(
                    ecs_client,
                    cluster,
                    service_name,
                    start_date_parsed,
                    end_date_parsed,
                    debug,
                )

                if count > 0:
                    deployment_counts[service_name] = count
                    total_successful_deployments += count

                if debug and sample_messages:
                    all_sample_messages[service_name] = sample_messages

            except Exception as e:
                console.print(f"Error processing {service_name}: {e}", style="red")

    # Print summary table
    console.print()
    console.print(
        f"[bold green]Found {total_successful_deployments} successful deployments across {len(deployment_counts)} services[/bold green]"
    )
    print_deployment_summary(deployment_counts, total_successful_deployments, console)

    # Print debug information if requested
    if debug:
        console.print("\n[bold yellow]Debug Information:[/bold yellow]")

        # Display deployment identification criteria
        console.print("\n[cyan]Deployment Identification Patterns:[/cyan]")
        console.print('1. "has reached a steady state" AND "deployment completed"')
        console.print('2. "has reached a steady state"')
        console.print('3. "deployment completed"')
        console.print('4. "has completed" AND "taskset"')
        console.print('5. "primary taskset" AND "complete"')
        console.print('6. "service became stable"')

        # Show sample messages
        if all_sample_messages:
            console.print("\n[cyan]Sample deployment messages:[/cyan]")
            for service_name, messages in all_sample_messages.items():
                if messages:
                    console.print(f"\n[bold]Service: {service_name}[/bold]")
                    for i, msg in enumerate(messages, 1):
                        console.print(f"{i}. {msg}")
        else:
            console.print(
                "\n[yellow]No deployment messages found in the specified time period.[/yellow]"
            )
            console.print(
                "[yellow]Try extending the date range with --start-date parameter.[/yellow]"
            )


if __name__ == "__main__":
    main()
