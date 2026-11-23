"""JoyStream AI Paso 25G: comparativas de cambios de juego y días de emisión.

Solo calcula a partir del historial de sesiones monitorizadas. No modifica
las tablas originales de Twitch ni atribuye causalidad a diferencias observadas.
"""
from __future__ import annotations

from statistics import mean
from datetime import datetime
from zoneinfo import ZoneInfo
import re

from app.ai_insights import normalize
from app.ai_comparisons import (
    _sessions,
    _games_for_session,
    _fmt,
    _fmt_int,
    load_session_history,
)

MADRID = ZoneInfo("Europe/Madrid")

_WEEKDAYS = (
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo",
)


def classify_advanced_comparison(question: str) -> str | None:
    """Clasifica únicamente preguntas comparativas inequívocas del Paso 25G."""
    q = normalize(question)
    if not q:
        return None

    # Una pregunta explícita sobre el cambio entre dos juegos tiene prioridad
    # sobre la comparación general de categorías.
    switch_action = any(term in q for term in (
        "cambiar de juego", "cambio de juego", "cambio entre juegos",
        "cambiar de videojuego", "cambio de videojuego",
        "al cambiar de juego", "cuando cambie de juego",
        "cambiando de juego", "cambie de juego",
    ))
    compare_action = any(term in q for term in (
        "como me fue", "que tal", "funciono", "compar", "mejor",
        "audiencia", "espectadores", "rendimiento", "resultado",
    ))
    explicit_two_streams = (
        (
            any(term in q for term in ("mismo dia", "hoy", "esta tarde", "esta noche"))
            or bool(re.search(r"\b\d{1,2}\s+de\s+[a-z]+\b", q))
            or bool(re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", q))
        )
        and any(term in q for term in ("directos", "emisiones", "streams"))
        and any(term in q for term in ("juego", "videojuego", "rocket league", "fortnite", "peak"))
        and compare_action
    )
    named_game_switch = (
        any(term in q for term in ("cambiar", "cambie", "cambio", "cambiando"))
        and bool(re.search(r"\bde .+ a .+", q))
    )
    if (switch_action and (compare_action or "cambio de juego" in q)) or named_game_switch or explicit_two_streams:
        return "game_switch"

    weekday_terms = any(term in q for term in (
        "dia de la semana", "dias de la semana", "que dia",
        "lunes", "martes", "miercoles", "jueves", "viernes",
        "sabado", "domingo",
    ))
    weekday_question = any(term in q for term in (
        "mejor", "funciona", "rinde", "audiencia", "espectadores",
        "conviene", "mas gente", "mas publico", "mas espectadores",
        "mas audiencia",
    ))
    if weekday_terms and weekday_question:
        return "best_weekday"

    game_terms = any(term in q for term in (
        "juego", "videojuego", "categoria", "rocket league", "fortnite", "peak",
    ))
    game_question = any(term in q for term in (
        "mejor", "funciona", "rinde", "resultado", "audiencia",
        "atrae", "espectadores", "compar",
    ))
    if game_terms and game_question:
        return "best_game"

    return None


def _one_game(session: dict) -> str | None:
    """Devuelve categoría solo si la sesión tiene exactamente una categoría."""
    games = _games_for_session(session)
    if len(games) != 1:
        return None
    return games[0]


def _clock(session: dict) -> str:
    return session["_started_dt"].astimezone(MADRID).strftime("%H:%M h")


def _local_day(session: dict):
    return session["_started_dt"].astimezone(MADRID).date()


def _duration(session: dict) -> str:
    value = session.get("observed_minutes")
    if value is None:
        return "duración observada no disponible"
    try:
        return f"{_fmt(value, 1)} min observados"
    except (TypeError, ValueError):
        return "duración observada no disponible"


def _delta_text(previous: float, current: float) -> str:
    delta = current - previous
    if abs(delta) < 0.005:
        return "prácticamente igual"
    direction = "más" if delta > 0 else "menos"
    return f"{_fmt(abs(delta))} espectadores {direction}"


def _requested_session_count(question: str) -> int | None:
    """Extrae una cantidad explícita de emisiones indicada por el usuario."""
    q = normalize(question)
    words = {
        "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
        "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
        "diez": 10,
    }
    match = re.search(
        r"\b(\d+|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)"
        r"\s+(?:directos?|emisiones?|streams?)\b",
        q,
    )
    if not match:
        return None
    token = match.group(1)
    try:
        count = int(token)
    except ValueError:
        count = words.get(token)
    return count if count and count >= 2 else None


def _session_label(session: dict) -> str:
    """Fecha y hora local en una sola expresión, sin duplicar la hora."""
    return session["_started_dt"].astimezone(MADRID).strftime("%d/%m/%Y a las %H:%M h")


def _requested_games(question: str, sessions: list[dict]) -> list[str]:
    """Detecta categorías mencionadas explícitamente que existan en los datos."""
    q = normalize(question)
    found = []
    seen = set()
    for session in sessions:
        game = _one_game(session)
        if not game:
            continue
        key = normalize(game)
        if key and key in q and key not in seen:
            found.append(game)
            seen.add(key)
    return found


def _deduplicate_sessions(sessions: list[dict]) -> list[dict]:
    """Ordena cronológicamente y evita contar dos veces el mismo stream_id."""
    ordered = sorted(sessions, key=lambda item: item["_started_dt"])
    result = []
    seen_ids = set()
    for session in ordered:
        stream_id = session.get("stream_id")
        if stream_id is not None:
            key = str(stream_id)
            if key in seen_ids:
                continue
            seen_ids.add(key)
        result.append(session)
    return result


def _reference_local_date(reference_time=None):
    if reference_time is None:
        return datetime.now(MADRID).date()
    if isinstance(reference_time, str):
        try:
            reference_time = datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(MADRID).date()
    if not isinstance(reference_time, datetime):
        return datetime.now(MADRID).date()
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=MADRID)
    return reference_time.astimezone(MADRID).date()



