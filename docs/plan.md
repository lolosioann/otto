# Plan: Centralized Cluster Deployment via SSH

## Goal

Deploy entire cluster from control plane:
- SSH into remote nodes
- Start node agents remotely
- Deploy containers as specified in config

## Config Format (docker-compose style)

```yaml
cluster:
  name: home-cluster

mqtt:
  host: 192.168.2.1  # Control plane IP
  port: 1883

nodes:
  - id: local
    host: localhost
    user: null  # No SSH needed
    docker_url: unix:///var/run/docker.sock

  - id: rpi-01
    host: 192.168.2.7
    user: lolosioann  # SSH user
    docker_url: unix:///var/run/docker.sock

services:
  - name: test-nginx
    image: nginx:alpine
    node: rpi-01
    ports:
      - "8080:80"
    environment:
      NGINX_HOST: localhost

  - name: test-redis
    image: redis:alpine
    node: local
    command: redis-server --appendonly yes
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Control Plane (PC)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ ClusterMgr  │  │ ControlPlane│  │ RemoteNodeDeployer      │  │
│  │             │  │ (metrics)   │  │ - SSH into nodes        │  │
│  │             │  │             │  │ - Start node agents     │  │
│  │             │  │             │  │ - Deploy containers     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                      │
         │ MQTT                                 │ SSH
         ▼                                      ▼
┌──────────────────────┐               ┌──────────────────────┐
│   Local Node Agent   │               │   Remote Node (Pi)   │
│   (in-process)       │               │   - Node Agent proc  │
│                      │               │   - Containers       │
└──────────────────────┘               └──────────────────────┘
```

## Implementation Steps

### Step 1: Enhance Config Models

```python
# src/config.py

class NodeConfig(BaseModel):
    id: str
    host: str
    user: str | None = None  # SSH user, None for local
    docker_url: str = "unix:///var/run/docker.sock"

    @property
    def is_local(self) -> bool:
        return self.host in ("localhost", "127.0.0.1") or self.user is None

class ServiceConfig(BaseModel):
    name: str
    image: str
    node: str
    command: str | None = None
    ports: list[str] = []           # "8080:80"
    environment: dict[str, str] = {}
    # Deferred: volumes, networks, resource limits
```

### Step 2: Remote Node Deployer

```python
# src/remote.py

class RemoteNodeDeployer:
    """Deploy node agents to remote nodes via SSH."""

    def __init__(self, node: NodeConfig, mqtt: MQTTConfig):
        self.node = node
        self.mqtt = mqtt
        self._ssh: asyncssh.SSHClientConnection | None = None
        self._process: asyncssh.SSHClientProcess | None = None

    async def connect(self) -> None:
        """Establish SSH connection."""
        self._ssh = await asyncssh.connect(
            self.node.host,
            username=self.node.user,
            known_hosts=None,  # Or configure properly
        )

    async def deploy_agent(self) -> None:
        """Start node agent on remote node."""
        # Run node agent script via SSH
        cmd = f"""
        cd ~/otto && uv run python -c "
import asyncio
from src.node_agent import run_node_agent
from src.config import NodeConfig, MQTTConfig
asyncio.run(run_node_agent(
    NodeConfig(id='{self.node.id}', host='{self.node.host}'),
    MQTTConfig(host='{self.mqtt.host}', port={self.mqtt.port}),
))
"
        """
        self._process = await self._ssh.create_process(cmd)

    async def stop(self) -> None:
        """Stop remote node agent."""
        if self._process:
            self._process.terminate()
        if self._ssh:
            self._ssh.close()
```

### Step 3: Container Deployer

```python
# src/node_agent.py (extend)

class NodeAgent:
    ...

    async def deploy_services(self, services: list[ServiceConfig]) -> None:
        """Deploy containers for this node."""
        for service in services:
            await self._deploy_service(service)

    async def _deploy_service(self, service: ServiceConfig) -> None:
        """Create and start a container from service config."""
        # Check if container exists
        # If not, create it
        # Start it
        ...
```

### Step 4: Update ClusterManager

```python
# src/cluster.py (update)

class ClusterManager:
    def __init__(self, config: OttoConfig):
        self.config = config
        self._control_plane: ControlPlane | None = None
        self._local_agents: dict[str, NodeAgent] = {}
        self._remote_deployers: dict[str, RemoteNodeDeployer] = {}

    async def start(self) -> None:
        # Start control plane
        self._control_plane = ControlPlane(...)
        self._control_plane.start()

        for node in self.config.nodes:
            services = self.config.get_services_for_node(node.id)

            if node.is_local:
                # Start local node agent
                agent = NodeAgent(node, self.config.mqtt)
                await agent.start()
                await agent.deploy_services(services)
                self._local_agents[node.id] = agent
            else:
                # Deploy to remote node via SSH
                deployer = RemoteNodeDeployer(node, self.config.mqtt)
                await deployer.connect()
                await deployer.deploy_agent()
                # Services deployed by remote agent
                self._remote_deployers[node.id] = deployer
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/config.py` | Update | Add `user` to NodeConfig, `is_local` property |
| `src/remote.py` | Create | RemoteNodeDeployer for SSH deployment |
| `src/node_agent.py` | Update | Add `deploy_services()` method |
| `src/cluster.py` | Update | Handle remote nodes via SSH |
| `otto.yaml` | Update | Example with remote node |

## Workflow

```bash
# 1. Ensure otto is installed on Pi
ssh lolosioann@192.168.2.7 "cd ~/otto && uv sync"

# 2. Configure cluster
cat > otto.yaml << 'EOF'
cluster:
  name: home-cluster

mqtt:
  host: 192.168.2.1  # Your PC IP
  port: 1883

nodes:
  - id: local
    host: localhost

  - id: rpi-01
    host: 192.168.2.7
    user: lolosioann

services:
  - name: test-nginx
    image: nginx:alpine
    node: rpi-01
    ports:
      - "8080:80"
EOF

# 3. Initialize and start
otto cluster init
otto cluster start
# This will:
# - Start control plane locally
# - Start local node agent
# - SSH to Pi, start node agent there
# - Deploy nginx container on Pi
```

## Prerequisites

1. SSH key auth to Pi (no password prompts)
2. Otto installed on Pi (`~/otto` with `uv sync` done)
3. MQTT broker accessible from both nodes

## MVP Scope

**Include:**
- SSH connection to remote nodes
- Remote node agent startup
- Basic container deployment (image, command, ports, env)

**Defer:**
- Volumes
- Networks
- Resource limits
- Health checks
- Automatic otto installation on remote

---

## Unresolved Questions

None.

## Plan Summary

Add SSH-based remote node deployment. Control plane SSHs into remote nodes, starts node agents, and deploys containers. Config includes `user` field for SSH and docker-compose-style service definitions.

---

**Waiting for confirmation before execution.**
