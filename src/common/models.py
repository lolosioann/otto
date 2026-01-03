"""
Pydantic data models for OTTO orchestration system.

This module defines all core data structures used across the system for:
- Node and cluster state representation
- Container specifications and metrics
- NFR definitions and violations
- Migration requests and results
- Event hierarchies

All models use Pydantic v2 for validation, serialization, and JSON schema generation.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# Resource Models
# =============================================================================


class ResourceCapacity(BaseModel):
    """
    Resource capacity and usage for a computational node.

    Parameters
    ----------
    cpu_cores : float
        Number of CPU cores available (e.g., 4.0 for 4 cores, 0.5 for half a core)
    cpu_used : float
        CPU cores currently in use
    ram_mb : float
        Total RAM in megabytes
    ram_used_mb : float
        RAM currently in use (megabytes)
    bandwidth_mbps : float
        Network bandwidth in megabits per second
    bandwidth_used_mbps : float
        Network bandwidth currently in use (megabits per second)

    Examples
    --------
    >>> capacity = ResourceCapacity(
    ...     cpu_cores=4.0,
    ...     cpu_used=2.5,
    ...     ram_mb=8192,
    ...     ram_used_mb=4096,
    ...     bandwidth_mbps=100,
    ...     bandwidth_used_mbps=50
    ... )
    >>> capacity.cpu_available
    1.5
    >>> capacity.cpu_utilization_percent
    62.5
    """

    model_config = ConfigDict(frozen=False, validate_assignment=True)

    cpu_cores: float = Field(..., gt=0, description="Total CPU cores available")
    cpu_used: float = Field(0.0, ge=0, description="CPU cores in use")
    ram_mb: float = Field(..., gt=0, description="Total RAM in megabytes")
    ram_used_mb: float = Field(0.0, ge=0, description="RAM in use (MB)")
    bandwidth_mbps: float = Field(..., gt=0, description="Network bandwidth (Mbps)")
    bandwidth_used_mbps: float = Field(0.0, ge=0, description="Bandwidth in use (Mbps)")

    @field_validator("cpu_used")
    @classmethod
    def validate_cpu_used(cls, v: float, info: Any) -> float:
        """Validate CPU usage doesn't exceed capacity."""
        if "cpu_cores" in info.data and v > info.data["cpu_cores"]:
            raise ValueError(f"CPU used ({v}) exceeds capacity ({info.data['cpu_cores']})")
        return v

    @field_validator("ram_used_mb")
    @classmethod
    def validate_ram_used(cls, v: float, info: Any) -> float:
        """Validate RAM usage doesn't exceed capacity."""
        if "ram_mb" in info.data and v > info.data["ram_mb"]:
            raise ValueError(f"RAM used ({v}) exceeds capacity ({info.data['ram_mb']})")
        return v

    @property
    def cpu_available(self) -> float:
        """Calculate available CPU cores."""
        return self.cpu_cores - self.cpu_used

    @property
    def ram_available_mb(self) -> float:
        """Calculate available RAM in megabytes."""
        return self.ram_mb - self.ram_used_mb

    @property
    def cpu_utilization_percent(self) -> float:
        """Calculate CPU utilization percentage."""
        return (self.cpu_used / self.cpu_cores) * 100

    @property
    def ram_utilization_percent(self) -> float:
        """Calculate RAM utilization percentage."""
        return (self.ram_used_mb / self.ram_mb) * 100


class ResourceRequirements(BaseModel):
    """
    Resource requirements for a container.

    Parameters
    ----------
    cpu : float
        CPU cores required (e.g., 0.5 for half a core)
    memory_mb : float
        Memory required in megabytes
    bandwidth_mbps : float, optional
        Network bandwidth required in megabits per second

    Examples
    --------
    >>> req = ResourceRequirements(cpu=0.5, memory_mb=512, bandwidth_mbps=10)
    >>> req.cpu
    0.5
    """

    model_config = ConfigDict(frozen=True)

    cpu: float = Field(..., gt=0, description="CPU cores required")
    memory_mb: float = Field(..., gt=0, description="Memory required (MB)")
    bandwidth_mbps: float = Field(0.0, ge=0, description="Bandwidth required (Mbps)")


