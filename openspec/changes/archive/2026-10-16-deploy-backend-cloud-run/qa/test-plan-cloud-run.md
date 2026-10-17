# Plan de pruebas: deploy-backend-cloud-run

Alcance: tareas 5.2 a 5.6 del cambio `deploy-backend-cloud-run` (la 5.1 la ejecuta el orquestador). Entorno: el servicio real `boticario-api` en Cloud Run (`northamerica-south1`, proyecto `boticario-ai`), desplegado desde el commit `fd94e8f` por la ejecución `38992727457` del workflow. No es producción de usuarios finales: es el único entorno del proyecto académico. No se ejecutó ningún comando de escritura en GCP ni en GitHub.

Resultados y evidencia: [`cloud-run-results.md`](cloud-run-results.md) y `evidence/`. Scripts: `scripts/`.

## Estrategia

- Caja negra sobre los escenarios de `specs/backend-deployment/spec.md` (cada escenario es un criterio de aceptación) más los deltas de `catalog-api`, `backend-container` y `flutter-app-bootstrap`.
- Técnicas: particiones de equivalencia y valores límite para `q`, `limit` y `offset` (0, 1, 100, 101, 200 y 201 caracteres, ASCII y multibyte, desbordes de entero); tabla de decisión para los métodos HTTP y las rutas reservadas por el frontal; transición de estados para el arranque en frío (instancia viva, inactiva, apagada, nueva); inspección de configuración (`gcloud ... describe`, IAM, Artifact Registry) contra cada escenario de configuración, identidad y control de costo; pruebas exploratorias de la documentación siguiéndola tal cual está escrita.
- Prioridad por riesgo: (1) la API pública responde correctamente por HTTPS y el contrato de errores se cumple; (2) la configuración de costo (máximo de instancias, escala a cero, facturación por petición) y la identidad sin claves; (3) la app `release` funciona de punta a punta contra Cloud Run; (4) arranque en frío compatible con el tiempo máximo de la app (10 s); (5) documentación operativa que un desarrollador seguiría.
- Pirámide: no se repiten las pruebas unitarias ni de integración del backend (`cargo test`) ni los tests de la app (5.1); aquí solo contratos de la API desplegada y flujos de usuario en el emulador.
- Herramientas: `curl` y `python3` (el MCP de Postman no estaba autenticado; no se creó colección), `gcloud` y `gh` de solo lectura, la API REST de Cloud Monitoring con el token de `gcloud` (solo lectura), `flutter`, `adb` y `uiautomator` en el emulador `boticario_catalog_api36`. No se instaló nada dentro del proyecto.
- Restricciones: sin `delete`, `update-traffic`, `deploy` ni relanzar el workflow; sin Docker local; sin credenciales ni ids de facturación en los artefactos (el id de la cuenta de facturación está sustituido por `<BILLING_ACCOUNT_ID>`).

## Casos

Resultado esperado = lo que exige el escenario citado. La columna Técnica usa: EP (partición de equivalencia), VL (valor límite), TD (tabla de decisión), TE (transición de estados), INS (inspección), EXP (exploratoria).

### Imagen y registro (requisito «Imagen amd64 publicada por CI y etiquetada por commit»)

| ID | Escenario | Técnica | Precondición y pasos | Esperado |
| --- | --- | --- | --- | --- |
| IMG-01 | Etiquetas de la imagen | INS | `gcloud artifacts docker images list ... --include-tags`; `HEAD` del manifiesto por SHA y por `latest` | Ambas etiquetas existen y apuntan al mismo digest |
| IMG-02 | Arquitectura de la imagen | INS | Leer el manifiesto y el blob de configuración por la API del registry con el token de `gcloud` | `os=linux`, `architecture=amd64`, manifiesto simple sin atestaciones |
| IMG-03 | Despliegue por SHA | INS | `gcloud run services describe`: imagen de la revisión y etiqueta `commit-sha`; `git rev-parse fd94e8f` | La imagen referencia la etiqueta del SHA completo del commit, no `latest` |
| IMG-04 | Repositorio privado | TD | Pedir el manifiesto sin credenciales; revisar el IAM del repositorio | 401 sin credenciales y ningún `allUsers` en el repositorio |
| IMG-05 | Sin registry público | INS | Revisar `tags` y el login del workflow | Solo `<region>-docker.pkg.dev` |

