"""Metrics collection and publishing for Otto node agents.

Provides classes for collecting node and container metrics and publishing
them to MQTT topics for the control plane to consume.
"""

import asyncio
import contextlib
from datetime import datetime
from typing import Any

import psutil

from src.dockerhandler import DockerManager
from src.models import ContainerMetrics, ContainerMetricsBatch, NodeMetrics


class MetricsCollector:
    """Collects node and container metrics.

    Parameters
    ----------
    node_id : str
        Unique identifier for this node.
    docker : DockerManager
        Docker manager instance for container stats.
    """

    def __init__(self, node_id: str, docker: DockerManager):
        self.node_id = node_id
        self.docker = docker

    async def collect_node_metrics(self) -> NodeMetrics:
        """Collect node-level metrics using psutil.

        Returns
        -------
        NodeMetrics
            Current node resource metrics.
        """
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        return NodeMetrics(
            node_id=self.node_id,
            timestamp=datetime.now(),
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_used_mb=mem.used / (1024 * 1024),
            memory_total_mb=mem.total / (1024 * 1024),
            disk_percent=disk.percent,
            disk_used_gb=disk.used / (1024 * 1024 * 1024),
            disk_total_gb=disk.total / (1024 * 1024 * 1024),
            network_bytes_sent=net.bytes_sent,
            network_bytes_recv=net.bytes_recv,
        )

    async def collect_container_metrics(self) -> ContainerMetricsBatch:
        """Collect metrics for all running containers.

        Returns
        -------
        ContainerMetricsBatch
            Metrics for all containers on this node.
        """
        containers = await self.docker.get_containers()
        metrics_list: list[ContainerMetrics] = []

        for container in containers:
            try:
                stats = await self.docker.get_container_stats(container.id)
                metrics = self._parse_container_stats(container.id, stats)
                metrics_list.append(metrics)
            except Exception as e:
                # Log and skip containers that fail to report stats
                print(f"[WARN] Failed to get stats for {container.id[:12]}: {e}")
                continue

        return ContainerMetricsBatch(
            node_id=self.node_id,
            timestamp=datetime.now(),
            containers=metrics_list,
        )

    def _parse_container_stats(self, container_id: str, stats: dict[str, Any]) -> ContainerMetrics:
        """Parse raw Docker stats into ContainerMetrics.

        Parameters
        ----------
        container_id : str
            Container ID.
        stats : dict
            Raw stats from Docker API.

        Returns
        -------
        ContainerMetrics
            Parsed container metrics.
        """
        # Extract container name (remove leading /)
        name = stats.get("name", container_id)
        if name.startswith("/"):
            name = name[1:]

        # CPU percentage calculation
        cpu_percent = self._calculate_cpu_percent(stats)

        # Memory stats
        mem_stats = stats.get("memory_stats", {})
        mem_usage = mem_stats.get("usage", 0)
        mem_limit = mem_stats.get("limit", 1)  # Avoid division by zero
        mem_percent = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0

        # Network stats (sum all interfaces)
        net_rx, net_tx = self._calculate_network_bytes(stats)

        # Block I/O stats
        blk_read, blk_write = self._calculate_block_io(stats)

        return ContainerMetrics(
            container_id=container_id,
            container_name=name,
            cpu_percent=cpu_percent,
            memory_percent=mem_percent,
            memory_usage_mb=mem_usage / (1024 * 1024),
            memory_limit_mb=mem_limit / (1024 * 1024),
            network_rx_bytes=net_rx,
            network_tx_bytes=net_tx,
            block_read_bytes=blk_read,
            block_write_bytes=blk_write,
        )

    def _calculate_cpu_percent(self, stats: dict[str, Any]) -> float:
        """Calculate CPU percentage from Docker stats.

        Uses the formula from Docker CLI:
        cpu_percent = (delta_container / delta_system) * num_cpus * 100
        """
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})

        cpu_usage = cpu_stats.get("cpu_usage", {})
        precpu_usage = precpu_stats.get("cpu_usage", {})

        container_delta = cpu_usage.get("total_usage", 0) - precpu_usage.get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
            "system_cpu_usage", 0
        )

        if system_delta > 0 and container_delta > 0:
            num_cpus = len(cpu_usage.get("percpu_usage", [])) or 1
            cpu_percent = (container_delta / system_delta) * num_cpus * 100
            return min(cpu_percent, 100.0)  # Cap at 100%

        return 0.0

    def _calculate_network_bytes(self, stats: dict[str, Any]) -> tuple[int, int]:
        """Calculate total network bytes from all interfaces."""
        networks = stats.get("networks", {})
        rx_bytes = 0
        tx_bytes = 0

        for iface_stats in networks.values():
            rx_bytes += iface_stats.get("rx_bytes", 0)
            tx_bytes += iface_stats.get("tx_bytes", 0)

        return rx_bytes, tx_bytes

    def _calculate_block_io(self, stats: dict[str, Any]) -> tuple[int, int]:
        """Calculate block I/O bytes from blkio stats."""
        blkio = stats.get("blkio_stats", {})
        io_bytes = blkio.get("io_service_bytes_recursive", []) or []

        read_bytes = 0
        write_bytes = 0

        for entry in io_bytes:
            op = entry.get("op", "").lower()
            value = entry.get("value", 0)
            if op == "read":
                read_bytes += value
            elif op == "write":
                write_bytes += value

        return read_bytes, write_bytes


class MetricsPublisher:
    """Publishes metrics to MQTT at regular intervals.

    Parameters
    ----------
    collector : MetricsCollector
        Collector instance for gathering metrics.
    publish_func : callable
        Function to publish messages. Signature: (topic: str, msg: PubSubMessage) -> None.
        Receives the topic string and the message object (NodeMetrics or ContainerMetricsBatch).
    interval_seconds : float
        Interval between metric collections (default: 5.0).
    """

    def __init__(
        self,
        collector: MetricsCollector,
        publish_func: callable,
        interval_seconds: float = 5.0,
    ):
        self.collector = collector
        self._publish = publish_func
        self.interval = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def node_id(self) -> str:
        """Return the node ID from collector."""
        return self.collector.node_id

    async def start(self) -> None:
        """Start the publishing loop."""
        self._running = True
        self._task = asyncio.create_task(self._publish_loop())

    async def stop(self) -> None:
        """Stop the publishing loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _publish_loop(self) -> None:
        """Main loop that collects and publishes metrics."""
        # Initial CPU measurement (first call returns 0)
        psutil.cpu_percent(interval=None)
        await asyncio.sleep(0.1)

        while self._running:
            try:
                # Collect metrics
                node_metrics = await self.collector.collect_node_metrics()
                container_metrics = await self.collector.collect_container_metrics()

                # Publish to MQTT
                self._publish_node_metrics(node_metrics)
                self._publish_container_metrics(container_metrics)

            except Exception as e:
                # Log error but continue loop
                print(f"Error collecting/publishing metrics: {e}")

            await asyncio.sleep(self.interval)

    def _publish_node_metrics(self, metrics: NodeMetrics) -> None:
        """Publish node metrics to MQTT topic.

        Parameters
        ----------
        metrics : NodeMetrics
            Node metrics to publish.
        """
        topic = f"otto/nodes/{self.node_id}/metrics/node"
        self._publish(topic, metrics)

    def _publish_container_metrics(self, metrics: ContainerMetricsBatch) -> None:
        """Publish container metrics to MQTT topic.

        Parameters
        ----------
        metrics : ContainerMetricsBatch
            Container metrics batch to publish.
        """
        topic = f"otto/nodes/{self.node_id}/metrics/containers"
        self._publish(topic, metrics)
