"""MQTT RPC server for Docker container operations.

Exposes Docker operations as RPC services over MQTT using commlib-py.
"""

import asyncio

from commlib.msg import RPCMessage
from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters

from src.dockerhandler import DockerManager


class StartContainerMessage(RPCMessage):
    """RPC message for starting a container."""

    class Request(RPCMessage.Request):
        """Request payload."""

        container_id: str

    class Response(RPCMessage.Response):
        """Response payload."""

        success: bool
        message: str


class StopContainerMessage(RPCMessage):
    """RPC message for stopping a container."""

    class Request(RPCMessage.Request):
        """Request payload."""

        container_id: str

    class Response(RPCMessage.Response):
        """Response payload."""

        success: bool
        message: str


class ListContainersMessage(RPCMessage):
    """RPC message for listing containers."""

    class Request(RPCMessage.Request):
        """Request payload (empty)."""

        pass

    class Response(RPCMessage.Response):
        """Response payload."""

        success: bool
        containers: list[str]
        message: str


class CreateContainerMessage(RPCMessage):
    """RPC message for creating a container."""

    class Request(RPCMessage.Request):
        """Request payload."""

        image: str
        name: str = ""

    class Response(RPCMessage.Response):
        """Response payload."""

        success: bool
        container_id: str
        message: str


class RemoveContainerMessage(RPCMessage):
    """RPC message for removing a container."""

    class Request(RPCMessage.Request):
        """Request payload."""

        container_id: str

    class Response(RPCMessage.Response):
        """Response payload."""

        success: bool
        message: str


class DockerHandlerServer:
    """RPC server exposing Docker operations over MQTT.

    Parameters
    ----------
    docker_url : str
        Docker daemon URL (e.g., unix:///var/run/docker.sock)
    conn_params : ConnectionParameters
        MQTT connection parameters
    """

    def __init__(
        self,
        docker_url: str = "unix:///var/run/docker.sock",
        conn_params: ConnectionParameters | None = None,
    ):
        self.docker_manager = DockerManager(docker_url)
        self._conn_params = conn_params or ConnectionParameters()
        self._node: Node | None = None
        self._loop = asyncio.new_event_loop()

    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        return self._loop.run_until_complete(coro)

    def start(self) -> None:
        """Start the RPC server."""
        self._node = Node(
            node_name="docker_handler_server",
            connection_params=self._conn_params,
        )

        self._node.create_rpc(
            msg_type=StartContainerMessage,
            rpc_name="docker_handler/start_container",
            on_request=self._on_start_container,
        )

        self._node.create_rpc(
            msg_type=StopContainerMessage,
            rpc_name="docker_handler/stop_container",
            on_request=self._on_stop_container,
        )

        self._node.create_rpc(
            msg_type=ListContainersMessage,
            rpc_name="docker_handler/list_containers",
            on_request=self._on_list_containers,
        )

        self._node.create_rpc(
            msg_type=CreateContainerMessage,
            rpc_name="docker_handler/create_container",
            on_request=self._on_create_container,
        )

        self._node.create_rpc(
            msg_type=RemoveContainerMessage,
            rpc_name="docker_handler/remove_container",
            on_request=self._on_remove_container,
        )

        self._node.run_forever()

    def stop(self) -> None:
        """Stop the server and cleanup."""
        self._run_async(self.docker_manager.disconnect())
        self._loop.close()

    def _on_start_container(
        self, msg: StartContainerMessage.Request
    ) -> StartContainerMessage.Response:
        """Handle start container RPC request."""
        try:
            self._run_async(self.docker_manager.start_container(msg.container_id))
            return StartContainerMessage.Response(
                success=True,
                message=f"Container {msg.container_id} started.",
            )
        except Exception as e:
            return StartContainerMessage.Response(
                success=False,
                message=str(e),
            )

    def _on_stop_container(
        self, msg: StopContainerMessage.Request
    ) -> StopContainerMessage.Response:
        """Handle stop container RPC request."""
        try:
            self._run_async(self.docker_manager.stop_container(msg.container_id))
            return StopContainerMessage.Response(
                success=True,
                message=f"Container {msg.container_id} stopped.",
            )
        except Exception as e:
            return StopContainerMessage.Response(
                success=False,
                message=str(e),
            )

    def _on_list_containers(
        self, msg: ListContainersMessage.Request
    ) -> ListContainersMessage.Response:
        """Handle list containers RPC request."""
        try:
            containers = self._run_async(self.docker_manager.get_containers())
            container_ids = [c.id for c in containers]
            return ListContainersMessage.Response(
                success=True,
                containers=container_ids,
                message=f"Found {len(container_ids)} containers.",
            )
        except Exception as e:
            return ListContainersMessage.Response(
                success=False,
                containers=[],
                message=str(e),
            )

    def _on_create_container(
        self, msg: CreateContainerMessage.Request
    ) -> CreateContainerMessage.Response:
        """Handle create container RPC request."""
        try:
            name = msg.name if msg.name else None
            container_id = self._run_async(
                self.docker_manager.create_container(msg.image, name=name)
            )
            return CreateContainerMessage.Response(
                success=True,
                container_id=container_id,
                message=f"Container created from {msg.image}.",
            )
        except Exception as e:
            return CreateContainerMessage.Response(
                success=False,
                container_id="",
                message=str(e),
            )

    def _on_remove_container(
        self, msg: RemoveContainerMessage.Request
    ) -> RemoveContainerMessage.Response:
        """Handle remove container RPC request."""
        try:
            self._run_async(self.docker_manager.remove_container(msg.container_id))
            return RemoveContainerMessage.Response(
                success=True,
                message=f"Container {msg.container_id} removed.",
            )
        except Exception as e:
            return RemoveContainerMessage.Response(
                success=False,
                message=str(e),
            )


def main():
    """Run the Docker handler server."""
    print("Starting Docker Handler Server...")
    print("Services:")
    print("  - docker_handler/create_container")
    print("  - docker_handler/start_container")
    print("  - docker_handler/stop_container")
    print("  - docker_handler/list_containers")
    print("  - docker_handler/remove_container")

    server = DockerHandlerServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == "__main__":
    main()
