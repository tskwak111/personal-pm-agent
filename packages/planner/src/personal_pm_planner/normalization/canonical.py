"""Canonical hashing for planner input.

Canonical bytes sort entity collections by stable keys, so collection order in
the caller never changes the hash.
"""

from __future__ import annotations

from personal_pm_planner.contracts.input import PlannerInput, canonical_input_bytes, input_hash


def canonicalize(value: PlannerInput) -> PlannerInput:
    """Return the normalized value.

    Entity snapshots already normalize themselves in ``__post_init__``
    (UTC instants, canonical enums); no additional rewriting is required here.
    """
    return value


def hash_canonical_input(value: PlannerInput) -> str:
    return input_hash(canonicalize(value))


__all__ = ["canonicalize", "hash_canonical_input", "canonical_input_bytes", "PlannerInput"]
