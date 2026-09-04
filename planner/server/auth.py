"""Single-user password. Nobody else gets a session."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import hmac
import os

from fastapi import Request
from fastapi.responses import RedirectResponse


def env_user() -> str:
    return os.environ.get("PLANER_USER", "me").strip() or "me"


def env_password() -> str:
    password = os.environ.get("PLANER_PASSWORD", "")
    if not password:
        raise RuntimeError("PLANER_PASSWORD is required. Set it in .env on the server.")
    return password


def env_secret() -> str:
    secret = os.environ.get("PLANER_SECRET", "")
    if len(secret) < 16:
        raise RuntimeError("PLANER_SECRET must be at least 16 characters.")
    return secret


_failures: dict[str, list[datetime]] = defaultdict(list)


def login_allowed(ip: str) -> bool:
    window = datetime.now() - timedelta(minutes=15)
    _failures[ip] = [stamp for stamp in _failures[ip] if stamp > window]
    return len(_failures[ip]) < 8


def record_failure(ip: str) -> None:
    _failures[ip].append(datetime.now())


def check_password(user: str, password: str) -> bool:
    return hmac.compare_digest(user, env_user()) and hmac.compare_digest(
        password, env_password()
    )


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def is_logged_in(request: Request) -> bool:
    return request.session.get("uid") == env_user()


def login_redirect(request: Request) -> RedirectResponse | None:
    if is_logged_in(request):
        return None
    return RedirectResponse("/login", status_code=303)