def _measurements(session: dict) -> int | None:
    """Número de mediciones válidas que intervienen en la media de la sesión."""
    raw = session.get("measurements")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        count = int(raw)
        if float(raw) != count or count <= 0:
            return None
    except (TypeError, ValueError, OverflowError):
        return None
    return count


def _weighted_average(sessions: list[dict]) -> tuple[float | None, int | None]:
    """Media ponderada por muestras de medias de sesión ya redondeadas.

    No equivale exactamente a recalcular la media desde los registros brutos.
    No inventa pesos cuando falta el número de muestras.
    """
    if not sessions:
        return None, None
    pairs = []
    for session in sessions:
        count = _measurements(session)
        avg = session.get("_average_num")
        if count is None or avg is None:
            return None, None
        pairs.append((float(avg), count))
    total = sum(count for _, count in pairs)
    return (sum(avg * count for avg, count in pairs) / total, total) if total else (None, None)


def _percent_change(previous: float, current: float) -> str:
    if previous <= 0:
        return "no calculable porque la referencia es cero"
    change = (current - previous) / previous * 100
    prefix = "+" if change > 0 else ""
    return f"{prefix}{format(change, '.1f').rstrip('0').rstrip('.').replace('.', ',')} %"


def _compare_multiple_sessions(
    selected: list[dict],
    target_day,
    requested_count: int | None = None,
) -> str:
    """Compara sesiones individuales y agrega dos métricas distintas por juego."""
    if len(selected) < 2:
        return "Necesito al menos dos emisiones independientes con muestras registradas para compararlas."

    day_label = target_day.strftime("%d/%m/%Y") if target_day else "el periodo seleccionado"
    lines = [f"**Comparación de {len(selected)} emisiones independientes · {day_label}**", ""]
    groups: dict[str, list[dict]] = {}
    mixed_count = 0
    for index, session in enumerate(selected, start=1):
        game = _one_game(session)
        if game:
            groups.setdefault(game, []).append(session)
            game_label = game
        else:
            game_label = "Categoría no única o no identificada"
            mixed_count += 1
        avg = session["_average_num"]
        peak = session.get("_peak_num")
        count = _measurements(session)
        details = f"media **{_fmt(avg)}** espectadores"
        if peak is not None:
            details += f"; pico **{_fmt_int(peak)}**"
        details += f"; {_duration(session)}"
        details += f"; **{count} muestras**" if count is not None else "; muestras no disponibles"
        lines.append(f"- **Emisión {index}** ({_session_label(session)}, **{game_label}**): {details}.")

    lines.extend(["", "**Resumen por videojuego**"])
    grouped_results = []
    for game, game_sessions in groups.items():
        avg_session = mean(s["_average_num"] for s in game_sessions)
        weighted, samples = _weighted_average(game_sessions)
        peaks = [s["_peak_num"] for s in game_sessions if s.get("_peak_num") is not None]
        peak_text = f"; pico máximo **{_fmt_int(max(peaks))}**" if peaks else ""
        weighted_text = (
            f"; media ponderada por muestras **{_fmt(weighted)}** espectadores "
            f"(**{samples} muestras**)"
            if weighted is not None else
            "; media ponderada no disponible (faltan muestras válidas)"
        )
        lines.append(
            f"- **{game}**: {len(game_sessions)} "
            f"{'emisión' if len(game_sessions) == 1 else 'emisiones'}; "
            f"media de las medias **{_fmt(avg_session)}** espectadores"
            f"{weighted_text}{peak_text}."
        )
        grouped_results.append((game, avg_session, weighted, samples))

    if len(grouped_results) == 2:
        first_game, first_avg, first_weighted, _ = grouped_results[0]
        second_game, second_avg, second_weighted, _ = grouped_results[1]
        lines.extend([
            "",
            f"**Comparación por emisión:** **{second_game}** tuvo **{_delta_text(first_avg, second_avg)}** "
            f"frente a **{first_game}** (**{_percent_change(first_avg, second_avg)}**).",
        ])
        if first_weighted is not None and second_weighted is not None:
            lines.append(
                f"**Comparación ponderada por muestras:** **{second_game}** tuvo "
                f"**{_delta_text(first_weighted, second_weighted)}** frente a "
                f"**{first_game}** (**{_percent_change(first_weighted, second_weighted)}**)."
            )

    if mixed_count:
        lines.extend([
            "",
            f"Se excluyeron {mixed_count} emisiones del resumen por videojuego porque "
            "tenían varias categorías o no tenían una categoría identificada.",
        ])

    lines.extend([
        "",
        "**Cómo leerlo:** la media de las medias da el mismo peso a cada emisión; "
        "la media ponderada da más peso a las sesiones con más muestras. "
        "Se calcula a partir de medias de sesión redondeadas, por lo que puede existir "
        "una pequeña diferencia frente al cálculo sobre muestras originales. "
        "Las muestras son observaciones puntuales, no minutos de visualización.",
        "",
        "**Limitación:** comparar categorías con pocos directos, horarios y duraciones "
        "diferentes no demuestra que el videojuego cause mayor audiencia.",
    ])
    return "\n".join(lines)



