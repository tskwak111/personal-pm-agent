"""Task duration estimates with slot rounding and sample-strength blending.

The planner speaks only of base demand and safety demand; it never claims a
statistical percentile for aggregate safety minutes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

UNCERTAINTY_MULTIPLIER = {"low": 1.15, "medium": 1.35, "high": 1.60}

FACTOR_FLOOR = 0.75
FACTOR_CEILING = 2.50

# Sample count -> share of the observed factor blended into 1.0.
_SAMPLE_STRENGTH = (
    (3, 0.30),
    (6, 0.60),
    (20, 0.80),
)


@dataclass(frozen=True, slots=True)
class Estimate:
    base_minutes: int
    safety_minutes: int


def ceil_to_slot(minutes: float, slot_minutes: int) -> int:
    return int(math.ceil(minutes / slot_minutes) * slot_minutes)


def blended_factor(observed: float, sample_count: int) -> float:
    """Blend the observed calibration factor by evidence strength."""
    if sample_count < _SAMPLE_STRENGTH[0][0]:
        return 1.0
    strength = next(
        (share for threshold, share in reversed(_SAMPLE_STRENGTH) if sample_count >= threshold),
        0.0,
    )
    return 1.0 + (observed - 1.0) * strength


def derive_estimate(
    raw_base_minutes: int,
    factor: float,
    uncertainty: str,
    slot_minutes: int,
) -> Estimate:
    clamped = min(FACTOR_CEILING, max(FACTOR_FLOOR, factor))
    adjusted = ceil_to_slot(raw_base_minutes * clamped, slot_minutes)
    multiplier = UNCERTAINTY_MULTIPLIER[uncertainty]
    safety = ceil_to_slot(adjusted * multiplier, slot_minutes)
    return Estimate(base_minutes=adjusted, safety_minutes=max(adjusted, safety))
