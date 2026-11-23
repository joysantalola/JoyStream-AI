# Checklist de publicación — JoyStream AI v1.0

No publicar etiqueta ni hacer push hasta completar lo esencial.

- [ ] `docker compose config --quiet` pasa.
- [ ] `docker compose ps` muestra los 7 servicios sin fallos/reinicios continuos.
- [ ] `GET http://127.0.0.1:8080/api/health` devuelve HTTP 200 JSON.
- [ ] `POST http://127.0.0.1:8080/api/sync` sin sesión devuelve 401 y NO sincroniza.
- [ ] `POST /api/channel/sync` sin sesión devuelve 401.
- [ ] `POST /api/ai/analyze` sin sesión devuelve 401.
- [ ] Sincronizar Twitch desde el dashboard con login funciona.
- [ ] Joy AI con login funciona y las estadísticas siguen visibles.
- [ ] Cerrar sesión y comprobar que se exige autenticación; revisar el límite de revocación descrito en SECURITY.md.
- [ ] **Bloqueante:** `scheduler` sigue sincronizando después del Paso 26C, o queda adaptado con credencial interna apropiada. Revisar `scheduler/scheduler.py` y sus logs.
- [ ] **Bloqueante:** reconstruir backend y comprobar que `/api/health` vuelve a 200 sin reiniciar Nginx manualmente.
- [ ] Ejecutar pruebas `unittest` sin regresiones graves.
- [ ] Verificar que `.env`, `.joystream-auth.env`, tokens, backups y exportaciones no están rastreados por Git.
- [ ] Revisar que todos los puertos publicados siguen ligados a `127.0.0.1`.
- [ ] Confirmar licencia (`LICENSE`) o indicar explícitamente que no hay licencia.
- [ ] Revisar README y capturas para que no contengan credenciales.
- [ ] Crear commit de release y etiqueta `v1.0.0` solo después de superar todo lo anterior.

### Comandos finales (manuales, no automáticos)

```bash
python3 VERIFICAR_RELEASE_V1.py
docker compose ps
docker compose logs --tail=50 scheduler
docker compose exec backend python -m unittest discover -s app -p 'test_*.py' -v
git status --short
git ls-files .env .joystream-auth.env
```

El último comando **no debe imprimir nombres de secretos**.
