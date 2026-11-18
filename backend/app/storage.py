
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from app.database import (
    engine,
    videos_table,
    clips_table,
    view_history_table,
    stream_samples_table
)


def parse_date(value):
    """Convierte una fecha de Twitch en datetime."""
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )



def save_items(table, items):
    """Actualiza datos y registra su historial."""

    content_type = (
        "video" if table.name == "videos" else "clip"
    )

    # Usamos una misma fecha para esta sincronización
    captured_at = datetime.now(timezone.utc)

    with engine.begin() as connection:

        for item in items:

            # 1. Insertar o actualizar el contenido
            statement = insert(table).values(**item)

            values_to_update = {
                key: value
                for key, value in item.items()
                if key != "id"
            }

            values_to_update["synced_at"] = captured_at

            statement = statement.on_conflict_do_update(
                index_elements=["id"],
                set_=values_to_update
            )

            connection.execute(statement)

            # 2. Guardar una medición histórica
            history_statement = insert(
                view_history_table
            ).values(
                content_type=content_type,
                content_id=item["id"],
                view_count=item["view_count"],
                captured_at=captured_at
            )

            connection.execute(history_statement)

    return len(items)



def save_videos(videos):
    """Guarda los vídeos de Twitch."""

    items = [
        {
            "id": video["id"],
            "title": video["title"],
            "created_at": parse_date(video["created_at"]),
            "duration": video["duration"],
            "view_count": video["view_count"],
            "url": video["url"]
        }
        for video in videos
    ]

    return save_items(videos_table, items)


def save_clips(clips):
    """Guarda los clips de Twitch."""

    items = [
        {
            "id": clip["id"],
            "title": clip["title"],
            "created_at": parse_date(clip["created_at"]),
            "duration": clip["duration"],
            "view_count": clip["view_count"],
            "game_id": clip["game_id"],
            "url": clip["url"]
        }
        for clip in clips
    ]

    return save_items(clips_table, items)


def list_items(table):
    """Recupera los registros guardados."""

    statement = select(table).order_by(
        table.c.created_at.desc()
    )

    with engine.connect() as connection:
        result = connection.execute(statement)
        return [dict(row) for row in result.mappings()]


def get_statistics():
    """Devuelve estadísticas básicas."""

    with engine.connect() as connection:
        total_videos = connection.scalar(
            select(func.count()).select_from(videos_table)
        )

        total_clips = connection.scalar(
            select(func.count()).select_from(clips_table)
        )

    return {
        "total_videos": total_videos,
        "total_clips": total_clips
    }



def get_history(content_type):
    """Devuelve el historial de vídeos o clips."""

    if content_type not in ("video", "clip"):
        raise ValueError("Tipo de contenido no válido")

    statement = (
        select(view_history_table)
        .where(
            view_history_table.c.content_type
            == content_type
        )
        .order_by(
            view_history_table.c.captured_at.asc(),
            view_history_table.c.id.asc()
        )
    )

    with engine.connect() as connection:
        result = connection.execute(statement)

        return [
            dict(row)
            for row in result.mappings()
        ]


def get_growth_stats(content_type):
    """Calcula el crecimiento por contenido."""

    history = get_history(content_type)

    grouped = {}

    for record in history:
        content_id = record["content_id"]

        if content_id not in grouped:
            grouped[content_id] = []

        grouped[content_id].append(record)

    results = []

    for content_id, records in grouped.items():

        first_views = records[0]["view_count"]
        last_views = records[-1]["view_count"]

        growth = last_views - first_views

        if first_views > 0:
            growth_percent = (
                growth / first_views
            ) * 100
        else:
            growth_percent = None

        results.append({
            "content_id": content_id,
            "first_views": first_views,
            "last_views": last_views,
            "growth": growth,
            "growth_percent": (
                round(growth_percent, 2)
                if growth_percent is not None
                else None
            ),
            "measurements": len(records)
        })

    return sorted(
        results,
        key=lambda item: item["growth"],
        reverse=True
    )


from sqlalchemy import select


def save_stream_sample(stream):
    """Guarda una medición de espectadores."""

    captured_at = datetime.now(timezone.utc)

    sample = {
        "stream_id": stream["id"],
        "viewer_count": stream["viewer_count"],
        "game_id": stream["game_id"],
        "game_name": stream["game_name"],
        "title": stream["title"],
        "started_at": datetime.fromisoformat(
            stream["started_at"].replace("Z", "+00:00")
        ),
        "captured_at": captured_at
    }

    with engine.begin() as connection:
        connection.execute(
            stream_samples_table.insert().values(**sample)
        )

    return sample


def get_stream_samples():
    """Recupera las mediciones históricas."""

    statement = (
        select(stream_samples_table)
        .order_by(
            stream_samples_table.c.captured_at.asc()
        )
    )

    with engine.connect() as connection:
        result = connection.execute(statement)
        return [
            dict(row)
            for row in result.mappings()
        ]
