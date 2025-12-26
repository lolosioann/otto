# otto

Docker handler library with connection management and error handling.

## Overview

Otto provides a clean Python wrapper around the Docker SDK with enhanced error handling, connection management, and a context manager interface for safe resource cleanup.

## Features

- Connection management with automatic retry logic
- Custom exception hierarchy for granular error handling
- Context manager support for safe resource cleanup
- Type hints throughout
- Comprehensive logging

## Setup

### Installation

```bash
# Clone repository
git clone https://github.com/lolosioann/otto.git
cd otto

# Install with uv
uv sync

# Or install with dependencies
uv add docker
```

### Development Setup

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black src/

# Lint
uv run ruff check src/

# Type check
uv run mypy src/
```

## Quick Start

```python
from docker_handler import DockerClientWrapper

# Basic usage
client = DockerClientWrapper()
containers = client.list_containers(all=True)

# Context manager usage (recommended)
with DockerClientWrapper() as client:
    container = client.get_container("my-container")
    info = client.get_info()

# Custom connection
client = DockerClientWrapper(
    base_url="unix://var/run/docker.sock",
    timeout=120
)
```

## Architecture

### Core Components

**DockerClientWrapper** (`src/docker_handler/client.py`)
- Main interface to Docker daemon
- Manages connection lifecycle
- Provides error translation from Docker SDK to custom exceptions
- Implements context manager protocol

**Exceptions** (`src/docker_handler/exceptions.py`)
- `DockerHandlerError`: Base exception
- `ContainerError`: Container operation failures
- `ContainerNotFoundError`: Missing container
- `ConfigurationError`: Invalid configuration

### Error Handling

All Docker SDK exceptions are caught and translated to custom exceptions with additional context:

```python
try:
    container = client.get_container("missing")
except ContainerNotFoundError as e:
    print(f"Error: {e.message}")
    print(f"Details: {e.details}")
```

## Dependencies

- `docker>=7.0.0`: Docker SDK for Python

## License

MIT