def _compare_same_day_game_switch(
    sessions: list[dict],
    question: str = "",
    reference_time=None,
) -> str:
    """Compara la cantidad solicitada de emisiones o, por defecto, el último cambio."""
    ordered = _deduplicate_sessions(sessions)
    if not ordered:
        return "No hay emisiones monitorizadas disponibles para comparar."

    q = normalize(question)
    requested_count = _requested_session_count(question)
    requested_games = _requested_games(question, ordered)
    asks_for_day = any(term in q for term in (
        "hoy", "mismo dia", "esta tarde", "esta noche",
    ))
    asks_for_sessions = any(term in q for term in (
        "directo", "emision", "stream",
    ))

    # Una petición con cantidad o periodo explícito compara todas las sesiones
    # seleccionadas, no solo el último par de juegos diferentes.
    if requested_count is not None or (asks_for_day and asks_for_sessions):
        filtered = ordered
        if requested_games:
            requested_keys = {normalize(game) for game in requested_games}
            filtered = [
                session for session in filtered
                if (game := _one_game(session)) is not None
                and normalize(game) in requested_keys
            ]

        if "hoy" in q:
            target_day = _reference_local_date(reference_time)
        else:
            available_days = sorted({_local_day(session) for session in filtered})
            if not available_days:
                return "No encuentro emisiones con las categorías indicadas para comparar."
            if requested_count is not None:
                qualifying = [
                    day for day in available_days
                    if sum(_local_day(s) == day for s in filtered) >= requested_count
                ]
                target_day = qualifying[-1] if qualifying else available_days[-1]
            else:
                target_day = available_days[-1]

        day_sessions = [
            session for session in filtered
            if _local_day(session) == target_day
        ]
        day_sessions = _deduplicate_sessions(day_sessions)

        if not day_sessions:
            requested_day = target_day.strftime("%d/%m/%Y")
            return (
                f"No encuentro emisiones registradas para el {requested_day}"
                + (f" con las categorías {', '.join(requested_games)}." if requested_games else ".")
            )

        expected = requested_count if requested_count is not None else len(day_sessions)
        if len(day_sessions) < expected:
            found_games = [
                _one_game(session) or "categoría no identificada"
                for session in day_sessions
            ]
            return (
                f"He encontrado **{len(day_sessions)} de {expected} emisiones** "
                f"para el {target_day.strftime('%d/%m/%Y')}. "
                f"Categorías encontradas: {', '.join(found_games)}. "
                "No completaré la comparación con emisiones de otro día."
            )

        selected = day_sessions[-expected:] if len(day_sessions) > expected else day_sessions
        return _compare_multiple_sessions(selected, target_day, requested_count)

    # Sin cantidad ni día explícitos, mantenemos la comparación del último
    # cambio real entre dos emisiones consecutivas con categorías distintas.
    candidates = []
    for previous, current in zip(ordered, ordered[1:]):
        if _local_day(previous) != _local_day(current):
            continue
        old_game = _one_game(previous)
        new_game = _one_game(current)
        if not old_game or not new_game or normalize(old_game) == normalize(new_game):
            continue
        if requested_games:
            wanted = {normalize(game) for game in requested_games}
            if normalize(old_game) not in wanted or normalize(new_game) not in wanted:
                continue
        candidates.append((previous, current, old_game, new_game))

    if not candidates:
        return (
            "No encuentro dos emisiones independientes del mismo día, con una "
            "categoría única y diferente en cada una, para comparar un cambio de juego. "
            "Necesito que ambas emisiones tengan muestras registradas y categorías identificadas."
        )

    previous, current, old_game, new_game = candidates[-1]
    old_avg = previous["_average_num"]
    new_avg = current["_average_num"]
    delta = new_avg - old_avg

    if old_avg > 0:
        pct = f" ({'+' if delta > 0 else ''}{_fmt((delta / old_avg) * 100, 1)} %)"
    else:
        pct = " (porcentaje no calculado porque la media anterior fue cero)"

    old_peak = previous.get("_peak_num")
    new_peak = current.get("_peak_num")
    peak_line = ""
    if old_peak is not None and new_peak is not None:
        peak_delta = new_peak - old_peak
        peak_line = (
            f"\n- Pico: **{_fmt_int(old_peak)}** → **{_fmt_int(new_peak)}** "
            f"({'+' if peak_delta > 0 else ''}{_fmt_int(peak_delta)})."
        )

    return (
        "**Comparación de dos emisiones independientes del mismo día**\n\n"
        f"- Anterior ({_session_label(previous)}, **{old_game}**): "
        f"media **{_fmt(old_avg)}** espectadores; {_duration(previous)}.\n"
        f"- Posterior ({_session_label(current)}, **{new_game}**): "
        f"media **{_fmt(new_avg)}** espectadores; {_duration(current)}.\n"
        f"{peak_line}\n\n"
        f"La media de la segunda emisión fue **{_delta_text(old_avg, new_avg)}**{pct}.\n\n"
        "**Interpretación:** son dos emisiones distintas registradas con identificadores "
        "de directo diferentes. La diferencia describe lo observado; no demuestra que "
        "el cambio de videojuego causara el resultado. También pueden influir el horario, "
        "la duración observada, el día y las condiciones de cada emisión."
    )


