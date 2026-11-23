
import os
import signal
import threading
from datetime import datetime, timezone

import requests


# CONFIGURACIÓN
API_URL = os.getenv(
    "API_URL",
    "http://backend:8000"
)

INTERVAL = int(
    os.getenv("SYNC_INTERVAL_SECONDS", "21600")
)

# Permite detener el programa correctamente
stop_event = threading.Event()


def stop_scheduler(signum, frame):
    print("Deteniendo scheduler...", flush=True)
    stop_event.set()


signal.signal(signal.SIGTERM, stop_scheduler)
signal.signal(signal.SIGINT, stop_scheduler)


# JOYSTREAM_26D_SCHEDULER_TOKEN
# No registrar ni imprimir este token en los logs.
def _internal_headers():
    token = os.getenv("JOY_INTERNAL_SYNC_TOKEN", "")
    if len(token) < 64:
        raise RuntimeError("Falta JOY_INTERNAL_SYNC_TOKEN; sincronización automática desactivada")
    return {"X-JoyStream-Internal-Token": token}


def sync_twitch():
    """Solicita una sincronización al backend."""

    now = datetime.now(timezone.utc)

    print(
        f"[{now.isoformat()}] Iniciando sincronización",
        flush=True
    )

    try:
        response = requests.post(
            f"{API_URL}/sync",
            headers=_internal_headers(),
            timeout=90
        )

        response.raise_for_status()

        data = response.json()

        print(
            "Sincronización completada: "
            f"{data['videos_processed']} vídeos, "
            f"{data['clips_processed']} clips",
            flush=True
        )


        # Sincronización de seguidores y suscriptores
        channel_response = requests.post(
            f"{API_URL}/channel/sync",
            headers=_internal_headers(),
            timeout=40
        )

        if channel_response.status_code == 409:
            print(
                "Twitch OAuth todavía no autorizado",
                flush=True
            )

        else:
            channel_response.raise_for_status()

            metrics = channel_response.json()

            print(
                "Comunidad actualizada: "
                f"{metrics['followers']} seguidores, "
                f"{metrics['subscribers']} suscriptores",
                flush=True
            )


    except requests.RequestException as error:
        print(
            f"Error en la sincronización: {error}",
            flush=True
        )


def main():
    if INTERVAL < 30:
        raise ValueError(
            "El intervalo debe ser de al menos 30 segundos"
        )

    print("JoyStream AI Scheduler iniciado")
    print(f"Intervalo configurado: {INTERVAL} segundos")

    # Primera ejecución inmediatamente
    # Reintenta si FastAPI todavía no está disponible
    while not stop_event.is_set():
        try:
            response = requests.get(
                f"{API_URL}/health",
                timeout=5
            )
            response.raise_for_status()
            break
        except requests.RequestException:
            print(
                "Esperando a que FastAPI esté disponible..."
            )
            stop_event.wait(10)

    # Bucle principal
    while not stop_event.is_set():

        sync_twitch()

        print(
            f"Próxima ejecución tras {INTERVAL} segundos",
            flush=True
        )

        stop_event.wait(INTERVAL)

    print("Scheduler detenido correctamente")


if __name__ == "__main__":
    main()
