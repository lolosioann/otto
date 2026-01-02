"""Tests for docker_handler.client module."""

from unittest.mock import Mock

import pytest
from docker.errors import APIError, DockerException, NotFound

from docker_handler.client import DockerClientWrapper
from docker_handler.exceptions import (
    ConfigurationError,
    ContainerError,
    ContainerNotFoundError,
)


class TestDockerClientWrapperInit:
    """Tests for DockerClientWrapper initialization."""

    def test_init_default_parameters(self, mock_docker_from_env):
        """Test initialization with default parameters."""
        client = DockerClientWrapper()
        assert client.base_url is None
        assert client.tls is None
        assert client.timeout == 60
        assert client.kwargs == {}

    def test_init_with_base_url(self, mock_docker_client_class):
        """Test initialization with base_url."""
        client = DockerClientWrapper(base_url="tcp://192.168.1.100:2375")
        assert client.base_url == "tcp://192.168.1.100:2375"

    def test_init_with_timeout(self, mock_docker_from_env):
        """Test initialization with custom timeout."""
        client = DockerClientWrapper(timeout=120)
        assert client.timeout == 120

    def test_init_with_kwargs(self, mock_docker_from_env):
        """Test initialization with additional kwargs."""
        client = DockerClientWrapper(version="1.41")
        assert client.kwargs == {"version": "1.41"}

    def test_init_connects_to_docker(self, mock_docker_from_env):
        """Test that initialization connects to Docker."""
        client = DockerClientWrapper()
        # _client should be set after initialization
        assert client._client is not None

    def test_init_calls_ping(self, mock_docker_from_env):
        """Test that initialization pings Docker daemon."""
        DockerClientWrapper()
        mock_docker_from_env.ping.assert_called_once()

    def test_init_with_connection_error(self, monkeypatch):
        """Test initialization when Docker connection fails."""
        import docker

        def mock_from_env(*args, **kwargs):
            raise DockerException("Connection refused")

        monkeypatch.setattr(docker, "from_env", mock_from_env)

        with pytest.raises(ConfigurationError) as exc_info:
            DockerClientWrapper()

        assert "Cannot connect to Docker daemon" in str(exc_info.value)
        assert "error" in exc_info.value.details


class TestDockerClientWrapperConnection:
    """Tests for Docker client connection management."""

    def test_connect_with_base_url(self, mock_docker_client_class):
        """Test _connect with base_url."""
        client = DockerClientWrapper(base_url="tcp://localhost:2375")
        assert client._client is not None

    def test_connect_from_env(self, mock_docker_from_env):
        """Test _connect using environment variables."""
        client = DockerClientWrapper()
        assert client._client is not None

    def test_client_property_returns_client(self, mock_docker_from_env):
        """Test that client property returns the Docker client."""
        wrapper = DockerClientWrapper()
        client = wrapper.client
        assert client is not None

    def test_client_property_connects_if_none(self, mock_docker_from_env):
        """Test that client property connects if _client is None."""
        wrapper = DockerClientWrapper()
        wrapper._client = None
        client = wrapper.client
        assert client is not None

    def test_client_property_raises_if_cannot_connect(self, monkeypatch):
        """Test client property raises if connection fails."""
        wrapper = DockerClientWrapper.__new__(DockerClientWrapper)
        wrapper._client = None
        wrapper.base_url = None
        wrapper.tls = None
        wrapper.timeout = 60
        wrapper.kwargs = {}

        import docker

        def mock_from_env(*args, **kwargs):
            raise DockerException("Connection failed")

        monkeypatch.setattr(docker, "from_env", mock_from_env)

        with pytest.raises(ConfigurationError):
            _ = wrapper.client

    def test_client_property_raises_if_client_none_after_connect(self, monkeypatch):
        """Test client property raises if _client is None after _connect()."""
        wrapper = DockerClientWrapper.__new__(DockerClientWrapper)
        wrapper._client = None
        wrapper.base_url = None
        wrapper.tls = None
        wrapper.timeout = 60
        wrapper.kwargs = {}

        # Mock _connect to not set _client and not raise exception
        def mock_connect(self):
            pass  # Does nothing - leaves _client as None

        monkeypatch.setattr(DockerClientWrapper, "_connect", mock_connect)

        with pytest.raises(ConfigurationError) as exc_info:
            _ = wrapper.client

        assert "Docker client not initialized" in str(exc_info.value)


