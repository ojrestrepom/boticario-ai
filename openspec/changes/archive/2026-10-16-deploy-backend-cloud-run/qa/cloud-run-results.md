# Resultados de QA: deploy-backend-cloud-run

Fecha: 2026-10-16 (UTC 2026-10-17). Entorno: servicio `boticario-api` en Cloud Run, revisión `boticario-api-00003-w5w`, imagen del commit `fd94e8f6c88d61faa80de39c128a93ce9f584548` (ejecución `38992727457`). Plan: [`test-plan-cloud-run.md`](test-plan-cloud-run.md). Todas las rutas de evidencia son relativas a esta carpeta.

## Resumen

- 83 casos: 70 PASS, 1 FAIL, 8 OBS y 4 NO EJECUTADO.
- Defecto: D-01 (severidad media), el build `release` no impone HTTPS aunque README y spec lo afirman.
- Arranque en frío medido: 2,58 s y 2,52 s la primera petición (frente a 0,29 a 0,44 s en caliente); latencia de arranque de la instancia 2,02 s en las 7 instancias iniciadas; memoria máxima observada 11 % de 256 MiB (unos 28 MiB).
- Consumo del día de QA: 448 peticiones, 120,8 vCPU-s y 12,7 GiB-s, es decir 0,02 %, 0,07 % y 0,004 % de la capa gratuita mensual.
- No se ejecutó ningún comando de escritura en GCP ni en GitHub. Único cambio en el emulador: ninguno persistente (el ajuste `stylus_handwriting_enabled` se desactivó un rato y se restauró a 1).

## Defectos

### D-01 (media): el build `release` admite HTTP en claro, contra lo que dicen README y la spec

- Requerimiento afectado: `flutter-app-bootstrap`, escenario «Release contra el backend desplegado» («el build `release` exige HTTPS»), y `README.md` secciones 2 («el HTTP en claro solo está habilitado en builds `debug` y `profile`, no en `release`, que exige HTTPS») y «Despliegue en Cloud Run».
- Reproducción: (1) `cd app && flutter build apk --release --dart-define=API_BASE_URL=http://10.0.2.2:8089`; (2) en el Mac, `python3 -I scripts/cleartext_probe_server.py 8089` (servidor HTTP mínimo, no es el backend); (3) `adb -s emulator-5554 install -r build/app/outputs/flutter-apk/app-release.apk`, abrir la app y entrar en Explorar.
- Esperado: el release no puede usar HTTP en claro; la app muestra el error de conexión con Reintentar.
- Obtenido: el servidor recibe `GET /v1/plants?limit=50&offset=0` con `User-Agent: Dart/3.13 (dart:io)` y la app muestra «No se encontraron plantas» (carga correcta). Con `API_BASE_URL=http://boticario-api-d3xv5q3iaa-pv.a.run.app` el release envió la petición en claro, Cloud Run respondió 302 a HTTPS y la app siguió la redirección y listó las plantas (logs de Cloud Run, petición 302 con `userAgent=Dart/3.13 (dart:io)`).
- Causa probable: `usesCleartextTraffic` solo gobierna la pila Java de Android; `dart:io` abre sus propios sockets y lo ignora, y `normalizeApiBaseUrl` acepta `http` y `https` sin distinguir el modo.
- Impacto: la URL desplegada es HTTPS, así que no hay fuga hoy; el riesgo es una garantía documentada que no se cumple. Solución posible (no aplicada): rechazar `http` en `kReleaseMode` en `normalizeApiBaseUrl`, o corregir la documentación y la spec.
- Evidencia: `evidence/app/12-release-http-local.png`, `evidence/app/cleartext-probe-server.log`, `evidence/app/11-release-http-claro.png`.
- Resolución: el usuario decidió corregir la documentación y las specs en vez del código (commit de cierre del cambio); la URL desplegada es HTTPS y las pruebas con HTTP en claro quedan en `debug`/`profile` contra el backend local.

## Observaciones

- O-01: la guía, el diseño y el workflow dicen que Cloud Run «reserva las rutas terminadas en z». Medido: solo `/healthz` exacto (con o sin query) devuelve el 404 HTML del frontal; `/healthz/`, `/readyz`, `/livez` y `/v1/healthz` llegan a la API (404 `problem+json`). La conclusión práctica (no usar `/healthz`) es correcta, la generalización no. Evidencia: `evidence/api/A12_*.txt`.
  Resolución: redacción corregida a «algunas rutas terminadas en z, como `/healthz`».
