"""Paso 25D: cálculos verificables y clasificación conservadora de preguntas.

No realiza consultas de red ni modifica datos. Las consultas SQL son de solo lectura.
"""
from __future__ import annotations

from datetime import datetime
from statistics import mean
import re
import unicodedata


def normalize(text: object) -> str:
    raw = unicodedata.normalize('NFKD', str(text or '').lower())
    return re.sub(r'\s+', ' ', ''.join(c for c in raw if not unicodedata.combining(c))).strip()


def _has(q: str, *terms: str) -> bool:
    return any(re.search(term, q) for term in terms)


def classify(question: str) -> str | None:
    """Solo asigna rutas cuando la intención es suficientemente clara.

    Las preguntas mixtas/abiertas se derivan a la IA con contexto acotado.
    """
    q = normalize(question)
    if not q:
        return None

    follower = _has(q, r'\bseguidores?\b', r'\bfollowers?\b', r'\b(?:gente|personas) (?:que )?me (?:sigue|siguen)\b', r'\bme siguen\b')
    subscription = _has(q, r'\bsuscriptores?\b', r'\bsubs\b', r'\bsubscripciones?\b', r'\bsuscripciones?\b')
    live = _has(q, r'\bdirecto\b', r'\bstream\b', r'\bemision\b', r'\baudiencia\b', r'\bespectadores?\b', r'\bviewers?\b')
    broad = _has(q, r'\bpor que\b', r'\brecomiend', r'\bestrateg', r'\bconsej', r'\bpredic', r'\bcomo mejor', r'\bideas?\b')
    mixed = sum((follower, subscription, live)) > 1
    if broad or mixed:
        return None

    historic = _has(q, r'\b(?:ayer|anteayer|semana pasada|mes pasado|hace \d+|en \d{4})\b')
    if not follower and not subscription and not live and _has(q, r'\bcomunidad\b') and _has(q, r'\bevolucion', r'\bevolucionad', r'\bcrecimient', r'\bvariacion\b'):
        follower = True
    if follower:
        if historic:
            return 'followers_historic'
        if _has(q, r'\b(?:ganad|perdid|crecid|subid|bajad|aumentad|disminuid)', r'\b(?:variacion|diferencia|crecimiento|evolucion|cambio)', r'\b(?:desde|entre)\b'):
            return 'followers_growth'
        if _has(q, r'\b(?:cuant|numero|total|cantidad|actual|ahora|tengo|tienes|dime|muestra|mis|me sigue|me siguen|seguidores|followers)'):
            return 'followers_current'
    if subscription:
        if historic:
            return 'subscribers_historic'
        if _has(q, r'\b(?:cuant|numero|total|cantidad|actual|ahora|tengo|tienes|dime|mis|suscriptores|subs)'):
            return 'subscribers_current'
    if live:
        if historic:
            return None
        if _has(q, r'\b(?:ultimo|ultima|reciente|mas reciente)\b') and _has(q, r'\b(?:analiz|resumen|media|promedio|pico|evolucion|duracion|estadistic|como fue|como ha ido|cuant|espectadores|directo|stream|emision)'):
            return 'latest_stream'
        if _has(q, r'\b(?:cuando|hora|momento)\b') and _has(q, r'\b(?:pico|maximo)\b'):
            return 'latest_stream'
    return None


def _format_ts(value):
    if value is None:
        return 'fecha no disponible'
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _num(value):
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _format_number(value):
    n = _num(value)
    if n is None:
        return '—'
    return str(int(n)) if n.is_integer() else f'{n:.2f}'.rstrip('0').rstrip('.')


def audience_insights(samples: list[dict]) -> dict | None:
    """Calcula instantes reales del pico y tendencia por mitades observadas.

    Las mitades se separan por el tiempo entre primera y última medición;
    no se extrapola fuera de la ventana observada.
    """
    records = []
    for row in samples:
        ts = row.get('captured_at')
        val = _num(row.get('viewer_count'))
        if not isinstance(ts, datetime) or val is None or val < 0:
            continue
        records.append((ts, val))
    records.sort(key=lambda item: item[0])
    if not records:
        return None
    peak = max(v for _, v in records)
    peaks = [t for t, v in records if v == peak]
    result = {
        'measurements': len(records),
        'peak': _format_number(peak),
        'peak_first_at': _format_ts(peaks[0]),
        'peak_last_at': _format_ts(peaks[-1]),
        'peak_occurrences': len(peaks),
        'first_viewers': _format_number(records[0][1]),
        'last_viewers': _format_number(records[-1][1]),
        'first_at': _format_ts(records[0][0]),
        'last_at': _format_ts(records[-1][0]),
        'first_half_mean': None,
        'second_half_mean': None,
        'trend': 'Muestras insuficientes para comparar mitades.',
    }
    if len(records) >= 4 and records[0][0] != records[-1][0]:
        split = records[0][0] + (records[-1][0] - records[0][0]) / 2
        first_half = [v for t, v in records if t <= split]
        second_half = [v for t, v in records if t > split]
        if len(first_half) >= 2 and len(second_half) >= 2:
            a, b = mean(first_half), mean(second_half)
            result['first_half_mean'] = round(a, 2)
            result['second_half_mean'] = round(b, 2)
            if abs(a - b) < 0.05:
                result['trend'] = 'Medias prácticamente iguales entre las dos mitades observadas.'
            elif b > a:
                result['trend'] = 'La segunda mitad tuvo una media mayor que la primera; no implica crecimiento constante.'
            else:
                result['trend'] = 'La segunda mitad tuvo una media menor que la primera; no implica caída constante.'
    return result


