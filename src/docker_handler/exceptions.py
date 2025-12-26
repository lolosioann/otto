"""Custom exceptions for Docker Handler subsystem."""

from typing import Any


class DockerHandlerError(Exception):
    """Base exception for all Docker Handler errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# Container operation errors
class ContainerError(DockerHandlerError):
    """Base exception for container-related errors."""

    pass


# Configuration errors
class ConfigurationError(DockerHandlerError):
    """Raised when configuration is invalid."""

    pass


class ContainerNotFoundError(ContainerError):
    """Raised when a container cannot be found."""

    pass