- O-02: la sonda de arranque con `periodSeconds=2` cuantiza el arranque en frío: la API escucha 0,2 s después de crear la instancia (`escuchando` a las 02:15:08,68) pero la sonda tiene éxito «after 2 attempts» a las 02:15:10,65; las 7 instancias iniciadas tardaron entre 2016 y 2034 ms (`container/startup_latencies`). Un `periodSeconds=1` recortaría cerca de 1 s. Mejora opcional; no contradice la spec.
- O-03: `gcloud run services describe` muestra en el formato por defecto `Scaling: Auto (Min: 0, Max: 20)` a nivel de servicio junto a `Max instances: 2` de la revisión; la anotación `autoscaling.knative.dev/maxScale: '2'` de la plantilla es la que cumple la spec. Con tráfico solo a la última revisión nunca hubo más de 1 instancia (ráfaga de 60 peticiones con 30 en paralelo). Conviene saberlo al leer la salida; la guía no lo explica. También hay `startup-cpu-boost: true` por defecto de `gcloud`.
- O-04: la sección del README «Despliegue en amd64» se renombró a «Despliegue en Cloud Run»; el escenario «README enlaza» cita el nombre antiguo. El contenido cubre la construcción y el despliegue por CI.
- O-05: la tarea 3.5 pide `grep -rn healthz` vacío fuera de `openspec/changes/archive/`; quedan menciones explicativas (workflow, guía, `design.md`, `proposal.md`, `tasks.md`) y las specs principales `openspec/specs/catalog-api` y `backend-container`, que cambiarán al archivar el cambio. El código de `backend/` no contiene `healthz`. Evidencia: `evidence/doc-static-checks.txt`.
- O-06: la cuenta de cómputo por defecto (`177181505486-compute@developer.gserviceaccount.com`) conserva `roles/editor` en el proyecto (valor por defecto de Google, no usada por el servicio, que corre como `boticario-runtime`). El deployer no tiene `serviceAccountUser` sobre ella. Endurecimiento opcional. Evidencia: `evidence/project-iam-summary.txt`.
- O-07: el presupuesto es de 5000 COP (la guía cita `4000COP` solo como ejemplo y 5000 COP «en esta cuenta»); que 5000 COP equivalgan a 1 USD depende del tipo de cambio y no se puede comprobar por CLI. Umbrales 50 %, 90 % y 100 %, sin `notificationsRule` explícita (avisos por defecto a los administradores de la cuenta). Evidencia: `evidence/budget.txt`.
- O-08: el commit `3700c2a` no está en `origin/main` (`origin/main` es `b50db31`); el estado remoto es el que cubre la evidencia de 3.7.
- O-09: una instancia inactiva se apaga unos 15 minutos después de la última petición (apagados observados: 02:13:59 tras 01:58:50, 02:32:27 tras 02:17:21 y 02:55:17 tras 02:40:07). Por eso la condición «15 minutos sin tráfico» de la spec equivale a esperar el apagado.
- O-10: comportamiento de la API sin contrato explícito: la búsqueda es insensible a acentos y mayúsculas (`lávandula` y `LAVANDULA` dan los mismos 7 resultados), `%` se trata como literal (0 resultados), `q=_` devuelve 1 resultado (`melaleuca-linariifolia`), `HEAD /health` responde 200 y `q` con un byte NUL responde 400.
- O-11: la guía usa la URL `boticario-api-d3xv5q3iaa-pv.a.run.app`, pero `describe` lista primero `boticario-api-177181505486.northamerica-south1.run.app`; ambas responden igual (A15).

## Arranque en frío (tarea 5.3, escenario «Primera petición tras inactividad»)

