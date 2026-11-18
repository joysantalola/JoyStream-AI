
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select, insert

from app.database import (
    engine,
    channel_metrics_table
)
from app.twitch_auth import (
    CLIENT_ID,
    CHANNEL_ID,
    get_user_access_token
)


async def fetch_channel_metrics():
    """Obtiene seguidores y suscripciones."""

    token = await get_user_access_token()

    headers = {
        "Client-ID": CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    async with httpx.AsyncClient(timeout=20) as client:

        try:
            followers_response = await client.get(
                "https://api.twitch.tv/helix/channels/followers",
                headers=headers,
                params={"broadcaster_id": CHANNEL_ID}
            )
            followers_response.raise_for_status()

            followers = followers_response.json()["total"]

        except (httpx.HTTPError, KeyError, ValueError):
            raise HTTPException(
                status_code=502,
                detail="Error consultando seguidores"
            )

        subscribers = None
        subscription_points = None
        subscription_status = "available"

        try:
            subs_response = await client.get(
                "https://api.twitch.tv/helix/subscriptions",
                headers=headers,
                params={"broadcaster_id": CHANNEL_ID}
            )

            if subs_response.status_code in (403, 404):
                subscription_status = "unavailable"

            else:
                subs_response.raise_for_status()
                data = subs_response.json()

                subscribers = data.get("total")
                subscription_points = data.get("points")

        except (httpx.HTTPError, ValueError):
            subscription_status = "error"

    return {
        "followers": followers,
        "subscribers": subscribers,
        "subscription_points": subscription_points,
        "subscription_status": subscription_status,
        "captured_at": datetime.now(timezone.utc)
    }


def save_channel_metrics(metrics):
    """Guarda una nueva medición histórica."""

    with engine.begin() as connection:
        connection.execute(
            insert(channel_metrics_table).values(
                followers=metrics["followers"],
                subscribers=metrics["subscribers"],
                subscription_points=metrics["subscription_points"],
                captured_at=metrics["captured_at"]
            )
        )

    return metrics


def get_channel_history():
    """Devuelve el historial de crecimiento."""

    statement = (
        select(channel_metrics_table)
        .order_by(channel_metrics_table.c.captured_at.asc())
    )

    with engine.connect() as connection:
        rows = connection.execute(statement)

        return [
            dict(row)
            for row in rows.mappings()
        ]
