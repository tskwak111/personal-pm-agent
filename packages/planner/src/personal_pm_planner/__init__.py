"""Pure deterministic planning engine for Personal PM Agent.

This package is the normative Planning Core calculation module. It must not
import FastAPI, SQLAlchemy, Redis, provider SDKs or LLM libraries, and it must
never read wall-clock time, global random state or locale settings.
"""

from .contracts.input import PlannerInput, canonical_input_bytes, input_hash
from .contracts.output import (
    MilestoneRisk,
    PassType,
    PlannerOutput,
    PlanPassResult,
    TaskAllocation,
    TodayPlan,
)
from .version import __version__

__all__ = [
    "__version__",
    "MilestoneRisk",
    "PassType",
    "PlanPassResult",
    "PlannerInput",
    "PlannerOutput",
    "TaskAllocation",
    "TodayPlan",
    "canonical_input_bytes",
    "input_hash",
]
