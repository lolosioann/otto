"""Container migration strategies for Otto.

Provides different strategies for migrating containers between nodes:
- StopStart: Simple stop on source, start on target (no state)
- ExportImport: Export filesystem, transfer, import (filesystem state)
- CRIU: Checkpoint/restore (full state, experimental)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.dockerhandler import DockerManager


class MigrationStrategy(Enum):
    """Available migration strategies."""

    STOP_START = "stop_start"
    EXPORT_IMPORT = "export_import"
    CRIU = "criu"


@dataclass
class ContainerSpec:
    """Specification for recreating a container."""

    image: str
    name: str
    env: dict[str, str] = field(default_factory=dict)
    ports: dict[str, int] = field(default_factory=dict)
    volumes: dict[str, str] = field(default_factory=dict)
    command: str | None = None


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    source_container_id: str
    target_container_id: str | None
    strategy: MigrationStrategy
    message: str
    metrics: dict[str, Any] = field(default_factory=dict)


class MigrationExecutor(ABC):
    """Abstract base class for migration strategies."""

    def __init__(self, docker: DockerManager):
        self.docker = docker

    @abstractmethod
    async def export_container(self, container_id: str) -> bytes | None:
        """Export container state for transfer.

        Returns None if strategy doesn't require export (e.g., stop/start).
        """
        pass

    @abstractmethod
    async def import_container(self, spec: ContainerSpec, data: bytes | None) -> str:
        """Import container state and create new container.

        Returns the new container ID.
        """
        pass

    @property
    @abstractmethod
    def strategy(self) -> MigrationStrategy:
        """Return the strategy type."""
        pass


class StopStartMigration(MigrationExecutor):
    """Simple migration: stop on source, recreate on target.

    No state is preserved. Suitable for stateless services.
    """

    @property
    def strategy(self) -> MigrationStrategy:
        return MigrationStrategy.STOP_START

    async def export_container(self, container_id: str) -> bytes | None:
        """Stop container, no data to export."""
        await self.docker.stop_container(container_id)
        return None

    async def import_container(self, spec: ContainerSpec, data: bytes | None) -> str:
        """Create and start container from spec."""
        container_id = await self.docker.create_container(
            image=spec.image,
            name=spec.name,
        )
        return container_id


class ExportImportMigration(MigrationExecutor):
    """Migration via docker export/import.

    Preserves filesystem state but not memory state.
    Suitable for containers with persistent data.
    """

    @property
    def strategy(self) -> MigrationStrategy:
        return MigrationStrategy.EXPORT_IMPORT

    async def export_container(self, container_id: str) -> bytes | None:
        """Stop and export container filesystem as tarball."""
        await self.docker.stop_container(container_id)
        data = await self.docker.export_container(container_id)
        return data

    async def import_container(self, spec: ContainerSpec, data: bytes | None) -> str:
        """Import tarball as image and create container."""
        if data is None:
            raise ValueError("ExportImport strategy requires export data")
        # Import as new image with migrated_ prefix
        image_name = f"migrated_{spec.name}"
        await self.docker.import_image(data, repository=image_name, tag="latest")
        # Create and start container from imported image
        # Imported images need explicit command since metadata is lost
        command = spec.command or "sh"
        container_id = await self.docker.create_container(
            image=f"{image_name}:latest",
            name=spec.name,
            command=command,
        )
        return container_id


class CRIUMigration(MigrationExecutor):
    """Migration via CRIU checkpoint/restore.

    Preserves full state including memory. Experimental.
    Requires CRIU support in Docker daemon.
    """

    @property
    def strategy(self) -> MigrationStrategy:
        return MigrationStrategy.CRIU

    async def export_container(self, container_id: str) -> bytes | None:
        """Checkpoint container with CRIU."""
        # TODO: Implement checkpoint
        # await self.docker.checkpoint_container(container_id, checkpoint_name)
        # return checkpoint_data
        raise NotImplementedError("CRIU checkpoint not yet implemented")

    async def import_container(self, spec: ContainerSpec, data: bytes | None) -> str:
        """Restore container from CRIU checkpoint."""
        # TODO: Implement restore
        raise NotImplementedError("CRIU restore not yet implemented")


def get_migration_executor(strategy: MigrationStrategy, docker: DockerManager) -> MigrationExecutor:
    """Factory function to get appropriate migration executor."""
    executors = {
        MigrationStrategy.STOP_START: StopStartMigration,
        MigrationStrategy.EXPORT_IMPORT: ExportImportMigration,
        MigrationStrategy.CRIU: CRIUMigration,
    }
    executor_class = executors.get(strategy)
    if executor_class is None:
        raise ValueError(f"Unknown migration strategy: {strategy}")
    return executor_class(docker)
