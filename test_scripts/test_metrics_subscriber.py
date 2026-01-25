"""Test script for MetricsSubscriber on control plane.

Run this on the control plane to receive metrics from nodes.
Subscribes to specific node topics (no wildcards).
"""

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters
from src.models import ContainerMetricsBatch, NodeMetrics

# Configuration
MQTT_HOST = "localhost"  # Change to your MQTT broker address
MQTT_PORT = 1883

# Known nodes in the cluster (would come from config file in production)
NODE_IDS = ["rpi-01"]


class MetricsSubscriber:
    """Subscribes to metrics from configured nodes.

    Parameters
    ----------
    node : Node
        commlib-py Node instance.
    node_ids : list[str]
        List of node IDs to subscribe to.
    """

    def __init__(self, node: Node, node_ids: list[str]):
        self.node = node
        self.node_ids = node_ids
        self._latest_node_metrics: dict[str, NodeMetrics] = {}
        self._latest_container_metrics: dict[str, ContainerMetricsBatch] = {}
        self._subscribers = []

    def start(self) -> None:
        """Create subscribers for all configured nodes."""
        for node_id in self.node_ids:
            # Node metrics subscriber
            node_sub = self.node.create_subscriber(
                topic=f"otto/nodes/{node_id}/metrics/node",
                msg_type=NodeMetrics,
                on_message=self._on_node_metrics,
            )
            self._subscribers.append(node_sub)

            # Container metrics subscriber
            container_sub = self.node.create_subscriber(
                topic=f"otto/nodes/{node_id}/metrics/containers",
                msg_type=ContainerMetricsBatch,
                on_message=self._on_container_metrics,
            )
            self._subscribers.append(container_sub)

            print(f"  Subscribed to node: {node_id}")

    def _on_node_metrics(self, msg: NodeMetrics) -> None:
        """Handle incoming node metrics."""
        self._latest_node_metrics[msg.node_id] = msg

        print(f"\n[NODE] {msg.node_id} @ {msg.timestamp}")
        print(f"  CPU: {msg.cpu_percent:.1f}%")
        print(
            f"  MEM: {msg.memory_percent:.1f}% "
            f"({msg.memory_used_mb:.0f}MB / {msg.memory_total_mb:.0f}MB)"
        )
        print(
            f"  DISK: {msg.disk_percent:.1f}% "
            f"({msg.disk_used_gb:.1f}GB / {msg.disk_total_gb:.1f}GB)"
        )
        print(f"  NET: TX {msg.network_bytes_sent:,} B / RX {msg.network_bytes_recv:,} B")

    def _on_container_metrics(self, msg: ContainerMetricsBatch) -> None:
        """Handle incoming container metrics."""
        self._latest_container_metrics[msg.node_id] = msg

        print(f"\n[CONTAINERS] {msg.node_id} @ {msg.timestamp}")
        if not msg.containers:
            print("  (no containers)")
        for c in msg.containers:
            name = c.container_name[:20]
            print(f"  [{name}] CPU: {c.cpu_percent:.1f}% | MEM: {c.memory_usage_mb:.1f}MB")

    def get_latest_node_metrics(self, node_id: str) -> NodeMetrics | None:
        """Get latest node metrics for a node."""
        return self._latest_node_metrics.get(node_id)

    def get_latest_container_metrics(self, node_id: str) -> ContainerMetricsBatch | None:
        """Get latest container metrics for a node."""
        return self._latest_container_metrics.get(node_id)


def main():
    """Run the metrics subscriber."""
    conn_params = ConnectionParameters(
        host=MQTT_HOST,
        port=MQTT_PORT,
    )
    node = Node(
        node_name="metrics_subscriber_control_plane",
        connection_params=conn_params,
    )

    print(f"Connecting to MQTT broker: {MQTT_HOST}:{MQTT_PORT}")
    print("Subscribing to nodes:")

    subscriber = MetricsSubscriber(node, NODE_IDS)
    subscriber.start()

    print("Press Ctrl+C to stop")
    print("-" * 50)

    try:
        node.run_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        node.stop()


if __name__ == "__main__":
    main()
