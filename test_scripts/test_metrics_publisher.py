"""Test script for MetricsPublisher on RPi node.

Run this on the Raspberry Pi to publish metrics to MQTT.
"""

import asyncio
import contextlib

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters
from src.dockerhandler import DockerManager
from src.metrics import MetricsCollector, MetricsPublisher
from src.models import ContainerMetricsBatch, NodeMetrics

# Configuration
NODE_ID = "rpi-01"  # Change to your node identifier
MQTT_HOST = "localhost"  # Change to your MQTT broker address
MQTT_PORT = 1883
PUBLISH_INTERVAL = 5.0  # seconds


async def main():
    """Run the metrics publisher."""
    # Setup Docker manager
    docker = DockerManager()
    await docker.connect()

    # Setup commlib-py node
    conn_params = ConnectionParameters(
        host=MQTT_HOST,
        port=MQTT_PORT,
    )
    node = Node(
        node_name=f"metrics_publisher_{NODE_ID}",
        connection_params=conn_params,
    )

    # Create publishers for each topic
    node_metrics_pub = node.create_publisher(
        topic=f"otto/nodes/{NODE_ID}/metrics/node",
        msg_type=NodeMetrics,
    )
    container_metrics_pub = node.create_publisher(
        topic=f"otto/nodes/{NODE_ID}/metrics/containers",
        msg_type=ContainerMetricsBatch,
    )

    # Publisher routing function
    def publish_func(topic: str, msg: NodeMetrics | ContainerMetricsBatch) -> None:
        """Route message to appropriate publisher."""
        if topic.endswith("/metrics/node"):
            node_metrics_pub.publish(msg)
        elif topic.endswith("/metrics/containers"):
            container_metrics_pub.publish(msg)
        print(f"[PUB] {topic} | CPU: {getattr(msg, 'cpu_percent', 'N/A')}")

    # Setup collector and publisher
    collector = MetricsCollector(node_id=NODE_ID, docker=docker)
    publisher = MetricsPublisher(
        collector=collector,
        publish_func=publish_func,
        interval_seconds=PUBLISH_INTERVAL,
    )

    print(f"Starting metrics publisher for node: {NODE_ID}")
    print(f"Publishing to MQTT broker: {MQTT_HOST}:{MQTT_PORT}")
    print(f"Interval: {PUBLISH_INTERVAL}s")
    print("Topics:")
    print(f"  otto/nodes/{NODE_ID}/metrics/node")
    print(f"  otto/nodes/{NODE_ID}/metrics/containers")
    print("Press Ctrl+C to stop")
    print("-" * 50)

    # Start commlib node in background
    node.run()

    try:
        await publisher.start()
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await publisher.stop()
        await docker.disconnect()
        node.stop()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
