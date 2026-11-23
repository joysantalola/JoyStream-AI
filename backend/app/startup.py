"""JoyStream AI 26A: espera limitada para operaciones iniciales de PostgreSQL."""
from __future__ import annotations

import os
import time
from sqlalchemy.exc import OperationalError, InterfaceError


def wait_for_database(operation, *, attempts=None, delay_seconds=None, sleep=time.sleep):
    """Ejecuta operation una vez por intento, reintentando solo fallos de conexión SQL.

    No crea, elimina ni migra datos por sí misma: reutiliza la operación existente.
    """
    attempts = int(os.getenv("DB_STARTUP_ATTEMPTS", "15")) if attempts is None else attempts
    delay_seconds = float(os.getenv("DB_STARTUP_DELAY_SECONDS", "3")) if delay_seconds is None else delay_seconds
    if not isinstance(attempts, int) or not 1 <= attempts <= 120:
        raise ValueError("DB_STARTUP_ATTEMPTS debe estar entre 1 y 120")
    if not 0 <= delay_seconds <= 60:
        raise ValueError("DB_STARTUP_DELAY_SECONDS debe estar entre 0 y 60")

    for index in range(1, attempts + 1):
        try:
            return operation()
        except (OperationalError, InterfaceError) as exc:
            if index == attempts:
                print(f"PostgreSQL no disponible tras {attempts} intentos; se aborta el arranque.", flush=True)
                raise
            # No imprimir exc, que puede contener URLs/credenciales de conexión.
            print(f"PostgreSQL aún no disponible ({index}/{attempts}); nuevo intento en {delay_seconds:g} s.", flush=True)
            sleep(delay_seconds)