class NFRDefinition(BaseModel):
    """
    Non-Functional Requirement definition for a container.

    Parameters
    ----------
    max_cpu_percent : float, optional
        Maximum CPU utilization percentage (0-100)
    max_memory_percent : float, optional
        Maximum memory utilization percentage (0-100)
    max_latency_ms : float, optional
        Maximum latency in milliseconds
    min_availability : float, optional
        Minimum availability (0.0-1.0)
    max_response_time_ms : float, optional
        Maximum response time in milliseconds

    Examples
    --------
    >>> nfr = NFRDefinition(
    ...     max_cpu_percent=80,
    ...     max_memory_percent=85,
    ...     max_latency_ms=100,
    ...     min_availability=0.99
    ... )
    >>> nfr.max_cpu_percent
    80.0
    """

    model_config = ConfigDict(frozen=True)

    max_cpu_percent: float | None = Field(None, ge=0, le=100, description="Max CPU utilization %")
    max_memory_percent: float | None = Field(
        None, ge=0, le=100, description="Max memory utilization %"
    )
    max_latency_ms: float | None = Field(None, gt=0, description="Max latency (ms)")
    min_availability: float | None = Field(
        None, ge=0.0, le=1.0, description="Min availability (0-1)"
    )
    max_response_time_ms: float | None = Field(None, gt=0, description="Max response time (ms)")


class ContainerSpec(BaseModel):
    """
    Complete specification for a container.

    This model is YAML/TOML compatible for file-based configuration.

    Parameters
    ----------
    name : str
        Unique container name
    image : str
        Docker image (e.g., "nginx:latest")
    resources : ResourceRequirements
        Resource requirements (CPU, memory, bandwidth)
    nfr : NFRDefinition
        Non-functional requirements
    environment : dict[str, str], optional
        Environment variables
    ports : dict[int, int], optional
        Port mappings (host_port: container_port)
    volumes : dict[str, str], optional
        Volume mounts (host_path: container_path)
    command : list[str], optional
        Override container command
    restart_policy : str, optional
        Restart policy ("no", "on-failure", "always", "unless-stopped")

    Examples
    --------
    >>> spec = ContainerSpec(
    ...     name="web-server",
    ...     image="nginx:latest",
    ...     resources=ResourceRequirements(cpu=1.0, memory_mb=512),
    ...     nfr=NFRDefinition(max_cpu_percent=80),
    ...     ports={8080: 80}
    ... )
    >>> spec.name
    'web-server'
    """

    model_config = ConfigDict(frozen=False)

    name: str = Field(..., min_length=1, description="Container name")
    image: str = Field(..., min_length=1, description="Docker image")
    resources: ResourceRequirements
    nfr: NFRDefinition
    environment: dict[str, str] = Field(default_factory=dict, description="Environment vars")
    ports: dict[int, int] = Field(default_factory=dict, description="Port mappings")
    volumes: dict[str, str] = Field(default_factory=dict, description="Volume mounts")
    command: list[str] | None = Field(None, description="Override command")
    restart_policy: str = Field("unless-stopped", description="Restart policy")

    @field_validator("restart_policy")
    @classmethod
    def validate_restart_policy(cls, v: str) -> str:
        """Validate restart policy is supported."""
        allowed = {"no", "on-failure", "always", "unless-stopped"}
        if v not in allowed:
            raise ValueError(f"Restart policy must be one of: {allowed}")
        return v


class ContainerMetrics(BaseModel):
    """
    Real-time metrics for a running container.

    Parameters
    ----------
    container_id : str
        Container ID or name
    timestamp : datetime
        Metric collection timestamp
    cpu_percent : float
        CPU utilization percentage relative to host
    memory_used_mb : float
        Memory usage in megabytes
    memory_limit_mb : float
        Memory limit in megabytes
    network_rx_bytes : float
        Network bytes received
    network_tx_bytes : float
        Network bytes transmitted
    block_read_bytes : float, optional
        Block I/O read bytes
    block_write_bytes : float, optional
        Block I/O write bytes

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> metrics = ContainerMetrics(
    ...     container_id="abc123",
    ...     timestamp=datetime.now(UTC),
    ...     cpu_percent=45.5,
    ...     memory_used_mb=256,
    ...     memory_limit_mb=512,
    ...     network_rx_bytes=1024,
    ...     network_tx_bytes=2048
    ... )
    >>> metrics.memory_percent
    50.0
    """

    model_config = ConfigDict(frozen=True)

    container_id: str
    timestamp: datetime
    cpu_percent: float = Field(..., ge=0, description="CPU utilization %")
    memory_used_mb: float = Field(..., ge=0, description="Memory used (MB)")
    memory_limit_mb: float = Field(..., gt=0, description="Memory limit (MB)")
    network_rx_bytes: float = Field(0.0, ge=0, description="Network RX bytes")
    network_tx_bytes: float = Field(0.0, ge=0, description="Network TX bytes")
    block_read_bytes: float = Field(0.0, ge=0, description="Block read bytes")
    block_write_bytes: float = Field(0.0, ge=0, description="Block write bytes")

    @property
    def memory_percent(self) -> float:
        """Calculate memory utilization percentage."""
        return (self.memory_used_mb / self.memory_limit_mb) * 100