| Muestra | Última petición previa (UTC) | Inactividad | Primera petición | Calientes (inmediatas) | Evidencia |
| --- | --- | --- | --- | --- | --- |
| 1 | 01:58:50 (instancia apagada a las 02:13:59) | 16,3 min | 2,577 s (conexión 0,09 s, TLS 0,16 s), 200 | 0,301 s, 0,286 s, 0,318 s | `evidence/cold-start-1.txt`, `evidence/logs-cold-start-1-window.txt` |
| 2 | 02:17:21 (instancia apagada a las 02:32:27) | 16,9 min | 2,520 s, 200 | 0,437 s, 0,305 s, 0,309 s | `evidence/cold-start-2.txt` |
| 3 | no ejecutada | | | | decisión del usuario, sin más esperas de 15 minutos |

- Cold start medido en servidor: la petición de la muestra 1 registra `latency=2,017 s`; el log de sistema muestra `Starting new instance. Reason: AUTOSCALING` a las 02:15:08,48 y `STARTUP HTTP probe succeeded after 2 attempts` a las 02:15:10,65. Sobrecarga de arranque en frío frente a caliente: unos 2,2 s. En caliente la API responde en 1 a 3 ms en el servidor (el resto de los 0,3 s es la red desde este Mac, con TLS nuevo en cada `curl`).
- Margen frente al tiempo máximo de la app (10 s): unos 7,4 s.
- Memoria (Cloud Monitoring `run.googleapis.com/container/memory/utilizations`, REST de solo lectura): máximo de 0,11 de utilización (cota del bucket) con 256 MiB, unos 28 MiB, es decir un margen de al menos 89 %; 0,03 a 0,10 en reposo y 0,08 durante las pruebas. Los logs de Cloud Run no traen la memoria; la métrica sí se pudo leer por CLI. Evidencia: `evidence/monitoring-4h.txt` (se genera con `scripts/monitoring.py 4 container/memory/utilizations`).
- No ejecutado: arranque en frío medido desde la app en el emulador (decisión del usuario).

## Logs y consumo (tarea 5.5)

- `gcloud run services logs read boticario-api --region=northamerica-south1 --limit=50` muestra las líneas de petición con método, código y URL (`evidence/logs-read-50.txt`). La línea de arranque `escuchando addr=0.0.0.0:8080 db=/app/catalog.db` y `apagado completado` están en `gcloud logging read` (`evidence/logs-counts.txt`, `evidence/logs-cold-start-1-window.txt`); con `--limit=50` quedó desplazada por la ráfaga de pruebas.
- Peticiones del día (24 h, cierre de la QA, `evidence/logs-counts-final.txt`): 448 en total; GET 370 con 200, 3 con 302, 26 con 400 y 35 con 404; DELETE 2, POST 6, PUT 2 y OPTIONS 2 con 405; HEAD 2 con 200. Cloud Monitoring `request_count` suma 448 en 4 h, igual que Logging.
- Consumo medido (`evidence/monitoring-4h.txt`, ventana de 4 h que cubre las 3 ejecuciones del workflow, la preparación y toda la QA): 120,8 vCPU-s (`container/cpu/allocation_time`), 12,7 GiB-s (`container/memory/allocation_time`) y 50,8 s de instancia facturable.
- Comparación con la capa gratuita mensual: 448 de 2.000.000 peticiones (0,022 %), 120,8 de 180.000 vCPU-s (0,067 %) y 12,7 de 360.000 GiB-s (0,0035 %). Salida de red: respuestas de unos 17 KB como máximo, muy por debajo de 1 GB.
- Estimación por petición (método del encargo): con la facturación mínima de 100 ms por petición, 1 vCPU y 1 solicitud/día de tráfico real serían 0,1 vCPU-s/día; incluso 1000 peticiones al día serían unos 3000 vCPU-s al mes (1,7 % de la capa). Cada arranque en frío cuesta unos 15 vCPU-s observados (dos buckets de 14,6 y 15,1 vCPU-s en las dos primeras instancias nuevas); 100 arranques al mes serían unos 1500 vCPU-s.
- Consola de Facturación (Facturación, Informes, filtrar por proyecto `boticario-ai` y servicio Cloud Run): NO EJECUTADO, solo existe en la consola; los datos de uso se contrastaron con Cloud Monitoring, que sí se pudo leer por la API REST con el token de `gcloud`.

## Tabla de casos

Evidencia: carpeta `evidence/` salvo que se indique otra. «Plan» = `test-plan-cloud-run.md`.

### Imagen y registro

