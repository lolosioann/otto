"""Test script for container migration strategies.

Tests both StopStart and ExportImport migration strategies locally.

Usage:
    uv run python -m test_scripts.test_migration
"""

import asyncio
import time

from src.dockerhandler import DockerManager
from src.migration import (
    ContainerSpec,
    ExportImportMigration,
    MigrationStrategy,
    StopStartMigration,
    get_migration_executor,
)


async def create_test_container(docker: DockerManager, name: str) -> str:
    """Create a test container with some state."""
    print(f"Creating test container '{name}'...")
    container_id = await docker.create_container(
        image="busybox",
        name=name,
    )
    print(f"  Created: {container_id[:12]}")
    return container_id


async def test_stop_start_migration(docker: DockerManager) -> bool:
    """Test the StopStart migration strategy."""
    print("\n" + "=" * 60)
    print("TEST: StopStart Migration")
    print("=" * 60)

    source_name = "otto_migration_test_source_ss"
    target_name = "otto_migration_test_target_ss"

    try:
        # Create source container
        source_id = await create_test_container(docker, source_name)

        # Get container spec (simulating what we'd extract from source)
        spec = ContainerSpec(
            image="busybox",
            name=target_name,
        )

        # Create executor
        executor = StopStartMigration(docker)
        print(f"\nStrategy: {executor.strategy.value}")

        # Export (stops container, returns None for this strategy)
        print("\nExporting (stopping source container)...")
        start_time = time.time()
        data = await executor.export_container(source_id)
        export_time = time.time() - start_time
        print(f"  Export time: {export_time:.2f}s")
        print(f"  Data size: {len(data) if data else 0} bytes (None expected)")

        # Import (creates new container)
        print("\nImporting (creating target container)...")
        start_time = time.time()
        target_id = await executor.import_container(spec, data)
        import_time = time.time() - start_time
        print(f"  Import time: {import_time:.2f}s")
        print(f"  Target container: {target_id[:12]}")

        print("\n✓ StopStart migration successful!")
        print(f"  Total time: {export_time + import_time:.2f}s")

        return True

    except Exception as e:
        print(f"\n✗ StopStart migration failed: {e}")
        return False

    finally:
        # Cleanup
        print("\nCleaning up...")
        try:
            await docker.remove_container(source_name, force=True)
            print(f"  Removed: {source_name}")
        except Exception:
            pass
        try:
            await docker.remove_container(target_name, force=True)
            print(f"  Removed: {target_name}")
        except Exception:
            pass


async def test_export_import_migration(docker: DockerManager) -> bool:
    """Test the ExportImport migration strategy."""
    print("\n" + "=" * 60)
    print("TEST: ExportImport Migration")
    print("=" * 60)

    source_name = "otto_migration_test_source_ei"
    target_name = "otto_migration_test_target_ei"
    imported_image = f"migrated_{target_name}"

    try:
        # Create source container
        source_id = await create_test_container(docker, source_name)

        # Get container spec
        spec = ContainerSpec(
            image="busybox",
            name=target_name,
        )

        # Create executor
        executor = ExportImportMigration(docker)
        print(f"\nStrategy: {executor.strategy.value}")

        # Export (stops container, exports filesystem)
        print("\nExporting container filesystem...")
        start_time = time.time()
        data = await executor.export_container(source_id)
        export_time = time.time() - start_time
        data_size_mb = len(data) / (1024 * 1024) if data else 0
        print(f"  Export time: {export_time:.2f}s")
        print(f"  Data size: {data_size_mb:.2f} MB")

        # Import (imports as image, creates container)
        print("\nImporting as new image and creating container...")
        start_time = time.time()
        target_id = await executor.import_container(spec, data)
        import_time = time.time() - start_time
        print(f"  Import time: {import_time:.2f}s")
        print(f"  Target container: {target_id[:12]}")

        print("\n✓ ExportImport migration successful!")
        print(f"  Total time: {export_time + import_time:.2f}s")
        print(f"  Data transferred: {data_size_mb:.2f} MB")

        return True

    except Exception as e:
        print(f"\n✗ ExportImport migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\nCleaning up...")
        try:
            await docker.remove_container(source_name, force=True)
            print(f"  Removed container: {source_name}")
        except Exception:
            pass
        try:
            await docker.remove_container(target_name, force=True)
            print(f"  Removed container: {target_name}")
        except Exception:
            pass
        try:
            # Remove imported image
            await docker.docker.images.delete(f"{imported_image}:latest", force=True)
            print(f"  Removed image: {imported_image}:latest")
        except Exception:
            pass


async def test_factory_function(docker: DockerManager) -> bool:
    """Test the get_migration_executor factory function."""
    print("\n" + "=" * 60)
    print("TEST: Factory Function")
    print("=" * 60)

    try:
        for strategy in MigrationStrategy:
            executor = get_migration_executor(strategy, docker)
            print(f"  {strategy.value}: {executor.__class__.__name__}")

        print("\n✓ Factory function works correctly!")
        return True

    except Exception as e:
        print(f"\n✗ Factory function failed: {e}")
        return False


async def main():
    """Run all migration tests."""
    print("=" * 60)
    print("Otto Migration Strategy Tests")
    print("=" * 60)

    docker = DockerManager()

    try:
        # Connect
        print("\nConnecting to Docker daemon...")
        await docker.connect()
        print("  Connected!")

        results = {}

        # Test factory function
        results["factory"] = await test_factory_function(docker)

        # Test StopStart
        results["stop_start"] = await test_stop_start_migration(docker)

        # Test ExportImport
        results["export_import"] = await test_export_import_migration(docker)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name}: {status}")

        all_passed = all(results.values())
        print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))

    finally:
        await docker.disconnect()
        print("\nDisconnected from Docker daemon.")


if __name__ == "__main__":
    asyncio.run(main())
