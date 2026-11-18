
import os

import pandas as pd
import requests
import streamlit as st


# CONFIGURACIÓN
API_URL = os.getenv("API_URL", "http://backend:8000")

st.set_page_config(
    page_title="JoyStream AI",
    page_icon="🎮",
    layout="wide"
)


# FUNCIONES

def get_data(endpoint):
    """Consulta un endpoint de nuestro backend."""
    response = requests.get(
        f"{API_URL}{endpoint}",
        timeout=15
    )
    response.raise_for_status()
    return response.json()


def sync_data():
    """Solicita actualizar vídeos y clips."""
    response = requests.post(
        f"{API_URL}/sync",
        timeout=60
    )
    response.raise_for_status()
    return response.json()


# CABECERA
st.title("🎮 JoyStream AI")
st.caption("Dashboard de analítica de Twitch")

st.sidebar.header("Joysantalola")
st.sidebar.write("Canal: joysantalola67")

if st.sidebar.button("🔄 Sincronizar Twitch"):
    try:
        with st.spinner("Consultando Twitch..."):
            result = sync_data()

        st.sidebar.success(
            f"Sincronizados: "
            f"{result['videos_processed']} vídeos y "
            f"{result['clips_processed']} clips"
        )
    except requests.RequestException as error:
        st.sidebar.error(
            f"Error de sincronización: {error}"
        )


# CARGAR DATOS
try:
    videos = get_data("/db/videos")
    clips = get_data("/db/clips")
except requests.RequestException as error:
    st.error(f"No se pudo conectar con FastAPI: {error}")
    st.stop()


# CONVERTIR JSON EN DATAFRAMES
df_videos = pd.DataFrame(videos)
df_clips = pd.DataFrame(clips)


# ESTADÍSTICAS
total_videos = len(df_videos)
total_clips = len(df_clips)

views_videos = (
    int(df_videos["view_count"].fillna(0).sum())
    if "view_count" in df_videos.columns else 0
)

views_clips = (
    int(df_clips["view_count"].fillna(0).sum())
    if "view_count" in df_clips.columns else 0
)


# TARJETAS DE MÉTRICAS
col1, col2, col3, col4 = st.columns(4)

col1.metric("📹 VOD guardados", total_videos)
col2.metric("🎬 Clips guardados", total_clips)
col3.metric("👀 Vistas VOD", f"{views_videos:,}")
col4.metric("🔥 Vistas clips", f"{views_clips:,}")


st.divider()


# ANÁLISIS ADICIONAL DE CLIPS

st.divider()
st.header("🎯 Rendimiento del contenido")

if not df_clips.empty:

    clips_100 = len(
        df_clips[df_clips["view_count"] >= 100]
    )

    average_views = df_clips["view_count"].mean()

    best_clip = df_clips.loc[
        df_clips["view_count"].idxmax()
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Clips con 100+ vistas",
        clips_100
    )

    col2.metric(
        "Media de vistas por clip",
        f"{average_views:.1f}"
    )

    col3.metric(
        "Máximo de vistas",
        int(best_clip["view_count"])
    )

    st.info(
        f"🏆 Tu clip más visto: {best_clip['title']}"
    )

else:
    st.info("No hay clips para analizar.")


# GRÁFICOS
st.header("📊 Análisis de clips")

if not df_clips.empty:

    # Mostramos los diez clips más vistos
    top_clips = (
        df_clips.sort_values(
            "view_count",
            ascending=False
        )
        .head(10)
        .copy()
    )

    # Etiquetas únicas para evitar títulos repetidos
    top_clips["label"] = (
        top_clips["title"].str.slice(0, 35)
        + " · "
        + top_clips["id"].str.slice(0, 6)
    )

    st.subheader("Top 10 clips más vistos")

    st.bar_chart(
        top_clips,
        x="label",
        y="view_count"
    )

    st.subheader("Filtrar por juego")

    games = sorted(
        df_clips["game_id"].dropna().unique().tolist()
    )

    selected_game = st.selectbox(
        "Selecciona un juego (Game ID)",
        ["Todos"] + games
    )

    if selected_game == "Todos":
        filtered_clips = df_clips
    else:
        filtered_clips = df_clips[
            df_clips["game_id"] == selected_game
        ]

    st.dataframe(
        filtered_clips[
            [
                "title",
                "created_at",
                "view_count",
                "duration",
                "game_id",
                "url"
            ]
        ],
        hide_index=True
    )

