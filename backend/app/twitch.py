
import os
import httpx
from fastapi import HTTPException

CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
CHANNEL = os.getenv("TWITCH_CHANNEL", "joysantalola67")


async def get_access_token():
    """Obtiene un token de aplicación de Twitch."""

    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Faltan las credenciales de Twitch"
        )

    url = "https://id.twitch.tv/oauth2/token"

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(url, data=data)
            response.raise_for_status()
            return response.json()["access_token"]
        except (httpx.HTTPError, KeyError, ValueError):
            raise HTTPException(
                status_code=502,
                detail="No se pudo autenticar con Twitch"
            )


async def get_channel_info():
    """Consulta la información pública del canal."""

    token = await get_access_token()

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    url = "https://api.twitch.tv/helix/users"

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(
                url,
                headers=headers,
                params={"login": CHANNEL}
            )
            response.raise_for_status()
            users = response.json()["data"]
        except (httpx.HTTPError, KeyError, ValueError):
            raise HTTPException(
                status_code=502,
                detail="No se pudo consultar Twitch"
            )

    if not users:
        raise HTTPException(
            status_code=404,
            detail="Canal no encontrado"
        )

    user = users[0]

    return {
        "id": user["id"],
        "login": user["login"],
        "display_name": user["display_name"],
        "description": user["description"],
        "profile_image_url": user["profile_image_url"],
        "view_count": user.get("view_count")
    }


async def fetch_paginated_data(
    endpoint,
    params,
    max_pages=5
):
    """Recupera varias páginas de la API de Twitch."""

    token = await get_access_token()

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    all_items = []
    cursor = None
    pages_fetched = 0

    async with httpx.AsyncClient(timeout=20) as client:

        for page in range(max_pages):

            request_params = params.copy()

            if cursor:
                request_params["after"] = cursor

            try:
                response = await client.get(
                    endpoint,
                    headers=headers,
                    params=request_params
                )

                response.raise_for_status()

                result = response.json()

                items = result["data"]

            except (
                httpx.HTTPError,
                KeyError,
                ValueError
            ):
                raise HTTPException(
                    status_code=502,
                    detail="Error consultando Twitch"
                )

            all_items.extend(items)
            pages_fetched += 1

            cursor = (
                result.get("pagination", {})
                .get("cursor")
            )

            print(
                f"Página {pages_fetched}: "
                f"{len(items)} registros",
                flush=True
            )

            # Si no hay más páginas, terminamos
            if not cursor or not items:
                break

    return {
        "items": all_items,
        "pages_fetched": pages_fetched,
        "has_more": bool(cursor and all_items)
    }



async def get_videos():
    """Recupera vídeos usando paginación."""

    url = "https://api.twitch.tv/helix/videos"

    params = {
        "user_id": "1477630760",
        "type": "archive",
        "first": 100
    }

    result = await fetch_paginated_data(
        endpoint=url,
        params=params,
        max_pages=5
    )

    videos = result["items"]

    return {
        "total": len(videos),
        "pages_fetched": result["pages_fetched"],
        "has_more": result["has_more"],
        "videos": [
            {
                "id": video["id"],
                "title": video["title"],
                "created_at": video["created_at"],
                "duration": video["duration"],
                "view_count": video["view_count"],
                "url": video["url"]
            }
            for video in videos
        ]
    }




async def get_clips():
    """Recupera clips utilizando paginación."""

    url = "https://api.twitch.tv/helix/clips"

    params = {
        "broadcaster_id": "1477630760",
        "first": 100
    }

    result = await fetch_paginated_data(
        endpoint=url,
        params=params,
        max_pages=5
    )

    clips = result["items"]

    return {
        "total": len(clips),
        "pages_fetched": result["pages_fetched"],
        "has_more": result["has_more"],
        "clips": [
            {
                "id": clip["id"],
                "title": clip["title"],
                "created_at": clip["created_at"],
                "duration": clip["duration"],
                "view_count": clip["view_count"],
                "game_id": clip["game_id"],
                "url": clip["url"]
            }
            for clip in clips
        ]
    }


async def get_live_stream(access_token=None):
    """Consulta si nuestro canal está en directo."""

    token = access_token or await get_access_token()

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    url = "https://api.twitch.tv/helix/streams"

    params = {
        "user_id": "1477630760"
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.get(
                url,
                headers=headers,
                params=params
            )

            response.raise_for_status()
            data = response.json()["data"]

        except (
            httpx.HTTPError,
            KeyError,
            ValueError
        ):
            raise HTTPException(
                status_code=502,
                detail="No se pudo consultar el directo"
            )

    if not data:
        return {
            "is_live": False,
            "stream": None
        }

    stream = data[0]

    return {
        "is_live": True,
        "stream": {
            "id": stream["id"],
            "title": stream["title"],
            "viewer_count": stream["viewer_count"],
            "game_id": stream["game_id"],
            "game_name": stream["game_name"],
            "started_at": stream["started_at"]
        }
    }
