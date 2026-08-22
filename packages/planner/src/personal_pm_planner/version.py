"""Planner package version resolved from installed distribution metadata."""

from importlib.metadata import version

__version__ = version("personal-pm-planner")

__all__ = ["__version__"]
