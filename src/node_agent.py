"""Node agent for Otto cluster.

Runs on each node to collect and publish metrics to the control plane.
"""

import asyncio

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters

from src.config import MQTTConfig, NodeConfig
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