### Workflow (requisito «Despliegue automático con verificación posterior»)

| ID | Escenario | Técnica | Precondición y pasos | Esperado |
| --- | --- | --- | --- | --- |
| WF-01 | Disparadores y filtros de ruta | INS | Leer `on:` del YAML | `push` a `main` con `paths` de la spec y `workflow_dispatch` |
| WF-02 | Cambio del backend en main | INS | `gh run view 38992727457` y revisión 00003 | Construye, publica, despliega y la revisión sirve |
| WF-03 | Cambio ajeno al backend | TD | `gh run list` y `git show --stat` de los pushes `c80f626`, `b50db31` (solo `docs/`, `openspec/`, `README.md`) | Ninguna ejecución para esos commits |
| WF-04 | Ejecución manual | INS | Ejecución `38991678058` (`workflow_dispatch`) | Recorre los mismos pasos que el `push` |
| WF-05 | Despliegues concurrentes | TE | Comparar `createdAt` y `startedAt` de las ejecuciones `38991643116` y `38991678058` y revisar `concurrency` | La segunda espera a la primera, sin cancelar |
| WF-06 | Verificación satisfactoria | INS | Paso «Verificar el servicio desplegado» de la `38992727457` | Job en éxito con 200 en las dos consultas |
| WF-07 | Verificación fallida | INS | Registros de las ejecuciones fallidas | El job falla cuando la consulta no responde 200 |
| WF-08 | Acciones fijadas y permisos | INS | `grep uses:`, comparar cada SHA con la etiqueta de su versión por la API de GitHub; `permissions` | Todas por SHA con comentario de versión; solo `contents: read` e `id-token: write` |
| WF-09 | `actionlint` | INS | Buscar el binario | Si no está instalado, se reporta |

### Configuración del servicio (requisito «Configuración del servicio en Cloud Run»)

| ID | Escenario | Técnica | Pasos | Esperado |
| --- | --- | --- | --- | --- |
| CFG-01 | Escala a cero y máximo de instancias | INS | `describe` | `min-instances` 0 (sin anotación) y `max-instances` 2 |
| CFG-02 | Facturación por petición | INS | `describe` | `cpu-throttling: true`, «CPU is only allocated during request processing» |
| CFG-03 | Recursos del contenedor | INS | `describe` | 1 vCPU y 256 MiB |
| CFG-04 | Sonda de arranque | INS | `describe` | HTTP a `/health` en el puerto 8080 |
| CFG-05 | Resto de la configuración | INS | `describe` y `get-iam-policy` | gen1, puerto 8080, cuenta `boticario-runtime`, `allUsers` con `run.invoker`, ingress `all` |
| CFG-06 | Ruta de salud alcanzable | EP | A01 | 200 |
| CFG-07 | Acceso público por HTTPS | EP | A03 | 200 con la lista |
| CFG-08 | Error del contrato | EP | A10 | 404 `application/problem+json` |
| CFG-09 | Primera petición tras inactividad | TE | CS-01 a CS-03 | La instancia arranca, responde 200 y el tiempo queda medido |

### Identidad (requisito «Identidad de despliegue sin claves de larga duración»)

| ID | Escenario | Técnica | Pasos | Esperado |
| --- | --- | --- | --- | --- |
| SEC-01 | Sin claves almacenadas | INS | `gh secret list`, `gcloud iam service-accounts keys list --managed-by=user`, `grep` de claves en el repositorio | Sin claves JSON; autenticación por WIF |
| SEC-02 | Permisos mínimos del deployer | INS | IAM del proyecto, del repositorio y de la cuenta de ejecución | `run.admin`, `artifactregistry.writer` (repositorio) y `serviceAccountUser` (solo sobre la de ejecución) |
| SEC-03 | Cuenta de ejecución sin roles | INS | IAM del proyecto filtrado por la cuenta | Ninguno |
| SEC-04 | Proveedor restringido al repositorio | INS | `providers describe` | `assertion.repository == 'sebastianrodriguez1115/boticario-ai'` y `principalSet` limitado al repositorio |
| SEC-05 | Un repositorio ajeno no puede asumir la identidad | TD | Requiere un token OIDC de otro repositorio | No ejecutable desde este equipo |
| SEC-06 | Revisión del IAM del proyecto | EXP | Resumen del IAM del proyecto | Sin sorpresas (`allUsers`, roles amplios para las cuentas del cambio) |