class TestDockerClientWrapperGetContainer:
    """Tests for get_container method."""

    def test_get_container_success(self, mock_docker_from_env, mock_container):
        """Test successful container retrieval."""
        mock_docker_from_env.containers.get.return_value = mock_container

        client = DockerClientWrapper()
        container = client.get_container("test-container")

        assert container == mock_container
        mock_docker_from_env.containers.get.assert_called_once_with("test-container")

    def test_get_container_not_found(self, mock_docker_from_env):
        """Test get_container when container doesn't exist."""
        mock_docker_from_env.containers.get.side_effect = NotFound("Container not found")

        client = DockerClientWrapper()

        with pytest.raises(ContainerNotFoundError) as exc_info:
            client.get_container("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "container_id" in exc_info.value.details

    def test_get_container_api_error(self, mock_docker_from_env):
        """Test get_container with API error."""
        mock_docker_from_env.containers.get.side_effect = APIError("API error")

        client = DockerClientWrapper()

        with pytest.raises(ContainerError) as exc_info:
            client.get_container("test")

        assert "error" in exc_info.value.details


class TestDockerClientWrapperListContainers:
    """Tests for list_containers method."""

    def test_list_containers_default(self, mock_docker_from_env, mock_container):
        """Test listing containers with default parameters."""
        mock_docker_from_env.containers.list.return_value = [mock_container]

        client = DockerClientWrapper()
        containers = client.list_containers()

        assert len(containers) == 1
        assert containers[0] == mock_container
        mock_docker_from_env.containers.list.assert_called_once_with(all=False, filters=None)

    def test_list_containers_all(self, mock_docker_from_env, mock_container):
        """Test listing all containers including stopped."""
        mock_docker_from_env.containers.list.return_value = [mock_container]

        client = DockerClientWrapper()
        containers = client.list_containers(all=True)

        assert len(containers) == 1
        mock_docker_from_env.containers.list.assert_called_once_with(all=True, filters=None)

    def test_list_containers_with_filters(self, mock_docker_from_env, mock_container):
        """Test listing containers with filters."""
        filters = {"label": "app=web"}
        mock_docker_from_env.containers.list.return_value = [mock_container]

        client = DockerClientWrapper()
        containers = client.list_containers(filters=filters)

        assert len(containers) == 1
        mock_docker_from_env.containers.list.assert_called_once_with(all=False, filters=filters)

    def test_list_containers_empty(self, mock_docker_from_env):
        """Test listing containers when none exist."""
        mock_docker_from_env.containers.list.return_value = []

        client = DockerClientWrapper()
        containers = client.list_containers()

        assert len(containers) == 0
        assert containers == []

    def test_list_containers_api_error(self, mock_docker_from_env):
        """Test list_containers with API error."""
        mock_docker_from_env.containers.list.side_effect = APIError("API error")

        client = DockerClientWrapper()

        with pytest.raises(ContainerError) as exc_info:
            client.list_containers()

        assert "Error listing containers" in str(exc_info.value)


class TestDockerClientWrapperPing:
    """Tests for ping method."""

    def test_ping_success(self, mock_docker_from_env):
        """Test successful ping."""
        mock_docker_from_env.ping.return_value = True

        client = DockerClientWrapper()
        result = client.ping()

        assert result is True

    def test_ping_failure(self, mock_docker_from_env):
        """Test ping when Docker daemon is unreachable."""
        # Let initialization succeed, then make ping fail
        client = DockerClientWrapper()

        # Now make ping fail for subsequent calls
        mock_docker_from_env.ping.side_effect = DockerException("Connection refused")
        result = client.ping()

        assert result is False


class TestDockerClientWrapperGetInfo:
    """Tests for get_info method."""

    def test_get_info_success(self, mock_docker_from_env):
        """Test successful get_info."""
        info_data = {
            "Containers": 10,
            "Images": 5,
            "ServerVersion": "20.10.0",
        }
        mock_docker_from_env.info.return_value = info_data

        client = DockerClientWrapper()
        info = client.get_info()

        assert info == info_data
        assert info["Containers"] == 10

    def test_get_info_api_error(self, mock_docker_from_env):
        """Test get_info with API error."""
        mock_docker_from_env.info.side_effect = APIError("API error")

        client = DockerClientWrapper()

        with pytest.raises(Exception) as exc_info:
            client.get_info()

        assert "Error getting Docker info" in str(exc_info.value)


class TestDockerClientWrapperGetVersion:
    """Tests for get_version method."""

    def test_get_version_success(self, mock_docker_from_env):
        """Test successful get_version."""
        version_data = {
            "Version": "20.10.0",
            "ApiVersion": "1.41",
            "GoVersion": "go1.16",
        }
        mock_docker_from_env.version.return_value = version_data

        client = DockerClientWrapper()
        version = client.get_version()

        assert version == version_data
        assert version["Version"] == "20.10.0"

    def test_get_version_api_error(self, mock_docker_from_env):
        """Test get_version with API error."""
        mock_docker_from_env.version.side_effect = APIError("API error")

        client = DockerClientWrapper()

        with pytest.raises(Exception) as exc_info:
            client.get_version()

        assert "Error getting Docker version" in str(exc_info.value)


class TestDockerClientWrapperHandleErrors:
    """Tests for handle_errors context manager."""

    def test_handle_errors_success(self, mock_docker_from_env):
        """Test handle_errors with successful operation."""
        client = DockerClientWrapper()

        with client.handle_errors("test operation"):
            pass  # No exception

    def test_handle_errors_not_found(self, mock_docker_from_env):
        """Test handle_errors with NotFound exception."""
        client = DockerClientWrapper()

        with (
            pytest.raises(ContainerNotFoundError) as exc_info,
            client.handle_errors("finding container"),
        ):
            raise NotFound("Container not found")

        assert "finding container" in str(exc_info.value)
        assert "operation" in exc_info.value.details

    def test_handle_errors_api_error(self, mock_docker_from_env):
        """Test handle_errors with APIError."""
        client = DockerClientWrapper()

        with pytest.raises(ContainerError) as exc_info, client.handle_errors("starting container"):
            raise APIError("Permission denied")

        assert "starting container" in str(exc_info.value)
        assert "operation" in exc_info.value.details

    def test_handle_errors_docker_exception(self, mock_docker_from_env):
        """Test handle_errors with generic DockerException."""
        client = DockerClientWrapper()

        with pytest.raises(Exception) as exc_info, client.handle_errors("docker operation"):
            raise DockerException("Generic error")

        assert "docker operation" in str(exc_info.value)


class TestDockerClientWrapperContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_enter_exit(self, mock_docker_from_env):
        """Test using DockerClientWrapper as context manager."""
        with DockerClientWrapper() as client:
            assert client is not None
            assert client._client is not None

    def test_context_manager_calls_close(self, mock_docker_from_env):
        """Test that context manager calls close on exit."""
        mock_client = mock_docker_from_env
        mock_client.close = Mock()

        with DockerClientWrapper():
            pass

        mock_client.close.assert_called_once()

    def test_context_manager_with_exception(self, mock_docker_from_env):
        """Test context manager cleanup when exception occurs."""
        mock_client = mock_docker_from_env
        mock_client.close = Mock()

        try:
            with DockerClientWrapper():
                raise ValueError("Test error")
        except ValueError:
            pass

        mock_client.close.assert_called_once()


class TestDockerClientWrapperClose:
    """Tests for close method."""

    def test_close_when_client_exists(self, mock_docker_from_env):
        """Test closing when client exists."""
        mock_client = mock_docker_from_env
        mock_client.close = Mock()

        client = DockerClientWrapper()
        client.close()

        mock_client.close.assert_called_once()
        assert client._client is None

    def test_close_when_client_none(self, mock_docker_from_env):
        """Test closing when client is None."""
        client = DockerClientWrapper()
        client._client = None

        # Should not raise exception
        client.close()
        assert client._client is None

    def test_del_calls_close(self, mock_docker_from_env):
        """Test that __del__ calls close."""
        mock_client = mock_docker_from_env
        mock_client.close = Mock()

        client = DockerClientWrapper()
        client.__del__()

        mock_client.close.assert_called_once()
