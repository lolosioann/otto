Quick Start Guide
=================

This guide will help you get started with Otto's Docker handler module.

Installation
------------

Prerequisites:

* Python 3.10 or higher
* Docker daemon running locally or remotely
* ``uv`` package manager

Install Otto:

.. code-block:: bash

   git clone <repo-url>
   cd otto
   uv sync --all-extras

Basic Usage
-----------

Connecting to Docker
~~~~~~~~~~~~~~~~~~~~

The :py:class:`~docker_handler.client.DockerClientWrapper` handles connection management:

.. doctest::

   >>> from docker_handler import DockerClientWrapper
   >>>
   >>> # Connect to local Docker daemon (uses environment variables)
   >>> client = DockerClientWrapper()
   >>>
   >>> # Verify connection
   >>> client.ping()
   True

You can also specify a custom Docker daemon URL:

.. code-block:: python

   # Connect to remote Docker daemon
   client = DockerClientWrapper(base_url="tcp://192.168.1.100:2375")

Listing Containers
~~~~~~~~~~~~~~~~~~

Get all running containers:

.. doctest::

   >>> from docker_handler import DockerClientWrapper
   >>> client = DockerClientWrapper()
   >>>
   >>> # List only running containers
   >>> containers = client.list_containers()
   >>> isinstance(containers, list)
   True
   >>>
   >>> # List all containers (including stopped)
   >>> all_containers = client.list_containers(all=True)
   >>> isinstance(all_containers, list)
   True

Filter containers by label:

.. code-block:: python

   # Get containers with specific label
   filtered = client.list_containers(
       filters={"label": "app=web"}
   )

Getting Container Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve a specific container:

.. code-block:: python

   try:
       container = client.get_container("my-container")
       print(f"Container: {container.name}")
       print(f"Status: {container.status}")
   except ContainerNotFoundError:
       print("Container not found")

Docker System Information
~~~~~~~~~~~~~~~~~~~~~~~~~

Get Docker daemon info:

.. doctest::

   >>> from docker_handler import DockerClientWrapper
   >>> client = DockerClientWrapper()
   >>>
   >>> # Get system information
   >>> info = client.get_info()
   >>> 'Containers' in info
   True
   >>>
   >>> # Get version information
   >>> version = client.get_version()
   >>> 'Version' in version
   True

Using Context Managers
~~~~~~~~~~~~~~~~~~~~~~

Always use context managers for proper cleanup:

.. code-block:: python

   from docker_handler import DockerClientWrapper

   with DockerClientWrapper() as client:
       containers = client.list_containers()
       for container in containers:
           print(f"{container.name}: {container.status}")
   # Connection automatically closed

Error Handling
~~~~~~~~~~~~~~

Otto provides detailed exceptions. See :doc:`guides/error_handling` for details:

.. code-block:: python

   from docker_handler import (
       DockerClientWrapper,
       ContainerNotFoundError,
       ConfigurationError,
   )

   try:
       client = DockerClientWrapper()
       container = client.get_container("nonexistent")
   except ContainerNotFoundError as e:
       print(f"Not found: {e}")
       print(f"Details: {e.details}")
   except ConfigurationError as e:
       print(f"Config error: {e}")

Next Steps
----------

* Read the :doc:`guides/error_handling` guide
* Explore the :doc:`api/docker_handler` API reference
* Check out :doc:`guides/context_managers` for advanced patterns