### Observabilidad y costo (requisito «Observabilidad y control de costo»)

| ID | Escenario | Técnica | Pasos | Esperado |
| --- | --- | --- | --- | --- |
| OBS-01 | Logs del servicio | INS | `gcloud run services logs read` y `gcloud logging read` | Líneas de petición con código y la línea de arranque de la API |
| OBS-02 | Historial de revisiones | INS | `gcloud run revisions list` | Revisiones consultables |
| OBS-03 | Alerta de presupuesto | INS | `gcloud billing budgets list` | Presupuesto del equivalente a 1 USD con umbrales |
| OBS-04 | Limpieza de imágenes | INS | `repositories describe` | Política activa, conserva las últimas 5 |
| OBS-05 | Consumo dentro de la capa gratuita | INS | Cloud Monitoring (peticiones, vCPU-s, GiB-s) y estimación | Dentro de 2 M peticiones, 180.000 vCPU-s y 360.000 GiB-s |
| OBS-06 | Memoria de la instancia | INS | Métrica `memory/utilizations` | Muy por debajo de 256 MiB |
| OBS-07 | Consumo en la consola de Facturación | EXP | Facturación, Informes | Solo es posible en la consola |

### API desplegada (tarea 5.2; contrato de `catalog-api` y escenarios de la spec de despliegue)

Los casos de API los ejecuta `scripts/api_tests.py`; la evidencia está en `evidence/api/`.

| ID | Cubre | Técnica | Pasos | Esperado |
| --- | --- | --- | --- | --- |
| A01 | CFG-06, `catalog-api` salud | EP | `GET /health` | 200, `application/json`, `{"status":"ok"}` |
| A02 | Misma API que la imagen local | INS | `GET /openapi.json` y comparar con `backend/openapi.json` | 200, mismos paths y métodos (y documento idéntico) |
| A03 | CFG-07 | EP | `GET /v1/plants?q=lavandula` | 200, página con `items`, `total`, `limit`, `offset` e incluye `lavandula-angustifolia` |
| A04 | Paginación | VL | `limit=2` con `offset` 0 y 2, `limit=100`, `limit=1`, `offset=2147483647` | Páginas disjuntas, `total` estable, ítems vacíos más allá del final |
| A05 | `q` vacío | EP | `q=` | Igual que sin `q` |
| A06 | `q` codificado | EP | Espacios (`%20`, `+`), bordes con espacios, mayúsculas, acento, comodines `%` y `_`, SQL, comillas, emoji, NUL | Nunca 5xx |
| A07 | `q` máximo 200 caracteres | VL | 200 y 201 caracteres, ASCII y multibyte | 200 y 400 `problem+json` con `param: q` |
| A08 | `limit` y `offset` inválidos | VL, EP | 0, 101, -1, `abc`, 1.5, vacío, desbordes | 400 `problem+json` con `param` |
| A09 | Detalle | EP | `lavandula-angustifolia`, `rosmarinus-officinalis`, `abies-spectabilis`, `chondrus-crispus` | 200 con campos obligatorios; `family` nula en `chondrus-crispus` |
| A10 | CFG-08 | EP | `GET /v1/plants/no-existe`, ids hostiles y ruta desconocida | 404 `problem+json`, nunca 5xx |
| A11 | Métodos | TD | `POST /health`, `POST /v1/plants`, `PUT`, `DELETE`, `POST /openapi.json`; `HEAD` y `OPTIONS` | 405 `problem+json` con `Allow: GET` |
| A12 | `/healthz` | TD | `GET /healthz` y rutas parecidas | 404 HTML del frontal (informativo) |
| A13 | HTTPS | EP | `http://.../health` sin seguir redirecciones | Redirección a HTTPS o fallo |
| A14 | Tiempos en caliente | EXP | 20 peticiones por endpoint | Informativo |
| A15 | URL `*.run.app` alternativa | EP | `https://boticario-api-<número>.northamerica-south1.run.app/health` | 200 |
| A16 | Público sin credenciales | EP | Cabecera `Authorization` inválida | 200 |
| A17 | Cabeceras | EXP | `Accept-Encoding: gzip` | Informativo |
| A18 | Concurrencia ligera | EXP | 60 peticiones, 30 en paralelo | Todas 200 |
| TLS | HTTPS | INS | `curl -v` | TLS 1.3 con certificado válido y h2; TLS 1.1 rechazado |

