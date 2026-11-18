"""JoyStream AI · Dashboard multipágina (Paso 18).

Ejecutar dentro del servicio dashboard de Docker Compose.
Requiere FastAPI accesible mediante API_URL.
"""

import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://backend:8000").rstrip("/")
CHANNEL_URL = "https://www.twitch.tv/joysantalola67"

st.set_page_config(
    page_title="JoyStream AI | Analytics",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS ligero: no depende de temas ni estilos internos inestables.
st.markdown(
    """
    <style>
      .block-container {max-width: 1450px; padding-top: 1.7rem;}
      h1 {letter-spacing: -.035em;}
      div[data-testid="stMetric"] {padding: 14px; border-radius: 13px; border: 1px solid rgba(120,120,120,.24);}
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path, timeout=20):
    """Devuelve JSON o informa del error sin romper el dashboard."""
    try:
        response = requests.get(f"{API_URL}{path}", timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        return None, str(exc)
    except ValueError:
        return None, "El backend no devolvió JSON válido."


def api_post(path, data=None, timeout=90):
    try:
        response = requests.post(f"{API_URL}{path}", json=data, timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            try:
                detail = str(exc.response.json().get("detail", ""))
            except ValueError:
                detail = exc.response.text[:180]
        return None, f"{exc}. {detail}".strip()
    except ValueError:
        return None, "El backend no devolvió JSON válido."


def to_df(payload):
    return pd.DataFrame(payload) if isinstance(payload, list) else pd.DataFrame()


def with_dates(df, columns=("created_at", "captured_at", "started_at")):
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], utc=True, errors="coerce")
    return df


def number(value):
    try:
        if value is None or pd.isna(value):
            return 0
        return int(value)
    except (ValueError, TypeError):
        return 0


def fmt(value):
    return f"{number(value):,}".replace(",", ".")


def sum_views(df):
    if df.empty or "view_count" not in df.columns:
        return 0
    return int(pd.to_numeric(df["view_count"], errors="coerce").fillna(0).sum())


def show_error(error, label):
    if error:
        st.error(f"No se pudieron cargar {label}: {error}")


def table(df, columns=None):
    if df.empty:
        st.info("Todavía no hay datos registrados para esta sección.")
        return
    columns = [c for c in (columns or df.columns.tolist()) if c in df.columns]
    st.dataframe(df[columns], use_container_width=True, hide_index=True)


def metric_row(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def load_core_data():
    videos, video_error = api_get("/db/videos")
    clips, clip_error = api_get("/db/clips")
    return with_dates(to_df(videos)), with_dates(to_df(clips)), video_error, clip_error


st.sidebar.title("🎮 JoyStream AI")
st.sidebar.caption("Panel local · joysantalola67")
page = st.sidebar.radio(
    "Secciones",
    [
        "🏠 Resumen", "🎬 Clips", "📹 VOD", "🔴 Directos",
        "👥 Comunidad", "🤖 Asistente IA", "🛠️ Estado del sistema",
    ],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.link_button("Ver canal en Twitch", CHANNEL_URL, use_container_width=True)

if st.sidebar.button("🔄 Sincronizar clips y VOD", use_container_width=True):
    with st.sidebar:
        with st.spinner("Sincronizando con Twitch..."):
            result, error = api_post("/sync", timeout=120)
        if error:
            st.error(error)
        else:
            st.success(
                f"Procesados: {result.get('videos_processed', 0)} VOD y "
                f"{result.get('clips_processed', 0)} clips"
            )
            st.rerun()

st.sidebar.caption("Los datos se actualizan al navegar o recargar la página.")


if page == "🏠 Resumen":
    st.title("📊 Resumen del canal")
    st.caption("Vista general del contenido almacenado; las vistas no equivalen a espectadores únicos.")
    videos, clips, video_error, clip_error = load_core_data()
    show_error(video_error, "los VOD")
    show_error(clip_error, "los clips")

    metric_row([
        ("🎬 Clips almacenados", fmt(len(clips))),
        ("📹 VOD almacenados", fmt(len(videos))),
        ("👀 Vistas de clips", fmt(sum_views(clips))),
        ("▶️ Vistas de VOD", fmt(sum_views(videos))),
    ])

    st.subheader("🏆 Clips con más visualizaciones")
    if not clips.empty and {"title", "view_count"}.issubset(clips.columns):
        top = clips.copy()
        top["view_count"] = pd.to_numeric(top["view_count"], errors="coerce").fillna(0)
        top = top.nlargest(8, "view_count")
        top["clip"] = top["title"].fillna("Sin título").astype(str).str.slice(0, 45)
        st.bar_chart(top, x="clip", y="view_count", horizontal=True)
    else:
        st.info("Sin clips para mostrar.")

    st.subheader("👥 Última medición de comunidad")
    community, error = api_get("/channel/history")
    if error:
        st.caption(f"Comunidad no disponible: {error}")
    elif community:
        latest = community[-1]
        subs = latest.get("subscribers")
        metric_row([
            ("Seguidores", fmt(latest.get("followers"))),
            ("Suscriptores", "No disponible" if subs is None else fmt(subs)),
        ])
    else:
        st.info("Aún no se ha registrado una medición de comunidad.")


elif page == "🎬 Clips":
    st.title("🎬 Analítica de clips")
    payload, error = api_get("/db/clips")
    show_error(error, "los clips")
    clips = with_dates(to_df(payload))

    if clips.empty:
        st.info("Sin clips guardados. Usa el botón de sincronización.")
    else:
        if "view_count" in clips.columns:
            clips["view_count"] = pd.to_numeric(clips["view_count"], errors="coerce").fillna(0)
        if "game_id" in clips.columns:
            options = sorted(clips["game_id"].dropna().astype(str).unique().tolist())
            selected = st.selectbox("Filtrar por Game ID", ["Todos"] + options)
            if selected != "Todos":
                clips = clips[clips["game_id"].astype(str) == selected]
            st.caption("En una mejora posterior resolveremos los Game ID a nombres de juegos.")

        metric_row([
            ("Clips filtrados", fmt(len(clips))),
            ("Vistas acumuladas", fmt(sum_views(clips))),
            ("Media de vistas", f"{pd.to_numeric(clips['view_count'], errors='coerce').mean():.1f}" if not clips.empty and "view_count" in clips else "—"),
        ])
        if not clips.empty and {"title", "view_count"}.issubset(clips.columns):
            top = clips.nlargest(10, "view_count").copy()
            top["clip"] = top["title"].fillna("Sin título").astype(str).str.slice(0, 40)
            st.subheader("Top 10 clips")
            st.bar_chart(top, x="clip", y="view_count", horizontal=True)
        st.subheader("Clips registrados")
        table(clips, ["title", "created_at", "view_count", "duration", "game_id", "url"])

    st.divider()
    st.subheader("📈 Evolución histórica de un clip")
    history, error = api_get("/history/clips")
    show_error(error, "el historial de clips")
    df_history = with_dates(to_df(history))
    if not df_history.empty and "content_id" in df_history.columns:
        names, _ = api_get("/db/clips")
        name_map = {str(c["id"]): c.get("title", c["id"]) for c in (names or []) if "id" in c}
        options = df_history["content_id"].dropna().astype(str).unique().tolist()
        chosen = st.selectbox("Clip a analizar", options, format_func=lambda x: name_map.get(x, x))
        selected = df_history[df_history["content_id"].astype(str) == chosen].sort_values("captured_at")
        st.line_chart(selected, x="captured_at", y="view_count")
        if len(selected):
            delta = number(selected.iloc[-1]["view_count"]) - number(selected.iloc[0]["view_count"])
            st.metric("Variación desde la primera muestra", fmt(delta))
        st.caption("Las muestras se generan durante las sincronizaciones de Twitch, no cada visualización.")
    else:
        st.info("Todavía no hay historial de visualizaciones de clips.")


elif page == "📹 VOD":
    st.title("📹 Vídeos y VOD")
    payload, error = api_get("/db/videos")
    show_error(error, "los VOD")
    videos = with_dates(to_df(payload))
    if videos.empty:
        st.info("Todavía no hay VOD registrados.")
    else:
        metric_row([
            ("VOD almacenados", fmt(len(videos))),
            ("Visualizaciones acumuladas", fmt(sum_views(videos))),
        ])
        if {"created_at", "view_count"}.issubset(videos.columns):
            chart = videos.sort_values("created_at").copy()
            chart["view_count"] = pd.to_numeric(chart["view_count"], errors="coerce").fillna(0)
            st.subheader("Visualizaciones por fecha del VOD")
            st.bar_chart(chart, x="created_at", y="view_count")
        st.subheader("Listado de VOD")
        table(videos, ["title", "created_at", "duration", "view_count", "url"])
    st.caption("Las vistas de VOD no deben confundirse con los espectadores simultáneos.")


elif page == "🔴 Directos":
    st.title("🔴 Monitorización de directos")
    live, live_error = api_get("/twitch/live")
    if live_error:
        st.warning(f"No se pudo consultar el estado actual: {live_error}")
    elif live and live.get("is_live"):
        current = live.get("stream") or {}
        st.success(f"EN DIRECTO · {current.get('game_name', 'Sin categoría')} · "
                   f"{fmt(current.get('viewer_count'))} espectadores")
        st.write(f"**Título:** {current.get('title', 'Sin título')}")
    else:
        st.info("El canal está offline en este momento.")

    session_payload, session_error = api_get("/analytics/sessions")
    game_payload, game_error = api_get("/analytics/games")
    show_error(session_error, "el análisis de sesiones")
    show_error(game_error, "el análisis por juegos")
    sessions = with_dates(to_df(session_payload))
    games = to_df(game_payload)

    if not sessions.empty:
        metric_row([
            ("Directos monitorizados", fmt(len(sessions))),
            ("Pico observado", fmt(sessions["peak_viewers"].max()) if "peak_viewers" in sessions else "—"),
            ("Muestras registradas", fmt(sessions["measurements"].sum()) if "measurements" in sessions else "—"),
        ])
        st.subheader("Comparativa de sesiones")
        metric = st.radio("Métrica", ["peak_viewers", "average_viewers"],
                          format_func=lambda x: "Pico" if x == "peak_viewers" else "Media", horizontal=True)
        if {"stream_id", metric}.issubset(sessions.columns):
            sessions["label"] = sessions["started_at"].dt.strftime("%d/%m %H:%M").fillna("Sin fecha") + " · " + sessions["stream_id"].astype(str).str[-5:]
            st.bar_chart(sessions, x="label", y=metric)
        table(sessions, ["started_at", "games_label", "average_viewers", "peak_viewers", "measurements", "observed_minutes"])
    else:
        st.info("Aún no tenemos sesiones monitorizadas. El monitor tomará muestras durante el próximo directo.")

    st.subheader("🎮 Comparativa de categorías")
    if not games.empty and {"game_name", "average_viewers"}.issubset(games.columns):
        st.bar_chart(games, x="game_name", y="average_viewers", horizontal=True)
        table(games, ["game_name", "sessions", "measurements", "average_viewers", "peak_viewers"])
    else:
        st.info("No hay datos suficientes para comparar Rocket League y Fortnite.")
    st.caption("Las medias y picos son observados por nuestro monitor, no los informes oficiales agregados de Twitch.")


elif page == "👥 Comunidad":
    st.title("👥 Seguidores y suscriptores")
    history, error = api_get("/channel/history")
    show_error(error, "el historial de comunidad")
    df = with_dates(to_df(history))

    if st.button("📥 Registrar medición ahora"):
        with st.spinner("Consultando Twitch..."):
            _, sync_error = api_post("/channel/sync", timeout=45)
        if sync_error:
            st.error(f"No se pudo sincronizar: {sync_error}")
            st.caption("Comprueba /auth/twitch/status y los permisos OAuth.")
        else:
            st.success("Nueva medición de comunidad registrada.")
            st.rerun()

    if df.empty:
        st.info("No hay mediciones todavía. Autoriza Twitch y registra la primera.")
        st.code("http://localhost:8000/auth/twitch/start")
    else:
        df = df.sort_values("captured_at")
        first, latest = df.iloc[0], df.iloc[-1]
        subs = latest.get("subscribers")
        metric_row([
            ("Seguidores (última muestra)", fmt(latest.get("followers"))),
            ("Variación neta registrada", fmt(number(latest.get("followers")) - number(first.get("followers")))),
            ("Suscriptores", "No disponible" if pd.isna(subs) else fmt(subs)),
        ])
        if {"captured_at", "followers"}.issubset(df.columns):
            st.subheader("Historial de seguidores")
            st.line_chart(df, x="captured_at", y="followers")
        if "subscribers" in df.columns and df["subscribers"].notna().any():
            st.subheader("Historial de suscriptores")
            st.line_chart(df.dropna(subset=["subscribers"]), x="captured_at", y="subscribers")
        table(df, ["captured_at", "followers", "subscribers", "subscription_points"])
        st.caption("El crecimiento es neto desde la primera medición; no equivale a altas brutas ni necesariamente a una semana.")


elif page == "🤖 Asistente IA":
    st.title("🤖 Asistente de IA local")
    st.caption("Ollama + Qwen · Sin API de pago · Las respuestas deben contrastarse con el dashboard.")
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []
    if st.button("🧹 Limpiar conversación"):
        st.session_state.ai_messages = []
        st.rerun()

    for message in st.session_state.ai_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Por ejemplo: ¿Cuál es mi clip más visto?")
    if question:
        st.session_state.ai_messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Consultando el modelo local..."):
                result, error = api_post("/ai/analyze", {"question": question}, timeout=240)
            if error:
                st.error(f"No se pudo completar el análisis: {error}")
            else:
                answer = result.get("answer", "No se recibió una respuesta.")
                st.markdown(answer)
                if result.get("model"):
                    st.caption(
                        f"Modelo: {result['model']} · "
                        f"Clips: {result.get('clips_analyzed', '—')} · "
                        f"VOD: {result.get('videos_analyzed', '—')} · "
                        f"Directos: {result.get('sessions_analyzed', '—')}"
                    )
                st.session_state.ai_messages.append({"role": "assistant", "content": answer})
    st.info("La IA recibe estadísticas resumidas. No visualiza el contenido de los clips ni puede deducir seguidores nuevos sin mediciones.")


else:  # Estado del sistema
    st.title("🛠️ Estado de JoyStream AI")
    health, health_error = api_get("/health", timeout=5)
    if health_error:
        st.error(f"Backend inaccesible: {health_error}")
    else:
        st.success(f"Backend accesible: {health}")

    oauth, oauth_error = api_get("/auth/twitch/status", timeout=10)
    if oauth_error:
        st.warning(f"No se pudo verificar OAuth: {oauth_error}")
    else:
        st.write("**OAuth Twitch autorizado:**", "Sí" if oauth.get("authorized") else "No")
    st.markdown("**Servicios Docker esperados:** `backend`, `db`, `dashboard`, `scheduler`, `monitor`, `ollama`.")
    st.code("docker compose ps\ndocker compose logs --tail=50 backend\ndocker compose logs --tail=50 dashboard", language="bash")
    st.caption("Esta página verifica la API, pero no demuestra que el Scheduler, el monitor y Ollama estén sanos.")

st.divider()
st.caption("JoyStream AI · Proyecto personal de AI Engineering · Datos recogidos desde Twitch")
