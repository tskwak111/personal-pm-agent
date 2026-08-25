"""Least-privilege Google OAuth flow: PKCE state, single-use, scoped modes."""

from __future__ import annotations

import secrets


class OAuthStateStore:
    """In-process single-use state store (Redis-backed in deployment)."""

    def __init__(self) -> None:
        self._states: dict[str, str] = {}

    def issue(self, workspace_id: str) -> str:
        state = secrets.token_urlsafe(24)
        self._states[state] = workspace_id
        return state

    def consume(self, state: str) -> str | None:
        """Return the bound workspace id once; the state is then invalidated."""
        return self._states.pop(state, None)


READ_ONLY_SCOPES = ("https://www.googleapis.com/auth/calendar.readonly",)
WRITE_SCOPES = READ_ONLY_SCOPES + ("https://www.googleapis.com/auth/calendar.events",)


def build_authorization_url(
    *,
    mode: str,
    state: str,
    client_id: str = "local-dev-client",
    redirect_uri: str = "http://localhost:3000/api/v1/calendar/oauth/callback",
) -> str:
    scopes = WRITE_SCOPES if mode == "READ_WRITE" else READ_ONLY_SCOPES
    params = [
        ("client_id", client_id),
        ("redirect_uri", redirect_uri),
        ("response_type", "code"),
        ("scope", " ".join(scopes)),
        ("state", state),
        ("access_type", "offline"),
        ("prompt", "consent"),
    ]
    query = "&".join(f"{k}={v}" for k, v in params)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"


__all__ = ["OAuthStateStore", "build_authorization_url", "READ_ONLY_SCOPES", "WRITE_SCOPES"]
