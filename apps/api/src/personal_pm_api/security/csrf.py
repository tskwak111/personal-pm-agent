"""CSRF status for the bearer-only API.

The API accepts sessions only through an explicit ``Authorization: Bearer``
header and does not issue or accept an ambient authentication cookie. CSRF
tokens become applicable only if cookie authentication is introduced.
"""

from __future__ import annotations

__all__: list[str] = []
