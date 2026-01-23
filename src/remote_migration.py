"""Remote container migration between Docker hosts.

Provides coordination for migrating containers between different Docker
hosts connected via SSH or Docker contexts.
"""

import time
from dataclasses import dataclass
from typing import Any

from src.dockerhandler import DockerManager
from src.migration import ContainerSpec, MigrationResult, MigrationStrategy


@dataclass
class RemoteMigrationMetrics:
    """Metrics collected during remote migration."""

    export_time_s: float = 0.0
    transfer_size_bytes: int = 0
    import_time_s: float = 0.0
    container_start_time_s: float = 0.0
    total_time_s: float = 0.0
    source_host: str = ""
    target_host: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "export_time_s": self.export_time_s,
            "transfer_size_bytes": self.transfer_size_bytes,
            "import_time_s": self.import_time_s,
            "container_start_time_s": self.container_start_time_s,
            "total_time_s": self.total_time_s,
            "source_host": self.source_host,
            "target_host": self.target_host,
        }


async def extract_container_spec(docker: DockerManager, container_id: str) -> ContainerSpec:
    """Extract ContainerSpec from a running container.

    Parameters
    ----------
    docker : DockerManager
        Docker manager connected to the host.
    container_id : str
        The container ID or name.

    Returns
    -------
    ContainerSpec
        Specification that can be used to recreate the container.
    """
    info = await docker.get_container_info(container_id)
    config = info.get("Config", {})
    host_config = info.get("HostConfig", {})

    # Extract name (remove leading /)
    name = info.get("Name", "").lstrip("/")

    # Extract image
    image = config.get("Image", "")

    # Extract environment variables
    env_list = config.get("Env", []) or []
    env = {}
    for item in env_list:
        if "=" in item:
            key, value = item.split("=", 1)
            env[key] = value

    # Extract port mappings
    port_bindings = host_config.get("PortBindings", {}) or {}
    ports = {}
    for container_port, bindings in port_bindings.items():
        if bindings:
            # Take first binding's host port
            host_port = bindings[0].get("HostPort", "")
            if host_port:
                ports[container_port] = int(host_port)

    # Extract volume mounts
    mounts = host_config.get("Binds", []) or []
    volumes = {}
    for mount in mounts:
        if ":" in mount:
            parts = mount.split(":")
            if len(parts) >= 2:
                volumes[parts[0]] = parts[1]

    # Extract command
    cmd = config.get("Cmd")
    command = None
    if cmd:
        command = " ".join(cmd) if isinstance(cmd, list) else cmd

    return ContainerSpec(
        image=image,
        name=name,
        env=env,
        ports=ports,
        volumes=volumes,
        command=command,
    )


class RemoteMigrationCoordinator:
    """Coordinates container migration between Docker hosts.

    Supports both SSH URLs and Docker contexts for remote connections.

    Parameters
    ----------
    source : DockerManager
        Docker manager for source host.
    target : DockerManager
        Docker manager for target host.

    Examples
    --------
    >>> # Using SSH URL
    >>> source = DockerManager()  # local
    >>> target = DockerManager(url="ssh://user@192.168.2.7")
    >>> coordinator = RemoteMigrationCoordinator(source, target)
    >>> result = await coordinator.migrate("my_container", MigrationStrategy.EXPORT_IMPORT)
    """

    def __init__(self, source: DockerManager, target: DockerManager):
        self.source = source
        self.target = target

    async def migrate(
        self,
        container_id: str,
        strategy: MigrationStrategy = MigrationStrategy.EXPORT_IMPORT,
        remove_source: bool = True,
    ) -> MigrationResult:
        """Migrate a container from source to target host.

        Parameters
        ----------
        container_id : str
            The container ID or name on the source host.
        strategy : MigrationStrategy
            Migration strategy to use (default: EXPORT_IMPORT).
        remove_source : bool
            Whether to remove the source container after migration.

        Returns
        -------
        MigrationResult
            Result of the migration including metrics.
        """
        metrics = RemoteMigrationMetrics(
            source_host=self.source._url,
            target_host=self.target._url,
        )
        total_start = time.perf_counter()

        try:
            # Connect to both hosts
            await self.source.connect()
            await self.target.connect()

            # Extract spec from source container
            spec = await extract_container_spec(self.source, container_id)

            if strategy == MigrationStrategy.STOP_START:
                result = await self._migrate_stop_start(container_id, spec, metrics, remove_source)
            elif strategy == MigrationStrategy.EXPORT_IMPORT:
                result = await self._migrate_export_import(
                    container_id, spec, metrics, remove_source
                )
            else:
                raise ValueError(f"Unsupported strategy for remote migration: {strategy}")

            metrics.total_time_s = time.perf_counter() - total_start
            result.metrics = metrics.to_dict()
            return result

        except Exception as e:
            metrics.total_time_s = time.perf_counter() - total_start
            return MigrationResult(
                success=False,
                source_container_id=container_id,
                target_container_id=None,
                strategy=strategy,
                message=f"Migration failed: {e}",
                metrics=metrics.to_dict(),
            )

    async def _migrate_stop_start(
        self,
        container_id: str,
        spec: ContainerSpec,
        metrics: RemoteMigrationMetrics,
        remove_source: bool,
    ) -> MigrationResult:
        """Migrate using stop/start strategy (no state transfer)."""
        # Stop source container
        export_start = time.perf_counter()
        await self.source.stop_container(container_id)
        metrics.export_time_s = time.perf_counter() - export_start

        # No data transfer for stop/start
        metrics.transfer_size_bytes = 0

        # Create container on target
        import_start = time.perf_counter()
        target_id = await self.target.create_container(
            image=spec.image,
            name=spec.name,
            command=spec.command,
        )
        metrics.import_time_s = time.perf_counter() - import_start

        # Remove source if requested
        if remove_source:
            await self.source.remove_container(container_id)

        return MigrationResult(
            success=True,
            source_container_id=container_id,
            target_container_id=target_id,
            strategy=MigrationStrategy.STOP_START,
            message="Migration completed (stop/start)",
        )

    async def _migrate_export_import(
        self,
        container_id: str,
        spec: ContainerSpec,
        metrics: RemoteMigrationMetrics,
        remove_source: bool,
    ) -> MigrationResult:
        """Migrate using export/import strategy (filesystem state)."""
        # Stop and export source container
        export_start = time.perf_counter()
        await self.source.stop_container(container_id)
        data = await self.source.export_container(container_id)
        metrics.export_time_s = time.perf_counter() - export_start
        metrics.transfer_size_bytes = len(data)

        # Import on target
        import_start = time.perf_counter()
        image_name = f"migrated_{spec.name}"
        await self.target.import_image(data, repository=image_name, tag="latest")
        metrics.import_time_s = time.perf_counter() - import_start

        # Create and start container on target
        start_time = time.perf_counter()
        command = spec.command or "sh"
        target_id = await self.target.create_container(
            image=f"{image_name}:latest",
            name=spec.name,
            command=command,
        )
        metrics.container_start_time_s = time.perf_counter() - start_time

        # Remove source if requested
        if remove_source:
            await self.source.remove_container(container_id)

        return MigrationResult(
            success=True,
            source_container_id=container_id,
            target_container_id=target_id,
            strategy=MigrationStrategy.EXPORT_IMPORT,
            message=f"Migration completed (export/import, {metrics.transfer_size_bytes} bytes)",
        )
