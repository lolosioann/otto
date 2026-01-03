"""
Async Docker client wrapper for OTTO orchestration system.

This module provides an async interface to Docker operations using aiodocker.
It runs in parallel with the existing sync client (client.py) and provides:
- Container lifecycle management (start, stop, restart)
- Metrics collection and streaming
- Migration support (export/import)
- Async context manager protocol

All operations use aiodocker for non-blocking I/O.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiodocker
from aiodocker.exceptions import DockerError

from src.common.exceptions import (
    MigrationExportError,
    MigrationImportError,
)
from src.common.models import ContainerMetrics, ContainerSpec
from src.docker_handler.exceptions import (
    ConfigurationError,
    ContainerError,
    ContainerNotFoundError,
)

logger = logging.getLogger(__name__)


class AsyncDockerClientWrapper:
    """
    Async wrapper around aiodocker for OTTO operations.

    Provides async interface to Docker with:
    - Container lifecycle (start/stop/restart)
    - Metrics collection and streaming
    - Export/import for migration
    - Context manager support

    Parameters
    ----------
    docker_url : str, optional
        Docker daemon URL (default: unix://var/run/docker.sock)
    timeout : int, optional
        Default timeout for operations in seconds (default: 120)

    Examples
    --------
    >>> async def example():
    ...     async with AsyncDockerClientWrapper() as client:
    ...         containers = await client.list_containers()
    ...         print(f"Found {len(containers)} containers")
    >>> asyncio.run(example())
    Found 0 containers

    >>> # Manual lifecycle
    >>> client = AsyncDockerClientWrapper()
    >>> await client.connect()
    >>> info = await client.get_info()
    >>> await client.close()
    """

    def __init__(self, docker_url: str = "unix://var/run/docker.sock", timeout: int = 120):
        """
        Initialize async Docker client.

        Parameters
        ----------
        docker_url : str
            Docker daemon URL
        timeout : int
            Default operation timeout (seconds)
        """
        self.docker_url = docker_url
        self.timeout = timeout
        self._client: aiodocker.Docker | None = None
        self._connected = False
        logger.info(f"Initialized AsyncDockerClient with URL: {docker_url}")

    async def connect(self) -> None:
        """
        Connect to Docker daemon.

        Raises
        ------
        ConfigurationError
            If connection fails

        Examples
        --------
        >>> client = AsyncDockerClientWrapper()
        >>> await client.connect()
        >>> client._connected
        True
        """
        if self._connected and self._client:
            logger.debug("Already connected to Docker daemon")
            return

        try:
            self._client = aiodocker.Docker(url=self.docker_url)
            # Test connection with ping
            await self._client.version()
            self._connected = True
            logger.info("Connected to Docker daemon successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise ConfigurationError(
                f"Cannot connect to Docker daemon at {self.docker_url}",
                details={"url": self.docker_url, "error": str(e)},
            ) from e

    async def close(self) -> None:
        """
        Close Docker client connection.

        Examples
        --------
        >>> client = AsyncDockerClientWrapper()
        >>> await client.connect()
        >>> await client.close()
        >>> client._connected
        False
        """
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False
            logger.info("Closed Docker client connection")

    @property
    def client(self) -> aiodocker.Docker:
        """
        Get Docker client instance.

        Returns
        -------
        aiodocker.Docker
            Docker client

        Raises
        ------
        ConfigurationError
            If not connected

        Examples
        --------
        >>> client = AsyncDockerClientWrapper()
        >>> await client.connect()
        >>> isinstance(client.client, aiodocker.Docker)
        True
        """
        if not self._connected or not self._client:
            raise ConfigurationError(
                "Docker client not connected. Call connect() first.",
                details={"connected": self._connected},
            )
        return self._client

    async def __aenter__(self) -> "AsyncDockerClientWrapper":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # =========================================================================
    # Container Lifecycle Operations
    # =========================================================================

    async def start_container(self, spec: ContainerSpec) -> str:
        """
        Start a container from specification.

        Parameters
        ----------
        spec : ContainerSpec
            Container specification

        Returns
        -------
        str
            Container ID

        Raises
        ------
        ContainerError
            If container creation/start fails

        Examples
        --------
        >>> from src.common.models import ResourceRequirements, NFRDefinition
        >>> spec = ContainerSpec(
        ...     name="test-container",
        ...     image="nginx:latest",
        ...     resources=ResourceRequirements(cpu=1.0, memory_mb=512),
        ...     nfr=NFRDefinition(max_cpu_percent=80)
        ... )
        >>> async with AsyncDockerClientWrapper() as client:
        ...     container_id = await client.start_container(spec)
        ...     print(f"Started: {container_id}")
        Started: abc123def456
        """
        try:
            # Build container config
            config = {
                "Image": spec.image,
                "Hostname": spec.name,
                "Env": [f"{k}={v}" for k, v in spec.environment.items()],
                "HostConfig": {
                    "RestartPolicy": {"Name": spec.restart_policy},
                    "PortBindings": {
                        f"{container_port}/tcp": [{"HostPort": str(host_port)}]
                        for host_port, container_port in spec.ports.items()
                    },
                    "Binds": [f"{host}:{container}" for host, container in spec.volumes.items()],
                    # Resource limits
                    "NanoCpus": int(spec.resources.cpu * 1e9),
                    "Memory": int(spec.resources.memory_mb * 1024 * 1024),
                },
            }

            if spec.command:
                config["Cmd"] = spec.command

            # Create and start container
            container = await self.client.containers.create(config, name=spec.name)
            await container.start()

            container_id = container.id
            logger.info(f"Started container: {spec.name} ({container_id})")
            return container_id

        except DockerError as e:
            logger.error(f"Failed to start container {spec.name}: {e}")
            raise ContainerError(
                f"Failed to start container: {spec.name}",
                details={"spec": spec.name, "error": str(e)},
            ) from e

    async def stop_container(
        self, container_id: str, timeout: int = 10, force: bool = False
    ) -> None:
        """
        Stop a running container.

        Parameters
        ----------
        container_id : str
            Container ID or name
        timeout : int
            Seconds to wait before killing (default: 10)
        force : bool
            Force kill without graceful shutdown (default: False)

        Raises
        ------
        ContainerNotFoundError
            If container doesn't exist
        ContainerError
            If stop operation fails

        Examples
        --------
        >>> async with AsyncDockerClientWrapper() as client:
        ...     await client.stop_container("test-container", timeout=5)
        """
        try:
            container = await self.client.containers.get(container_id)

            if force:
                await container.kill()
                logger.info(f"Force killed container: {container_id}")
            else:
                await container.stop(timeout=timeout)
                logger.info(f"Stopped container: {container_id}")

        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                raise ContainerNotFoundError(
                    f"Container not found: {container_id}",
                    details={"container_id": container_id},
                ) from e
            raise ContainerError(
                f"Failed to stop container: {container_id}",
                details={"container_id": container_id, "error": str(e)},
            ) from e

    async def restart_container(self, container_id: str, timeout: int = 10) -> None:
        """
        Restart a container.

        Parameters
        ----------
        container_id : str
            Container ID or name
        timeout : int
            Seconds to wait before killing (default: 10)

        Raises
        ------
        ContainerNotFoundError
            If container doesn't exist
        ContainerError
            If restart fails

        Examples
        --------
        >>> async with AsyncDockerClientWrapper() as client:
        ...     await client.restart_container("test-container")
        """
        try:
            container = await self.client.containers.get(container_id)
            await container.restart(timeout=timeout)
            logger.info(f"Restarted container: {container_id}")

        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                raise ContainerNotFoundError(
                    f"Container not found: {container_id}",
                    details={"container_id": container_id},
                ) from e
            raise ContainerError(
                f"Failed to restart container: {container_id}",
                details={"container_id": container_id, "error": str(e)},
            ) from e

    async def list_containers(self, all: bool = False) -> list[dict[str, Any]]:
        """
        List containers.

        Parameters
        ----------
        all : bool
            Include stopped containers (default: False)

        Returns
        -------
        list[dict[str, Any]]
            List of container info dicts

        Raises
        ------
        ContainerError
            If listing fails

        Examples
        --------
        >>> async with AsyncDockerClientWrapper() as client:
        ...     containers = await client.list_containers()
        ...     len(containers)
        0
        """
        try:
            containers = await self.client.containers.list(all=all)
            result = []
            for container in containers:
                info = await container.show()
                result.append(info)
            return result

        except DockerError as e:
            raise ContainerError(
                "Failed to list containers",
                details={"error": str(e)},
            ) from e

    # =========================================================================
    # Metrics Operations
    # =========================================================================

    async def get_container_stats(self, container_id: str) -> ContainerMetrics:
        """
        Get current resource usage statistics for a container.

        Parameters
        ----------
        container_id : str
            Container ID or name

        Returns
        -------
        ContainerMetrics
            Current metrics

        Raises
        ------
        ContainerNotFoundError
            If container doesn't exist
        ContainerError
            If stats retrieval fails

        Examples
        --------
        >>> async with AsyncDockerClientWrapper() as client:
        ...     metrics = await client.get_container_stats("test-container")
        ...     print(f"CPU: {metrics.cpu_percent}%")
        CPU: 45.5%
        """
        try:
            container = await self.client.containers.get(container_id)

            # Get one stats snapshot
            stats = await container.stats(stream=False)

            # Parse stats into ContainerMetrics
            metrics = self._parse_stats(container_id, stats)
            return metrics

        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                raise ContainerNotFoundError(
                    f"Container not found: {container_id}",
                    details={"container_id": container_id},
                ) from e
            raise ContainerError(
                f"Failed to get stats for container: {container_id}",
                details={"container_id": container_id, "error": str(e)},
            ) from e

    async def stream_stats(
        self, container_id: str, interval_seconds: float = 1.0
    ) -> AsyncIterator[ContainerMetrics]:
        """
        Stream container statistics.

        Parameters
        ----------
        container_id : str
            Container ID or name
        interval_seconds : float
            Time between stat collections (default: 1.0)

        Yields
        ------
        ContainerMetrics
            Metrics snapshots

        Raises
        ------
        ContainerNotFoundError
            If container doesn't exist
        ContainerError
            If streaming fails

        Examples
        --------
        >>> async with AsyncDockerClientWrapper() as client:
        ...     async for metrics in client.stream_stats("test-container"):
        ...         print(f"CPU: {metrics.cpu_percent}%")
        ...         if metrics.cpu_percent > 80:
        ...             break
        CPU: 45.5%
        CPU: 62.3%
        CPU: 85.1%
        """
        try:
            container = await self.client.containers.get(container_id)

            while True:
                stats = await container.stats(stream=False)
                metrics = self._parse_stats(container_id, stats)
                yield metrics
                await asyncio.sleep(interval_seconds)

        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                raise ContainerNotFoundError(
                    f"Container not found: {container_id}",
                    details={"container_id": container_id},
                ) from e
            raise ContainerError(
                f"Failed to stream stats for container: {container_id}",
                details={"container_id": container_id, "error": str(e)},
            ) from e

    def _parse_stats(self, container_id: str, stats: dict[str, Any]) -> ContainerMetrics:
        """Parse Docker stats into ContainerMetrics model."""
        # Calculate CPU percentage
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        )
        num_cpus = stats["cpu_stats"]["online_cpus"]
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0

        # Memory stats
        memory_used_mb = stats["memory_stats"]["usage"] / (1024 * 1024)
        memory_limit_mb = stats["memory_stats"]["limit"] / (1024 * 1024)

        # Network stats
        networks = stats.get("networks", {})
        network_rx = sum(net["rx_bytes"] for net in networks.values())
        network_tx = sum(net["tx_bytes"] for net in networks.values())

        # Block I/O stats
        blkio = stats.get("blkio_stats", {}).get("io_service_bytes_recursive", [])
        block_read = sum(entry["value"] for entry in blkio if entry.get("op") == "Read")
        block_write = sum(entry["value"] for entry in blkio if entry.get("op") == "Write")

        return ContainerMetrics(
            container_id=container_id,
            timestamp=datetime.now(UTC),
            cpu_percent=cpu_percent,
            memory_used_mb=memory_used_mb,
            memory_limit_mb=memory_limit_mb,
            network_rx_bytes=network_rx,
            network_tx_bytes=network_tx,
            block_read_bytes=block_read,
            block_write_bytes=block_write,
        )

    # =========================================================================
    # Migration Support Operations
    # =========================================================================

    async def export_container(self, container_id: str, output_path: Path) -> Path:
        """
        Export container filesystem as tarball.

        Parameters
        ----------
        container_id : str
            Container ID or name
        output_path : Path
            Where to save tarball

        Returns
        -------
        Path
            Path to exported tarball

        Raises
        ------
        ContainerNotFoundError
            If container doesn't exist
        MigrationExportError
            If export fails

        Examples
        --------
        >>> from pathlib import Path
        >>> async with AsyncDockerClientWrapper() as client:
        ...     tarball = await client.export_container("test", Path("/tmp/test.tar"))
        ...     print(f"Exported to: {tarball}")
        Exported to: /tmp/test.tar
        """
        try:
            container = await self.client.containers.get(container_id)

            # Export container
            export_data = await container.export()

            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                async for chunk in export_data:
                    f.write(chunk)

            logger.info(f"Exported container {container_id} to {output_path}")
            return output_path

        except aiodocker.exceptions.DockerError as e:
            if e.status == 404:
                raise ContainerNotFoundError(
                    f"Container not found: {container_id}",
                    details={"container_id": container_id},
                ) from e
            raise MigrationExportError(
                f"Failed to export container: {container_id}",
                details={"container_id": container_id, "error": str(e)},
            ) from e
        except OSError as e:
            raise MigrationExportError(
                f"Failed to write export file: {output_path}",
                details={"output_path": str(output_path), "error": str(e)},
            ) from e

    async def import_image(self, tarball_path: Path) -> str:
        """
        Import image from tarball.

        Parameters
        ----------
        tarball_path : Path
            Path to tarball created by export_container

        Returns
        -------
        str
            Imported image ID

        Raises
        ------
        MigrationImportError
            If import fails

        Examples
        --------
        >>> from pathlib import Path
        >>> async with AsyncDockerClientWrapper() as client:
        ...     image_id = await client.import_image(Path("/tmp/test.tar"))
        ...     print(f"Imported: {image_id}")
        Imported: sha256:abc123...
        """
        try:
            # Read tarball
            with open(tarball_path, "rb") as f:
                tarball_data = f.read()

            # Import image
            result = await self.client.images.import_image(tarball_data)
            image_id = result  # Image ID or tag

            logger.info(f"Imported image from {tarball_path}: {image_id}")
            return image_id

        except OSError as e:
            raise MigrationImportError(
                f"Failed to read tarball: {tarball_path}",
                details={"tarball_path": str(tarball_path), "error": str(e)},
            ) from e
        except DockerError as e:
            raise MigrationImportError(
                f"Failed to import image from {tarball_path}",
                details={"tarball_path": str(tarball_path), "error": str(e)},
            ) from e

    # =========================================================================
    # System Operations
    # =========================================================================

    async def ping(self) -> bool:
        """
        Ping Docker daemon.

        Returns
        -------
        bool
            True if daemon responds

        Raises
        ------
        ContainerError
            If ping fails

        Examples
        --------
        >>> async with AsyncDockerClientWrapper() as client:
        ...     alive = await client.ping()
        ...     print(f"Docker daemon alive: {alive}")
        Docker daemon alive: True
        """
        try:
            await self.client.version()
            return True
        except DockerError as e:
            raise ContainerError(
                "Failed to ping Docker daemon",
                details={"error": str(e)},
            ) from e

    async def get_info(self) -> dict[str, Any]:
        """
        Get Docker daemon system information.

        Returns
        -------
        dict[str, Any]
            System information

        Raises
        ------
        ContainerError
            If info retrieval fails

        Examples
        --------
        >>> async with AsyncDockerClientWrapper() as client:
        ...     info = await client.get_info()
        ...     print(f"Containers: {info['Containers']}")
        Containers: 5
        """
        try:
            info = await self.client.system.info()
            return info
        except DockerError as e:
            raise ContainerError(
                "Failed to get Docker info",
                details={"error": str(e)},
            ) from e