else:
    st.info("Todavía no hay clips guardados.")


st.divider()


# ANÁLISIS DE VÍDEOS
st.header("📹 Análisis de directos guardados")

if not df_videos.empty:

    st.subheader("Visualizaciones por VOD")

    st.bar_chart(
        df_videos.sort_values("created_at"),
        x="created_at",
        y="view_count"
    )

    st.subheader("Historial de VOD")

    st.dataframe(
        df_videos[
            [
                "title",
                "created_at",
                "duration",
                "view_count",
                "url"
            ]
        ],
        hide_index=True
    )

else:
    st.info("Todavía no hay VOD guardados.")


st.divider()

st.caption("JoyStream AI · Proyecto personal de AI Engineering")


# HISTORIAL DE CRECIMIENTO

st.divider()
st.header("📈 Evolución de visualizaciones")

try:
    history = get_data("/history/clips")
    growth = get_data("/growth/clips")

except requests.RequestException as error:
    st.error(f"Error al cargar historial: {error}")
    st.stop()


df_history = pd.DataFrame(history)
df_growth = pd.DataFrame(growth)


if not df_history.empty:

    # Convertimos la fecha a formato datetime
    df_history["captured_at"] = pd.to_datetime(
        df_history["captured_at"],
        utc=True
    )

    st.subheader("Crecimiento por clip")

    if not df_clips.empty:
        # Relacionamos los IDs con sus títulos
        clip_names = dict(
            zip(df_clips["id"], df_clips["title"])
        )
    else:
        clip_names = {}

    available_ids = (
        df_history["content_id"]
        .drop_duplicates()
        .tolist()
    )

    selected_id = st.selectbox(
        "Selecciona el clip",
        available_ids,
        format_func=lambda clip_id: (
            clip_names.get(clip_id, clip_id)
        )
    )

    selected_history = df_history[
        df_history["content_id"] == selected_id
    ].sort_values("captured_at")

    st.line_chart(
        selected_history,
        x="captured_at",
        y="view_count"
    )

    # Calculamos el crecimiento del clip
    first_views = int(
        selected_history.iloc[0]["view_count"]
    )

    last_views = int(
        selected_history.iloc[-1]["view_count"]
    )

    difference = last_views - first_views

    col1, col2, col3 = st.columns(3)

    col1.metric("Primera medición", first_views)
    col2.metric("Última medición", last_views)
    col3.metric(
        "Crecimiento",
        difference,
        delta=difference,
        delta_color="off"
    )

    st.caption(
        "Crecimiento desde la primera medición "
        "almacenada, no necesariamente desde "
        "la creación del clip."
    )

    st.subheader("Ranking de crecimiento")

    if not df_growth.empty:
        df_growth["clip"] = df_growth[
            "content_id"
        ].map(
            lambda clip_id: clip_names.get(
                clip_id, clip_id
            )
        )

        st.dataframe(
            df_growth[
                [
                    "clip",
                    "first_views",
                    "last_views",
                    "growth",
                    "growth_percent",
                    "measurements"
                ]
            ],
            hide_index=True
        )

else:
    st.info(
        "Todavía no hay historial. "
        "Pulsa Sincronizar Twitch para "
        "registrar la primera medición."
    )


# MONITORIZACIÓN DE DIRECTOS

st.divider()
st.header("🔴 Monitorización de directos")

try:
    live = get_data("/twitch/live")
    samples = get_data("/streams/history")

except requests.RequestException as error:
    st.error(
        f"No se pudieron cargar los directos: {error}"
    )
    st.stop()


