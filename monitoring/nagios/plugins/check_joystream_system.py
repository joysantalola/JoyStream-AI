#!/usr/bin/env python3
import argparse
import re
import sys
import time
from urllib.request import urlopen

URL = "http://node-exporter:9100/metrics"


def get_metrics():
    with urlopen(URL, timeout=10) as response:
        text = response.read().decode()

    result = []

    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        raw = parts[0]
        name = raw.split("{", 1)[0]
        labels = {}

        if "{" in raw:
            content = raw[raw.find("{") + 1:raw.rfind("}")]
            labels = dict(
                re.findall(r'(\w+)="((?:\\.|[^"])*)"', content)
            )

        try:
            value = float(parts[1])
            result.append((name, labels, value))
        except ValueError:
            continue

    return result


def scalar(data, name):
    for metric, labels, value in data:
        if metric == name:
            return value
    raise ValueError(f"No se encuentra la métrica {name}")


def finish(code, message, perf):
    print(f"{message} | {perf}")
    sys.exit(code)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metric", choices=["cpu", "memory", "disk"], required=True
    )
    parser.add_argument("--warning", type=float, required=True)
    parser.add_argument("--critical", type=float, required=True)
    args = parser.parse_args()

    try:
        data = get_metrics()

        if args.metric == "cpu":
            idle1 = sum(
                value for name, labels, value in data
                if name == "node_cpu_seconds_total"
                and labels.get("mode") == "idle"
            )
            total1 = sum(
                value for name, labels, value in data
                if name == "node_cpu_seconds_total"
            )

            time.sleep(1)
            data = get_metrics()

            idle2 = sum(
                value for name, labels, value in data
                if name == "node_cpu_seconds_total"
                and labels.get("mode") == "idle"
            )
            total2 = sum(
                value for name, labels, value in data
                if name == "node_cpu_seconds_total"
            )

            delta = total2 - total1
            if delta <= 0:
                raise ValueError("No hay datos suficientes de CPU")

            usage = max(0, min(100, (1 - (idle2-idle1)/delta)*100))
            label = "CPU"

        elif args.metric == "memory":
            total = scalar(data, "node_memory_MemTotal_bytes")
            available = scalar(data, "node_memory_MemAvailable_bytes")
            usage = (total - available) / total * 100
            label = "RAM"

        else:
            sizes = {}
            available = {}

            excluded = {
                "tmpfs", "devtmpfs", "overlay", "squashfs",
                "proc", "sysfs", "cgroup2", "ramfs"
            }

            for name, labels, value in data:
                key = tuple(sorted(labels.items()))

                if name == "node_filesystem_size_bytes":
                    sizes[key] = (labels, value)

                elif name == "node_filesystem_free_bytes":
                    available[key] = value

            candidates = []

            for key, (labels, size) in sizes.items():
                mount = labels.get("mountpoint", "")
                fstype = labels.get("fstype", "")

                if fstype in excluded:
                    continue

                if mount.startswith(
                    ("/proc", "/sys", "/dev", "/run",
                     "/var/lib/docker", "/host")
                ):
                    continue

                if size < 1024**3 or key not in available:
                    continue

                avail = available[key]
                percent = (size - avail) / size * 100
                candidates.append((percent, mount))

            if not candidates:
                raise ValueError("No se encuentran sistemas de archivos válidos")

            root = next(
                (item for item in candidates if item[1] == "/"),
                None
            )
            if root is None:
                raise ValueError(
                    "No se encuentra el filesystem raiz /"
                )
            usage, mount = root
            label = f"Disco WSL {mount}"

        if usage >= args.critical:
            code = 2
            status = "CRITICAL"
        elif usage >= args.warning:
            code = 1
            status = "WARNING"
        else:
            code = 0
            status = "OK"

        finish(
            code,
            f"{status} - {label}: {usage:.2f}% utilizado",
            f"usage={usage:.2f}%;{args.warning};{args.critical};0;100"
        )

    except Exception as error:
        finish(3, f"UNKNOWN - {error}", "")


if __name__ == "__main__":
    main()