| ID | Descripción | Escenario | Resultado | Evidencia |
| --- | --- | --- | --- | --- |
| IMG-01 | Etiquetas `fd94e8f…` y `latest` con el mismo digest `sha256:7f317ecb…` | Etiquetas de la imagen | PASS | `artifact-images.txt`, `image-platform-and-privacy.txt` |
| IMG-02 | Configuración de la imagen: `os=linux`, `architecture=amd64`, usuario `app`, puerto 8080, manifiesto OCI simple | Arquitectura de la imagen | PASS | `image-platform-and-privacy.txt` |
| IMG-03 | Revisión 00003 con imagen `…/boticario-api:fd94e8f6c88d…` y etiqueta `commit-sha` igual a `git rev-parse fd94e8f` | Despliegue por SHA | PASS | `service-describe.yaml`, `revisions-list.txt` |
| IMG-04 | Manifiesto sin credenciales: 401; el IAM del repositorio solo tiene el deployer como `writer` | Repositorio privado | PASS | `image-platform-and-privacy.txt`, `artifact-repo-iam.txt` |
| IMG-05 | El workflow solo publica en `${{ vars.GCP_REGION }}-docker.pkg.dev` | No publicar en registry público | PASS | `workflow-uses.txt` |

### Workflow

| ID | Descripción | Escenario | Resultado | Evidencia |
| --- | --- | --- | --- | --- |
| WF-01 | `push` a `main` con las 6 rutas de la spec y `workflow_dispatch` | Disparadores | PASS | `.github/workflows/deploy-backend.yml` |
| WF-02 | Ejecución `38992727457` (push de `fd94e8f`): construye (3 min), publica, despliega y verifica; la revisión 00003 sirve | Cambio del backend en main | PASS | `gh-run-durations.txt`, `gh-run-list.txt` |
| WF-03 | Los pushes `c80f626` y `b50db31` (solo `docs/`, `openspec/`, `README.md`) no tienen ejecución de «Deploy backend»; la lista de ejecuciones no contiene esos SHA | Cambio ajeno al backend | PASS | `gh-run-list.json`, `gh-all-runs.txt` |
| WF-04 | Ejecución `38991678058` por `workflow_dispatch` recorre checkout, autenticación, login, buildx, construcción, despliegue y verificación | Ejecución manual | PASS | `gh-run-durations.txt` |
| WF-05 | La ejecución `38991678058` se creó a las 01:37:49 y su job empezó a las 01:42:44, tres segundos después de terminar la `38991643116` (01:42:41); `concurrency: deploy-backend`, `cancel-in-progress: false` | Despliegues concurrentes | PASS | `gh-run-durations.txt` |
| WF-06 | Verificación con 200 en `/health` y en el detalle: job en éxito (paso de 1 s) | Verificación satisfactoria | PASS | `gh-run-durations.txt` |
| WF-07 | Las ejecuciones `38991643116` y `38991678058` fallaron en el paso de verificación por el 404 de `/healthz`, tras 3 reintentos visibles | Verificación fallida | PASS | `gh-failed-verify-logs.txt` |
| WF-08 | 6 acciones fijadas por SHA con comentario de versión, cada SHA coincide con la etiqueta en GitHub; `permissions` solo `contents: read` e `id-token: write` (a nivel de workflow, que aplica al job) | Acciones fijadas | PASS | `workflow-uses.txt` |
| WF-09 | `actionlint`: no está instalado (`which` y `mise exec` fallan) | Tarea 3.2 | NO EJECUTADO | `actionlint.txt` |

### Configuración

| ID | Descripción | Escenario | Resultado | Evidencia |
| --- | --- | --- | --- | --- |
| CFG-01 | `min` sin anotación (0), revisión con `maxScale: '2'`; ver O-03 | Escala a cero y máximo | PASS | `service-describe.yaml`, `service-describe-text.txt` |
| CFG-02 | `cpu-throttling: 'true'`, «CPU is only allocated during request processing» | Facturación por petición | PASS | `service-describe-text.txt` |
| CFG-03 | `cpu: '1'`, `memory: 256Mi` | Recursos del contenedor | PASS | `service-describe.yaml` |
| CFG-04 | Sonda HTTP `/health` en 8080, cada 2 s, umbral 10 | Sonda de arranque | PASS | `service-describe.yaml` |
| CFG-05 | gen1, puerto 8080, `boticario-runtime`, `allUsers` con `roles/run.invoker`, ingress `all`, 100 % al último | Resto de la configuración | PASS | `service-describe.yaml`, `run-iam-policy.txt` |
| CFG-06 | `GET /health` 200 por la URL pública | Ruta de salud alcanzable | PASS | `api/A01.txt` |
| CFG-07 | `GET /v1/plants?q=lavandula` 200 con 7 plantas por HTTPS sin credenciales | Acceso público por HTTPS | PASS | `api/A03.txt` |
| CFG-08 | `GET /v1/plants/no-existe` 404 `application/problem+json` | Error del contrato | PASS | `api/A10.txt` |
| CFG-09 | Arranque en frío: 200 en las dos muestras y tiempo medido | Primera petición tras inactividad | PASS | `cold-start-1.txt`, `cold-start-2.txt` |

