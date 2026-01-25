"""Node agent for Otto cluster.

Runs on each node to collect and publish metrics to the control plane.
"""

import asyncio

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters

from src.config import MQTTConfig, NodeConfig, ServiceConfig
from src.dockerhandler import DockerManager
from src.metrics import MetricsCollector, MetricsPublisher
from src.models import ContainerMetricsBatch, NodeMetrics


class NodeAgent:
    """Agent running on a node, collecting metrics and managing containers.

    Parameters
    ----------
    node_config : NodeConfig
        Node configuration.
    mqtt_config : MQTTConfig
        MQTT broker configuration.
    publish_interval : float
        Metrics publishing interval in seconds.
    """

    def __init__(
        self,
        node_config: NodeConfig,
        mqtt_config: MQTTConfig,
        publish_interval: float = 5.0,
    ):
        self.config = node_config
        self.mqtt_config = mqtt_config
        self.publish_interval = publish_interval

        self._docker: DockerManager | None = None
        self._commlib_node: Node | None = None
        self._publisher: MetricsPublisher | None = None
        self._running = False

    @property
    def node_id(self) -> str:
        """Return the node ID."""
        return self.config.id

    async def start(self) -> None:
        """Start the node agent."""
        if self._running:
            return

        # Initialize Docker manager
        self._docker = DockerManager(self.config.docker_url)
        await self._docker.connect()

        # Initialize commlib node
        conn_params = ConnectionParameters(
            host=self.mqtt_config.host,
            port=self.mqtt_config.port,
        )
        self._commlib_node = Node(
            node_name=f"otto_node_{self.node_id}",
            connection_params=conn_params,
        )

        # Create publishers
        node_metrics_pub = self._commlib_node.create_publisher(
            topic=f"otto/nodes/{self.node_id}/metrics/node",
            msg_type=NodeMetrics,
        )
        container_metrics_pub = self._commlib_node.create_publisher(
            topic=f"otto/nodes/{self.node_id}/metrics/containers",
            msg_type=ContainerMetricsBatch,
        )

        def publish_func(topic: str, msg: NodeMetrics | ContainerMetricsBatch) -> None:
            """Route message to appropriate publisher."""
            if topic.endswith("/metrics/node"):
                node_metrics_pub.publish(msg)
            elif topic.endswith("/metrics/containers"):
                container_metrics_pub.publish(msg)

        # Create collector and publisher
        collector = MetricsCollector(node_id=self.node_id, docker=self._docker)
        self._publisher = MetricsPublisher(
            collector=collector,
            publish_func=publish_func,
            interval_seconds=self.publish_interval,
        )

        # Start commlib node
        self._commlib_node.run()

        # Start metrics publisher
        await self._publisher.start()
        self._running = True

    async def stop(self) -> None:
        """Stop the node agent."""
        if not self._running:
            return

        self._running = False

        if self._publisher:
            await self._publisher.stop()
            self._publisher = None

        if self._commlib_node:
            self._commlib_node.stop()
            self._commlib_node = None

        if self._docker:
            await self._docker.disconnect()
            self._docker = None

    @property
    def is_running(self) -> bool:
        """Check if the agent is running."""
        return self._running

    async def deploy_services(self, services: list[ServiceConfig]) -> None:
        """Deploy containers for services assigned to this node.

        Parameters
        ----------
        services : list[ServiceConfig]
            Services to deploy on this node.
        """
        if self._docker is None:
            raise RuntimeError("Node agent not started. Call start() first.")

        for service in services:
            await self._deploy_service(service)

    async def _deploy_service(self, service: ServiceConfig) -> None:
        """Deploy a single service container.

        Parameters
        ----------
        service : ServiceConfig
            Service configuration.
        """
        if self._docker is None:
            return

        print(f"[{self.node_id}] Deploying service: {service.name}")

        # Check if container already exists
        containers = await self._docker.get_containers()
        existing = None
        for c in containers:
            info = await self._docker.get_container_info(c.id)
            name = info.get("Name", "").lstrip("/")
            if name == service.name:
                existing = c
                break

        if existing:
            print(f"[{self.node_id}] Service {service.name} already running")
            return

        # Pull image if needed and create container
        try:
            await self._docker.pull_image(service.image)
        except Exception as e:
            print(f"[{self.node_id}] Warning: Could not pull image: {e}")

        # Build container config
        container_id = await self._create_service_container(service)
        print(f"[{self.node_id}] Service {service.name} started: {container_id[:12]}")

    async def _create_service_container(self, service: ServiceConfig) -> str:
        """Create and start a container for a service.

        Parameters
        ----------
        service : ServiceConfig
            Service configuration.

        Returns
        -------
        str
            Container ID.
        """
        if self._docker is None:
            raise RuntimeError("Docker not connected")

        container_id = await self._docker.create_container(
            image=service.image,
            name=service.name,
            command=service.command,
            ports=service.ports if service.ports else None,
            environment=service.environment if service.environment else None,
        )
        return container_id


async def run_node_agent(
    node_config: NodeConfig,
    mqtt_config: MQTTConfig,
    publish_interval: float = 5.0,
) -> None:
    """Run a node agent until interrupted.

    Parameters
    ----------
    node_config : NodeConfig
        Node configuration.
    mqtt_config : MQTTConfig
        MQTT broker configuration.
    publish_interval : float
        Metrics publishing interval in seconds.
    """
    agent = NodeAgent(node_config, mqtt_config, publish_interval)

    await agent.start()
    print(f"Node agent started: {node_config.id}")

    try:
        while agent.is_running:
            await asyncio.sleep(1)
    finally:
        await agent.stop()
        print(f"Node agent stopped: {node_config.id}")
