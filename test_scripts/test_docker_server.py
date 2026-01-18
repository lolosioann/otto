"""Test client for DockerHandlerServer RPC services.

Run the server first:
    uv run python -m src.docker_handler_server

Then run this client:
    uv run python -m test_scripts.test_docker_server
"""

from commlib.node import Node
from commlib.transports.mqtt import ConnectionParameters
from src.docker_handler_server import (
    CreateContainerMessage,
    ListContainersMessage,
    RemoveContainerMessage,
    StartContainerMessage,
    StopContainerMessage,
)


class DockerHandlerClient:
    """RPC client for DockerHandlerServer."""

    def __init__(self, conn_params: ConnectionParameters | None = None):
        self._conn_params = conn_params or ConnectionParameters()
        self._node = Node(
            node_name="docker_handler_client",
            connection_params=self._conn_params,
        )

        self._create_client = self._node.create_rpc_client(
            msg_type=CreateContainerMessage,
            rpc_name="docker_handler/create_container",
        )

        self._list_client = self._node.create_rpc_client(
            msg_type=ListContainersMessage,
            rpc_name="docker_handler/list_containers",
        )

        self._start_client = self._node.create_rpc_client(
            msg_type=StartContainerMessage,
            rpc_name="docker_handler/start_container",
        )

        self._stop_client = self._node.create_rpc_client(
            msg_type=StopContainerMessage,
            rpc_name="docker_handler/stop_container",
        )

        self._remove_client = self._node.create_rpc_client(
            msg_type=RemoveContainerMessage,
            rpc_name="docker_handler/remove_container",
        )

        self._node.run()

    def create_container(self, image: str, name: str = "") -> CreateContainerMessage.Response:
        """Create a new container."""
        request = CreateContainerMessage.Request(image=image, name=name)
        return self._create_client.call(request)

    def list_containers(self) -> ListContainersMessage.Response:
        """List all containers."""
        request = ListContainersMessage.Request()
        return self._list_client.call(request)

    def start_container(self, container_id: str) -> StartContainerMessage.Response:
        """Start a container by ID."""
        request = StartContainerMessage.Request(container_id=container_id)
        return self._start_client.call(request)

    def stop_container(self, container_id: str) -> StopContainerMessage.Response:
        """Stop a container by ID."""
        request = StopContainerMessage.Request(container_id=container_id)
        return self._stop_client.call(request)

    def remove_container(self, container_id: str) -> RemoveContainerMessage.Response:
        """Remove a container by ID."""
        request = RemoveContainerMessage.Request(container_id=container_id)
        return self._remove_client.call(request)


def main():
    """Test the DockerHandlerServer RPC services."""
    print("Connecting to Docker Handler Server...")
    client = DockerHandlerClient()

    # Test 1: Create a test container
    print("\n--- Test 1: Create Container (busybox) ---")
    create_resp = client.create_container(image="busybox", name="otto_test_container")
    print(f"Success: {create_resp.success}")
    print(f"Message: {create_resp.message}")
    if not create_resp.success:
        print("Failed to create container, aborting tests.")
        return

    container_id = create_resp.container_id
    short_id = container_id[:12]
    print(f"Container ID: {short_id}")

    # Test 2: List containers (should include our new container)
    print("\n--- Test 2: List Containers ---")
    list_resp = client.list_containers()
    print(f"Success: {list_resp.success}")
    print(f"Message: {list_resp.message}")
    if list_resp.success:
        print(f"Containers ({len(list_resp.containers)}):")
        for cid in list_resp.containers:
            marker = " <-- test container" if cid == container_id else ""
            print(f"  - {cid[:12]}{marker}")

    # Test 3: Stop the test container
    print(f"\n--- Test 3: Stop Container {short_id} ---")
    stop_resp = client.stop_container(container_id)
    print(f"Success: {stop_resp.success}")
    print(f"Message: {stop_resp.message}")

    # Test 4: Start the test container
    print(f"\n--- Test 4: Start Container {short_id} ---")
    start_resp = client.start_container(container_id)
    print(f"Success: {start_resp.success}")
    print(f"Message: {start_resp.message}")

    # Test 5: Remove the test container
    print(f"\n--- Test 5: Remove Container {short_id} ---")
    remove_resp = client.remove_container(container_id)
    print(f"Success: {remove_resp.success}")
    print(f"Message: {remove_resp.message}")

    print("\n--- Tests Complete ---")


if __name__ == "__main__":
    main()
