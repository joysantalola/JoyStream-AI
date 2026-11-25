#!/usr/bin/env python3
import argparse
import json
import sys
from urllib.request import urlopen

BASE = "http://docker-socket-proxy:2375"

OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3


def get_json(path):
    with urlopen(BASE + path, timeout=10) as response:
        return json.loads(response.read())


def finish(code, message, performance=""):
    suffix = f" | {performance}" if performance else ""
    print(message + suffix)
    sys.exit(code)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--warning-mb", type=float, required=True)
    parser.add_argument("--critical-mb", type=float, required=True)
    parser.add_argument("--warning-cpu", type=float, required=True)
    parser.add_argument("--critical-cpu", type=float, required=True)
    args = parser.parse_args()

    try:
        api = get_json("/version")["ApiVersion"]
        containers = get_json(
            f"/v{api}/containers/json?all=1"
        )

        target = None
        for container in containers:
            names = [
                name.lstrip("/")
                for name in container.get("Names", [])
            ]
            if args.container in names:
                target = container
                break

        if target is None:
            finish(CRITICAL, f"Contenedor no encontrado: {args.container}")

        if target.get("State") != "running":
            finish(
                CRITICAL,
                f"{args.container}: {target.get('State', 'desconocido')}"
            )

        stats = get_json(
            f"/v{api}/containers/{target['Id']}/stats?stream=false"
        )

        memory = stats.get("memory_stats", {})
        usage = memory.get("usage", 0)
        cache = memory.get("stats", {}).get("inactive_file")

        if cache is None:
            cache = memory.get("stats", {}).get(
                "total_inactive_file", 0
            )

        memory_mb = max(0, usage - cache) / 1024**2

        cpu = stats.get("cpu_stats", {})
        previous = stats.get("precpu_stats", {})

        current_cpu = cpu.get("cpu_usage", {}).get("total_usage", 0)
        previous_cpu = previous.get("cpu_usage", {}).get("total_usage", 0)

        current_system = cpu.get("system_cpu_usage", 0)
        previous_system = previous.get("system_cpu_usage", 0)

        cores = (
            cpu.get("online_cpus")
            or len(cpu.get("cpu_usage", {}).get("percpu_usage", []))
            or 1
        )

        cpu_pct = None

        if current_system > previous_system:
            cpu_pct = (
                (current_cpu - previous_cpu)
                / (current_system - previous_system)
                * cores * 100
            )
            cpu_pct = max(0, cpu_pct)

        code = OK
        reasons = []

        if memory_mb >= args.critical_mb:
            code = CRITICAL
            reasons.append("RAM crítica")
        elif memory_mb >= args.warning_mb:
            code = max(code, WARNING)
            reasons.append("RAM elevada")

        if cpu_pct is not None:
            if cpu_pct >= args.critical_cpu:
                code = CRITICAL
                reasons.append("CPU crítica")
            elif cpu_pct >= args.warning_cpu:
                code = max(code, WARNING)
                reasons.append("CPU elevada")

        labels = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]
        status = labels[code]

        if not reasons:
            reasons.append("recursos normales")

        cpu_text = (
            f"{cpu_pct:.2f}%"
            if cpu_pct is not None else "N/D"
        )

        performance = (
            f"memory_mb={memory_mb:.1f}MB;"
            f"{args.warning_mb};{args.critical_mb};0; "
        )

        if cpu_pct is not None:
            performance += (
                f"cpu_pct={cpu_pct:.2f}%;"
                f"{args.warning_cpu};{args.critical_cpu};0;"
            )

        finish(
            code,
            f"{status} - {args.container}: "
            f"RAM {memory_mb:.1f} MB, CPU {cpu_text} "
            f"({', '.join(reasons)})",
            performance
        )

    except Exception as error:
        finish(UNKNOWN, f"Error consultando Docker: {error}")


if __name__ == "__main__":
    main()
