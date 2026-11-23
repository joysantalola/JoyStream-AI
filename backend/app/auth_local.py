"""JoyStream AI 26C: login local con cookie firmada para acciones sensibles.

La aplicación está destinada a localhost; NO sustituye HTTPS ni una solución de
usuarios/roles para desplegarla públicamente. Claves solo por entorno del backend.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE = "joy_auth"
TTL_SECONDS = 12 * 3600
PROTECTED = frozenset({"/sync", "/channel/sync", "/ai/analyze"})
AUTH_OPEN = frozenset({"/auth/login", "/auth/logout", "/auth/status", "/health"})
FAILURES: dict[str, deque] = defaultdict(deque)
router = APIRouter()


def _config():
    salt = os.getenv("JOY_AUTH_SALT", "")
    expected = os.getenv("JOY_AUTH_HASH", "")
    secret = os.getenv("JOY_AUTH_SESSION_SECRET", "")
    if not (re.fullmatch(r"[0-9a-f]{32}", salt) and re.fullmatch(r"[0-9a-f]{64}", expected)
            and len(secret) >= 40):
        raise RuntimeError("Paso 26C sin secretos de entorno correctos: revisa .joystream-auth.env")
    return bytes.fromhex(salt), expected, secret.encode("utf-8")


def _password_ok(password: str) -> bool:
    salt, expected, _ = _config()
    calculated = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390000).hex()
    return hmac.compare_digest(calculated, expected)


def _sign(timestamp: int, secret: bytes) -> str:
    nonce = secrets.token_urlsafe(18)
    payload = f"{timestamp}.{nonce}"
    signature = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _verify(token: str | None) -> bool:
    if not token or len(token) > 512:
        return False
    try:
        timestamp_text, nonce, supplied = token.split(".")
        if not timestamp_text.isascii() or not timestamp_text.isdecimal() or not nonce or len(nonce) > 40:
            return False
        timestamp = int(timestamp_text)
        now = int(time.time())
        if timestamp > now + 30 or timestamp < now - TTL_SECONDS:
            return False
        _, _, secret = _config()
        expected = hmac.new(secret, f"{timestamp_text}.{nonce}".encode("ascii"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(supplied, expected)
    except (ValueError, UnicodeEncodeError):
        return False


def _safe_request(request: Request) -> bool:
    """Defensa CSRF para solicitudes web; la cookie SameSite=Strict es otra capa."""
    origin = request.headers.get("origin")
    if origin:
        try:
            parsed = urlsplit(origin)
            if parsed.scheme not in ("http", "https") or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
                return False
        except ValueError:
            return False
    return request.headers.get("sec-fetch-site", "").lower() not in ("cross-site", "same-site")


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
async def login(body: LoginRequest, request: Request):
    if not _safe_request(request):
        return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
    key = request.client.host if request.client else "unknown"
    events = FAILURES[key]
    now = time.monotonic()
    while events and events[0] < now - 600:
        events.popleft()
    if len(events) >= 8:
        return JSONResponse({"detail": "Demasiados intentos. Vuelve a intentarlo en 10 minutos."}, status_code=429)
    if not _password_ok(body.password):
        events.append(now)
        return JSONResponse({"detail": "Contraseña incorrecta"}, status_code=401)
    events.clear()
    _, _, secret = _config()
    result = JSONResponse({"authenticated": True})
    # localhost utiliza HTTP; Secure requiere HTTPS y se habilitará si se publica.
    result.set_cookie(COOKIE, _sign(int(time.time()), secret), max_age=TTL_SECONDS,
                      httponly=True, samesite="strict", secure=False, path="/")
    result.headers["Cache-Control"] = "no-store"
    return result


@router.post("/auth/logout")
async def logout():
    result = JSONResponse({"authenticated": False})
    result.delete_cookie(COOKIE, path="/", samesite="strict")
    result.headers["Cache-Control"] = "no-store"
    return result


@router.get("/auth/status")
async def status(request: Request):
    result = JSONResponse({"authenticated": _verify(request.cookies.get(COOKIE))})
    result.headers["Cache-Control"] = "no-store"
    return result


# JOYSTREAM_26D_SCHEDULER_TOKEN
# Credencial separada de la cookie del navegador. Solo se entrega al scheduler.
def _internal_scheduler_ok(request: Request) -> bool:
    supplied = request.headers.get("x-joystream-internal-token", "")
    expected = os.getenv("JOY_INTERNAL_SYNC_TOKEN", "")
    return (
        bool(expected)
        and len(expected) >= 64
        and len(supplied) == len(expected)
        and hmac.compare_digest(supplied, expected)
    )


class LocalAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if request.method.upper() == "POST" and path in PROTECTED:
            if not _safe_request(request):
                return JSONResponse({"detail": "Origen no permitido"}, status_code=403)
            if not (
                (path in ("/sync", "/channel/sync") and _internal_scheduler_ok(request))
                or _verify(request.cookies.get(COOKIE))
            ):
                return JSONResponse({"detail": "Inicia sesión para realizar esta acción"}, status_code=401,
                                    headers={"Cache-Control": "no-store"})
        return await call_next(request)
