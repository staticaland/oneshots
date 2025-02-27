#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "rich",
#     "boto3",
#     "python-dateutil",
#     "textual",
# ]
# ///

import datetime
import sys
from typing import List, Optional, Dict, Any

import boto3
import click
from dateutil import parser
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn
from textual.app import App, ComposeResult
from textual.widgets import SelectionList, Button, Footer
from textual.containers import Container


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


def get_service_deployments(
    ecs_client, 
    cluster: str, 
    service: str, 
    start_date: datetime.datetime, 
    end_date: datetime.datetime
) -> List[Dict[str, Any]]:
    """Get deployment events for a service within the specified date range."""
    response = ecs_client.describe_services(
        cluster=cluster,
        services=[service]
    )
    
    if not response["services"]:
        return []
        
    service_data = response["services"][0]
    deployments = []
    
    # Check service deployments
    for deployment in service_data.get("deployments", []):
        created_at = deployment.get("createdAt")
        updated_at = deployment.get("updatedAt")
        
        if created_at and start_date <= created_at <= end_date:
            deployments.append({
                "type": "deployment",
                "id": deployment.get("id"),
                "status": deployment.get("status"),
                "task_definition": deployment.get("taskDefinition").split("/")[-1] if deployment.get("taskDefinition") else "N/A",
                "created_at": created_at,
                "updated_at": updated_at
            })
    
    # Check service events related to deployments
    for event in service_data.get("events", []):
        created_at = event.get("createdAt")
        message = event.get("message", "")
        
        if created_at and start_date <= created_at <= end_date and (
            "deployment" in message.lower() or 
            "task definition" in message.lower()
        ):
            deployments.append({
                "type": "event",
                "id": f"event-{len(deployments)}",
                "status": "N/A",
                "task_definition": "N/A",
                "message": message,
                "created_at": created_at,
            })
    
    return sorted(deployments, key=lambda x: x["created_at"], reverse=True)


def print_deployments_table(deployments: List[Dict[str, Any]], console: Console):
    """Print a rich table of deployments."""
    if not deployments:
        console.print("No deployments found in the specified time range.", style="yellow")
        return
        
    table = Table(title="ECS Service Deployments")
    
    table.add_column("Date", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Task Definition", style="magenta")
    table.add_column("Details", style="white")
    
    for deployment in deployments:
        date_str = deployment["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        
        if deployment["type"] == "deployment":
            table.add_row(
                date_str,
                "Deployment",
                deployment["status"],
                deployment["task_definition"],
                f"ID: {deployment['id']}"
            )
        else:  # event
            table.add_row(
                date_str,
                "Event",
                "N/A",
                "N/A",
                deployment.get("message", "")
            )
    
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
def main(
    cluster: Optional[str],
    service: Optional[str],
    profile: Optional[str],
    region: str,
    start_date: Optional[str],
    end_date: Optional[str],
):
    """
    Show ECS service deployments within a specified time period.
    
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
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Fetching available ECS clusters..."),
            transient=True,
        ) as progress:
            task = progress.add_task("Fetching", total=None)
            try:
                clusters = get_aws_clusters(ecs_client)
                progress.update(task, completed=True)
                
                if not clusters:
                    console.print(Panel("No ECS clusters found in this region.", 
                                       title="Error", 
                                       border_style="red"))
                    return
                
                # Use Textual for interactive selection if we're in a terminal
                if sys.stdout.isatty():
                    class ClusterSelector(App):
                        CSS = """
                        Screen {
                            align: center middle;
                        }
                        
                        #container {
                            width: 60%;
                            height: auto;
                            border: solid green;
                            padding: 1 2;
                        }
                        
                        SelectionList {
                            height: auto;
                            max-height: 15;
                        }
                        
                        Button {
                            margin-top: 1;
                        }
                        """
                        
                        BINDINGS = [("q", "quit", "Quit")]
                        
                        def __init__(self, clusters):
                            super().__init__()
                            self.clusters = clusters
                            self.selected_cluster = None
                        
                        def compose(self) -> ComposeResult:
                            with Container(id="container"):
                                yield SelectionList[str](id="cluster-list")
                                yield Button("Select", variant="success", id="select-btn")
                            yield Footer()
                        
                        def on_mount(self) -> None:
                            selection_list = self.query_one("#cluster-list")
                            for i, c in enumerate(self.clusters):
                                selection_list.add_option((c, c))
                            if self.clusters:
                                selection_list.select_first()
                        
                        def on_button_pressed(self, event: Button.Pressed) -> None:
                            selection_list = self.query_one("#cluster-list")
                            selected = selection_list.selected
                            if selected:
                                self.selected_cluster = selected[0]
                                self.exit()
                        
                        def on_selection_list_selected(self, event) -> None:
                            # Enable double-click selection
                            if event.selection_list.selected:
                                self.selected_cluster = event.selection_list.selected[0]
                                self.exit()
                    
                    # Run the Textual app
                    app = ClusterSelector(clusters)
                    app.run()
                    
                    if app.selected_cluster:
                        cluster = app.selected_cluster
                    else:
                        console.print(Panel("No cluster selected", title="Cancelled", border_style="yellow"))
                        return
                else:
                    # Fallback to simple prompt if not in a terminal
                    console.print(Panel("Available clusters:", title="Select a cluster", border_style="green"))
                    for i, c in enumerate(clusters, 1):
                        console.print(f"  [cyan]{i}.[/cyan] [green]{c}[/green]")
                    
                    selected = Prompt.ask(
                        "Select cluster by number",
                        choices=[str(i) for i in range(1, len(clusters) + 1)],
                        default="1"
                    )
                    cluster = clusters[int(selected) - 1]
            except Exception as e:
                console.print(Panel(f"Error fetching clusters: {e}", 
                                  title="Error", 
                                  border_style="red"))
                return
    
    console.print(f"Using cluster: [bold cyan]{cluster}[/bold cyan]")
    
    # Parse dates
    today = datetime.datetime.now(datetime.timezone.utc)
    default_start = today - datetime.timedelta(days=7)
    
    try:
        if start_date:
            start_date_parsed = parser.parse(start_date)
            if not start_date_parsed.tzinfo:
                start_date_parsed = start_date_parsed.replace(tzinfo=datetime.timezone.utc)
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
                console.print(f"No services found in cluster {cluster}.", style="yellow")
                return
    except Exception as e:
        console.print(f"Error fetching services: {e}", style="red")
        return
    
    # Process each service
    total_deployments = 0
    for service_name in services:
        if len(services) > 1:
            console.print(f"\nChecking service: [bold green]{service_name}[/bold green]")
        
        try:
            deployments = get_service_deployments(
                ecs_client, 
                cluster, 
                service_name, 
                start_date_parsed, 
                end_date_parsed
            )
            
            if deployments:
                total_deployments += len(deployments)
                print_deployments_table(deployments, console)
        except Exception as e:
            console.print(f"Error fetching deployments for {service_name}: {e}", style="red")
    
    # Summary
    if len(services) > 1:
        console.print(f"\nSummary: Found [bold]{total_deployments}[/bold] deployments across [bold]{len(services)}[/bold] services.")


if __name__ == "__main__":
    main()