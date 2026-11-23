#!/usr/bin/env python3
"""Auditoría conservadora SOLO LECTURA. No imprime variables de entorno."""
from pathlib import Path
import subprocess
import json
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
checks = []

def result(kind, label, detail=""):
    checks.append((kind, label))
    print(f"{kind:7} {label}" + (f" — {detail}" if detail else ""))

def run(*args, timeout=15):
    try:
        return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

def http(method, route):
    try:
        req = urllib.request.Request('http://127.0.0.1:8080' + route, method=method)
        with urllib.request.urlopen(req, timeout=7) as res:
            return res.status
    except urllib.error.HTTPError as ex:
        return ex.code
    except (urllib.error.URLError, TimeoutError):
        return None

print('=== JoyStream AI v1.0 · Auditoría de lanzamiento (SOLO LECTURA) ===')
c = run('docker', 'compose', 'config', '--quiet')
result('OK' if c and c.returncode == 0 else 'REVISAR', 'Docker Compose válido')

c = run('docker', 'compose', 'ps', '--format', 'json')
if c and c.returncode == 0:
    raw = c.stdout.strip()
    try:
        items = json.loads(raw) if raw.startswith('[') else [json.loads(line) for line in raw.splitlines() if line.strip()]
        statuses = {x.get('Service'): str(x.get('State', '')).lower() for x in items}
        required = {'backend','frontend','db','monitor','scheduler','dashboard','ollama'}
        failed = sorted(s for s in required if statuses.get(s) != 'running')
        result('OK' if not failed else 'REVISAR', 'Siete servicios en ejecución', 'servicios sin estado running: ' + ', '.join(failed) if failed else '')
    except (ValueError, TypeError, AttributeError):
        result('REVISAR', 'No se pudo interpretar docker compose ps')
else:
    result('REVISAR', 'No se pudo consultar Docker Compose')

result('OK' if http('GET', '/api/health') == 200 else 'REVISAR', 'API health por frontend HTTP 200')
for path in ('/api/sync', '/api/channel/sync', '/api/ai/analyze'):
    code = http('POST', path)
    result('OK' if code == 401 else 'REVISAR', f'POST {path} sin sesión devuelve 401', f'HTTP {code}')

for name in ('.env', '.joystream-auth.env'):
    p = ROOT / name
    result('OK' if p.is_file() else 'REVISAR', f'{name} existe (contenido no mostrado)')
    check = run('git', 'ls-files', '--error-unmatch', name)
    result('REVISAR' if check and check.returncode == 0 else 'OK', f'{name} no está rastreado por Git')

p = ROOT / 'scheduler' / 'scheduler.py'
if p.is_file():
    code = p.read_text(encoding='utf-8', errors='replace')
    sensitive = any(x in code for x in ('/sync', '/channel/sync'))
    result('REVISAR' if sensitive else 'AVISO', 'Integración scheduler y autenticación',
           'se observan llamadas potencialmente protegidas; comprobar 401 en logs y adaptar' if sensitive else 'revisar manualmente mecanismo de sincronización')
else:
    result('REVISAR', 'No se encontró scheduler/scheduler.py')

c = run('docker', 'compose', 'logs', '--tail=100', 'scheduler')
if c and c.returncode == 0:
    logs = (c.stdout + c.stderr).lower()
    result('REVISAR' if any(t in logs for t in ('401 unauthorized', '401 client error', 'status code: 401')) else 'AVISO',
           'Logs de scheduler', 'no se detectó 401 explícito; confirmar una ejecución programada' if '401' not in logs else 'posibles rechazos de autenticación; revisar manualmente')

c = run('git', 'status', '--porcelain')
if c and c.returncode == 0:
    result('AVISO' if c.stdout.strip() else 'OK', 'Estado de Git',
           'hay cambios; revisar antes del commit' if c.stdout.strip() else 'sin cambios locales')

print('\nNO se han alterado los archivos ni los contenedores.')
print('Comprobaciones OK:', sum(k == 'OK' for k,_ in checks), '· Revisar:', sum(k == 'REVISAR' for k,_ in checks), '· Avisos:', sum(k == 'AVISO' for k,_ in checks))
print('La auditoría no certifica seguridad ni garantiza sincronización programada.')
