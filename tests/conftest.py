"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def docker_url() -> str:
    """Default Docker daemon URL."""
    return "unix:///var/run/docker.sock"
