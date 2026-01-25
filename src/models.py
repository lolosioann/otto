"""Pydantic models for Otto metrics and data structures.

Provides structured models for node and container metrics used in
monitoring and decision-making.
"""

from datetime import datetime

from commlib.msg import PubSubMessage
from pydantic import Field


class NodeMetrics(PubSubMessage):
    """Node-level resource metrics.

    Parameters
    ----------
    node_id : str
        Unique identifier for the node.
    timestamp : datetime
        When metrics were collected.
    cpu_percent : float
        CPU utilization (0-100).
    memory_percent : float
        Memory utilization (0-100).
    memory_used_mb : float
        Used memory in megabytes.
    memory_total_mb : float
        Total memory in megabytes.
    disk_percent : float
        Disk utilization (0-100).
    disk_used_gb : float
        Used disk space in gigabytes.
    disk_total_gb : float
        Total disk space in gigabytes.
    network_bytes_sent : int
        Total bytes sent since boot.
    network_bytes_recv : int
        Total bytes received since boot.
    """

    node_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    memory_used_mb: float = Field(ge=0)
    memory_total_mb: float = Field(ge=0)
    disk_percent: float = Field(ge=0, le=100)
    disk_used_gb: float = Field(ge=0)
    disk_total_gb: float = Field(ge=0)
    network_bytes_sent: int = Field(ge=0)
    network_bytes_recv: int = Field(ge=0)


class ContainerMetrics(PubSubMessage):
    """Metrics for a single container.

    Parameters
    ----------
    container_id : str
        Docker container ID.
    container_name : str
        Container name.
    cpu_percent : float
        CPU utilization (0-100).
    memory_percent : float
        Memory utilization relative to limit (0-100).
    memory_usage_mb : float
        Current memory usage in megabytes.
    memory_limit_mb : float
        Memory limit in megabytes.
    network_rx_bytes : int
        Bytes received.
    network_tx_bytes : int
        Bytes transmitted.
    block_read_bytes : int
        Bytes read from disk.
    block_write_bytes : int
        Bytes written to disk.
    """

    container_id: str
    container_name: str
    cpu_percent: float = Field(ge=0, default=0.0)
    memory_percent: float = Field(ge=0, le=100, default=0.0)
    memory_usage_mb: float = Field(ge=0, default=0.0)
    memory_limit_mb: float = Field(ge=0, default=0.0)
    network_rx_bytes: int = Field(ge=0, default=0)
    network_tx_bytes: int = Field(ge=0, default=0)
    block_read_bytes: int = Field(ge=0, default=0)
    block_write_bytes: int = Field(ge=0, default=0)


class ContainerMetricsBatch(PubSubMessage):
    """Batch of container metrics from a single node.

    Parameters
    ----------
    node_id : str
        Node that collected these metrics.
    timestamp : datetime
        When metrics were collected.
    containers : list[ContainerMetrics]
        Metrics for each container on the node.
    """

    node_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    containers: list[ContainerMetrics] = Field(default_factory=list)
