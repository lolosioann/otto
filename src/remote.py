"""Remote node deployment via SSH.

Provides utilities for deploying node agents to remote nodes.
"""

import contextlib
import json

import asyncssh

from src.config import MQTTConfig, NodeConfig, ServiceConfig


class RemoteNodeDeployer:
    """Deploy and manage node agents on remote nodes via SSH.

    Parameters
    ----------
    node : NodeConfig
        Node configuration (must have user set for SSH).
    mqtt : MQTTConfig
        MQTT broker configuration.
    otto_path : str
        Path to otto installation on remote node.
    """

    def __init__(
        self,
        node: NodeConfig,
        mqtt: MQTTConfig,
        otto_path: str = "~/otto",
    ):
        if node.user is None:
            raise ValueError(f"Node {node.id} has no SSH user configured")

        self.node = node
        self.mqtt = mqtt
        self.otto_path = otto_path

        self._ssh: asyncssh.SSHClientConnection | None = None
        self._agent_process: asyncssh.SSHClientProcess | None = None

    async def connect(self) -> None:
        """Establish SSH connection to the remote node."""
        self._ssh = await asyncssh.connect(
            self.node.host,
            username=self.node.user,
            known_hosts=None,
        )

    async def deploy_agent(self, services: list[ServiceConfig] | None = None) -> None:
        """Start node agent on the remote node.

        Parameters
        ----------
        services : list[ServiceConfig], optional
            Services to deploy on this node.
        """
        if self._ssh is None:
            raise RuntimeError("Not connected. Call connect() first.")

        # Build services JSON for the remote agent
        services_json = "[]"
        if services:
            services_data = [s.model_dump() for s in services]
            services_json = json.dumps(services_data)

        # Build the Python script to run
        script = f'''import asyncio
import json
from src.node_agent import NodeAgent
from src.config import NodeConfig, MQTTConfig, ServiceConfig

async def main():
    node_config = NodeConfig(
        id="{self.node.id}",
        host="{self.node.host}",
        docker_url="{self.node.docker_url}",
    )
    mqtt_config = MQTTConfig(
        host="{self.mqtt.host}",
        port={self.mqtt.port},
    )

    services_data = json.loads("""{services_json}""")
    services = [ServiceConfig.model_validate(s) for s in services_data]

    agent = NodeAgent(node_config, mqtt_config)
    await agent.start()

    if services:
        await agent.deploy_services(services)

    print(f"Node agent {{node_config.id}} started")

    try:
        while agent.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await agent.stop()

asyncio.run(main())
'''

        # Write script to temp file and execute
        script_path = f"{self.otto_path}/.otto_agent_{self.node.id}.py"
        await self._ssh.run(f"cat > {script_path} << 'OTTOSCRIPT'\n{script}\nOTTOSCRIPT")

        cmd = f"cd {self.otto_path} && uv run python {script_path}"

        self._agent_process = await self._ssh.create_process(
            cmd,
            stderr=asyncssh.STDOUT,
        )

    async def stop(self) -> None:
        """Stop the remote node agent and close SSH connection."""
        if self._agent_process:
            self._agent_process.terminate()
            with contextlib.suppress(Exception):
                await self._agent_process.wait()
            self._agent_process = None

        if self._ssh:
            self._ssh.close()
            await self._ssh.wait_closed()
            self._ssh = None

    async def run_command(self, cmd: str) -> tuple[str, str]:
        """Run a command on the remote node.

        Parameters
        ----------
        cmd : str
            Command to run.

        Returns
        -------
        tuple[str, str]
            stdout and stderr output.
        """
        if self._ssh is None:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self._ssh.run(cmd)
        return result.stdout or "", result.stderr or ""

    async def check_otto_installed(self) -> bool:
        """Check if otto is installed on the remote node.

        Returns
        -------
        bool
            True if otto is installed and ready.
        """
        try:
            stdout, _ = await self.run_command(
                f"cd {self.otto_path} && uv run python -c 'import src; print(\"ok\")'"
            )
            return "ok" in stdout
        except Exception:
            return False

    @property
    def is_connected(self) -> bool:
        """Check if SSH connection is established."""
        return self._ssh is not None

    @property
    def is_agent_running(self) -> bool:
        """Check if the remote agent process is running."""
        if self._agent_process is None:
            return False
        return self._agent_process.returncode is None
