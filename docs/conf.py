# docs/conf.py
import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "Otto CLI"
author = "lolosioann"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"

# Allow both .rst and .md files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Root document
master_doc = "index"