### Identidad

| ID | Descripción | Escenario | Resultado | Evidencia |
| --- | --- | --- | --- | --- |
| SEC-01 | Los secretos son solo `GCP_WORKLOAD_IDENTITY_PROVIDER` y `GCP_DEPLOYER_SERVICE_ACCOUNT`; 0 claves de usuario en las dos cuentas; sin `credentials_json` ni claves en el repositorio; el workflow usa `google-github-actions/auth` con WIF | Sin claves almacenadas | PASS | `gh-secrets.txt`, `deployer-user-keys.txt`, `runtime-user-keys.txt` |
| SEC-02 | Deployer: `roles/run.admin` en el proyecto, `artifactregistry.writer` en el repositorio y `serviceAccountUser` solo en `boticario-runtime` | Permisos mínimos | PASS | `deployer-project-roles.txt`, `artifact-repo-iam.txt`, `runtime-sa-iam.txt` |
| SEC-03 | `boticario-runtime` sin roles en el proyecto | Cuenta de ejecución sin roles | PASS | `runtime-project-roles.txt` |
| SEC-04 | Condición `assertion.repository == 'sebastianrodriguez1115/boticario-ai'`, proveedor ACTIVE y `principalSet` por `attribute.repository` del mismo repositorio | Proveedor restringido | PASS | `wif-provider.txt`, `deployer-sa-iam.txt` |
| SEC-05 | Un repositorio ajeno no puede asumir la identidad (requiere un token OIDC de otro repositorio) | Proveedor restringido (negativo) | NO EJECUTADO | no ejecutable desde este equipo |
| SEC-06 | IAM del proyecto sin `allUsers`; ver O-06 (editor de la cuenta de cómputo por defecto) | Exploratorio | OBS | `project-iam-summary.txt` |

### Observabilidad y costo

| ID | Descripción | Escenario | Resultado | Evidencia |
| --- | --- | --- | --- | --- |
| OBS-01 | Logs de petición (código, método, URL) y salida de la API (`escuchando`, `apagado completado`) en Cloud Logging | Logs del servicio | PASS | `logs-read-50.txt`, `logs-counts.txt` |
| OBS-02 | 3 revisiones consultables; la 00003 activa | Historial de revisiones | PASS | `revisions-list.txt` |
| OBS-03 | Presupuesto `boticario-ai presupuesto` de 5000 COP con umbrales 0,5, 0,9 y 1,0 acotado al proyecto; ver O-07 | Alerta de presupuesto | PASS | `budget.txt` |
| OBS-04 | Política activa (`cleanupPolicyDryRun` desactivado): `delete-old` (más de 86400 s) y `keep-last-5`; el repositorio tiene 2 imágenes y 37,7 MB | Limpieza de imágenes | PASS | `artifact-repo-describe.txt`, `doc-commands-readonly.txt` |
| OBS-05 | 448 peticiones, 120,8 vCPU-s y 12,7 GiB-s, muy por debajo de la capa gratuita | Consumo dentro de la capa gratuita | PASS | `monitoring-4h.txt` |
| OBS-06 | Memoria máxima 11 % de 256 MiB | Recursos del contenedor | PASS | `monitoring-4h.txt` |
| OBS-07 | Lectura en la consola de Facturación, Informes | Consumo | NO EJECUTADO | solo en la consola (ver sección «Logs y consumo») |

### API desplegada (tarea 5.2)