# ESTADO ACTUAL
if live["is_live"]:

    current = live["stream"]

    st.success(
        f"🔴 EN DIRECTO | "
        f"{current['game_name']} | "
        f"{current['viewer_count']} espectadores"
    )

    st.write(f"**Título:** {current['title']}")

else:
    st.info("⚫ Joysantalola está offline.")


# HISTORIAL DE DIRECTOS
df_streams = pd.DataFrame(samples)

if not df_streams.empty:

    df_streams["captured_at"] = pd.to_datetime(
        df_streams["captured_at"],
        utc=True
    )

    df_streams["started_at"] = pd.to_datetime(
        df_streams["started_at"],
        utc=True
    )

    # Cada stream_id representa un directo distinto
    sessions = (
        df_streams.sort_values("started_at")
        .drop_duplicates("stream_id", keep="last")
        .sort_values("started_at", ascending=False)
    )

    session_ids = sessions["stream_id"].tolist()

    labels = {
        row["stream_id"]: (
            f"{row['started_at']:%d/%m/%Y %H:%M} UTC"
            f" · {row['game_name']}"
        )
        for _, row in sessions.iterrows()
    }

    selected_stream = st.selectbox(
        "Selecciona un directo",
        session_ids,
        format_func=lambda stream_id: labels[stream_id]
    )

    selected = (
        df_streams[
            df_streams["stream_id"] == selected_stream
        ]
        .sort_values("captured_at")
    )

    # Estadísticas de la sesión
    peak = int(selected["viewer_count"].max())
    average = selected["viewer_count"].mean()
    last = int(selected.iloc[-1]["viewer_count"])

    col1, col2, col3 = st.columns(3)

    col1.metric("Pico observado", peak)
    col2.metric("Media de muestras", f"{average:.1f}")
    col3.metric("Última muestra", last)

    st.subheader("📈 Evolución de espectadores")

    st.line_chart(
        selected,
        x="captured_at",
        y="viewer_count"
    )

    st.subheader("🎮 Categorías del directo")

    game_stats = (
        selected.groupby("game_name", dropna=False)
        .agg(
            viewers_mean=("viewer_count", "mean"),
            viewers_peak=("viewer_count", "max"),
            measurements=("viewer_count", "count")
        )
        .reset_index()
    )

    st.dataframe(
        game_stats,
        hide_index=True
    )

    st.caption(
        "Los resultados representan muestras "
        "recogidas por JoyStream AI, "
        "no métricas oficiales agregadas de Twitch."
    )

else:
    st.info(
        "Todavía no hay mediciones históricas. "
        "Se guardarán automáticamente cuando "
        "el canal esté en directo."
    )


# COMPARATIVA DE DIRECTOS Y VIDEOJUEGOS

st.divider()
st.header("🎮 Comparativa de directos")

try:
    sessions_data = get_data("/analytics/sessions")
    games_data = get_data("/analytics/games")

except requests.RequestException as error:
    st.error(f"Error cargando analítica: {error}")
    st.stop()


df_sessions = pd.DataFrame(sessions_data)
df_games = pd.DataFrame(games_data)


# RESUMEN GENERAL

if not df_sessions.empty:

    total_sessions = len(df_sessions)

    highest_peak = int(
        df_sessions["peak_viewers"].max()
    )

    total_samples = int(
        df_sessions["measurements"].sum()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Directos monitorizados",
        total_sessions
    )

    col2.metric(
        "Mayor pico observado",
        highest_peak
    )

    col3.metric(
        "Muestras recogidas",
        total_samples
    )

    st.subheader("📅 Rendimiento por directo")

    # Convertimos fechas al tipo datetime
    df_sessions["started_at"] = pd.to_datetime(
        df_sessions["started_at"],
        utc=True
    )

    df_sessions["session_label"] = (
        df_sessions["started_at"].dt.strftime(
            "%d/%m/%Y %H:%M UTC"
        )
        + " · "
        + df_sessions["stream_id"].str.slice(-6)
    )

    # Orden cronológico
    df_sessions = df_sessions.sort_values(
        "started_at"
    )

    metric = st.radio(
        "¿Qué quieres comparar?",
        [
            "Pico de espectadores",
            "Media de espectadores"
        ],
        horizontal=True
    )

    if metric == "Pico de espectadores":
        column = "peak_viewers"
    else:
        column = "average_viewers"

    st.bar_chart(
        df_sessions,
        x="session_label",
        y=column
    )

    st.subheader("📋 Tabla de directos")

    st.dataframe(
        df_sessions[
            [
                "session_label",
                "games_label",
                "average_viewers",
                "peak_viewers",
                "measurements",
                "observed_minutes"
            ]
        ],
        hide_index=True
    )

