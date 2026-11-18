"""Metadatos adicionales para JoyStream AI (solo lectura).

No modifica las tablas existentes. Las categorías de VOD solo se muestran
si están respaldadas por muestras del directo o clips asociados al VOD.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import asyncio

import httpx
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.twitch import CLIENT_ID, get_access_token
from app.storage import list_items, get_stream_samples
from app.database import clips_table, videos_table
from app.twitch_auth import get_user_access_token, CHANNEL_ID

router = APIRouter(prefix="/enhanced", tags=["Enriquecimiento Twitch"])
_cache = {"data": None, "expires": None}
_lock = asyncio.Lock()


def chunked(items, size=100):
    for pos in range(0, len(items), size):
        yield items[pos:pos + size]


async def twitch_get(client, path, headers, ids=None, params=None):
    request_params = params or {}
    if ids:
        # Helix admite varios parámetros id en la misma consulta.
        request_params = [("id", item) for item in ids]
    response = await client.get(
        "https://api.twitch.tv/helix/" + path,
        headers=headers,
        params=request_params,
    )
    response.raise_for_status()
    return response.json().get("data", [])


async def build_catalog():
    clips = await run_in_threadpool(list_items, clips_table)
    videos = await run_in_threadpool(list_items, videos_table)
    samples = await run_in_threadpool(get_stream_samples)
    token = await get_access_token()
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"}

    clip_ids = [str(c["id"]) for c in clips if c.get("id")]
    video_ids = [str(v["id"]) for v in videos if v.get("id")]
    game_ids = {str(c["game_id"]) for c in clips if c.get("game_id")}
    remote_clips, remote_videos = [], []

    async with httpx.AsyncClient(timeout=25) as client:
        try:
            profile = await twitch_get(
                client, "users", headers,
                params={"login": "joysantalola67"}
            )
            # Conserva hasta 1000 asociaciones en una lectura: suficiente
            # para el proyecto personal y evita consultas ilimitadas.
            for ids in chunked(clip_ids[:1000]):
                remote_clips.extend(await twitch_get(client, "clips", headers, ids=ids))
            for ids in chunked(video_ids[:1000]):
                remote_videos.extend(await twitch_get(client, "videos", headers, ids=ids))
            game_ids.update(str(c["game_id"]) for c in remote_clips if c.get("game_id"))
            categories = []
            for ids in chunked(sorted(game_ids)):
                categories.extend(await twitch_get(client, "games", headers, ids=ids))
        except (httpx.HTTPError, ValueError, KeyError) as err:
            raise HTTPException(status_code=502, detail="Fallo al consultar metadatos de Twitch") from err

    game_names = {str(g["id"]): g["name"] for g in categories}
    game_art = {str(g["id"]): g.get("box_art_url", "").replace("{width}", "144").replace("{height}", "192") for g in categories}
    clips_by_id = {str(c["id"]): c for c in remote_clips}
    remote_videos_by_id = {str(v["id"]): v for v in remote_videos}

    clip_labels = {}
    video_clip_games = defaultdict(set)
    for c in clips:
        cid = str(c["id"])
        remote = clips_by_id.get(cid, {})
        gid = str(c.get("game_id") or remote.get("game_id") or "")
        name = game_names.get(gid, "Categoría desconocida")
        clip_labels[cid] = {"game_id": gid or None, "game_name": name,
                            "cover": game_art.get(gid) or None,
                            "source": "twitch_clip" if gid and name != "Categoría desconocida" else "unknown"}
        if remote.get("video_id") and gid and name != "Categoría desconocida":
            video_clip_games[str(remote["video_id"])].add(name)

    # Las muestras de directo son evidencias temporales del juego emitido.
    stream_games = defaultdict(set)
    for sample in samples:
        if sample.get("game_name"):
            stream_games[str(sample["stream_id"])].add(sample["game_name"])

    video_labels = {}
    for v in videos:
        vid = str(v["id"])
        remote = remote_videos_by_id.get(vid, {})
        stream_id = remote.get("stream_id")
        observed = stream_games.get(str(stream_id), set()) if stream_id else set()
        inferred = video_clip_games.get(vid, set())
        names = sorted(observed | inferred)
        if observed:
            source = "stream_samples"  # juegos observados, no siempre cobertura completa
        elif inferred:
            source = "associated_clips"  # inferencia indirecta
        else:
            source = "unknown"
        video_labels[vid] = {"games": names, "source": source, "stream_id": stream_id}

    user = profile[0] if profile else {}
    return {
        "profile": {"display_name": user.get("display_name", "joysantalola67"),
                    "description": user.get("description", ""),
                    "profile_image_url": user.get("profile_image_url", ""),
                    "url": "https://www.twitch.tv/joysantalola67"},
        "clips": clip_labels,
        "videos": video_labels,
        "game_names": game_names,
        "coverage": {"clips": len(clips), "vod": len(videos),
                     "clip_links_checked": len(remote_clips), "vod_checked": len(remote_videos)},
        "notes": ["Las categorías de VOD se muestran como observadas o inferidas; no como metadatos directos de VOD.",
                  "Categoría desconocida significa falta de evidencia, no un juego concreto."],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/catalog")
async def catalog(refresh: bool = False):
    now = datetime.now(timezone.utc)
    if not refresh and _cache["data"] and _cache["expires"] > now:
        return _cache["data"]
    async with _lock:
        now = datetime.now(timezone.utc)
        if not refresh and _cache["data"] and _cache["expires"] > now:
            return _cache["data"]
        result = await build_catalog()
        _cache["data"] = result
        _cache["expires"] = datetime.now(timezone.utc) + timedelta(minutes=30)
        return result


@router.get("/ads")
async def ads_schedule():
    """Estado actual de programación, NO historial ni contador por directo."""
    try:
        token = await get_user_access_token()
    except HTTPException as exc:
        if exc.status_code in (401, 403, 409):
            return {"available": False, "reason": "Autoriza Twitch primero", "schedule": None}
        raise
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.get(
                "https://api.twitch.tv/helix/channels/ads",
                params={"broadcaster_id": CHANNEL_ID},
                headers={"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"},
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="No se pudo consultar Twitch Ads") from exc
    if response.status_code in (401, 403):
        return {"available": False, "reason": "Falta el permiso channel:read:ads o el canal no tiene acceso", "schedule": None}
    if response.status_code != 200:
        return {"available": False, "reason": f"Twitch devolvió HTTP {response.status_code}", "schedule": None}
    rows = response.json().get("data", [])
    if not rows:
        return {"available": False, "reason": "Sin programación publicitaria disponible", "schedule": None}
    row = rows[0]
    return {"available": True, "schedule": {
        "last_ad_at": row.get("last_ad_at"), "next_ad_at": row.get("next_ad_at"),
        "next_duration_seconds": row.get("duration"), "preroll_free_time": row.get("preroll_free_time"),
        "snooze_count": row.get("snooze_count")},
        "notice": "Estos datos no son un contador histórico de pausas publicitarias por emisión."}
