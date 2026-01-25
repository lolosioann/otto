# Plan: CLI Interface for Otto Cluster Management

## Goal

Create a Docker-like CLI for managing Otto clusters with commands like:
- `otto cluster init` - Initialize cluster from config file
- `otto cluster start` - Start the cluster (control plane + node agents)
- `otto cluster stop` - Stop the cluster
- `otto cluster status` - Show cluster status

## Config File Format (`otto.yaml`)

```yaml
cluster:
  name: my-cluster

mqtt:
  host: localhost
  port: 1883

nodes:
  - id: rpi-01
    host: 192.168.2.7
    docker_url: unix:///var/run/docker.sock  # Local to that node

  - id: local
    host: localhost
    docker_url: unix:///var/run/docker.sock

services:
  - name: test-nginx
    image: nginx:alpine
    node: rpi-01
    ports:
      - "8080:80"

  - name: test-redis
    image: redis:alpine
    node: local
```

## CLI Structure

```
otto
├── cluster
│   ├── init      # Read otto.yaml, validate, save state
│   ├── start     # Start control plane + node agents
│   ├── stop      # Stop everything
│   └── status    # Show cluster state
└── node
    ├── list      # List nodes
    └── metrics   # Show node metrics (future)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         otto cluster start                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Control Plane (local)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ MetricsSubscriber│  │ ClusterManager  │  │  ServiceManager │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │ MQTT
                               ▼
┌──────────────────────┐      ┌──────────────────────┐
│   Node Agent (rpi-01) │      │   Node Agent (local)  │
│  ┌────────────────┐  │      │  ┌────────────────┐   │
│  │MetricsPublisher│  │      │  │MetricsPublisher│   │
│  │ DockerManager  │  │      │  │ DockerManager  │   │
│  └────────────────┘  │      │  └────────────────┘   │
└──────────────────────┘      └──────────────────────┘
```

## Implementation Steps

### Step 1: Add Dependencies

```toml
# pyproject.toml
dependencies = [
    ...
    "typer>=0.9.0",
    "rich>=13.0.0",  # For pretty output (typer dependency)
    "pyyaml>=6.0.0",
]

[project.scripts]
otto = "src.cli:app"
```

### Step 2: Config Models (`src/config.py`)

```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class MQTTConfig(BaseModel):
    host: str = "localhost"
    port: int = 1883

class NodeConfig(BaseModel):
    id: str
    host: str
    docker_url: str = "unix:///var/run/docker.sock"

class ServiceConfig(BaseModel):
    name: str
    image: str
    node: str
    command: str | None = None
    ports: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)

class ClusterConfig(BaseModel):
    name: str = "default"

class OttoConfig(BaseModel):
    cluster: ClusterConfig = Field(default_factory=ClusterConfig)
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    nodes: list[NodeConfig] = Field(default_factory=list)
    services: list[ServiceConfig] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> "OttoConfig":
        ...
```

### Step 3: CLI Entry Point (`src/cli.py`)

```python
import typer

app = typer.Typer(help="Otto - Container orchestration for edge computing")
cluster_app = typer.Typer(help="Cluster management commands")
app.add_typer(cluster_app, name="cluster")

@cluster_app.command("init")
def cluster_init(
    config: str = typer.Option("otto.yaml", "--config", "-c", help="Config file path")
):
    """Initialize cluster from config file."""
    ...

@cluster_app.command("start")
def cluster_start():
    """Start the cluster."""
    ...

@cluster_app.command("stop")
def cluster_stop():
    """Stop the cluster."""
    ...

@cluster_app.command("status")
def cluster_status():
    """Show cluster status."""
    ...
```

### Step 4: Cluster Manager (`src/cluster.py`)

```python
class ClusterManager:
    """Manages the Otto cluster lifecycle."""

    def __init__(self, config: OttoConfig):
        self.config = config
        self._node_agents: dict[str, NodeAgent] = {}
        self._control_plane: ControlPlane | None = None

    async def start(self) -> None:
        """Start control plane and all node agents."""
        ...

    async def stop(self) -> None:
        """Stop all components."""
        ...

    def status(self) -> ClusterStatus:
        """Get cluster status."""
        ...
```

### Step 5: Node Agent (`src/node_agent.py`)

```python
class NodeAgent:
    """Agent running on each node, collecting metrics and managing containers."""

    def __init__(self, node_config: NodeConfig, mqtt_config: MQTTConfig):
        self.config = node_config
        self.mqtt_config = mqtt_config
        self.docker = DockerManager(node_config.docker_url)
        self.publisher: MetricsPublisher | None = None

    async def start(self) -> None:
        """Start the node agent."""
        ...

    async def stop(self) -> None:
        """Stop the node agent."""
        ...
```

## File Structure

```
src/
├── __init__.py
├── cli.py              # Typer CLI entry point
├── config.py           # Pydantic config models
├── cluster.py          # ClusterManager
├── node_agent.py       # NodeAgent
├── control_plane.py    # ControlPlane (metrics subscriber + orchestration)
├── dockerhandler.py    # (existing)
├── metrics.py          # (existing)
└── models.py           # (existing)
```

## MVP Scope (This PR)

1. `otto cluster init` - Parse and validate otto.yaml
2. `otto cluster start` - Start local control plane + local node agent only
3. `otto cluster stop` - Stop everything
4. `otto cluster status` - Basic status output

**Deferred:**
- Remote node agents (SSH deployment)
- Service deployment (just metrics for now)
- Hot reload of config

## Example Usage

```bash
# Create config
cat > otto.yaml << EOF
cluster:
  name: dev-cluster

mqtt:
  host: localhost
  port: 1883

nodes:
  - id: local
    host: localhost
    docker_url: unix:///var/run/docker.sock

services: []
EOF

# Initialize
otto cluster init

# Start
otto cluster start

# Check status
otto cluster status

# Stop
otto cluster stop
```

## Testing

```bash
# After implementation
uv run otto cluster init
uv run otto cluster start
# In another terminal, check MQTT messages or run subscriber
uv run otto cluster status
uv run otto cluster stop
```

---

## Unresolved Questions

None - starting with MVP scope.

## Plan Summary

Add typer CLI with `otto cluster {init,start,stop,status}` commands. Create config models for otto.yaml parsing. Implement ClusterManager and NodeAgent to orchestrate metrics streaming. MVP focuses on local operation only.

---

**Waiting for confirmation before execution.**
