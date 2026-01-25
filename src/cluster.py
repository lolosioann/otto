"""Cluster manager for Otto.

Orchestrates the control plane and node agents.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.config import OttoConfig
from src.control_plane import ControlPlane
from src.node_agent import NodeAgent
from src.remote import RemoteNodeDeployer

# State file location
STATE_DIR = Path(".otto")
STATE_FILE = STATE_DIR / "cluster.json"


@dataclass
class ClusterState:
    """Persistent cluster state.

    Parameters
    ----------
    config_path : str
        Path to the otto.yaml config file.
    initialized_at : str
        ISO timestamp of initialization.
    cluster_name : str
        Name of the cluster.
    node_ids : list[str]
        List of node IDs in the cluster.
    """

    config_path: str
    initialized_at: str
    cluster_name: str
    node_ids: list[str] = field(default_factory=list)

    def save(self) -> None:
        """Save state to disk."""
        STATE_DIR.mkdir(exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(
                {
                    "config_path": self.config_path,
                    "initialized_at": self.initialized_at,
                    "cluster_name": self.cluster_name,
                    "node_ids": self.node_ids,
                },
                f,
                indent=2,
            )

    @classmethod
    def load(cls) -> "ClusterState | None":
        """Load state from disk.

        Returns
        -------
        ClusterState or None
            Loaded state or None if not found.
        """
        if not STATE_FILE.exists():
            return None
        with open(STATE_FILE) as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def clear(cls) -> None:
        """Clear saved state."""
        if STATE_FILE.exists():
            STATE_FILE.unlink()


class ClusterManager:
    """Manages the Otto cluster lifecycle.

    Parameters
    ----------
    config : OttoConfig
        Cluster configuration.
    """

    def __init__(self, config: OttoConfig):
        self.config = config
        self._control_plane: ControlPlane | None = None
        self._local_agents: dict[str, NodeAgent] = {}
        self._remote_deployers: dict[str, RemoteNodeDeployer] = {}
        self._running = False

    async def start(self) -> None:
        """Start the cluster (control plane + node agents)."""
        if self._running:
            return

        # Start control plane
        self._control_plane = ControlPlane(
            mqtt_config=self.config.mqtt,
            nodes=self.config.nodes,
        )
        self._control_plane.start()

        # Start node agents
        for node_config in self.config.nodes:
            services = self.config.get_services_for_node(node_config.id)

            if node_config.is_local:
                # Start local node agent
                agent = NodeAgent(
                    node_config=node_config,
                    mqtt_config=self.config.mqtt,
                )
                await agent.start()

                # Deploy services on local node
                if services:
                    await agent.deploy_services(services)

                self._local_agents[node_config.id] = agent
            else:
                # Deploy to remote node via SSH
                deployer = RemoteNodeDeployer(
                    node=node_config,
                    mqtt=self.config.mqtt,
                )
                try:
                    await deployer.connect()
                    await deployer.deploy_agent(services)
                    self._remote_deployers[node_config.id] = deployer
                except Exception as e:
                    print(f"[WARN] Failed to deploy to {node_config.id}: {e}")

        self._running = True

    async def stop(self) -> None:
        """Stop all cluster components."""
        if not self._running:
            return

        self._running = False

        # Stop local node agents
        for agent in self._local_agents.values():
            await agent.stop()
        self._local_agents.clear()

        # Stop remote deployers
        for deployer in self._remote_deployers.values():
            await deployer.stop()
        self._remote_deployers.clear()

        # Stop control plane
        if self._control_plane:
            self._control_plane.stop()
            self._control_plane = None

    @property
    def is_running(self) -> bool:
        """Check if the cluster is running."""
        return self._running

    @property
    def control_plane(self) -> ControlPlane | None:
        """Get the control plane instance."""
        return self._control_plane

    def get_status(self) -> dict:
        """Get cluster status.

        Returns
        -------
        dict
            Cluster status information.
        """
        status = {
            "cluster_name": self.config.cluster.name,
            "running": self._running,
            "nodes": [],
        }

        for node_config in self.config.nodes:
            is_local = node_config.is_local
            agent_running = (
                node_config.id in self._local_agents
                if is_local
                else node_config.id in self._remote_deployers
            )

            node_status = {
                "id": node_config.id,
                "host": node_config.host,
                "type": "local" if is_local else "remote",
                "agent_running": agent_running,
            }

            # Add metrics if available
            if self._control_plane:
                metrics = self._control_plane.get_node_metrics(node_config.id)
                if metrics:
                    node_status["cpu_percent"] = metrics.cpu_percent
                    node_status["memory_percent"] = metrics.memory_percent

                container_metrics = self._control_plane.get_container_metrics(node_config.id)
                if container_metrics:
                    node_status["container_count"] = len(container_metrics.containers)

            status["nodes"].append(node_status)

        return status


def init_cluster(config_path: str) -> ClusterState:
    """Initialize a cluster from config file.

    Parameters
    ----------
    config_path : str
        Path to otto.yaml config file.

    Returns
    -------
    ClusterState
        Initialized cluster state.

    Raises
    ------
    FileNotFoundError
        If config file not found.
    ValueError
        If config is invalid.
    """
    # Load and validate config
    config = OttoConfig.from_yaml(config_path)

    # Create state
    state = ClusterState(
        config_path=str(Path(config_path).resolve()),
        initialized_at=datetime.now().isoformat(),
        cluster_name=config.cluster.name,
        node_ids=[n.id for n in config.nodes],
    )
    state.save()

    return state


def load_cluster_config() -> OttoConfig:
    """Load cluster config from saved state.

    Returns
    -------
    OttoConfig
        Loaded configuration.

    Raises
    ------
    RuntimeError
        If cluster not initialized.
    """
    state = ClusterState.load()
    if state is None:
        raise RuntimeError("Cluster not initialized. Run 'otto cluster init' first.")

    return OttoConfig.from_yaml(state.config_path)


async def run_cluster(config: OttoConfig) -> None:
    """Run the cluster until interrupted.

    Parameters
    ----------
    config : OttoConfig
        Cluster configuration.
    """
    manager = ClusterManager(config)

    await manager.start()

    try:
        while manager.is_running:
            await asyncio.sleep(1)
    finally:
        await manager.stop()
