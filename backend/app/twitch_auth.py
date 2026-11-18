
import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from starlette.concurrency import run_in_threadpool

from app.database import engine, oauth_tokens_table


router = APIRouter(prefix="/auth/twitch")

CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

REDIRECT_URI = os.getenv(
    "TWITCH_REDIRECT_URI",
    "http://localhost:8000/auth/twitch/callback"
)

CHANNEL_ID = "1477630760"

SCOPES = [
    "moderator:read:followers",
    "channel:read:subscriptions",
    "channel:read:ads"
]


def save_tokens(data):
    """Guarda credenciales de forma persistente."""

    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=data["expires_in"]
    )

    values = {
        "id": 1,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": expires_at
    }

    statement = insert(oauth_tokens_table).values(**values)

    statement = statement.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "access_token": values["access_token"],
            "refresh_token": values["refresh_token"],
            "expires_at": expires_at
        }
    )

    with engine.begin() as connection:
        connection.execute(statement)


def load_tokens():
    with engine.connect() as connection:
        result = connection.execute(
            select(oauth_tokens_table).where(
                oauth_tokens_table.c.id == 1
            )
        ).mappings().first()

        return dict(result) if result else None


@router.get("/start")
async def oauth_start():
    """Redirige al propietario para autorizar Twitch."""

    state = secrets.token_urlsafe(32)

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state
    }

    url = httpx.URL(
        "https://id.twitch.tv/oauth2/authorize",
        params=params
    )

    response = RedirectResponse(str(url))

    response.set_cookie(
        key="twitch_oauth_state",
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600
    )

    return response


@router.get("/callback")
async def oauth_callback(request: Request):
    """Intercambia el código OAuth por tokens."""

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    saved_state = request.cookies.get("twitch_oauth_state")

    if (
        not code
        or not state
        or not saved_state
        or not secrets.compare_digest(state, saved_state)
    ):
        raise HTTPException(
            status_code=400,
            detail="Autorización cancelada o estado inválido"
        )

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            result = await client.post(
                "https://id.twitch.tv/oauth2/token",
                data=data
            )
            result.raise_for_status()
            tokens = result.json()

            validation = await client.get(
                "https://id.twitch.tv/oauth2/validate",
                headers={
                    "Authorization":
                        f"OAuth {tokens['access_token']}"
                }
            )
            validation.raise_for_status()
            identity = validation.json()

        except (httpx.HTTPError, KeyError, ValueError):
            raise HTTPException(
                status_code=502,
                detail="No se pudo completar la autorización"
            )

    # Impedimos autorizar una cuenta distinta
    if identity.get("user_id") != CHANNEL_ID:
        raise HTTPException(
            status_code=403,
            detail="Debes autorizar como joysantalola67"
        )

    if not set(SCOPES).issubset(
        set(identity.get("scopes", []))
    ):
        raise HTTPException(
            status_code=403,
            detail="Faltan permisos de Twitch"
        )

    await run_in_threadpool(save_tokens, tokens)

    response = RedirectResponse(
        url="http://localhost:8501"
    )
    response.delete_cookie("twitch_oauth_state")

    return response


async def get_user_access_token():
    """Devuelve un token válido, renovándolo si caduca."""

    saved = await run_in_threadpool(load_tokens)

    if saved is None:
        raise HTTPException(
            status_code=409,
            detail="Primero debes autorizar Twitch"
        )

    now = datetime.now(timezone.utc)

    if saved["expires_at"] > now + timedelta(minutes=2):
        return saved["access_token"]

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": saved["refresh_token"]
                }
            )

            response.raise_for_status()
            tokens = response.json()

        except (httpx.HTTPError, ValueError):
            raise HTTPException(
                status_code=503,
                detail="No se pudo renovar el token de Twitch"
            )

    await run_in_threadpool(save_tokens, tokens)

    return tokens["access_token"]


@router.get("/status")
async def oauth_status():
    saved = await run_in_threadpool(load_tokens)

    return {
        "authorized": saved is not None
    }