def _latest_session(context):
    sessions = (context.get('live') or {}).get('recent_sessions') or []
    return max(sessions, key=lambda s: str(s.get('started_at') or '')) if sessions else None


def answer_fact(question: str, context: dict, fetch_samples=None) -> str | None:
    kind = classify(question)
    if kind is None:
        return None
    community = context.get('community') or {}
    if kind in ('followers_historic', 'subscribers_historic'):
        return ('No puedo dar una cifra histórica para esa fecha con el resumen actual. '
                'Necesito seleccionar mediciones de PostgreSQL dentro del periodo solicitado.')
    if kind == 'followers_current':
        n = community.get('followers_current', community.get('followers'))
        if n is None:
            return 'No hay una medición válida de seguidores. Actualiza Comunidad para consultarla.'
        return (f'Tienes **{_format_number(n)} seguidores** según la última medición '
                f'({_format_ts(community.get("last_measurement"))}).')
    if kind == 'followers_growth':
        delta = community.get('followers_net_change')
        first = community.get('first_measurement')
        last = community.get('last_measurement')
        measurements = community.get('measurements', 0)
        if delta is None or not first or not last or measurements == 1 or first == last:
            return 'No hay dos mediciones distintas suficientes para calcular la variación neta de seguidores.'
        return (f'La **variación neta es {_num(delta):+g} seguidores** desde '
                f'{_format_ts(first)} hasta {_format_ts(last)}. '
                'Es la diferencia entre totales; **no equivale a nuevos follows brutos**.')
    if kind == 'subscribers_current':
        n = community.get('subscribers_current', community.get('subscribers'))
        if n is None:
            return 'El total de suscriptores no está disponible en la última medición de Comunidad; no significa cero.'
        return f'La última medición registra **{_format_number(n)} suscriptores** ({_format_ts(community.get("last_measurement"))}).'
    if kind == 'latest_stream':
        session = _latest_session(context)
        if session is None:
            return 'Todavía no hay directos monitorizados con muestras en PostgreSQL.'
        head = (f'**Último directo**, iniciado el {_format_ts(session.get("started_at"))}: '
                f'media de **{_format_number(session.get("average_viewers"))}** espectadores; '
                f'pico de **{_format_number(session.get("peak_viewers"))}**; '
                f'mínimo de **{_format_number(session.get("min_viewers"))}**; '
                f'**{_format_number(session.get("observed_minutes"))} minutos observados** '
                f'y **{_format_number(session.get("measurements"))} mediciones**.')
        stream_id = session.get('stream_id')
        if fetch_samples is None or not stream_id:
            return head + ' No he consultado la serie temporal: no puedo situar el pico ni describir la evolución.'
        detail = audience_insights(fetch_samples(stream_id))
        if detail is None:
            return head + ' No hay muestras temporales válidas para localizar el pico.'
        if _num(session.get('peak_viewers')) != _num(detail['peak']):
            head += ' Advertencia: el pico del resumen y el de las muestras consultadas no coincide.'
        return (head + '\n\n**Evolución comprobada:** el pico registrado de '
                f'**{detail["peak"]}** espectadores ocurrió por primera vez '
                f'el **{detail["peak_first_at"]}**'
                + (f' (se repitió {detail["peak_occurrences"]} veces)' if detail['peak_occurrences'] > 1 else '')
                + f'. Primera muestra: **{detail["first_viewers"]}**, última muestra: **{detail["last_viewers"]}**. '
                + (f'Media primera mitad: **{_format_number(detail["first_half_mean"])}**; '
                   f'segunda mitad: **{_format_number(detail["second_half_mean"])}**. '
                   if detail['first_half_mean'] is not None else '')
                + detail['trend']
                + '\n\n**Limitación:** las muestras son observaciones puntuales, no una medición continua.')
    return None


def load_stream_samples(stream_id: str) -> list[dict]:
    """Consulta de solo lectura, limitada al directo seleccionado."""
    from sqlalchemy import select
    from app.database import engine, stream_samples_table
    stmt = (select(stream_samples_table.c.captured_at, stream_samples_table.c.viewer_count)
            .where(stream_samples_table.c.stream_id == stream_id)
            .order_by(stream_samples_table.c.captured_at, stream_samples_table.c.id))
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(stmt).mappings()]
