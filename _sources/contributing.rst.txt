Contributing
============

See the main :file:`CONTRIBUTING.md` in the repository root for development setup and guidelines.

Documentation Guidelines
------------------------

When contributing documentation:

Write More Than Docstrings
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Docstrings**: API reference (what functions do)
* **Guides**: How-to articles, tutorials, best practices
* **Narrative docs**: Architecture, design decisions, concepts

Use reStructuredText Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cross-references:

.. code-block:: rst

   :py:class:`~docker_handler.client.DockerClientWrapper`
   :py:exc:`ValueError`
   :doc:`guides/error_handling`
   :ref:`some-label`

Code blocks with doctest:

.. code-block:: rst

   .. doctest::

      >>> from docker_handler import DockerClientWrapper
      >>> client = DockerClientWrapper()
      >>> client.ping()
      True

Directives:

.. code-block:: rst

   .. note:: Important information

   .. warning:: Critical warning

   .. code-block:: python

      # Code example
      pass

Documentation Checks
--------------------

Before submitting:

1. **Spell-check**: ``make spelling`` (runs sphinxcontrib-spelling)
2. **Doctest**: ``make doctest`` (tests code examples)
3. **Build**: ``make html`` (builds HTML output)
4. **Interrogate**: Pre-commit hook checks docstring coverage

All checks run automatically in CI.

Building Docs Locally
----------------------

.. code-block:: bash

   cd docs
   make html
   open _build/html/index.html

Or using uv:

.. code-block:: bash

   uv run sphinx-build -b html docs docs/_build/html

Testing Doctests
----------------

.. code-block:: bash

   uv run sphinx-build -b doctest docs docs/_build/doctest

Spell-Checking
--------------

.. code-block:: bash

   uv run sphinx-build -b spelling docs docs/_build/spelling

Add project-specific words to :file:`spelling_wordlist.txt`.

Style Guide
-----------

* Line length: ~80 characters in reST
* Use semantic markup: ``:py:class:``, ``:py:func:``, etc.
* Include examples for all public APIs
* Write from user perspective, not implementation
* Test all code examples with doctest

See Also
--------

* `Sphinx documentation <https://www.sphinx-doc.org/>`_
* `reStructuredText primer <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_
* `Napoleon documentation <https://sphinxcontrib-napoleon.readthedocs.io/>`_
