# Plan: Real-Time Metrics Streaming

## Goal

Stream Docker container stats and node resource metrics from RPi node agent to central control plane via MQTT pub/sub.

## Architecture

```
RPi Node                                    Control Plane
┌────────────────────────┐                 ┌────────────────────────┐
│  MetricsCollector      │                 │  MetricsSubscriber     │
│  ├─ psutil (node)      │                 │  ├─ on_node_metrics()  │
│  └─ Docker stats       │                 │  └─ on_container_metrics()
│           │            │                 │           ▲            │
│           ▼            │                 │           │            │
│  MetricsPublisher      │   MQTT topics   │   subscribe to topics  │
│  └─ publish every Ns   │ ──────────────► │                        │
└────────────────────────┘                 └────────────────────────┘
```

## MQTT Topics

- `otto/nodes/{node_id}/metrics/node` - Node-level metrics (CPU, RAM, disk, network)
- `otto/nodes/{node_id}/metrics/containers` - All container metrics for this node

## Implementation Steps

### Step 1: Pydantic Models (`src/models.py`)

```python
from pydantic import BaseModel
from datetime import datetime

class NodeMetrics(BaseModel):
    """Node-level resource metrics."""
    node_id: str
    timestamp: datetime
    cpu_percent: float          # 0-100
    memory_percent: float       # 0-100
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float         # 0-100
    disk_used_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int

class ContainerMetrics(BaseModel):
    """Single container metrics."""
    container_id: str
    container_name: str
    cpu_percent: float
    memory_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    network_rx_bytes: int
    network_tx_bytes: int
    block_read_bytes: int
    block_write_bytes: int

class ContainerMetricsBatch(BaseModel):
    """Batch of container metrics from a node."""
    node_id: str
    timestamp: datetime
    containers: list[ContainerMetrics]
```

### Step 2: Metrics Collector (`src/metrics.py`)

```python
class MetricsCollector:
    """Collects node and container metrics."""

    def __init__(self, node_id: str, docker: DockerManager):
        self.node_id = node_id
        self.docker = docker

    async def collect_node_metrics(self) -> NodeMetrics:
        """Collect node-level metrics using psutil."""
        # psutil.cpu_percent(), psutil.virtual_memory(), etc.
        ...

    async def collect_container_metrics(self) -> ContainerMetricsBatch:
        """Collect metrics for all running containers."""
        # Use docker.get_containers() + docker.get_container_stats()
        ...
```

### Step 3: Metrics Publisher (`src/metrics.py`)

```python
class MetricsPublisher:
    """Publishes metrics to MQTT at regular intervals."""

    def __init__(
        self,
        collector: MetricsCollector,
        node: Node,  # commlib-py Node
        interval_seconds: float = 5.0,
    ):
        self.collector = collector
        self.node = node
        self.interval = interval_seconds
        self._running = False

    async def start(self) -> None:
        """Start publishing loop."""
        self._running = True
        while self._running:
            node_metrics = await self.collector.collect_node_metrics()
            container_metrics = await self.collector.collect_container_metrics()

            # Publish to MQTT (you implement this part)
            self._publish_node_metrics(node_metrics)
            self._publish_container_metrics(container_metrics)

            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        """Stop publishing loop."""
        self._running = False

    def _publish_node_metrics(self, metrics: NodeMetrics) -> None:
        """Publish node metrics to MQTT topic."""
        # commlib-py publisher - you fill in
        topic = f"otto/nodes/{self.collector.node_id}/metrics/node"
        ...

    def _publish_container_metrics(self, metrics: ContainerMetricsBatch) -> None:
        """Publish container metrics to MQTT topic."""
        topic = f"otto/nodes/{self.collector.node_id}/metrics/containers"
        ...
```

### Step 4: Control Plane Subscriber (separate file or test script)

```python
class MetricsSubscriber:
    """Subscribes to metrics from all nodes."""

    def __init__(self, node: Node):
        self.node = node
        self._latest_metrics: dict[str, NodeMetrics] = {}

    def start(self) -> None:
        """Subscribe to metrics topics."""
        # Subscribe to otto/nodes/+/metrics/node
        # Subscribe to otto/nodes/+/metrics/containers
        ...

    def on_node_metrics(self, msg: NodeMetrics) -> None:
        """Handle incoming node metrics."""
        print(f"[{msg.node_id}] CPU: {msg.cpu_percent}% MEM: {msg.memory_percent}%")
        self._latest_metrics[msg.node_id] = msg

    def on_container_metrics(self, msg: ContainerMetricsBatch) -> None:
        """Handle incoming container metrics."""
        for c in msg.containers:
            print(f"  [{c.container_name}] CPU: {c.cpu_percent}% MEM: {c.memory_usage_mb}MB")
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/models.py` | Create | Pydantic models for metrics |
| `src/metrics.py` | Create | MetricsCollector + MetricsPublisher |
| `src/__init__.py` | Update | Export new classes |
| `test_scripts/test_metrics_publisher.py` | Create | Test script for RPi |
| `test_scripts/test_metrics_subscriber.py` | Create | Test script for control plane |

## Your Part (commlib-py)

You'll need to fill in:
1. `MetricsPublisher._publish_node_metrics()` - publish to topic
2. `MetricsPublisher._publish_container_metrics()` - publish to topic
3. `MetricsSubscriber.start()` - subscribe with wildcard topics

I'll implement:
1. Pydantic models
2. psutil collection logic
3. Docker stats parsing
4. Overall class structure

## Docker Stats Parsing

Raw Docker stats need parsing. Key fields:
- `cpu_stats.cpu_usage.total_usage` / `cpu_stats.system_cpu_usage` → CPU %
- `memory_stats.usage` / `memory_stats.limit` → Memory
- `networks.eth0.rx_bytes`, `tx_bytes` → Network
- `blkio_stats` → Block I/O

## Testing

1. Start MQTT broker: `docker compose up -d mqtt`
2. Run publisher on RPi: `python test_scripts/test_metrics_publisher.py`
3. Run subscriber on PC: `python test_scripts/test_metrics_subscriber.py`
4. Verify metrics flow

---

## Unresolved Questions

None - scope is clear.

## Plan Summary

Create Pydantic models for metrics, implement collector using psutil + Docker stats, create publisher/subscriber classes. User implements commlib-py pub/sub specifics.

---

**Waiting for confirmation before execution.**
