"""Test remote migration to Raspberry Pi.

Run with: uv run python test_scripts/test_remote_migration.py
"""

import asyncio
import json

from src.dockerhandler import DockerManager
from src.migration import MigrationStrategy
from src.remote_migration import RemoteMigrationCoordinator, extract_container_spec

# Configuration
RPI_SSH_URL = "ssh://lolosioann@192.168.2.7"
TEST_IMAGE = "busybox:latest"
TEST_CONTAINER_NAME = "migration_test"


async def test_extract_spec():
    """Test extracting container spec."""
    print("\n=== Testing spec extraction ===")
    docker = DockerManager()
    await docker.connect()

    # Create a test container
    container_id = await docker.create_container(
        image=TEST_IMAGE,
        name=TEST_CONTAINER_NAME,
        command="sleep 3600",
    )
    print(f"Created test container: {container_id[:12]}")

    # Extract spec
    spec = await extract_container_spec(docker, container_id)
    print("Extracted spec:")
    print(f"  image: {spec.image}")
    print(f"  name: {spec.name}")
    print(f"  command: {spec.command}")

    # Cleanup
    await docker.remove_container(container_id)
    await docker.disconnect()
    print("Cleanup done")
    return True


async def test_ssh_connection():
    """Test SSH connection to Pi."""
    print("\n=== Testing SSH connection ===")
    docker = DockerManager(url=RPI_SSH_URL)
    try:
        await docker.connect()
        containers = await docker.get_containers()
        print(f"Connected to Pi via SSH. Containers: {len(containers)}")
        await docker.disconnect()
        return True
    except Exception as e:
        print(f"SSH connection failed: {e}")
        return False


async def test_stop_start_migration():
    """Test stop/start migration to Pi."""
    print("\n=== Testing stop/start migration ===")

    source = DockerManager()
    target = DockerManager(url=RPI_SSH_URL)

    # Create test container locally
    await source.connect()
    container_id = await source.create_container(
        image=TEST_IMAGE,
        name=TEST_CONTAINER_NAME,
        command="sleep 3600",
    )
    print(f"Created local container: {container_id[:12]}")

    # Migrate
    coordinator = RemoteMigrationCoordinator(source, target)
    result = await coordinator.migrate(
        container_id,
        strategy=MigrationStrategy.STOP_START,
        remove_source=True,
    )

    print(f"Migration result: {result.success}")
    print(f"Message: {result.message}")
    print(f"Metrics: {json.dumps(result.metrics, indent=2)}")

    # Verify on target
    await target.connect()
    containers = await target.get_containers()
    migrated = any(TEST_CONTAINER_NAME in str(c) for c in containers)
    print(f"Container found on Pi: {migrated}")

    # Cleanup on target
    if result.target_container_id:
        await target.remove_container(result.target_container_id)
        print("Cleaned up container on Pi")

    await source.disconnect()
    await target.disconnect()
    return result.success


async def test_export_import_migration():
    """Test export/import migration to Pi."""
    print("\n=== Testing export/import migration ===")

    source = DockerManager()
    target = DockerManager(url=RPI_SSH_URL)

    # Create test container locally with some data
    await source.connect()
    container_id = await source.create_container(
        image=TEST_IMAGE,
        name=TEST_CONTAINER_NAME,
        command="sh -c 'echo hello > /data.txt && sleep 3600'",
    )
    print(f"Created local container: {container_id[:12]}")

    # Give it a moment to write the file
    await asyncio.sleep(1)

    # Migrate
    coordinator = RemoteMigrationCoordinator(source, target)
    result = await coordinator.migrate(
        container_id,
        strategy=MigrationStrategy.EXPORT_IMPORT,
        remove_source=True,
    )

    print(f"Migration result: {result.success}")
    print(f"Message: {result.message}")
    print(f"Metrics: {json.dumps(result.metrics, indent=2)}")

    # Cleanup on target
    await target.connect()
    if result.target_container_id:
        await target.remove_container(result.target_container_id)
        print("Cleaned up container on Pi")

    # Cleanup migrated image on target
    try:
        async with target.docker._query(
            f"images/migrated_{TEST_CONTAINER_NAME}:latest",
            method="DELETE",
        ):
            pass
        print("Cleaned up migrated image on Pi")
    except Exception:
        pass

    await source.disconnect()
    await target.disconnect()
    return result.success


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Remote Migration Test Suite")
    print("=" * 50)

    results = {}

    # Test spec extraction
    results["spec_extraction"] = await test_extract_spec()

    # Test SSH connection
    results["ssh_connection"] = await test_ssh_connection()

    if results["ssh_connection"]:
        # Test stop/start migration
        results["stop_start_migration"] = await test_stop_start_migration()

        # Test export/import migration
        results["export_import_migration"] = await test_export_import_migration()

    # Summary
    print("\n" + "=" * 50)
    print("Results:")
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