def _compare_games_strict(sessions: list[dict]) -> str:
    groups: dict[str, list[dict]] = {}
    excluded_mixed = 0
    for session in sessions:
        game = _one_game(session)
        if game is None:
            if _games_for_session(session):
                excluded_mixed += 1
            continue
        groups.setdefault(game, []).append(session)

    eligible = [(name, values) for name, values in groups.items() if len(values) >= 2]
    if len(eligible) < 2:
        counts = sorted(groups.items(), key=lambda item: item[0].casefold())
        detail = "; ".join(f"{name}: {len(values)} directo(s)" for name, values in counts)
        extra = f" Se excluyeron {excluded_mixed} sesiones con varias categorías." if excluded_mixed else ""
        return (
            "Todavía no hay suficientes datos para comparar videojuegos con rigor. "
            "Necesito al menos dos emisiones de cada una de dos categorías distintas. "
            f"Datos disponibles: {detail or 'ninguno'}.{extra}"
        )

    eligible.sort(key=lambda item: mean(s["_average_num"] for s in item[1]), reverse=True)
    lines = ["**Comparativa por videojuego (sesiones con categoría única)**", ""]
    for game, values in eligible[:8]:
        avg = mean(s["_average_num"] for s in values)
        weighted, count = _weighted_average(values)
        extra = (
            f"; media ponderada por muestras **{_fmt(weighted)}** "
            f"(**{count} muestras**)" if weighted is not None
            else "; media ponderada no disponible (faltan muestras válidas)"
        )
        lines.append(f"- **{game}**: media por emisión **{_fmt(avg)}** en "
                     f"**{len(values)}** directos{extra}.")

    lines.extend([
        "",
        f"La mayor media por emisión observada corresponde a **{eligible[0][0]}**. "
        "Esto no implica que el juego cause mejores resultados.",
    ])
    if excluded_mixed:
        lines.append(f"Se excluyeron {excluded_mixed} emisiones con varias categorías.")
    lines.append("La media ponderada utiliza los números de muestras y medias de sesión "
                 "redondeadas; no debe confundirse con la media por emisión.")
    return "\n".join(lines)