Detalle de cada subcaso en `evidence/api/results.jsonl` y en `evidence/api/<caso>*.txt`; salida de la ejecución en `evidence/api-tests-run.log`.

| ID | Descripción | Resultado | Evidencia |
| --- | --- | --- | --- |
| A01 | `GET /health` 200, `application/json`, `{"status":"ok"}`, HTTP/2 | PASS | `api/A01.txt` |
| A02 | `/openapi.json` 200; 4 paths y documento idéntico a `backend/openapi.json` | PASS | `api/A02.txt` |
| A03 | `q=lavandula`: 7 resultados, incluye `lavandula-angustifolia`, `limit=20` por defecto | PASS | `api/A03.txt` |
| A04 | Paginación: total 2376 estable, páginas disjuntas, `limit=100` devuelve 100, `offset=2147483647` devuelve vacío | PASS | `api/A04_*.txt` |
| A05 | `q=` vacío igual a sin `q` | PASS | `api/A05_q_vacio.txt` |
| A06 | `q` con `%20`, `+`, bordes con espacios, mayúsculas, acento, `%`, `_`, SQL, comillas, emoji y NUL: nunca 5xx | PASS | `api/A06_*.txt` |
| A06b | Acento y comodines (ver O-10) | OBS | `api/A06_acento.txt` |
| A07 | `q` de 200 caracteres 200 y de 201 caracteres 400 `problem+json` con `param: q`, en ASCII y multibyte | PASS | `api/A07_*.txt` |
| A08 | `limit` 0, 101, -1, `abc`, 1,5, vacío, desbordado y `offset` -1, `abc`, 2147483648: 400 `problem+json` con `param` | PASS | `api/A08_*.txt` |
| A08b | `limit=1`, `limit=100` y `offset=0`: 200 | PASS | `api/A04_*.txt` |
| A09 | Detalle de los 4 ids: 200 con `id`, `scientificName`, `names`, `parts`, `uses` (lavanda 2/4/10, romero 2/9/59, abies 1/3/2, chondrus 2/2/0) | PASS | `api/A09_*.txt` |
| A09b | `chondrus-crispus` con `family` nula; `abies-spectabilis` solo con nombre científico | PASS | `api/A09_chondrus-crispus.txt` |
| A10 | `no-existe`: 404 `problem+json` con `instance` | PASS | `api/A10.txt` |
| A10b | Ids con mayúsculas, `%2F`, `..%2F`, 2000 caracteres, espacio y SQL: 404 `problem+json` | PASS | `api/A10_*.txt` |
| A10c | Ruta desconocida: 404 `problem+json` | PASS | `api/A10_ruta_desconocida.txt` |
| A11 | `POST /health`, `POST /v1/plants`, `PUT`, `DELETE` y `POST /openapi.json`: 405 `problem+json` con `Allow: GET` | PASS | `api/A11_*.txt` |
| A11b | `HEAD /health` 200 y `OPTIONS /health` 405 | OBS | `api/A11_head_health.txt` |
| A12 | `GET /healthz`: 404 `text/html` del frontal de Google, no de la API (escenario informativo) | PASS | `api/A12.txt` |
| A12b | Qué rutas reserva el frontal (ver O-01) | OBS | `api/A12_*.txt` |
| A13 | `http://…/health`: 302 con `Location: https://…` | PASS | `api/A13.txt` |
| A14 | Tiempos en caliente desde este Mac: `/health` p50 313 ms, p95 324 ms; lista `q` p50 310 ms; lista de 100 p50 343 ms; detalle p50 314 ms | OBS | `api/A14_timings.json` |
| A15 | La URL con número de proyecto responde 200 | PASS | `api/A15.txt` |
| A16 | Con `Authorization: Bearer token-invalido` sigue 200 | PASS | `api/A16.txt` |
| A17 | Sin compresión ni `Cache-Control`; `Server: Google Frontend`; HTTP/2; 17 KB para 100 plantas | OBS | `api/A17.txt` |
| A18 | 60 peticiones con 30 en paralelo: todas 200 en menos de 1,2 s, una sola instancia | PASS | `api-tests-run.log`, `monitoring-4h.txt` |
| TLS | TLSv1.3, ALPN h2, certificado `*.a.run.app` de Google Trust Services válido hasta 2026-12-11; TLS 1.1 rechazado | PASS | `tls.txt` |

