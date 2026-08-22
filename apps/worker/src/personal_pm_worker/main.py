"""Worker entrypoint contract.

The worker validates explicit settings, exposes a deterministic startup
identity and shuts down gracefully. Product jobs are registered in later
phases through an explicit job registry.
"""


def build_worker_identity(environment: str) -> str:
    normalized = environment.strip().lower()
    if not normalized:
        raise ValueError("environment must not be empty")
    return f"personal-pm-worker:{normalized}"
