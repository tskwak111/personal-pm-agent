"""Pure deterministic planning engine for Personal PM Agent.

This package is the normative Planning Core calculation module. It must not
import FastAPI, SQLAlchemy, Redis, provider SDKs or LLM libraries, and it must
never read wall-clock time, global random state or locale settings.
"""

from .version import __version__

__all__ = ["__version__"]