def _compare_weekdays(sessions: list[dict]) -> str:
    groups: dict[str, list[float]] = {}
    for session in sessions:
        local = session["_started_dt"].astimezone(MADRID)
        day = _WEEKDAYS[local.weekday()]
        groups.setdefault(day, []).append(session["_average_num"])

    eligible = [(day, values) for day, values in groups.items() if len(values) >= 2]
    if len(eligible) < 2:
        counts = sorted(groups.items(), key=lambda item: item[0])
        detail = "; ".join(f"{day}: {len(values)} directo(s)" for day, values in counts)
        return (
            "Todavía no hay suficientes directos para comparar días de la semana. "
            "Necesito al menos dos emisiones en cada uno de dos días distintos. "
            f"Datos disponibles: {detail or 'ninguno'}."
        )

    eligible.sort(key=lambda item: mean(item[1]), reverse=True)
    lines = [
        f"- **{day.capitalize()}**: **{_fmt(mean(values))}** espectadores de media por directo "
        f"en {len(values)} directos."
        for day, values in eligible
    ]
    winner = eligible[0]
    return (
        "**Comparativa por día de la semana (hora española)**\n\n"
        + "\n".join(lines)
        + f"\n\nEl día con mayor media observada es **{winner[0]}**. "
        "La muestra puede ser pequeña y no controla el videojuego, la hora, "
        "la duración ni otros factores; no es una predicción de audiencia."
    )


def answer_advanced_comparison(
    question: str,
    context: dict,
    fetch_sessions=None,
) -> str | None:
    """Respuesta determinista para comparativas avanzadas; None si no corresponde."""
    intent = classify_advanced_comparison(question)
    if intent is None:
        return None

    sessions = _sessions(context, fetch_sessions or load_session_history)

    if intent == "game_switch":
        return _compare_same_day_game_switch(sessions, question, context.get('generated_at'))
    if intent == "best_game":
        return _compare_games_strict(sessions)
    if intent == "best_weekday":
        return _compare_weekdays(sessions)
    return None
