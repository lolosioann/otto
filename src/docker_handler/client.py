"""Docker client wrapper with connection management and error handling."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from types import TracebackType
from typing import Any

import docker
from docker import DockerClient as _DockerClient
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container

from .exceptions import (
    ConfigurationError,
    ContainerError,
    ContainerNotFoundError,
    DockerHandlerError,
)

logger = logging.getLogger(__name__)


class DockerClientWrapper:
    """
    Wrapper around Docker SDK client with enhanced error handling.

    Provides connection management and error translation.
    """

    _client: _DockerClient | None = None

    def __init__(
        self,
        base_url: str | None = None,
        tls: Any | None = None,
        timeout: int = 60,
        **kwargs: Any,
    ) -> None:
        """
        Initialize Docker client wrapper.

        Args:
            base_url: Docker daemon URL (default: from environment)
            tls: TLS configuration
            timeout: Request timeout in seconds
            **kwargs: Additional Docker client parameters
        """
        self.base_url = base_url
        self.tls = tls
        self.timeout = timeout
        self.kwargs = kwargs
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Docker daemon."""
        try:
            if self.base_url:
                self._client = docker.DockerClient(
                    base_url=self.base_url,
                    tls=self.tls,
                    timeout=self.timeout,
                    **self.kwargs,
                )
            else:
                # Use environment variables or defaults
                self._client = docker.from_env(timeout=self.timeout)

            # Verify connection
            self._client.ping()
            logger.info(f"Connected to Docker daemon at {self._client.api.base_url}")

        except DockerException as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise ConfigurationError(
                "Cannot connect to Docker daemon",
                details={"error": str(e), "base_url": self.base_url},
            ) from e

    @property
    def client(self) -> _DockerClient:
        """Get the underlying Docker client."""
        if self._client is None:
            self._connect()
        return self._client

    def get_container(self, container_id: str) -> Container:
        """
        Get container by ID or name.

        Args:
            container_id: Container ID or name

        Returns:
            Container object

        Raises:
            ContainerNotFoundError: If container doesn't exist
        """
        try:
            return self.client.containers.get(container_id)
        except NotFound as e:
            raise ContainerNotFoundError(
                f"Container not found: {container_id}",
                details={"container_id": container_id},
            ) from e
        except APIError as e:
            raise ContainerError(
                f"Error retrieving container: {e}",
                details={"container_id": container_id, "error": str(e)},
            ) from e

    def list_containers(
        self, all: bool = False, filters: dict[str, Any] | None = None
    ) -> list[Container]:
        """
        List containers.

        Args:
            all: Include stopped containers
            filters: Filters to apply

        Returns:
            List of Container objects
        """
        try:
            return self.client.containers.list(all=all, filters=filters)  # type: ignore[no-any-return]
        except APIError as e:
            raise ContainerError(f"Error listing containers: {e}", details={"error": str(e)}) from e

    def ping(self) -> bool:
        """
        Check if Docker daemon is reachable.

        Returns:
            True if daemon responds
        """
        try:
            return self.client.ping()  # type: ignore[no-any-return]
        except DockerException:
            return False

    def get_info(self) -> dict[str, Any]:
        """
        Get Docker daemon system information.

        Returns:
            System info dictionary
        """
        try:
            return self.client.info()  # type: ignore[no-any-return]
        except APIError as e:
            raise DockerHandlerError(
                f"Error getting Docker info: {e}", details={"error": str(e)}
            ) from e

    def get_version(self) -> dict[str, Any]:
        """
        Get Docker daemon version information.

        Returns:
            Version info dictionary
        """
        try:
            return self.client.version()  # type: ignore[no-any-return]
        except APIError as e:
            raise DockerHandlerError(
                f"Error getting Docker version: {e}", details={"error": str(e)}
            ) from e

    @contextmanager
    def handle_errors(self, operation: str) -> Generator[None, None, None]:
        """
        Context manager for consistent error handling.

        Args:
            operation: Description of operation being performed

        Yields:
            None

        Example:
            with client.handle_errors("starting container"):
                container.start()
        """
        try:
            yield
        except NotFound as e:
            raise ContainerNotFoundError(
                f"Container not found during {operation}",
                details={"operation": operation, "error": str(e)},
            ) from e
        except APIError as e:
            raise ContainerError(
                f"Docker API error during {operation}: {e}",
                details={"operation": operation, "error": str(e)},
            ) from e
        except DockerException as e:
            raise DockerHandlerError(
                f"Docker error during {operation}: {e}",
                details={"operation": operation, "error": str(e)},
            ) from e

    def close(self) -> None:
        """Close connection to Docker daemon."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Closed Docker client connection")

    def __enter__(self) -> "DockerClientWrapper":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
