"""JoyStream AI Paso 25F: comparativas históricas y seguimiento de recomendaciones.

Las comparativas se calculan con sesiones observadas. No atribuye causalidad.
La única escritura es un registro de referencia cuando el usuario solicita
una recomendación; no modifica las tablas de Twitch ni las muestras originales.
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from zoneinfo import ZoneInfo
import re

from app.ai_insights import normalize

MADRID = ZoneInfo("Europe/Madrid")


def _dt(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str) and value.strip():
        try:
            result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


def _num(value):
    try:
        number = float(value)
        return number if number >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _fmt(value, digits=2):
    number = _num(value)
    if number is None:
        return "no disponible"
    return f"{number:.{digits}f}".rstrip("0").rstrip(".").replace(".", ",")


def _fmt_int(value):
    number = _num(value)
    return "no disponible" if number is None else str(int(number))


def _date(value):
    parsed = _dt(value)
    if parsed is None:
        return "fecha no disponible"
    return parsed.astimezone(MADRID).strftime("%d/%m/%Y a las %H:%M h")


def _sessions(context, fetch_sessions=None):
    rows = None
    if fetch_sessions is not None:
        try:
            rows = fetch_sessions()
        except Exception:
            rows = None
    if not rows:
        rows = ((context.get("live") or {}).get("recent_sessions") or [])
    valid = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        started = _dt(row.get("started_at"))
        average = _num(row.get("average_viewers"))
        if started is None or average is None:
            continue
        item = dict(row)
        item["_started_dt"] = started
        item["_average_num"] = average
        item["_peak_num"] = _num(row.get("peak_viewers"))
        valid.append(item)
    valid.sort(key=lambda item: item["_started_dt"])
    # Deduplicate in case the same sessions are supplied by both API/context.
    deduped = {}
    for item in valid:
        key = str(item.get("stream_id") or item["_started_dt"].isoformat())
        deduped[key] = item
    return sorted(deduped.values(), key=lambda item: item["_started_dt"])


def load_session_history():
    """Carga el historial completo mediante la misma función usada por analítica."""
    from app.analytics import session_report
    return session_report()


def _games_for_session(session):
    raw = session.get("games")
    if isinstance(raw, (list, tuple, set)):
        names = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str) and raw.strip():
        names = [part.strip() for part in re.split(r"[,;|]", raw) if part.strip()]
    else:
        label = session.get("games_label") or session.get("game_name")
        names = [str(label).strip()] if label and str(label).strip() else []
    ignored = {"desconocido", "unknown", "sin categoria", "sin categoría", "none"}
    return [name for name in names if normalize(name) not in ignored]


def classify_comparison(question):
    q = normalize(question)
    if not q:
        return None

    recommendation = any(term in q for term in (
        "ultima recomendacion", "ultimo consejo", "desde la recomendacion",
        "despues de la recomendacion", "despues del consejo", "he mejorado desde",
        "funciono la recomendacion", "funciono el consejo",
    ))
    if recommendation:
        return "after_recommendation"

    game_terms = any(term in q for term in ("juego", "videojuego", "categoria", "categoría"))
    compare_terms = any(term in q for term in ("mejor", "mejores", "funciona", "rinde", "resultados", "audiencia", "atrae"))
    if game_terms and compare_terms:
        return "best_game"

    time_terms = any(term in q for term in ("horario", "franja", "hora"))
    time_compare = any(term in q for term in ("mejor", "funciona", "rinde", "audiencia", "conviene", "cuando deberia", "cuando me conviene"))
    if time_terms and time_compare:
        return "best_time"

    live_terms = any(term in q for term in ("directo", "directos", "stream", "streams", "emision", "emisiones"))
    progress_terms = any(term in q for term in (
        "mejorando", "he mejorado", "comparado", "comparar", "respecto",
        "anterior", "ultimos", "ultimas", "rendimiento", "progreso",
    ))
    if live_terms and progress_terms:
        return "latest_vs_previous"
    if "estoy mejorando" in q or "he mejorado" in q:
        return "latest_vs_previous"
    return None


def _compare_latest_sessions(sessions):
    if len(sessions) < 2:
        return ("Todavía necesito al menos dos directos monitorizados para comparar "
                "el último con el anterior.")
    previous, current = sessions[-2], sessions[-1]
    old_avg, new_avg = previous["_average_num"], current["_average_num"]
    delta = new_avg - old_avg
    if abs(delta) < 0.005:
        change = "prácticamente igual"
    elif delta > 0:
        noun = "espectador" if abs(delta) == 1 else "espectadores"
        change = f"{_fmt(delta)} {noun} más de media"
    else:
        noun = "espectador" if abs(delta) == 1 else "espectadores"
        change = f"{_fmt(abs(delta))} {noun} menos de media"
    if old_avg > 0:
        pct = (delta / old_avg) * 100
        pct_text = f" ({'+' if pct > 0 else ''}{_fmt(pct, 1)} %)"
    else:
        pct_text = " (no calculo porcentaje porque la media anterior fue cero)"
    old_peak = previous.get("_peak_num")
    new_peak = current.get("_peak_num")
    peak_text = ""
    if old_peak is not None and new_peak is not None:
        peak_delta = new_peak - old_peak
        peak_text = (f" El pico pasó de **{_fmt_int(old_peak)}** a **{_fmt_int(new_peak)}** "
                     f"({'+' if peak_delta > 0 else ''}{_fmt_int(peak_delta)}).")
    old_game = ", ".join(_games_for_session(previous)) or "categoría no disponible"
    new_game = ", ".join(_games_for_session(current)) or "categoría no disponible"
    return (f"**Comparación de los dos últimos directos**\n\n"
            f"- Anterior ({_date(previous.get('started_at'))}, {old_game}): "
            f"media **{_fmt(old_avg)}** espectadores.\n"
            f"- Último ({_date(current.get('started_at'))}, {new_game}): "
            f"media **{_fmt(new_avg)}** espectadores.\n\n"
            f"La media del último fue **{change}**{pct_text}." + peak_text + "\n\n"
            "**Interpretación:** es una comparación descriptiva. Si cambiaron el juego, "
            "la duración, el horario u otras condiciones, no se puede atribuir la diferencia "
            "a una sola causa ni concluir una tendencia estable con solo dos directos.")


def _compare_games(sessions):
    groups = {}
    for session in sessions:
        names = _games_for_session(session)
        if not names:
            continue
        # Una sesión con varias categorías contribuye a cada categoría observada.
        for name in names:
            groups.setdefault(name, []).append(session["_average_num"])
    eligible = [(name, values) for name, values in groups.items() if len(values) >= 2]
    if len(eligible) < 2:
        return ("Todavía no hay suficientes datos para determinar qué videojuego funciona mejor. "
                "Necesito al menos dos directos registrados en cada una de dos categorías distintas.")
    eligible.sort(key=lambda item: mean(item[1]), reverse=True)
    lines = [f"- **{name}**: media de **{_fmt(mean(values))}** espectadores "
             f"en {len(values)} directos." for name, values in eligible[:5]]
    winner, winner_values = eligible[0]
    return (f"**Comparativa por videojuego**\n\n{chr(10).join(lines)}\n\n"
            f"La media más alta corresponde a **{winner}** ({len(winner_values)} directos). "
            "Esto no demuestra que el juego cause una mayor audiencia: también influyen "
            "horario, duración, promoción y variación entre emisiones. Compara más sesiones "
            "en condiciones similares antes de decidir.")


def _time_slot(hour):
    if 6 <= hour < 12:
        return "mañana"
    if 12 <= hour < 18:
        return "tarde"
    if 18 <= hour < 24:
        return "noche"
    return "madrugada"


def _compare_times(sessions):
    groups = {}
    for session in sessions:
        local = session["_started_dt"].astimezone(MADRID)
        slot = _time_slot(local.hour)
        groups.setdefault(slot, []).append(session["_average_num"])
    eligible = [(name, values) for name, values in groups.items() if len(values) >= 2]
    if len(eligible) < 2:
        return ("Aún no hay suficientes directos repartidos entre distintas franjas para "
                "identificar un horario que funcione mejor. Necesito al menos dos directos "
                "en cada una de dos franjas horarias distintas.")
    eligible.sort(key=lambda item: mean(item[1]), reverse=True)
    lines = [f"- **{name.capitalize()}**: **{_fmt(mean(values))}** espectadores de media "
             f"en {len(values)} directos." for name, values in eligible]
    winner = eligible[0]
    return (f"**Comparativa por franja de inicio (hora española)**\n\n{chr(10).join(lines)}\n\n"
            f"La franja con mayor media observada es **{winner[0]}**. La muestra sigue siendo "
            "pequeña y no controla el juego, la duración ni el día de la semana; no lo tomes "
            "como un horario óptimo definitivo.")


def _baseline_table():
    from sqlalchemy import (MetaData, Table, Column, Integer, String, Float,
                            DateTime, Text)
    metadata = MetaData()
    table = Table(
        "ai_experiment_baselines", metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("baseline_stream_id", String(128), nullable=False),
        Column("baseline_started_at", DateTime(timezone=True), nullable=False),
        Column("baseline_average_viewers", Float, nullable=False),
        Column("baseline_peak_viewers", Float, nullable=True),
        Column("baseline_games", Text, nullable=True),
        Column("recommendation_question", Text, nullable=False),
        Column("recommendation_text", Text, nullable=True),
    )
    return metadata, table


def save_recommendation_baseline(context, question, answer, save_callback=None):
    """Guarda una referencia al pedir recomendaciones; no registra que se hayan aplicado."""
    sessions = _sessions(context)
    if not sessions:
        return False
    session = sessions[-1]
    stream_id = session.get("stream_id")
    if stream_id is None:
        return False
    baseline = {
        "created_at": datetime.now(timezone.utc),
        "baseline_stream_id": str(stream_id),
        "baseline_started_at": session["_started_dt"],
        "baseline_average_viewers": session["_average_num"],
        "baseline_peak_viewers": session.get("_peak_num"),
        "baseline_games": ", ".join(_games_for_session(session)) or None,
        "recommendation_question": str(question)[:500],
        "recommendation_text": str(answer)[:4000],
    }
    if save_callback is not None:
        return bool(save_callback(baseline))
    try:
        from app.database import engine
        metadata, table = _baseline_table()
        with engine.begin() as connection:
            metadata.create_all(connection)
            from sqlalchemy import select, desc, insert
            existing = connection.execute(
                select(table.c.baseline_stream_id)
                .order_by(desc(table.c.created_at), desc(table.c.id)).limit(1)
            ).scalar_one_or_none()
            if str(existing) == str(stream_id):
                return False
            connection.execute(insert(table).values(**baseline))
        return True
    except Exception:
        # El chat debe responder aunque no se pueda persistir el seguimiento.
        return False


def _load_latest_baseline():
    from sqlalchemy import select, desc
    from app.database import engine
    metadata, table = _baseline_table()
    with engine.begin() as connection:
        metadata.create_all(connection)
        row = connection.execute(
            select(table).order_by(desc(table.c.created_at), desc(table.c.id)).limit(1)
        ).mappings().first()
        return dict(row) if row else None


def _after_recommendation(sessions, baseline_loader=None):
    try:
        baseline = baseline_loader() if baseline_loader else _load_latest_baseline()
    except Exception:
        return "No he podido consultar el registro local de recomendaciones. No voy a inferir si hubo mejora."
    if not baseline:
        return ("Todavía no hay una recomendación guardada como referencia. Pídeme una recomendación "
                "sobre un directo y guardaré sus métricas iniciales para compararlas con el siguiente.")
    if not sessions:
        return "No hay directos disponibles para comparar con la última recomendación guardada."
    current = sessions[-1]
    baseline_id = str(baseline.get("baseline_stream_id"))
    current_id = str(current.get("stream_id"))
    baseline_started = _dt(baseline.get("baseline_started_at"))
    if current_id == baseline_id or (baseline_started and current["_started_dt"] <= baseline_started):
        return (f"La última recomendación se guardó tomando como referencia el directo del "
                f"{_date(baseline_started)}. Todavía no hay un directo posterior registrado "
                "para medir cambios.")
    old_avg = _num(baseline.get("baseline_average_viewers"))
    new_avg = current["_average_num"]
    if old_avg is None:
        return "La referencia guardada no contiene una media válida; no puedo calcular la comparación."
    delta = new_avg - old_avg
    direction = "subió" if delta > 0.005 else "bajó" if delta < -0.005 else "se mantuvo prácticamente igual"
    pct = f" ({'+' if delta > 0 else ''}{_fmt((delta / old_avg) * 100, 1)} %)" if old_avg > 0 else ""
    old_game = baseline.get("baseline_games") or "categoría no disponible"
    new_game = ", ".join(_games_for_session(current)) or "categoría no disponible"
    return (f"**Comparación posterior a la última recomendación**\n\n"
            f"- Referencia ({_date(baseline_started)}, {old_game}): media **{_fmt(old_avg)}**.\n"
            f"- Directo posterior ({_date(current.get('started_at'))}, {new_game}): media **{_fmt(new_avg)}**.\n\n"
            f"La media {direction} **{_fmt(abs(delta))} espectadores**{pct}.\n\n"
            "Esto mide el cambio observado después de la recomendación; no confirma que se aplicara "
            "ni que la recomendación causara el resultado.")


def answer_comparison(question, context, fetch_sessions=None, baseline_loader=None):
    """Devuelve respuesta determinista para comparativas o None si no corresponde."""
    intent = classify_comparison(question)
    if intent is None:
        return None
    sessions = _sessions(context, fetch_sessions)
    if intent == "latest_vs_previous":
        return _compare_latest_sessions(sessions)
    if intent == "best_game":
        return _compare_games(sessions)
    if intent == "best_time":
        return _compare_times(sessions)
    if intent == "after_recommendation":
        return _after_recommendation(sessions, baseline_loader)
    return None
