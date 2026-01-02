Changelog
=========

All notable changes to Otto will be documented in this file.

Version 0.1.0 (2025-01-02)
--------------------------

Initial release.

Features
~~~~~~~~

* Docker client wrapper with connection management
* Custom exception hierarchy with detailed error context
* Context manager support for safe resource cleanup
* Type-safe API with full mypy coverage
* NumPy-style docstrings throughout
* Comprehensive documentation with Sphinx

API
~~~

* :py:class:`docker_handler.client.DockerClientWrapper` - Main client class
* :py:exc:`docker_handler.exceptions.DockerHandlerError` - Base exception
* :py:exc:`docker_handler.exceptions.ContainerError` - Container operation errors
* :py:exc:`docker_handler.exceptions.ContainerNotFoundError` - Container not found
* :py:exc:`docker_handler.exceptions.ConfigurationError` - Configuration errors

Development
~~~~~~~~~~~

* CI/CD pipeline with GitHub Actions
* Pre-commit hooks (ruff, bandit, interrogate, mypy)
* Documentation testing with doctest
* Spell-checking with sphinxcontrib-spelling
* Test coverage requirements (85%)
* uv-based dependency management
