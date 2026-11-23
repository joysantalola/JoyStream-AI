#!/usr/bin/env python3
"""Genera credenciales locales para JoyStream AI.

No reemplaza credenciales existentes ni imprime secretos.
Compatible con backend/app/auth_local.py y Paso 26D.
"""

import getpass
import hashlib
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def write_private(filename, content):
    path = ROOT / filename

    if path.exists() or path.is_symlink():
        print(f"CONSERVADO: {filename} ya existe")
        return False

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        path.unlink(missing_ok=True)
        raise

    print(f"CREADO: {filename} (permisos 600)")
    return True


def setup_admin():
    path = ROOT / ".joystream-auth.env"

    if path.exists() or path.is_symlink():
        print("CONSERVADO: autenticación del administrador")
        return

    print("\nConfigura una contraseña local de 12 a 256 caracteres.")

    password = getpass.getpass("Contraseña: ")
    repeat = getpass.getpass("Repetir contraseña: ")

    if password != repeat:
        raise ValueError("Las contraseñas no coinciden")

    if not 12 <= len(password) <= 256:
        raise ValueError("La contraseña debe tener entre 12 y 256 caracteres")

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        390000
    ).hex()

    session_secret = secrets.token_urlsafe(48)

    content = (
        f"JOY_AUTH_SALT={salt.hex()}\n"
        f"JOY_AUTH_HASH={password_hash}\n"
        f"JOY_AUTH_SESSION_SECRET={session_secret}\n"
    )

    write_private(".joystream-auth.env", content)


def setup_scheduler():
    token = secrets.token_hex(48)

    write_private(
        ".joystream-internal.env",
        f"JOY_INTERNAL_SYNC_TOKEN={token}\n"
    )


def main():
    os.umask(0o077)

    print("=== JoyStream AI v1.0 · Configuración local ===")

    setup_admin()
    setup_scheduler()

    if not (ROOT / ".env").is_file():
        print("\nPENDIENTE: crear .env con la configuración de Twitch")
        print("y POSTGRES_PASSWORD antes de ejecutar Docker Compose.")
    else:
        print("\nOK: .env existe")

    print("\nConfiguración de credenciales terminada.")
    print("No compartas los archivos .env ni los subas a Git.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyboardInterrupt) as error:
        print(f"\nERROR: {error}")
        raise SystemExit(1)
