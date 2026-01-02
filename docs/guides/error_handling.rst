Error Handling Guide
====================

Otto uses a custom exception hierarchy for clear, actionable error messages.

Exception Hierarchy
-------------------

All Otto exceptions inherit from :py:exc:`~docker_handler.exceptions.DockerHandlerError`:

.. code-block:: text

   DockerHandlerError (base)
   ├── ContainerError
   │   └── ContainerNotFoundError
   └── ConfigurationError

Exception Details
-----------------

Every exception includes:

* **Message**: Human-readable error description
* **Details dict**: Contextual information (container ID, error codes, etc.)
* **Cause chain**: Original exception via ``from e``

Example:

.. doctest::

   >>> from docker_handler import DockerClientWrapper, ContainerNotFoundError
   >>> client = DockerClientWrapper()
   >>>
   >>> try:
   ...     container = client.get_container("nonexistent-container")
   ... except ContainerNotFoundError as e:
   ...     print(e.message)  # doctest: +ELLIPSIS
   ...     print(e.details['container_id'])
   Container not found: nonexistent-container
   nonexistent-container

Common Scenarios
----------------

Connection Failures
~~~~~~~~~~~~~~~~~~~

When Docker daemon is unreachable:

.. code-block:: python

   from docker_handler import DockerClientWrapper, ConfigurationError

   try:
       client = DockerClientWrapper(base_url="tcp://invalid:2375")
   except ConfigurationError as e:
       print(f"Cannot connect: {e}")
       print(f"Base URL: {e.details['base_url']}")

Container Not Found
~~~~~~~~~~~~~~~~~~~

When a container doesn't exist:

.. code-block:: python

   from docker_handler import ContainerNotFoundError

   try:
       container = client.get_container("missing-container")
   except ContainerNotFoundError as e:
       print(f"Container ID: {e.details['container_id']}")
       # Handle gracefully

API Errors
~~~~~~~~~~

Docker API errors are wrapped in :py:exc:`~docker_handler.exceptions.ContainerError`:

.. code-block:: python

   from docker_handler import ContainerError

   try:
       # Some operation that fails
       result = client.list_containers()
   except ContainerError as e:
       print(f"API error: {e}")
       print(f"Details: {e.details['error']}")

Best Practices
--------------

1. **Catch specific exceptions**: Don't catch bare ``Exception``

   .. code-block:: python

      # Good
      try:
          container = client.get_container(name)
      except ContainerNotFoundError:
          return None
      except ContainerError as e:
          logger.error(f"Failed to get container: {e}")
          raise

      # Bad
      try:
          container = client.get_container(name)
      except Exception:  # Too broad!
          pass

2. **Use exception details**: They contain useful context

   .. code-block:: python

      except ContainerError as e:
          logger.error(
              "Container operation failed",
              extra={"details": e.details}
          )

3. **Let exceptions propagate**: Don't swallow errors silently

   .. code-block:: python

      # Good - caller can handle
      def get_container_status(container_id: str) -> str:
          container = client.get_container(container_id)
          return container.status

      # Bad - hides errors
      def get_container_status(container_id: str) -> str:
          try:
              container = client.get_container(container_id)
              return container.status
          except:  # Never do this!
              return "unknown"

Context Manager Pattern
-----------------------

Use the :py:meth:`~docker_handler.client.DockerClientWrapper.handle_errors` context manager for consistent error handling:

.. code-block:: python

   with client.handle_errors("starting container"):
       container.start()
   # Exceptions automatically wrapped with operation context

See Also
--------

* :py:mod:`docker_handler.exceptions` - Full exception API reference
* :doc:`context_managers` - Advanced error handling patterns
* :py:class:`docker_handler.client.DockerClientWrapper` - Client API
