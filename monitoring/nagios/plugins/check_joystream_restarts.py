#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://docker-socket-proxy:2375"
STATE = Path("/opt/nagios/var/joystream_restarts.json")
WINDOW = 1800

def api(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.load(r)

try:
    now = time.time()
    version = api("/version")["ApiVersion"]
    containers = api(f"/v{version}/containers/json?all=1")

    if STATE.exists():
        previous = json.loads(STATE.read_text())
    else:
        previous = {}

    current = {}
    alerts = []
    monitored = 0

    for container in containers:
        labels = container.get("Labels") or {}
        if labels.get("com.docker.compose.project") != "joystream-ai":
            continue

        monitored += 1
        cid = container["Id"]
        name = container["Names"][0].lstrip("/")
        details = api(f"/v{version}/containers/{cid}/json")
        restarts = int(details.get("RestartCount", 0))

        old = previous.get(cid, {})
        old_count = int(old.get("count", restarts))
        events = [
            event for event in old.get("events", [])
            if now - event[0] < WINDOW
        ]

        if restarts > old_count:
            events.append([now, restarts - old_count])

        total = sum(event[1] for event in events)
        current[cid] = {"count": restarts, "events": events}

        if total:
            alerts.append((name, total))

    if monitored == 0:
        raise RuntimeError("No se encontraron contenedores JoyStream AI")

    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(current))
    os.replace(tmp, STATE)

    if any(count >= 3 for _, count in alerts):
        code, status = 2, "CRITICAL"
    elif alerts:
        code, status = 1, "WARNING"
    else:
        code, status = 0, "OK"

    details = ", ".join(
        f"{name}: {count}" for name, count in alerts
    ) or "sin reinicios nuevos"

    print(
        f"{status} - {monitored} contenedores, "
        f"{details} en los ultimos 30 minutos"
    )
    sys.exit(code)

except Exception as error:
    print(f"UNKNOWN - {error}")
    sys.exit(3)
