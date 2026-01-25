"""Control plane for Otto cluster.

Subscribes to metrics from all nodes and provides cluster-wide visibility.
"""

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters

from src.config import MQTTConfig, NodeConfig
from src.models import ContainerMetricsBatch, NodeMetrics


class ControlPlane:
    """Control plane that subscribes to metrics from all nodes.

    Parameters
    ----------
    mqtt_config : MQTTConfig
        MQTT broker configuration.
    nodes : list[NodeConfig]
        List of nodes to subscribe to.
    """

    def __init__(self, mqtt_config: MQTTConfig, nodes: list[NodeConfig]):
        self.mqtt_config = mqtt_config
        self.nodes = nodes

        self._commlib_node: Node | None = None
        self._subscribers: list = []
        self._running = False

        # Latest metrics storage
        self._node_metrics: dict[str, NodeMetrics] = {}
        self._container_metrics: dict[str, ContainerMetricsBatch] = {}

    def start(self) -> None:
        """Start the control plane."""
        if self._running:
            return

        # Initialize commlib node
        conn_params = ConnectionParameters(
            host=self.mqtt_config.host,
            port=self.mqtt_config.port,
        )
        self._commlib_node = Node(
            node_name="otto_control_plane",
            connection_params=conn_params,
        )

        # Subscribe to each node's metrics
        for node in self.nodes:
            # Node metrics subscriber
            node_sub = self._commlib_node.create_subscriber(
                topic=f"otto/nodes/{node.id}/metrics/node",
                msg_type=NodeMetrics,
                on_message=self._on_node_metrics,
            )
            self._subscribers.append(node_sub)

            # Container metrics subscriber
            container_sub = self._commlib_node.create_subscriber(
                topic=f"otto/nodes/{node.id}/metrics/containers",
                msg_type=ContainerMetricsBatch,
                on_message=self._on_container_metrics,
            )
            self._subscribers.append(container_sub)

        # Start commlib node (non-blocking)
        self._commlib_node.run()
        self._running = True

    def stop(self) -> None:
        """Stop the control plane."""
        if not self._running:
            return

        self._running = False
        self._subscribers.clear()

        if self._commlib_node:
            self._commlib_node.stop()
            self._commlib_node = None

    def _on_node_metrics(self, msg: NodeMetrics) -> None:
        """Handle incoming node metrics."""
        self._node_metrics[msg.node_id] = msg

    def _on_container_metrics(self, msg: ContainerMetricsBatch) -> None:
        """Handle incoming container metrics."""
        self._container_metrics[msg.node_id] = msg

    def get_node_metrics(self, node_id: str) -> NodeMetrics | None:
        """Get latest metrics for a node.

        Parameters
        ----------
        node_id : str
            Node identifier.

        Returns
        -------
        NodeMetrics or None
            Latest metrics if available.
        """
        return self._node_metrics.get(node_id)

    def get_container_metrics(self, node_id: str) -> ContainerMetricsBatch | None:
        """Get latest container metrics for a node.

        Parameters
        ----------
        node_id : str
            Node identifier.

        Returns
        -------
        ContainerMetricsBatch or None
            Latest container metrics if available.
        """
        return self._container_metrics.get(node_id)

    def get_all_node_metrics(self) -> dict[str, NodeMetrics]:
        """Get latest metrics for all nodes.

        Returns
        -------
        dict[str, NodeMetrics]
            Mapping of node ID to metrics.
        """
        return self._node_metrics.copy()

    def get_all_container_metrics(self) -> dict[str, ContainerMetricsBatch]:
        """Get latest container metrics for all nodes.

        Returns
        -------
        dict[str, ContainerMetricsBatch]
            Mapping of node ID to container metrics.
        """
        return self._container_metrics.copy()

    @property
    def is_running(self) -> bool:
        """Check if the control plane is running."""
        return self._running