### Arranque en frío

| ID | Descripción | Resultado | Evidencia |
| --- | --- | --- | --- |
| CS-01 | Muestra 1: 2,577 s en frío, 200 | PASS | `cold-start-1.txt` |
| CS-02 | Muestra 2: 2,520 s en frío, 200 | PASS | `cold-start-2.txt` |
| CS-03 | Muestra 3 | NO EJECUTADO (decisión del usuario) | |
| CS-04 | `container/startup_latencies` de 2016 a 2034 ms en 7 instancias; memoria máxima 11 % | PASS | `monitoring-4h.txt` |

### App release contra Cloud Run (tarea 5.4)

Emulador `emulator-5554` (Android 16, 1080x1920, densidad de 360x640 dp).

| ID | Descripción | Resultado | Evidencia |
| --- | --- | --- | --- |
| APP-01 | `flutter build apk --release --dart-define=API_BASE_URL=https://boticario-api-d3xv5q3iaa-pv.a.run.app` compila (51,1 MB) e `adb install -r` termina en Success; `flutter run --release --no-resident -d emulator-5554 --dart-define=…` también compila (18,2 MB), instala y lanza | PASS | `app/01-inicio.png` |
| APP-02 | Inicio → Explorar plantas y aceites: lista cargada desde Cloud Run (Okra, Manioc Hibiscus, Ambrette, Silver-Fir, en el orden de la API) | PASS | `app/02-explorar-lista.png` |
| APP-03 | Búsqueda `lavandula`: English Lavender, Aspic, Lavender, Lavandula spica, Hybrid Lavender | PASS | `app/04-explorar-busqueda-lavandula.png` |
| APP-04 | Scroll: más de 20 elementos con carga de páginas posteriores (hasta Annona, Apium) | PASS | `app/03-explorar-scroll.png`, `app/03b-explorar-scroll-profundo.png` |
| APP-05 | Pasaporte de Lavandula angustifolia: General (familia Lamiaceae, English Lavender, partes, referencia Steinmetz) y Usos (registros tradicionales con aviso de no eficacia clínica); volver conserva la búsqueda | PASS | `app/05-pasaporte-general.png`, `app/06-pasaporte-usos.png`, `app/07-volver-explorar.png` |
| APP-06 | Red del emulador apagada (`svc wifi disable` y `svc data disable`): Explorar muestra «No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.» con Reintentar; Reintentar sin red mantiene el error; con la red reactivada carga la lista. Red reactivada al terminar | PASS | `app/08-sin-red-error.png`, `app/09-reintentar-con-red.png` |
| APP-07 | `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_BASE_URL=https://…`: «+1: real app against the catalog API: Home, Explore, passport and returns», `exit=0`, 51 s | PASS | `app/smoke-integration-test.log` |
| APP-08 | Release sin `--dart-define`: apunta por defecto a `http://10.0.2.2:8080`, donde no hay backend: «No se pudo conectar con el servidor» con Reintentar | PASS | `app/10-release-sin-define.png` |
| APP-09 | El release no admite HTTP en claro | FAIL (D-01) | `app/12-release-http-local.png`, `app/cleartext-probe-server.log`, `app/11-release-http-claro.png` |

### Documentación

