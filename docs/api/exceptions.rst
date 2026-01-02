Exception Classes
=================

Otto defines a hierarchy of exceptions for clear error handling.

Exception Hierarchy
-------------------

.. code-block:: text

   DockerHandlerError
   ├── ContainerError
   │   └── ContainerNotFoundError
   └── ConfigurationError

Base Exception
--------------

.. autoclass:: docker_handler.exceptions.DockerHandlerError
   :members:
   :show-inheritance:
   :special-members: __init__

Container Exceptions
--------------------

.. autoclass:: docker_handler.exceptions.ContainerError
   :members:
   :show-inheritance:
   :special-members: __init__

.. autoclass:: docker_handler.exceptions.ContainerNotFoundError
   :members:
   :show-inheritance:
   :special-members: __init__

Configuration Exceptions
------------------------

.. autoclass:: docker_handler.exceptions.ConfigurationError
   :members:
   :show-inheritance:
   :special-members: __init__

Usage Examples
--------------

Catching specific exceptions:

.. code-block:: python

   from docker_handler import (
       DockerClientWrapper,
       ContainerNotFoundError,
       ConfigurationError,
   )

   try:
       client = DockerClientWrapper()
       container = client.get_container("my-app")
   except ContainerNotFoundError as e:
       print(f"Container not found: {e.details['container_id']}")
   except ConfigurationError as e:
       print(f"Cannot connect to Docker: {e}")

Exception Details
-----------------

All exceptions provide:

* ``message``: Human-readable error message
* ``details``: Dictionary with context (container IDs, URLs, error codes)
* ``__cause__``: Original exception from Docker SDK (via ``from e``)

Example:

.. doctest::

   >>> from docker_handler.exceptions import ContainerNotFoundError
   >>>
   >>> exc = ContainerNotFoundError(
   ...     "Container xyz not found",
   ...     details={"container_id": "xyz", "status": 404}
   ... )
   >>> exc.message
   'Container xyz not found'
   >>> exc.details['container_id']
   'xyz'

See Also
--------

* :doc:`../guides/error_handling` - Comprehensive error handling guide
* :py:class:`docker_handler.client.DockerClientWrapper` - Client that raises these exceptions
