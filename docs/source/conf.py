# Pallas Documentation - Sphinx Configuration

import os
import sys

# Backend-Code für Autodoc erreichbar machen
sys.path.insert(0, os.path.abspath("../.."))

# Projekt-Info
project = "Pallas"
author = "Noah Rolli"
release = "0.1.0"

# Extensions
extensions = [
    "myst_parser",           # Markdown-Support
    "sphinx.ext.autodoc",    # Docstrings automatisch auslesen
    "sphinx.ext.viewcode",   # Link zum Quellcode
    "sphinx.ext.napoleon",   # Google/NumPy Style Docstrings
]

# Markdown-Dateien als Quellen erlauben
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Furo Theme (modern, clean)
html_theme = "furo"
html_title = "Pallas Docs"

# Sprache
language = "en"