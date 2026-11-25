#!/usr/bin/env python3

import argparse
import json
import sys
import urllib.request

URL = "http://docker-socket-proxy:2375/system/df"

OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

parser = argparse.ArgumentParser()
parser.add_argument("--volume", required=True)
parser.add_argument("--warning", type=float, default=1024)
parser.add_argument("--critical", type=float, default=2048)
args = parser.parse_args()

try:
    request = urllib.request.Request(URL)

    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)

    volumes = data.get("Volumes") or []

    volume = next(
        (v for v in volumes if v.get("Name") == args.volume),
        None
    )

    if volume is None:
        print(f"UNKNOWN - Volumen no encontrado: {args.volume}")
        sys.exit(UNKNOWN)

    usage = volume.get("UsageData") or {}
    size = usage.get("Size")

    if size is None or size < 0:
        print("UNKNOWN - Docker no proporciona el tamaño")
        sys.exit(UNKNOWN)

    size_mb = size / (1024 * 1024)

    if size_mb >= args.critical:
        status = CRITICAL
        label = "CRITICAL"
    elif size_mb >= args.warning:
        status = WARNING
        label = "WARNING"
    else:
        status = OK
        label = "OK"

    print(
        f"{label} - {args.volume}: "
        f"{size_mb:.2f} MB | "
        f"used_mb={size_mb:.2f}MB;"
        f"{args.warning:.0f};{args.critical:.0f};0;"
    )

    sys.exit(status)

except Exception as error:
    print(f"UNKNOWN - Error consultando Docker: {error}")
    sys.exit(UNKNOWN)
