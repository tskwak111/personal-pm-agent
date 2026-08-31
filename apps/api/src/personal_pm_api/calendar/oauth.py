"""Least-privilege Google OAuth with PKCE and validated token exchange."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from urllib.parse import urlencode

import httpx

from personal_pm_api.settings import ApiSettings

READ_ONLY_SCOPES = ("https://www.googleapis.com/auth/calendar.readonly",)
WRITE_SCOPES = READ_ONLY_SCOPES + ("https://www.googleapis.com/auth/calendar.events",)


@dataclass(frozen=True, slots=True)
class OAuthState:
    workspace_id: str
    mode: str
    code_verifier: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenResponse:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: tuple[str, ...]


class OAuthExchangeError(RuntimeError):
    pass


class OAuthStateStore:
    """Single-use state store for one API process."""

    def __init__(self, ttl: timedelta = timedelta(minutes=10)) -> None:
        self._ttl = ttl
        self._states: dict[str, OAuthState] = {}
        self._lock = Lock()

    def issue(self, workspace_id: str, *, mode: str, now_utc: datetime) -> str:
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError("OAuth state clock must be timezone-aware")
        state = secrets.token_urlsafe(32)
        value = OAuthState(
            workspace_id=workspace_id,
            mode=mode,
            code_verifier=secrets.token_urlsafe(64),
            issued_at=now_utc,
            expires_at=now_utc + self._ttl,
        )
        with self._lock:
            self._states = {
                key: existing
                for key, existing in self._states.items()
                if existing.expires_at > now_utc
            }
            self._states[state] = value
        return state

    def peek(self, state: str) -> OAuthState | None:
        with self._lock:
            return self._states.get(state)

    def consume(self, state: str, *, now_utc: datetime) -> OAuthState | None:
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError("OAuth state clock must be timezone-aware")
        with self._lock:
            value = self._states.pop(state, None)
        if value is None or now_utc < value.issued_at or now_utc >= value.expires_at:
            return None
        return value


def code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def configured_scopes(mode: str) -> tuple[str, ...]:
    return WRITE_SCOPES if mode == "READ_WRITE" else READ_ONLY_SCOPES


def provider_is_configured(settings: ApiSettings) -> bool:
    return bool(
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret is not None
        and settings.google_oauth_redirect_uri
        and settings.token_encryption_key is not None
    )


def build_authorization_url(
    *,
    mode: str,
    state: str,
    code_verifier: str,
    settings: ApiSettings,
) -> str:
    params = {
        "client_id": settings.google_oauth_client_id or "",
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(configured_scopes(mode)),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": code_challenge(code_verifier),
        "code_challenge_method": "S256",
    }
    return f"{settings.google_oauth_authorize_url}?{urlencode(params)}"


async def exchange_authorization_code(
    code: str,
    redirect_uri: str,
    settings: ApiSettings,
    *,
    code_verifier: str,
) -> TokenResponse:
    client_secret = settings.google_oauth_client_secret
    if not settings.google_oauth_client_id or client_secret is None:
        raise OAuthExchangeError("OAuth provider is not configured")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                settings.google_oauth_token_url,
                data={
                    "code": code,
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": client_secret.get_secret_value(),
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise OAuthExchangeError("provider token exchange failed") from error
    if not isinstance(payload, dict):
        raise OAuthExchangeError("provider token response is invalid")

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    raw_scope = payload.get("scope")
    if (
        not isinstance(access_token, str)
        or not access_token
        or not isinstance(refresh_token, str)
        or not refresh_token
        or isinstance(expires_in, bool)
        or not isinstance(expires_in, int)
        or expires_in <= 0
        or not isinstance(raw_scope, str)
        or not raw_scope.strip()
    ):
        raise OAuthExchangeError("provider token response is incomplete")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        scopes=tuple(sorted(set(raw_scope.split()))),
    )


__all__ = [
    "OAuthExchangeError",
    "OAuthState",
    "OAuthStateStore",
    "READ_ONLY_SCOPES",
    "TokenResponse",
    "WRITE_SCOPES",
    "build_authorization_url",
    "configured_scopes",
    "exchange_authorization_code",
    "provider_is_configured",
]
