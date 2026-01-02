"""Pytest configuration and shared fixtures."""

from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    client = MagicMock()
    client.ping.return_value = True
    client.api.base_url = "http://localhost:2375"
    return client


@pytest.fixture
def mock_docker_from_env(monkeypatch, mock_docker_client):
    """Mock docker.from_env to return a mock client."""
    import docker

    def mock_from_env(*args, **kwargs):
        return mock_docker_client

    monkeypatch.setattr(docker, "from_env", mock_from_env)
    return mock_docker_client


@pytest.fixture
def mock_docker_client_class(monkeypatch, mock_docker_client):
    """Mock docker.DockerClient class."""
    import docker

    def mock_docker_client_init(*args, **kwargs):
        return mock_docker_client

    monkeypatch.setattr(docker, "DockerClient", mock_docker_client_init)
    return mock_docker_client


@pytest.fixture
def mock_container():
    """Create a mock Docker container."""
    container = Mock()
    container.id = "abc123"
    container.name = "test-container"
    container.status = "running"
    return container