| ID | Descripción | Resultado | Evidencia |
| --- | --- | --- | --- |
| DOC-01 | «Comprobaciones rápidas» (`curl -i /health`, `/openapi.json | head -c 300`, lista con comillas) y «Medir el arranque en frío» ejecutados tal cual (con `cold-start.sh`, que usa el mismo `curl -w`): coinciden con lo descrito, la diferencia caliente frente a frío es de unos 2,2 s | PASS | `cold-start-1.txt`, `api/A01.txt` |
| DOC-02 | Los comandos de runbook, rollback y desmontaje existen en `gcloud` (`--help`); los listados de comprobación (`services list`, `repositories list`, `service-accounts list`, `workload-identity-pools list`, filtro del presupuesto por `displayName`, `list-cleanup-policies`) funcionan y muestran lo documentado; `update-traffic` ofrece `--to-latest` y `--to-revisions`; no se ejecutó ningún comando destructivo. El historial (revisiones 00001 a 00003 y tráfico 100 % al último) es coherente con el rollback que reporta 4.2 | PASS | `doc-static-checks.txt`, `doc-commands-readonly.txt` |
| DOC-03 | Siete APIs habilitadas, `billingEnabled: True`, política de limpieza, proveedor y presupuesto como describe la guía | PASS | `doc-static-checks.txt`, `wif-provider.txt`, `budget.txt` |
| DOC-04 | Enlaces relativos y anclas de `README.md` y de la guía resuelven (el único aparente «no existe» es `docs/Boticario%20AI.docx`, que existe con espacio) | PASS | `links-check.txt` |
| DOC-05 | Sin líneas de continuación en `README.md` ni en `docs/deploy/cloud-run.md` | PASS | `scripts/check-md-lines.py` |
| DOC-06 | README secciones 2, 4 y «Despliegue en Cloud Run» traen los comandos con `https://`, el aviso de que sin el define la dirección es la del emulador, el enlace a la guía; los comandos funcionan tal cual (APP-01, APP-07). La afirmación «release exige HTTPS» es la que falla en D-01 | PASS | `README.md` |
| DOC-07 | Afirmaciones de la guía contra la realidad: duraciones del workflow (1 min con caché, 59 s observados; unos 5 min con cambio de `backend/`, 4 min observados), URL, 5000 COP; imprecisa la reserva de rutas «terminadas en z» (O-01); tarifas de la tabla de costo no verificadas contra la página de precios | OBS | `gh-run-durations.txt`, `api/A12_*.txt` |
| DOC-08 | `grep healthz` no es vacío fuera del archivo (O-05) | OBS | `doc-static-checks.txt` |

## Cobertura y riesgos residuales

- Sin probar: rechazo de un repositorio ajeno por el proveedor WIF (SEC-05); consola de Facturación (OBS-07); `actionlint` (no instalado); muestra 3 de arranque en frío y arranque en frío desde la app (decisión del usuario); rollback y desmontaje (restricción: solo lectura); un nuevo ciclo del workflow con un cambio de `backend/` (no se relanzó); los escenarios de `docker compose` de `backend-container` y de `catalog-api` en local (sin Docker por indicación; el contrato equivalente se probó contra Cloud Run: `/health`, búsqueda real y `RUST_LOG` por defecto con la línea INFO `escuchando`); tarifas de la guía; colección de Postman (MCP sin autenticar, se usó `curl`); accesibilidad de la app más allá de las etiquetas semánticas que expone `uiautomator`.
- Riesgos residuales: D-01; la API es pública, sin autenticación ni límite de tasa, y `max-instances=2` junto con la alerta de presupuesto son el único freno al abuso (diseño aceptado); la alerta de 5000 COP puede no equivaler exactamente a 1 USD; `3700c2a` sin publicar; la política de limpieza actúa hasta un día después, por lo que el rollback solo debe apuntarse a revisiones recientes.

## Cómo re-ejecutar

Desde la raíz del repositorio, con `gcloud` y `gh` autenticados y `source .env.cloud-run`:

- API: `python3 -I openspec/changes/deploy-backend-cloud-run/qa/scripts/api_tests.py` (variable opcional `BASE_URL`).
- Arranque en frío, tras al menos 15 minutos sin tráfico: `bash openspec/changes/deploy-backend-cloud-run/qa/scripts/cold-start.sh <n>`.
- Métricas: `python3 -I openspec/changes/deploy-backend-cloud-run/qa/scripts/monitoring.py 4 request_count container/memory/utilizations container/cpu/allocation_time container/memory/allocation_time container/startup_latencies container/instance_count`.
- Markdown: `python3 -I openspec/changes/deploy-backend-cloud-run/qa/scripts/check-md-lines.py README.md docs/deploy/cloud-run.md`.
- App: los comandos de `README.md` secciones 2 y 4; la interacción con el emulador la hace `scripts/adb_ui.py` (`dump`, `tap`, `shot`, `swipe`).
- D-01: `scripts/cleartext_probe_server.py 8089` más el build `release` con `API_BASE_URL=http://10.0.2.2:8089`.
- Herramientas instaladas: ninguna (solo `curl`, `python3` con la biblioteca estándar, `gcloud`, `gh`, `flutter` y `adb` que ya estaban). No se tocó el proyecto fuera de `qa/`.
