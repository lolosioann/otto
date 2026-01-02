"""Tests for docker_handler.exceptions module."""

from docker_handler.exceptions import (
    ConfigurationError,
    ContainerError,
    ContainerNotFoundError,
    DockerHandlerError,
)


class TestDockerHandlerError:
    """Tests for DockerHandlerError base exception."""

    def test_init_with_message_only(self):
        """Test exception initialization with only message."""
        exc = DockerHandlerError("Test error")
        assert exc.message == "Test error"
        assert exc.details == {}
        assert str(exc) == "Test error"

    def test_init_with_message_and_details(self):
        """Test exception initialization with message and details."""
        details = {"key": "value", "count": 42}
        exc = DockerHandlerError("Test error", details=details)
        assert exc.message == "Test error"
        assert exc.details == details
        assert str(exc) == "Test error"

    def test_init_with_empty_details(self):
        """Test exception with empty details dict."""
        exc = DockerHandlerError("Test error", details={})
        assert exc.message == "Test error"
        assert exc.details == {}

    def test_repr(self):
        """Test exception repr."""
        exc = DockerHandlerError("Test error", details={"key": "value"})
        repr_str = repr(exc)
        assert "DockerHandlerError" in repr_str
        assert "Test error" in repr_str

    def test_inheritance(self):
        """Test that DockerHandlerError inherits from Exception."""
        exc = DockerHandlerError("Test")
        assert isinstance(exc, Exception)


class TestContainerError:
    """Tests for ContainerError exception."""

    def test_init_with_message_only(self):
        """Test ContainerError initialization."""
        exc = ContainerError("Container operation failed")
        assert exc.message == "Container operation failed"
        assert exc.details == {}

    def test_init_with_details(self):
        """Test ContainerError with details."""
        details = {"container_id": "abc123", "error": "timeout"}
        exc = ContainerError("Operation failed", details=details)
        assert exc.message == "Operation failed"
        assert exc.details == details
        assert exc.details["container_id"] == "abc123"

    def test_inheritance(self):
        """Test ContainerError inheritance."""
        exc = ContainerError("Test")
        assert isinstance(exc, DockerHandlerError)
        assert isinstance(exc, Exception)


class TestContainerNotFoundError:
    """Tests for ContainerNotFoundError exception."""

    def test_init_with_message_only(self):
        """Test ContainerNotFoundError initialization."""
        exc = ContainerNotFoundError("Container not found")
        assert exc.message == "Container not found"
        assert exc.details == {}

    def test_init_with_container_id(self):
        """Test ContainerNotFoundError with container ID in details."""
        details = {"container_id": "xyz789"}
        exc = ContainerNotFoundError("Container xyz789 not found", details=details)
        assert exc.message == "Container xyz789 not found"
        assert exc.details["container_id"] == "xyz789"

    def test_inheritance(self):
        """Test ContainerNotFoundError inheritance chain."""
        exc = ContainerNotFoundError("Test")
        assert isinstance(exc, ContainerError)
        assert isinstance(exc, DockerHandlerError)
        assert isinstance(exc, Exception)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_init_with_message_only(self):
        """Test ConfigurationError initialization."""
        exc = ConfigurationError("Invalid configuration")
        assert exc.message == "Invalid configuration"
        assert exc.details == {}

    def test_init_with_base_url(self):
        """Test ConfigurationError with base_url in details."""
        details = {"base_url": "tcp://invalid:2375", "error": "connection refused"}
        exc = ConfigurationError("Cannot connect", details=details)
        assert exc.message == "Cannot connect"
        assert exc.details["base_url"] == "tcp://invalid:2375"

    def test_inheritance(self):
        """Test ConfigurationError inheritance."""
        exc = ConfigurationError("Test")
        assert isinstance(exc, DockerHandlerError)
        assert isinstance(exc, Exception)


class TestExceptionChaining:
    """Tests for exception chaining behavior."""

    def test_exception_from_cause(self):
        """Test exception chaining with 'from'."""
        original = ValueError("Original error")
        try:
            raise ContainerError("Wrapped error") from original
        except ContainerError as exc:
            assert exc.__cause__ is original
            assert exc.message == "Wrapped error"

    def test_multiple_details_keys(self):
        """Test exception with multiple detail keys."""
        details = {
            "container_id": "test123",
            "operation": "start",
            "error_code": 500,
            "timestamp": "2025-01-02T00:00:00",
        }
        exc = ContainerError("Complex error", details=details)
        assert len(exc.details) == 4
        assert exc.details["container_id"] == "test123"
        assert exc.details["operation"] == "start"
        assert exc.details["error_code"] == 500
