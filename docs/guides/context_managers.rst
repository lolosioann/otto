Context Managers
================

Otto provides context manager support for safe resource management.

Basic Usage
-----------

The :py:class:`~docker_handler.client.DockerClientWrapper` implements the context manager protocol:

.. code-block:: python

   from docker_handler import DockerClientWrapper

   with DockerClientWrapper() as client:
       containers = client.list_containers()
       # Use client...
   # Connection automatically closed

This ensures the Docker client connection is properly closed even if an exception occurs.

Manual Connection Management
-----------------------------

If you need manual control:

.. code-block:: python

   client = DockerClientWrapper()
   try:
       containers = client.list_containers()
   finally:
       client.close()

Error Handling Context
----------------------

Use :py:meth:`~docker_handler.client.DockerClientWrapper.handle_errors` for operation-specific error handling:

.. code-block:: python

   with client.handle_errors("retrieving container logs"):
       logs = container.logs()

This wraps exceptions with operation context, making debugging easier.

Nested Context Managers
------------------------

Combine multiple context managers:

.. code-block:: python

   with DockerClientWrapper() as client:
       with client.handle_errors("container operations"):
           container = client.get_container("web-app")
           container.restart()

Best Practices
--------------

1. **Always use context managers** for production code

   .. code-block:: python

      # Good
      with DockerClientWrapper() as client:
          return client.list_containers()

      # Acceptable for scripts
      client = DockerClientWrapper()
      containers = client.list_containers()
      client.close()

      # Bad - connection leak
      client = DockerClientWrapper()
      return client.list_containers()

2. **Use handle_errors for operations** with multiple steps

   .. code-block:: python

      with client.handle_errors("deploying application"):
          container = client.get_container("app")
          container.stop()
          container.remove()
          # Create new container...

3. **Keep context narrow**: Don't hold connections longer than needed

   .. code-block:: python

      # Good - short-lived connection
      def get_running_containers():
          with DockerClientWrapper() as client:
              return client.list_containers()

      # Bad - connection held too long
      def process_containers():
          with DockerClientWrapper() as client:  # Open
              containers = client.list_containers()
              # ... lots of processing ...
              # Connection still open!

Cleanup Guarantees
------------------

The context manager guarantees cleanup even on exceptions:

.. code-block:: python

   try:
       with DockerClientWrapper() as client:
           raise RuntimeError("Something went wrong")
   except RuntimeError:
       pass
   # Client connection still properly closed

See Also
--------

* :py:class:`docker_handler.client.DockerClientWrapper` - Client API reference
* :doc:`error_handling` - Exception handling guide
* :py:meth:`docker_handler.client.DockerClientWrapper.handle_errors` - Error context manager
