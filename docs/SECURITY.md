# Seguridad — JoyStream AI (candidato v1.0)

**Uso previsto:** una sola máquina, interfaz web en `127.0.0.1:8080` y backend en `127.0.0.1:8000`. No exponer estos puertos públicamente ni añadir un túnel público sin rediseñar la autenticación.

## Protección implementada y límites

- FastAPI exige sesión local para `POST /sync`, `POST /channel/sync` y `POST /ai/analyze`.
- Inicio de sesión mediante contraseña, derivación PBKDF2, cookie firmada `HttpOnly` y `SameSite=Strict`, validez máxima de 12 h.
- Las restricciones de origen en Nginx y FastAPI son defensa adicional; cabeceras pueden ser manipuladas fuera del navegador.
- HTTP local no aporta cifrado en tránsito. No asumir protección de HTTPS.
- El endpoint `/auth/logout` borra la cookie del navegador, pero el token firmado no dispone de lista de revocación del servidor. Si se copia, podría seguir vigente hasta expirar o cambiar el secreto de firma.
- Según el código conocido, las rutas GET de datos no tienen un control de acceso integral y FastAPI también es accesible directamente en el puerto local 8000.
- **Riesgo de integración**: el servicio `scheduler` podría invocar `/sync` sin sesión y dejar de sincronizar automáticamente desde que se añadió la protección; revisar antes de etiquetar v1.0.

## Secretos y repositorio

Excluir de Git `.env`, `.joystream-auth.env`, tokens, copias de seguridad y bases de datos exportadas. Verificar con `git ls-files`, sin imprimir el contenido de las credenciales. Si se publicó una credencial accidentalmente, revocarla o rotarla en el proveedor, además de limpiar el historial Git si es necesario.

## Recomendaciones para un despliegue futuro

Usar HTTPS, control de acceso para todas las rutas apropiadas, autenticación entre servicios para tareas automáticas, límites de tasa persistentes, protección CSRF explícita para acciones con cookies, usuarios/roles, registros y gestión de sesiones revocables. No confundir la etiqueta v1.0 de un proyecto local con una auditoría de seguridad.