### Arranque en frío (tarea 5.3)

| ID | Técnica | Pasos | Esperado |
| --- | --- | --- | --- |
| CS-01 a CS-03 | TE | Con `scripts/cold-start.sh <n>`: comprobar en Cloud Logging la última petición, esperar al menos 15 minutos sin tráfico, medir la primera petición y 3 inmediatas con `curl -w` | 200 en todas; primera mucho más lenta; tiempo menor que el máximo de 10 s de la app |
| CS-04 | INS | Logs de sistema del arranque, métrica `container/startup_latencies` y `container/memory/utilizations` | Latencia de arranque coherente con las muestras; memoria muy por debajo de 256 MiB |

### App release contra Cloud Run (tarea 5.4; `flutter-app-bootstrap`)

| ID | Técnica | Pasos | Esperado |
| --- | --- | --- | --- |
| APP-01 | INS | `flutter build apk --release --dart-define=API_BASE_URL=https://boticario-api-d3xv5q3iaa-pv.a.run.app` e instalar en el emulador | Build correcto e instalación |
| APP-02 | EXP | Inicio → Explorar con lista cargada desde Cloud Run, captura | La lista aparece |
| APP-03 | EP | Búsqueda `lavandula`, captura | Resultados filtrados |
| APP-04 | EXP | Scroll de la lista, captura | Se cargan más elementos |
| APP-05 | EP | Pasaporte de `Lavandula angustifolia`, pestañas General y Usos, volver, capturas | Datos del detalle |
| APP-06 | TE | Red del emulador apagada, abrir Explorar y reintentar; reactivar la red y reintentar | Error con botón Reintentar; tras reactivar, carga |
| APP-07 | INS | `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_BASE_URL=https://...` | El smoke pasa |
| APP-08 | TD | Build `release` sin `--dart-define` instalado en el emulador | No funciona (apunta a `http://10.0.2.2:8080`: sin backend y sin HTTP en claro en `release`); mensaje reintentable |
| APP-09 | TD | Mismo build con `API_BASE_URL=http://...` | El `release` no admite HTTP en claro |

### Documentación (tarea 5.6; requisito «Documentación...» y escenario «Release contra el backend desplegado»)

| ID | Técnica | Pasos | Esperado |
| --- | --- | --- | --- |
| DOC-01 | EXP | Ejecutar tal cual «Comprobaciones rápidas» y «Medir el arranque en frío» | Los comandos funcionan y coinciden con lo descrito |
| DOC-02 | INS | Comprobar con `--help` que los comandos del runbook, del rollback y del desmontaje existen, y ejecutar los listados de comprobación de solo lectura | Existen; el listado de servicio, repositorio, cuentas y pool coincide con lo documentado |
| DOC-03 | INS | Comprobar las siete APIs, `billingEnabled`, política de limpieza, proveedor y presupuesto citados en la preparación | Coinciden con la guía |
| DOC-04 | INS | Resolver los enlaces relativos y las anclas de `README.md` y de la guía | Todos resuelven |
| DOC-05 | INS | `scripts/check-md-lines.py` sobre `README.md` y la guía | Sin líneas de continuación (regla de `AGENTS.md`) |
| DOC-06 | INS | Revisar README secciones 2 y 4 y «Despliegue en Cloud Run» | Comandos con `https://`, el release exige HTTPS y sin el define la dirección sigue siendo la del emulador; enlazan a la guía |
| DOC-07 | INS | Comprobar las afirmaciones de la guía contra la realidad (duraciones del workflow, cuenta del presupuesto, reserva de rutas «terminadas en z») | Coinciden |
| DOC-08 | INS | `grep healthz` fuera de `openspec/changes/archive/` | Solo menciones explicativas |