else:
    st.info(
        "Todavía no hay directos monitorizados."
    )


# COMPARATIVA DE JUEGOS

st.divider()
st.header("🏆 Comparativa por videojuego")

if not df_games.empty:

    st.subheader("Media observada por categoría")

    st.bar_chart(
        df_games,
        x="game_name",
        y="average_viewers"
    )

    st.subheader("Pico observado por categoría")

    st.bar_chart(
        df_games,
        x="game_name",
        y="peak_viewers"
    )

    st.subheader("Estadísticas completas")

    st.dataframe(
        df_games[
            [
                "game_name",
                "sessions",
                "measurements",
                "average_viewers",
                "peak_viewers",
                "min_viewers"
            ]
        ],
        hide_index=True
    )

    # Comparación concreta: Rocket League vs Fortnite
    rocket = df_games[
        df_games["game_name"] == "Rocket League"
    ]

    fortnite = df_games[
        df_games["game_name"] == "Fortnite"
    ]

    if not rocket.empty and not fortnite.empty:

        rocket_average = float(
            rocket.iloc[0]["average_viewers"]
        )

        fortnite_average = float(
            fortnite.iloc[0]["average_viewers"]
        )

        difference = (
            rocket_average - fortnite_average
        )

        st.subheader(
            "🚀 Rocket League vs Fortnite"
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Rocket League",
            f"{rocket_average:.1f}"
        )

        col2.metric(
            "Fortnite",
            f"{fortnite_average:.1f}"
        )

        col3.metric(
            "Diferencia de medias",
            f"{difference:+.1f}"
        )

        st.caption(
            "Diferencia entre medias de muestras. "
            "No implica causalidad ni garantiza "
            "que un juego atraiga más espectadores."
        )

else:
    st.info(
        "Todavía no hay datos para comparar juegos."
    )



# ==========================================
# ASISTENTE DE IA LOCAL - OLLAMA
# ==========================================

st.divider()
st.header("🤖 JoyStream AI — Asistente gratuito")

st.caption("Modelo local con Ollama · Sin API de pago")

# Guardar conversación en la sesión
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []


# Mostrar mensajes anteriores
for message in st.session_state.ai_messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Entrada del usuario
question = st.chat_input(
    "Pregunta sobre tus estadísticas..."
)


if question:

    # Mostrar pregunta
    st.session_state.ai_messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    # Generar respuesta
    with st.chat_message("assistant"):

        with st.spinner("Analizando datos con Ollama..."):

            try:
                response = requests.post(
                    f"{API_URL}/ai/analyze",
                    json={"question": question},
                    timeout=240
                )

                response.raise_for_status()

                result = response.json()
                answer = result["answer"]

                # Mostrar respuesta de Ollama
                st.markdown(answer)

                # Mostrar información del modelo
                if result["model"]:
                    st.caption(
                        f"🤖 Modelo: {result['model']} | "
                        f"🎬 Clips: {result['clips_analyzed']} | "
                        f"📹 VOD: {result['videos_analyzed']} | "
                        f"🔴 Directos: {result['sessions_analyzed']}"
                    )

                # Guardar respuesta
                st.session_state.ai_messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except requests.RequestException as error:
                st.error(
                    "No se pudo completar el análisis. "
                    "Comprueba FastAPI y Ollama."
                )
                st.caption(str(error))
