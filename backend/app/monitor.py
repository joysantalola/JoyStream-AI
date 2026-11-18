
import asyncio
import os
import time

from fastapi import HTTPException

from app.database import create_tables
from app.storage import save_stream_sample
from app.twitch import (
    get_access_token,
    get_live_stream
)


INTERVAL = int(
    os.getenv("MONITOR_INTERVAL_SECONDS", "60")
)


async def main():

    if INTERVAL < 30:
        raise ValueError(
            "El intervalo debe ser de al menos 30 segundos"
        )

    create_tables()

    print("JoyStream AI Monitor iniciado", flush=True)
    print(
        f"Intervalo: {INTERVAL} segundos",
        flush=True
    )

    token = None
    token_created_at = 0

    while True:

        try:
            # Reutilizamos el token durante un máximo
            # de 45 minutos en este monitor.
            if (
                token is None
                or time.monotonic() - token_created_at > 2700
            ):
                token = await get_access_token()
                token_created_at = time.monotonic()

            result = await get_live_stream(
                access_token=token
            )

            if result["is_live"]:

                stream = result["stream"]

                # Guardar una nueva medición
                save_stream_sample(stream)

                print(
                    f"🔴 EN DIRECTO | "
                    f"{stream['game_name']} | "
                    f"{stream['viewer_count']} espectadores",
                    flush=True
                )

            else:
                print(
                    "⚫ Canal offline. Sin medición.",
                    flush=True
                )

        except HTTPException as error:
            token = None
            print(
                f"Error de Twitch: {error.detail}",
                flush=True
            )

        except Exception as error:
            print(
                f"Error del monitor: {error}",
                flush=True
            )

        await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
