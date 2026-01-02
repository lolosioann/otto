# docs/conf.py
"""Sphinx configuration for Otto documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "Otto CLI"
author = "lolosioann"
release = "0.1.0"
copyright = "2025, lolosioann"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",  # Pull in docstrings
    "sphinx.ext.napoleon",  # NumPy/Google style docstrings
    "sphinx.ext.doctest",  # Test code examples
    "sphinx.ext.intersphinx",  # Link to other projects' docs
    "sphinx.ext.viewcode",  # Add source code links
    "sphinx.ext.coverage",  # Check documentation coverage
    "sphinxcontrib.spelling",  # Spell-check docs
    "myst_parser",  # Markdown support
]

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

# Root document
master_doc = "index"

# -- Extension configuration -------------------------------------------------

# Napoleon settings (NumPy-style docstrings)
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Intersphinx: link to other projects
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "docker": ("https://docker-py.readthedocs.io/en/stable/", None),
}

# Doctest configuration
doctest_default_flags = (
    0 | __import__("doctest").ELLIPSIS | __import__("doctest").NORMALIZE_WHITESPACE
)
doctest_global_setup = """
from docker_handler import DockerClientWrapper
"""

# Spell-checking configuration
spelling_lang = "en_US"
spelling_word_list_filename = ["spelling_wordlist.txt"]
spelling_show_suggestions = True
spelling_exclude_patterns = ["api/*"]

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
}
html_static_path: list[str] = []
html_show_sourcelink = True

# -- Options for Markdown support --------------------------------------------
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# MyST settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
]
