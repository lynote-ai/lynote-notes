"""Compatibility shim for editable installs on older pip versions.

Project metadata lives in pyproject.toml; this file only exists so that
``pip install -e .`` works with pip < 22 (which cannot do PEP 660 editable
installs for pyproject-only projects).
"""

from setuptools import setup

setup()
