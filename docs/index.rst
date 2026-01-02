Otto CLI Documentation
======================

**Otto** is a Python CLI tool for monitoring and orchestrating Docker containers.

.. note::
   This project is in early development (v0.1.0). The API is subject to change.

Features
--------

* **Connection management**: Automatic Docker daemon connection with error handling
* **Type-safe**: Full type hints with strict mypy checking
* **Context managers**: Safe resource cleanup
* **Custom exceptions**: Detailed error information with context
* **Well-documented**: NumPy-style docstrings throughout

Quick Start
-----------

Installation:

.. code-block:: bash

   # Clone and install with uv
   git clone <repo-url>
   cd otto
   uv sync --all-extras

Basic usage:

.. doctest::

   >>> from docker_handler import DockerClientWrapper
   >>>
   >>> # Create client (connects to local Docker daemon)
   >>> client = DockerClientWrapper()
   >>>
   >>> # Check connection
   >>> client.ping()
   True
   >>>
   >>> # Get Docker version info
   >>> info = client.get_version()
   >>> 'Version' in info
   True

See :doc:`quickstart` for more detailed examples.

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   quickstart
   guides/error_handling
   guides/context_managers

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/docker_handler
   api/exceptions

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
