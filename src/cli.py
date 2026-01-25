"""CLI entry point for Otto.

Provides Docker-like commands for cluster management.
"""

import asyncio
import contextlib
import signal
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from src.cluster import (
    ClusterManager,
    ClusterState,
    init_cluster,
    load_cluster_config,
)
from src.config import OttoConfig

# Create CLI app
app = typer.Typer(
    name="otto",
    help="Otto - Container orchestration for edge computing",
    no_args_is_help=True,
)

# Cluster subcommands
cluster_app = typer.Typer(help="Cluster management commands", no_args_is_help=True)
app.add_typer(cluster_app, name="cluster")

console = Console()


@cluster_app.command("init")
def cmd_cluster_init(
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="Path to otto.yaml config file"),
    ] = "otto.yaml",
) -> None:
    """Initialize cluster from config file."""
    try:
        state = init_cluster(config)
        rprint(f"[green]✓[/green] Cluster '{state.cluster_name}' initialized")
        rprint(f"  Config: {state.config_path}")
        rprint(f"  Nodes: {', '.join(state.node_ids)}")
    except FileNotFoundError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[red]Error:[/red] Failed to initialize cluster: {e}")
        raise typer.Exit(1) from None


@cluster_app.command("start")
def cmd_cluster_start(
    foreground: Annotated[
        bool,
        typer.Option("--foreground", "-f", help="Run in foreground (blocking)"),
    ] = True,
) -> None:
    """Start the cluster."""
    try:
        config = load_cluster_config()
    except RuntimeError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    rprint(f"[blue]Starting cluster '{config.cluster.name}'...[/blue]")
    rprint(f"  MQTT: {config.mqtt.host}:{config.mqtt.port}")
    rprint(f"  Nodes: {', '.join(n.id for n in config.nodes)}")
    rprint()

    manager = ClusterManager(config)

    async def run() -> None:
        await manager.start()
        rprint("[green]✓[/green] Cluster started")
        rprint("  Press Ctrl+C to stop")
        rprint()

        # Handle shutdown signals
        loop = asyncio.get_event_loop()
        stop_event = asyncio.Event()

        def signal_handler() -> None:
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        # Wait for stop signal
        await stop_event.wait()

        rprint("\n[yellow]Stopping cluster...[/yellow]")
        await manager.stop()
        rprint("[green]✓[/green] Cluster stopped")

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())


@cluster_app.command("stop")
def cmd_cluster_stop() -> None:
    """Stop the cluster.

    Note: In MVP, cluster runs in foreground, so this just clears state.
    """
    state = ClusterState.load()
    if state is None:
        rprint("[yellow]No cluster initialized[/yellow]")
        return

    # Clear state
    ClusterState.clear()
    rprint(f"[green]✓[/green] Cluster '{state.cluster_name}' state cleared")


@cluster_app.command("status")
def cmd_cluster_status() -> None:
    """Show cluster status."""
    state = ClusterState.load()
    if state is None:
        rprint("[yellow]No cluster initialized[/yellow]")
        rprint("Run 'otto cluster init' first")
        raise typer.Exit(1)

    try:
        config = OttoConfig.from_yaml(state.config_path)
    except Exception as e:
        rprint(f"[red]Error loading config:[/red] {e}")
        raise typer.Exit(1) from None

    # Show cluster info
    rprint(f"[bold]Cluster:[/bold] {state.cluster_name}")
    rprint(f"[bold]Config:[/bold] {state.config_path}")
    rprint(f"[bold]Initialized:[/bold] {state.initialized_at}")
    rprint()

    # Show nodes table
    table = Table(title="Nodes")
    table.add_column("ID", style="cyan")
    table.add_column("Host")
    table.add_column("Docker URL")

    for node in config.nodes:
        table.add_row(node.id, node.host, node.docker_url)

    console.print(table)

    # Show services if any
    if config.services:
        rprint()
        services_table = Table(title="Services")
        services_table.add_column("Name", style="cyan")
        services_table.add_column("Image")
        services_table.add_column("Node")

        for service in config.services:
            services_table.add_row(service.name, service.image, service.node)

        console.print(services_table)


# Entry point for the CLI
if __name__ == "__main__":
    app()
