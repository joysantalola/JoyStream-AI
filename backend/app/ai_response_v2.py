"""JoyStream AI 25E: respuestas deterministas, adaptadas a la intención.

Importa ai_insights de 25D para sus consultas y para analizar muestras reales.
No escribe datos y no contacta con servicios externos.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.ai_insights import classify, normalize, audience_insights, _latest_session

MADRID = ZoneInfo('Europe/Madrid')


def readable_date(value, *, hour=True):
    """Fechas de Twitch/DB en hora española. Sin TZ => UTC, indicado explícitamente."""
    if not value:
        return 'fecha no disponible'
    try:
        if isinstance(value, str):
            date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        elif isinstance(value, datetime):
            date = value
        else:
            return 'fecha no disponible'
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        date = date.astimezone(MADRID)
        return date.strftime('%d/%m/%Y a las %H:%M h (hora española)') if hour else date.strftime('%d/%m/%Y')
    except (ValueError, TypeError, OverflowError):
        return 'fecha no disponible'


def count(value):
    if value is None:
        return 'no disponible'
    try:
        return str(int(value))
    except (ValueError, TypeError, OverflowError):
        return 'no disponible'


def decimal(value):
    if value is None:
        return 'no disponible'
    try:
        return f'{float(value):.2f}'.rstrip('0').rstrip('.').replace('.', ',')
    except (ValueError, TypeError, OverflowError):
        return 'no disponible'


def route(question):
    """25D decide primero; 25E diferencia preguntas breves dentro de 'latest_stream'."""
    q = normalize(question)
    if any(token in q for token in ('ultimo directo', 'ultima emision', 'ultimo stream')) and any(
        token in q for token in ('recomiend', 'recomendacion', 'que puedo mejorar', 'como mejorar')
    ):
        return 'live_recommendations'
    kind = classify(question)
    if kind != 'latest_stream':
        return kind
    if any(token in q for token in ('cuando', 'a que hora', 'en que momento', 'hora del pico')) and any(
        token in q for token in ('pico', 'maximo')
    ):
        return 'peak_time'
    if any(token in q for token in ('recomiend', 'recomendacion', 'que puedo mejorar', 'como mejorar')):
        return 'live_recommendations'
    return kind


def _live_details(context, fetch_samples):
    session = _latest_session(context)
    if not session:
        return None, None
    stream_id = session.get('stream_id')
    if not stream_id or fetch_samples is None:
        return session, None
    return session, audience_insights(fetch_samples(stream_id))


def precise_answer(question, context, fetch_samples):
    """Devuelve texto o None: None significa usar ruta anterior/LLM sin inventar datos."""
    kind = route(question)
    community = context.get('community') or {}
    if kind == 'followers_current':
        followers = community.get('followers_current')
        if followers is None:
            return 'No tengo una medición válida de seguidores. Actualiza Comunidad.'
        return (f'Tienes **{count(followers)} seguidores**. '
                f'Última medición: {readable_date(community.get("last_measurement"))}.')
    if kind == 'followers_growth':
        variation = community.get('followers_net_change')
        first = community.get('first_measurement')
        last = community.get('last_measurement')
        if variation is None or not first or not last or first == last or community.get('measurements', 0) < 2:
            return 'Todavía no hay dos mediciones diferentes suficientes para calcular la variación neta de seguidores.'
        signed = f'{int(variation):+d}'
        return (f'La **variación neta de seguidores es {signed}** entre el '
                f'{readable_date(first)} y el {readable_date(last)}. '
                'Es la diferencia entre los totales registrados, no el número bruto de personas que te han seguido.')
    if kind == 'subscribers_current':
        subs = community.get('subscribers_current')
        if subs is None:
            return 'El total de suscriptores no está disponible en la última medición. **No significa cero**.'
        return (f'Tienes **{count(subs)} suscriptores** según la última medición '
                f'({readable_date(community.get("last_measurement"))}).')
    if kind in ('peak_time', 'latest_stream', 'live_recommendations'):
        session, detail = _live_details(context, fetch_samples)
        if session is None:
            return 'Todavía no hay directos monitorizados con datos suficientes para responder.'
        peak_summary = session.get('peak_viewers')
        if kind == 'peak_time':
            if detail is None:
                return 'No hay muestras temporales válidas para saber cuándo ocurrió el pico del último directo.'
            repeats = detail['peak_occurrences']
            discrepancy = ''
            try:
                if peak_summary is not None and float(peak_summary) != float(detail['peak']):
                    discrepancy = ' **Atención:** el pico del resumen no coincide con el de las muestras.'
            except (ValueError, TypeError):
                pass
            return (f'El primer pico observado de **{detail["peak"]} espectadores** ocurrió el '
                    f'**{readable_date(detail["peak_first_at"])}** en el último directo. '
                    f'El mismo máximo aparece en **{repeats} mediciones**.' + discrepancy)
        if kind == 'live_recommendations':
            if detail is None:
                return ('Necesito muestras temporales del último directo para recomendar '
                        'acciones basadas en su evolución, no en suposiciones.')
            a = detail.get('first_half_mean')
            b = detail.get('second_half_mean')
            if a is None or b is None:
                return 'Aún no hay suficientes muestras en ambas mitades del último directo para comparar su audiencia.'
            direction = 'mayor' if b > a else 'menor' if b < a else 'similar'
            return (f'En tu último directo, la primera mitad observada promedió **{decimal(a)}** '
                    f'espectadores y la segunda **{decimal(b)}**; la segunda fue {direction}.\n\n'
                    '**Dos pruebas para tus próximos tres directos:**\n'
                    '1. Mantén constante el tipo de contenido y compara las medias de ambas mitades.\n'
                    '2. Anota cambios de juego, pausas o eventos importantes y contrástalos con las horas de audiencia, '
                    'sin asumir causalidad.\n\n'
                    '**Limitación:** son comparaciones descriptivas de muestras, no predicciones.')
        answer = (f'**Último directo** ({readable_date(session.get("started_at"))}): '
                  f'**{decimal(session.get("average_viewers"))}** espectadores de media, '
                  f'pico de **{count(peak_summary)}**, mínimo de **{count(session.get("min_viewers"))}**, '
                  f'**{decimal(session.get("observed_minutes"))} min** observados '
                  f'y **{count(session.get("measurements"))} mediciones**.')
        if detail is None:
            return answer + '\n\nNo tengo muestras temporales válidas para describir la evolución.'
        answer += (f'\n\n**Pico verificado:** {detail["peak"]} espectadores por primera vez el '
                   f'{readable_date(detail["peak_first_at"])} '
                   f'({detail["peak_occurrences"]} mediciones con ese máximo).')
        a, b = detail.get('first_half_mean'), detail.get('second_half_mean')
        if a is not None and b is not None:
            relation = 'mayor' if b > a else 'menor' if b < a else 'similar'
            answer += (f'\n\n**Evolución por mitades del tiempo observado:** primera **{decimal(a)}**, '
                       f'segunda **{decimal(b)}** espectadores de media. '
                       f'La segunda mitad tuvo una media {relation}; esto no prueba una tendencia constante.')
        else:
            answer += '\n\nNo hay suficientes muestras para comparar las dos mitades temporales.'
        answer += '\n\n**Limitación:** son observaciones puntuales; no equivalen a una medición continua.'
        return answer
    return None
