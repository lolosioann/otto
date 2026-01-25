"""Configuration models for Otto cluster.

Provides Pydantic models for parsing and validating otto.yaml configuration files.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class MQTTConfig(BaseModel):
    """MQTT broker configuration.

    Parameters
    ----------
    host : str
        MQTT broker hostname.
    port : int
        MQTT broker port.
    """

    host: str = "localhost"
    port: int = 1883


class NodeConfig(BaseModel):
    """Node configuration.

    Parameters
    ----------
    id : str
        Unique node identifier.
    host : str
        Node hostname or IP address.
    docker_url : str
        Docker daemon URL on the node.
    """

    id: str
    host: str
    docker_url: str = "unix:///var/run/docker.sock"


class ServiceConfig(BaseModel):
    """Service (container) configuration.

    Parameters
    ----------
    name : str
        Service name.
    image : str
        Docker image to run.
    node : str
        Node ID where the service should run.
    command : str, optional
        Command to run in the container.
    ports : list[str]
        Port mappings (e.g., "8080:80").
    environment : dict[str, str]
        Environment variables.
    """

    name: str
    image: str
    node: str
    command: str | None = None
    ports: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)


class ClusterConfig(BaseModel):
    """Cluster metadata.

    Parameters
    ----------
    name : str
        Cluster name.
    """

    name: str = "default"


class OttoConfig(BaseModel):
    """Root configuration for Otto cluster.

    Parameters
    ----------
    cluster : ClusterConfig
        Cluster metadata.
    mqtt : MQTTConfig
        MQTT broker configuration.
    nodes : list[NodeConfig]
        List of nodes in the cluster.
    services : list[ServiceConfig]
        List of services to deploy.
    """

    cluster: ClusterConfig = Field(default_factory=ClusterConfig)
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    nodes: list[NodeConfig] = Field(default_factory=list)
    services: list[ServiceConfig] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "OttoConfig":
        """Load configuration from a YAML file.

        Parameters
        ----------
        path : str or Path
            Path to the YAML configuration file.

        Returns
        -------
        OttoConfig
            Parsed configuration.

        Raises
        ------
        FileNotFoundError
            If the config file doesn't exist.
        ValueError
            If the config file is invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls.model_validate(data)

    def get_node(self, node_id: str) -> NodeConfig | None:
        """Get node configuration by ID.

        Parameters
        ----------
        node_id : str
            Node identifier.

        Returns
        -------
        NodeConfig or None
            Node configuration if found.
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_services_for_node(self, node_id: str) -> list[ServiceConfig]:
        """Get services assigned to a node.

        Parameters
        ----------
        node_id : str
            Node identifier.

        Returns
        -------
        list[ServiceConfig]
            Services assigned to the node.
        """
        return [s for s in self.services if s.node == node_id]
