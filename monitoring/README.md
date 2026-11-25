# JoyStream AI - Monitorizacion

Monitorizacion mediante Nagios Core, Node Exporter y Docker Socket Proxy.

## Acceso

- Nagios: http://127.0.0.1:8090
- Nagstamon: conectar al Nagios local con el usuario configurado.
- No se utiliza correo electronico.

## Comprobaciones

- Estado de FastAPI, Nginx, PostgreSQL y Ollama.
- CPU y RAM del sistema.
- Espacio utilizado en la raiz de WSL2.
- CPU, RAM y estado de los contenedores.
- Reinicios de contenedores.
- Tamano del volumen PostgreSQL.

## Configuracion

Docker Compose utiliza compose.yaml y compose.override.yaml.

Los archivos locales de credenciales, resource.cfg,
el estado de Nagios y sus logs no se publican en Git.

Antes de desplegar en otro equipo, provisionar las credenciales
de acceso de Nagios y los archivos locales excluidos del repositorio.

El proxy Docker permite consultas de lectura. No debe
publicarse su puerto en redes externas.

## Validacion

docker compose config -q

docker compose exec -T nagios \
  /opt/nagios/bin/nagios -v /opt/nagios/etc/nagios.cfg

docker compose ps

## Alertas

Nagstamon muestra WARNING, CRITICAL y UNKNOWN desde Windows.

Las pruebas deben realizarse sin detener PostgreSQL ni
modificar los datos de produccion.
