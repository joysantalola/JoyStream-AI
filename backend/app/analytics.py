
from collections import defaultdict
from statistics import mean

from sqlalchemy import select

from app.database import engine, stream_samples_table


def load_samples():
    """Obtiene las muestras desde PostgreSQL."""

    statement = (
        select(stream_samples_table)
        .order_by(
            stream_samples_table.c.captured_at.asc(),
            stream_samples_table.c.id.asc()
        )
    )

    with engine.connect() as connection:
        rows = connection.execute(statement)
        return [dict(row) for row in rows.mappings()]


def normalize_game(name):
    """Normaliza el nombre de la categoría."""
    return (name or "").strip() or "Sin categoría"


def session_report():
    """Calcula estadísticas de cada directo."""

    samples = load_samples()
    sessions = defaultdict(list)

    for sample in samples:
        sessions[sample["stream_id"]].append(sample)

    results = []

    for stream_id, records in sessions.items():

        viewers = [
            record["viewer_count"]
            for record in records
        ]

        first = records[0]["captured_at"]
        last = records[-1]["captured_at"]

        games = sorted({
            normalize_game(record["game_name"])
            for record in records
        })

        observed_minutes = (
            last - first
        ).total_seconds() / 60

        results.append({
            "stream_id": stream_id,
            "started_at": records[0]["started_at"],
            "first_sample": first,
            "last_sample": last,
            "games": games,
            "games_label": ", ".join(games),
            "average_viewers": round(mean(viewers), 2),
            "peak_viewers": max(viewers),
            "min_viewers": min(viewers),
            "measurements": len(records),
            "observed_minutes": round(
                observed_minutes, 1
            )
        })

    return sorted(
        results,
        key=lambda item: item["started_at"],
        reverse=True
    )


def games_report():
    """Compara las muestras por videojuego."""

    samples = load_samples()

    games = defaultdict(
        lambda: {"viewers": [], "sessions": set()}
    )

    for sample in samples:

        name = normalize_game(sample["game_name"])

        games[name]["viewers"].append(
            sample["viewer_count"]
        )

        games[name]["sessions"].add(
            sample["stream_id"]
        )

    results = []

    for game_name, data in games.items():

        viewers = data["viewers"]

        results.append({
            "game_name": game_name,
            "sessions": len(data["sessions"]),
            "measurements": len(viewers),
            "average_viewers": round(mean(viewers), 2),
            "peak_viewers": max(viewers),
            "min_viewers": min(viewers)
        })

    return sorted(
        results,
        key=lambda item: item["average_viewers"],
        reverse=True
    )
