# Registro de cambios

## v1.0.0 — Candidato, sin publicar

### Funcionalidad

- Panel de clips, VOD, directos, comunidad y analítica de audiencia.
- Análisis con Ollama y métricas determinadas desde Python/PostgreSQL.
- Comparaciones entre emisiones, categorías, fechas y días de la semana, con medios simples y ponderados.
- Seguimiento de referencias para recomendaciones en nuevos directos.

### Infraestructura

- Healthcheck PostgreSQL y dependencias de arranque en Compose.
- Reintentos de inicialización para servicios dependientes de PostgreSQL.
- Proxy Nginx con resolución dinámica y comprobaciones de origen.
- Inicio de sesión local para tres endpoints sensibles.

### Pendiente antes de declarar estable

- Verificar que `scheduler` conserva la sincronización programada con la nueva autenticación.
- Prueba real de recreación de backend sin `502` persistente en frontend.
- Comprobar expiración y cierre de sesión, rutas protegidas y permisos locales.
- Ejecutar todas las pruebas Python y revisar exclusiones de Git.
- Añadir o confirmar una licencia si procede.
