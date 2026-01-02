Docker Handler Module
=====================

The :py:mod:`docker_handler` module provides a wrapper around the Docker SDK with enhanced error handling and type safety.

Client Wrapper
--------------

.. autoclass:: docker_handler.client.DockerClientWrapper
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __enter__, __exit__

Examples
--------

Basic connection:

.. doctest::

   >>> from docker_handler import DockerClientWrapper
   >>> client = DockerClientWrapper()
   >>> client.ping()
   True

Using context manager:

.. code-block:: python

   with DockerClientWrapper() as client:
       containers = client.list_containers()
       for container in containers:
           print(f"{container.name}: {container.status}")

Cross-references
----------------

* Exception hierarchy: :doc:`exceptions`
* Error handling guide: :doc:`../guides/error_handling`
* Context manager guide: :doc:`../guides/context_managers`
