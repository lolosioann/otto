"""
Custom exceptions for OTTO orchestration system.

This module defines the exception hierarchy for distributed system errors:
- Migration failures
- Network/communication errors
- Node failures
- Cluster state inconsistencies
- NFR violations (as exceptions)

All exceptions follow the pattern from docker_handler.exceptions with
message and optional details dict for structured error information.
"""

from typing import Any


class OTTOError(Exception):
    """
    Base exception for all OTTO system errors.

    Parameters
    ----------
    message : str
        Human-readable error message
    details : dict[str, Any], optional
        Structured error details for logging/debugging

    Examples
    --------
    >>> error = OTTOError("System error", details={"component": "orchestrator"})
    >>> error.message
    'System error'
    >>> error.details["component"]
    'orchestrator'
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Initialize OTTO error.

        Parameters
        ----------
        message : str
            Error message
        details : dict[str, Any], optional
            Additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class MigrationError(OTTOError):
    """
    Base exception for migration-related errors.

    Raised when container migration operations fail.
    """

    pass


class MigrationPreparationError(MigrationError):
    """
    Raised when migration preparation fails.

    Examples include:
    - Cannot checkpoint container
    - Cannot export container filesystem
    - Source node unreachable
    """

    pass


class MigrationExportError(MigrationError):
    """
    Raised when container export fails.

    Examples include:
    - Cannot export container filesystem
    - Disk space exhausted
    - I/O errors during export
    """

    pass


class MigrationImportError(MigrationError):
    """
    Raised when container/image import fails.

    Examples include:
    - Cannot import tarball
    - Corrupted tarball
    - Invalid image format
    """

    pass


class MigrationTransferError(MigrationError):
    """
    Raised when migration transfer fails.

    Examples include:
    - Network transfer timeout
    - Corrupted checkpoint data
    - Insufficient bandwidth
    """

    pass


class MigrationRestoreError(MigrationError):
    """
    Raised when restoring container on target fails.

    Examples include:
    - Cannot restore from checkpoint
    - Cannot import container
    - Target node resource exhausted
    """

    pass


class MigrationRollbackError(MigrationError):
    """
    Raised when migration rollback fails.

    This is critical as it indicates container may be lost.
    """

    pass


class NetworkError(OTTOError):
    """
    Base exception for network/communication errors.

    Raised for MQTT, RPC, and inter-node communication failures.
    """

    pass


class MQTTConnectionError(NetworkError):
    """
    Raised when MQTT broker connection fails.

    Examples include:
    - Broker unreachable
    - Authentication failure
    - Connection timeout
    """

    pass


class RPCTimeoutError(NetworkError):
    """
    Raised when RPC call times out.

    Indicates target node may be unresponsive or overloaded.
    """

    pass


class MessageSerializationError(NetworkError):
    """
    Raised when message serialization/deserialization fails.

    Examples include:
    - Invalid JSON
    - Pydantic validation error
    - Unknown message type
    """

    pass


class NodeError(OTTOError):
    """
    Base exception for node-related errors.

    Raised for node agent failures and node management issues.
    """

    pass


class NodeNotFoundError(NodeError):
    """
    Raised when a node cannot be found in cluster state.

    May indicate node has been deregistered or failed.
    """

    pass


class NodeUnhealthyError(NodeError):
    """
    Raised when attempting operation on unhealthy node.

    Node may be degraded, failed, or unknown state.
    """

    pass


class NodeResourceExhaustedError(NodeError):
    """
    Raised when node has insufficient resources.

    Examples include:
    - CPU exhausted
    - Memory exhausted
    - No available bandwidth
    """

    pass


class HeartbeatTimeoutError(NodeError):
    """
    Raised when node heartbeat times out.

    Indicates node may have crashed or lost network connectivity.
    """

    pass


class ClusterStateError(OTTOError):
    """
    Base exception for cluster state management errors.

    Raised for inconsistencies in distributed cluster state.
    """

    pass


class ContainerPlacementError(ClusterStateError):
    """
    Raised when container placement is invalid or inconsistent.

    Examples include:
    - Container reported on multiple nodes
    - Container placement not found
    - Placement conflicts with resource constraints
    """

    pass


class StateInconsistencyError(ClusterStateError):
    """
    Raised when cluster state is inconsistent.

    Examples include:
    - Node reported metrics but not registered
    - Container running but no placement record
    - Resource usage exceeds capacity
    """

    pass


class NFRError(OTTOError):
    """
    Base exception for NFR-related errors.

    Note: NFR violations are typically handled as events, not exceptions.
    These exceptions are for NFR system failures (e.g., cannot evaluate NFRs).
    """

    pass


class NFRDefinitionError(NFRError):
    """
    Raised when NFR definition is invalid.

    Examples include:
    - Missing required NFR fields
    - Invalid threshold values
    - Conflicting NFR constraints
    """

    pass


class NFREvaluationError(NFRError):
    """
    Raised when NFR evaluation fails.

    Examples include:
    - Cannot calculate metrics
    - Missing required data
    - Evaluation timeout
    """

    pass


class ConfigurationError(OTTOError):
    """
    Raised when configuration is invalid or missing.

    Examples include:
    - Missing required config values
    - Invalid config format
    - Conflicting config settings
    """

    pass


class SpecValidationError(ConfigurationError):
    """
    Raised when container spec validation fails.

    Examples include:
    - Invalid YAML/TOML format
    - Missing required spec fields
    - Pydantic validation errors
    """

    pass