class NodeHealth(str, Enum):
    """Node health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class NodeState(BaseModel):
    """
    Complete state of an edge node.

    Parameters
    ----------
    node_id : str
        Unique node identifier
    hostname : str
        Node hostname
    resources : ResourceCapacity
        Node resource capacity and usage
    health : NodeHealth
        Node health status
    last_heartbeat : datetime
        Last heartbeat timestamp
    metadata : dict[str, Any], optional
        Additional metadata (OS, location, etc.)

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> state = NodeState(
    ...     node_id="edge-01",
    ...     hostname="raspberry-pi-4",
    ...     resources=ResourceCapacity(
    ...         cpu_cores=4.0, cpu_used=2.0,
    ...         ram_mb=8192, ram_used_mb=4096,
    ...         bandwidth_mbps=100, bandwidth_used_mbps=50
    ...     ),
    ...     health=NodeHealth.HEALTHY,
    ...     last_heartbeat=datetime.now(UTC)
    ... )
    >>> state.node_id
    'edge-01'
    """

    model_config = ConfigDict(frozen=False)

    node_id: str = Field(..., min_length=1)
    hostname: str = Field(..., min_length=1)
    resources: ResourceCapacity
    health: NodeHealth = Field(default=NodeHealth.UNKNOWN)
    last_heartbeat: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class MigrationStrategy(str, Enum):
    """Migration strategy enumeration."""

    SIMPLE_STOP_START = "simple_stop_start"
    EXPORT_IMPORT = "export_import"
    CRIU_CHECKPOINT = "criu_checkpoint"


class MigrationRequest(BaseModel):
    """
    Request to migrate a container between nodes.

    Parameters
    ----------
    container_id : str
        Container to migrate
    source_node_id : str
        Source node ID
    target_node_id : str
        Target node ID
    strategy : MigrationStrategy
        Migration strategy to use
    timestamp : datetime
        Request timestamp

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> req = MigrationRequest(
    ...     container_id="web-01",
    ...     source_node_id="edge-01",
    ...     target_node_id="edge-02",
    ...     strategy=MigrationStrategy.SIMPLE_STOP_START,
    ...     timestamp=datetime.now(UTC)
    ... )
    >>> req.strategy
    <MigrationStrategy.SIMPLE_STOP_START: 'simple_stop_start'>
    """

    model_config = ConfigDict(frozen=True)

    container_id: str = Field(..., min_length=1)
    source_node_id: str = Field(..., min_length=1)
    target_node_id: str = Field(..., min_length=1)
    strategy: MigrationStrategy
    timestamp: datetime


class MigrationResult(BaseModel):
    """
    Result of a container migration.

    Parameters
    ----------
    request : MigrationRequest
        Original migration request
    success : bool
        Whether migration succeeded
    total_time_ms : float
        Total migration time (milliseconds)
    downtime_ms : float
        Container downtime (milliseconds)
    transfer_size_bytes : float, optional
        Data transferred (bytes)
    error_message : str, optional
        Error message if failed
    timestamp_completed : datetime
        Completion timestamp

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> req = MigrationRequest(
    ...     container_id="web-01",
    ...     source_node_id="edge-01",
    ...     target_node_id="edge-02",
    ...     strategy=MigrationStrategy.SIMPLE_STOP_START,
    ...     timestamp=datetime.now(UTC)
    ... )
    >>> result = MigrationResult(
    ...     request=req,
    ...     success=True,
    ...     total_time_ms=15000,
    ...     downtime_ms=5000,
    ...     transfer_size_bytes=0,
    ...     timestamp_completed=datetime.now(UTC)
    ... )
    >>> result.success
    True
    """

    model_config = ConfigDict(frozen=True)

    request: MigrationRequest
    success: bool
    total_time_ms: float = Field(..., ge=0)
    downtime_ms: float = Field(..., ge=0)
    transfer_size_bytes: float = Field(0.0, ge=0)
    error_message: str | None = None
    timestamp_completed: datetime


class EventSeverity(str, Enum):
    """Event severity enumeration."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Event type enumeration."""

    # Node events
    NODE_REGISTERED = "node_registered"
    NODE_HEALTHY = "node_healthy"
    NODE_DEGRADED = "node_degraded"
    NODE_FAILED = "node_failed"
    NODE_RECOVERING = "node_recovering"

    # Container events
    CONTAINER_STARTED = "container_started"
    CONTAINER_STOPPED = "container_stopped"
    CONTAINER_FAILED = "container_failed"
    CONTAINER_RESTARTING = "container_restarting"

    # NFR events
    NFR_VIOLATION = "nfr_violation"
    NFR_WARNING = "nfr_warning"
    NFR_RECOVERED = "nfr_recovered"

    # Migration events
    MIGRATION_STARTED = "migration_started"
    MIGRATION_COMPLETED = "migration_completed"
    MIGRATION_FAILED = "migration_failed"


