from app.auth_local import router as auth_router, LocalAuthMiddleware  # JOYSTREAM_26C_LOCAL_AUTH

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool
from app.enhancements import router as enhancements_router

from app.twitch import (
    get_channel_info,
    get_videos,
    get_clips,
    get_live_stream
)

from app.startup import wait_for_database  # JOYSTREAM_26A

from app.database import (
    create_tables,
    videos_table,
    clips_table
)

from app.storage import (
    save_videos,
    save_clips,
    list_items,
    get_statistics,
    get_history,
    get_growth_stats,
    get_stream_samples
)

from app.channel_metrics import (
    fetch_channel_metrics,
    save_channel_metrics,
    get_channel_history
)

from app.analytics import session_report, games_report
from app.twitch_auth import router as twitch_auth_router

from pydantic import BaseModel, Field
from app.ai import analyze_channel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al iniciar, creamos las tablas que falten
    await run_in_threadpool(wait_for_database, create_tables)
    yield


app = FastAPI(
    title="JoyStream AI",
    lifespan=lifespan
    
)

app.include_router(auth_router)
app.add_middleware(LocalAuthMiddleware)

# REGISTRAR RUTAS DE TWITCH OAUTH
app.include_router(twitch_auth_router)
app.include_router(enhancements_router)

@app.get("/")
def home():
    return {
        "project": "JoyStream AI",
        "status": "running",
        "channel": "joysantalola67"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# TWITCH API

@app.get("/twitch/channel")
async def twitch_channel():
    return await get_channel_info()


@app.get("/twitch/videos")
async def twitch_videos():
    return await get_videos()


@app.get("/twitch/clips")
async def twitch_clips():
    return await get_clips()


# BASE DE DATOS

@app.post("/sync")
async def sync_twitch():
    # 1. Recuperamos datos de Twitch
    videos_data = await get_videos()
    clips_data = await get_clips()

    # 2. Los guardamos en PostgreSQL
    total_videos = await run_in_threadpool(
        save_videos,
        videos_data["videos"]
    )

    total_clips = await run_in_threadpool(
        save_clips,
        clips_data["clips"]
    )

    return {
        "message": "Sincronización completada",
        "videos_processed": total_videos,
        "clips_processed": total_clips
    }


@app.get("/db/videos")
def database_videos():
    return list_items(videos_table)


@app.get("/db/clips")
def database_clips():
    return list_items(clips_table)


@app.get("/stats")
def statistics():
    return get_statistics()



@app.get("/history/clips")
def clips_history():
    return get_history("clip")


@app.get("/history/videos")
def videos_history():
    return get_history("video")


@app.get("/growth/clips")
def clips_growth():
    return get_growth_stats("clip")


@app.get("/growth/videos")
def videos_growth():
    return get_growth_stats("video")


@app.get("/twitch/live")
async def twitch_live():
    """Consulta el estado actual del canal."""
    return await get_live_stream()


@app.get("/streams/history")
def streams_history():
    """Devuelve las mediciones almacenadas."""
    return get_stream_samples()


@app.get("/analytics/sessions")
def analytics_sessions():
    """Estadísticas agrupadas por directo."""
    return session_report()


@app.get("/analytics/games")
def analytics_games():
    """Estadísticas agrupadas por videojuego."""
    return games_report()


class AIQuestion(BaseModel):
    question: str = Field(
        min_length=5,
        max_length=500
    )
    history: list[dict] = Field(
        default_factory=list,
        max_length=8
    )


@app.post("/ai/analyze")
async def ai_analyze(request: AIQuestion):
    """Analiza el canal usando Ollama."""
    return await analyze_channel(request.question, request.history)


@app.get("/channel/current")
async def channel_current():
    """Consulta las métricas actuales de Twitch."""
    return await fetch_channel_metrics()


@app.post("/channel/sync")
async def channel_sync():
    """Consulta y guarda una medición histórica."""

    metrics = await fetch_channel_metrics()

    return await run_in_threadpool(
        save_channel_metrics,
        metrics
    )


@app.get("/channel/history")
def channel_history():
    """Devuelve el historial almacenado."""
    return get_channel_history()
