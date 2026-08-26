"""CSRF protection for mutating requests (double-submit token).

Scope note: the current API authenticates via the ``Authorization:
Bearer`` header, which browsers do NOT attach cross-site automatically,
so the API is structurally immune to CSRF today. This control exists for
the cookie-session mode (Phase 8 hardening); wire it into routers at that
point via ``Depends``.
"""

from __future__ import annotations

from typing import Any


def require_csrf_token(request: Any, *, expected: str) -> bool:
    """Reject mutating requests whose CSRF header does not match the session."""
    supplied = str(request.headers.get("X-CSRF-Token", ""))
    if not supplied or supplied != expected:
        raise PermissionError("missing or invalid CSRF token")
    return True


__all__ = ["require_csrf_token"]