class BaseEvent(BaseModel):
    """
    Base event model.

    Parameters
    ----------
    event_type : EventType
        Type of event
    severity : EventSeverity
        Event severity
    timestamp : datetime
        Event timestamp
    details : dict[str, Any]
        Event-specific details

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> event = BaseEvent(
    ...     event_type=EventType.NODE_REGISTERED,
    ...     severity=EventSeverity.INFO,
    ...     timestamp=datetime.now(UTC),
    ...     details={"node_id": "edge-01"}
    ... )
    >>> event.severity
    <EventSeverity.INFO: 'info'>
    """

    model_config = ConfigDict(frozen=True)

    event_type: EventType
    severity: EventSeverity
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class NodeEvent(BaseEvent):
    """
    Node-specific event.

    Parameters
    ----------
    node_id : str
        Node that generated the event

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> event = NodeEvent(
    ...     event_type=EventType.NODE_REGISTERED,
    ...     severity=EventSeverity.INFO,
    ...     timestamp=datetime.now(UTC),
    ...     node_id="edge-01",
    ...     details={"hostname": "pi4"}
    ... )
    >>> event.node_id
    'edge-01'
    """

    node_id: str = Field(..., min_length=1)


class ContainerEvent(BaseEvent):
    """
    Container-specific event.

    Parameters
    ----------
    node_id : str
        Node hosting the container
    container_id : str
        Container that generated the event

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> event = ContainerEvent(
    ...     event_type=EventType.CONTAINER_STARTED,
    ...     severity=EventSeverity.INFO,
    ...     timestamp=datetime.now(UTC),
    ...     node_id="edge-01",
    ...     container_id="web-01"
    ... )
    >>> event.container_id
    'web-01'
    """

    node_id: str = Field(..., min_length=1)
    container_id: str = Field(..., min_length=1)


class NFRViolationEvent(ContainerEvent):
    """
    NFR violation event.

    Parameters
    ----------
    metric_name : str
        Which NFR metric was violated
    metric_value : float
        Actual metric value
    threshold_value : float
        Threshold that was violated

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> event = NFRViolationEvent(
    ...     event_type=EventType.NFR_VIOLATION,
    ...     severity=EventSeverity.WARNING,
    ...     timestamp=datetime.now(UTC),
    ...     node_id="edge-01",
    ...     container_id="web-01",
    ...     metric_name="cpu_percent",
    ...     metric_value=85.5,
    ...     threshold_value=80.0
    ... )
    >>> event.metric_value > event.threshold_value
    True
    """

    metric_name: str = Field(..., min_length=1)
    metric_value: float
    threshold_value: float


class MigrationEvent(BaseEvent):
    """
    Migration event.

    Parameters
    ----------
    container_id : str
        Container being migrated
    source_node_id : str
        Source node
    target_node_id : str
        Target node
    strategy : MigrationStrategy
        Migration strategy used

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> event = MigrationEvent(
    ...     event_type=EventType.MIGRATION_STARTED,
    ...     severity=EventSeverity.INFO,
    ...     timestamp=datetime.now(UTC),
    ...     container_id="web-01",
    ...     source_node_id="edge-01",
    ...     target_node_id="edge-02",
    ...     strategy=MigrationStrategy.SIMPLE_STOP_START
    ... )
    >>> event.strategy
    <MigrationStrategy.SIMPLE_STOP_START: 'simple_stop_start'>
    """

    container_id: str = Field(..., min_length=1)
    source_node_id: str = Field(..., min_length=1)
    target_node_id: str = Field(..., min_length=1)
    strategy: MigrationStrategy
