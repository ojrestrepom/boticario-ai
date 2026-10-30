# Resultados de QA: add-api-token-auth

Alcance: tareas 9.1 a 9.5. Plan, casos y trazabilidad en [`test-plan-api-token.md`](test-plan-api-token.md). Evidencia en `evidence/` y scripts en `scripts/`. Fecha de ejecución: 2026-10-18 y 2026-10-19 (UTC).

Entornos: backend local con `docker compose` (imagen reconstruida desde `main`, `f318165`, con tokens de prueba propios `<token-local-1>`, `<token-local-2>`, `<token-local-3>`); Cloud Run `boticario-api`, revisión `boticario-api-00007-fgc`, con los tokens reales `<token-app>` y `<token-ci>` leídos de la versión 1 del secreto; emulador Android `boticario_catalog_api36` (arm64, API 36). No se tocó el teléfono físico del usuario. No se ejecutó ningún comando de escritura en Google Cloud ni en GitHub.

## Resumen

- 88 casos del plan: 87 pasan, 0 fallan, 0 quedan bloqueados y 1 queda cubierto por la medición anterior por decisión del usuario (DEP-11, arranque en frío; no se ejecutó en este cambio). En la primera ejecución eran 86 pasan, 1 falla (DOC-01) y 1 pendiente; tras corregirse la documentación, DOC-01 se re-verificó y pasa.
- Contra la spec: no se encontró ningún defecto de comportamiento. Ninguna ruta de datos de `/v1` responde sin un token válido, en local ni en Cloud Run, incluidos 21 intentos de evasión de ruta.
- Defectos: los 4 de severidad baja (DEF-01 a DEF-04, 3 de documentación y 1 de usabilidad de Compose) están corregidos en la documentación y re-verificados (véase «Defectos»). La observación de redacción OBS-07 quedó corregida en `af67029` y verificada.
- Incidente de la propia QA: el token real de la app quedó una vez en los logs de petición de Cloud Logging por una prueba mía (véase OBS-05). Decisión del usuario del 2026-10-18: acepta el riesgo y no se rota el token.
- Arranque en frío (DEP-11): no re-medido en este cambio. Decisión del usuario: darlo por cubierto con la medición del cambio archivado (2,577 s y 2,520 s), sin volver a medir, porque este cambio solo añade leer `API_TOKENS` al arrancar.

## Desvíos respecto de las tareas

- La tarea 9.3 menciona `qa/cloud-run-results.md`, un resto del cambio anterior. Todo el informe está en este archivo, `api-token-results.md`.
- 9.2: el CLI de Postman 1.74 está instalado pero sin sesión iniciada (`postman whoami` no tiene cuenta), así que no se creó colección. Se usó `curl`-equivalente en Python con sockets en bruto (`scripts/api_tests.py`), que además permite cabeceras duplicadas, bytes no ASCII y rutas sin normalizar.
- 9.3: la rotación se ejecutó contra el contenedor local, como se acordó. El procedimiento de Cloud Run se revisó sin ejecutarlo.
- Arranque en frío: no re-medido en este cambio. El usuario decidió darlo por cubierto con la medición previa. Medición previa del cambio archivado `deploy-backend-cloud-run`: 2,577 s y 2,520 s la primera petición tras 16,3 y 16,9 minutos de inactividad (`openspec/changes/archive/2026-10-16-deploy-backend-cloud-run/qa/evidence/cold-start-1.txt` y `cold-start-2.txt`). Dato adicional de esta QA, no una medición de arranque en frío: Cloud Monitoring registra una latencia de arranque de la instancia de 1,02 s para la revisión 00007 (`evidence/cloud/monitoring-24h.txt`), con la sonda que espera 1 s antes del primer intento.
- El build `release` contra Cloud Run se hizo con `flutter run --release`, como documenta el README. El resto de variantes de la app usan `flutter run` de depuración con `--dart-define-from-file` desde un archivo fuera del repositorio; el backend local se alcanzó a través de `scripts/logging_proxy.py` (puerto 8081) para contar peticiones sin registrar tokens, en lugar de directamente en el 8080. El smoke local sí usó el 8080 por defecto.

## Resultados por caso

Cada fila indica el estado y dónde está la evidencia. `L` es local y `C` es Cloud Run. Los conteos de «comprobaciones» son los de los scripts.

### API (9.2): `scripts/api_tests.py`

Local: 121 comprobaciones PASS, 0 FAIL, 8 observaciones (`evidence/api/run-local.log`). Cloud Run: 124 PASS, 0 FAIL, 9 observaciones (`evidence/api/run-cloud.log`). Cada caso tiene su archivo `evidence/api/<local|cloud>/AUT-NN.txt` con cada petición, estado, cabeceras y cuerpo, con los valores de token sustituidos por marcadores.

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| AUT-01 token válido en el listado | PASA (L, C) | 200, JSON, 2 elementos |
| AUT-02 token válido en el detalle | PASA (L, C) | 200 con `Lavandula angustifolia` |
| AUT-03 `bearer`, `BEARER`, `BeArEr` | PASA (L, C) | 200 en los tres |
| AUT-04 cabecera ausente | PASA (L, C) | 401, `application/problem+json`, `WWW-Authenticate: Bearer`, sin datos |
| AUT-05 token incorrecto | PASA (L, C) | mismo cuerpo y cabeceras que AUT-04 |
| AUT-06 último carácter distinto | PASA (L, C) | 401 idéntico |
| AUT-07 prefijos de 63, 32 y 1 caracteres | PASA (L, C) | 401 idéntico |
| AUT-08 válido más un carácter, en mayúsculas, sin el primer carácter | PASA (L, C) | 401 idéntico |
| AUT-09 `Basic`, token sin esquema, `Token`, `Bearer<token>` pegado | PASA (L, C) | 401 idéntico |
| AUT-10 cabecera vacía, `Bearer`, `Bearer ` | PASA (L, C) | 401 idéntico |
| AUT-11 ruta inexistente | PASA (L, C) | sin token 401; con token 404 `problem+json`; el 401 sigue siendo JSON válido con `%22` en la ruta |
| AUT-12 `/v1` y `/v1/` | PASA (L, C) | 401 sin token, 404 con token |
| AUT-13 `POST`, `PUT`, `PATCH`, `DELETE` sin token | PASA (L, C) | 401, no 405 |
| AUT-14 los mismos métodos con token | PASA (L, C) | 405 `problem+json`; el listado sigue intacto |
| AUT-15 `HEAD` y `OPTIONS` | PASA (L, C) | 401 sin token; `HEAD` 200 con token; `OPTIONS` con token 405 (observación) |
| AUT-16 rutas públicas | PASA (L, C) | `/health` y `/openapi.json` 200 sin token, con token y con token incorrecto; `/health` devuelve siempre `{"status":"ok"}` |
| AUT-17 cuerpo y cabeceras idénticos | PASA (L, C) | 16 rechazos distintos con un único cuerpo y un único conjunto de cabeceras (`evidence/api/*/AUT-17.txt`) |
| AUT-18 ninguna respuesta refleja el token | PASA (L, C) | 0 apariciones de 6 u 8 sondas (token, prefijos de 63 y 32, sufijo de 32, incorrecto) en 127 y 130 respuestas |
| AUT-19 token por query, `X-Api-Key`, `Proxy-Authorization`, `Cookie` | PASA (L, C) | 401; la respuesta no incluye la query. En C se usó un token incorrecto en la query (véase OBS-05) |
| AUT-20 cabeceras `Authorization` duplicadas | PASA, con observación (L, C) | dos inválidas 401; inválida y luego válida 401; válida y luego inválida 200 (se usa la primera; OBS-01) |
| AUT-21 separadores | PASA, con observación (L, C) | dos espacios 200, espacio final 200, tabulador 401 (OBS-01) |
| AUT-22 bytes no ASCII y cabeceras de 16 KB y 100 KB | PASA (L, C) | 401, 401 y en C 413 para 100 KB; nunca 200 ni 5xx |
| AUT-23 evasión de ruta (CH-1) | PASA (L, C) | 21 rutas por 2 credenciales: ninguna devuelve datos; 401 para lo que cae bajo `/v1`, 404 para el resto (`/V1`, `//v1`, `/x/../v1`, `/%76%31`, `/v1%2F`, `/v1x`, forma absoluta) |
| AUT-24 errores del contrato | PASA (L, C) | `limit=abc` con token 400 que nombra `limit`; `no-existe` con token 404; sin token ambos 401 |
| AUT-25 documento OpenAPI | PASA (L, C) | esquema Bearer, seguridad en las operaciones de `/v1`, ninguna en `/health` ni `/openapi.json`, 401 `problem+json`, rutas solo `/health`, `/openapi.json` y `/v1/*`, sin tokens, igual al `backend/openapi.json` versionado |
| AUT-26 consistencia | PASA (L, C) | 20 peticiones alternadas, sin una sola desviación |
| AUT-27 `Authorization` intacta en Cloud Run | PASA (C) | `<token-app>` y `<token-ci>` dan 200 (solo posible si la cabecera llega byte a byte); el 401 lleva el cuerpo y la cabecera de la API, y `server: Google Frontend` solo está delante |
| AUT-28 tiempo según la posición de la diferencia | PASA, indicativo (L) | 3000 peticiones por variante: mediana 155,6 us con el primer y con el último carácter distinto (diferencia 0,1 us); `evidence/api/timing-local.txt`. No es una prueba de tiempo constante |

### Configuración y contenedor (9.2): `scripts/container_tests.py`

55 comprobaciones PASS, 0 FAIL (`evidence/container-run.log`, `evidence/container/*.txt`).

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| CFG-01 variable ausente | PASA | código 2, el mensaje nombra `API_TOKENS` |
| CFG-02 vacía, solo espacios, solo salto de línea | PASA | código 2 con el mismo mensaje |
| CFG-03 31 y 257 caracteres | PASA | código 2; indica la longitud mínima o máxima; sin el valor |
| CFG-04 32 y 256 caracteres | PASA | arranca, acepta el token y rechaza otro |
| CFG-05 `a,,b`, coma final, coma inicial, `@`, espacio interior, `é`, un token corto entre buenos | PASA | código 2, nombra `API_TOKENS`, sin el valor |
| CFG-06 un token de 64 hex | PASA | acepta ese token y rechaza otro |
| CFG-07 `<t1> , <t2>\n` y `<t1>,<t2>\r\n` | PASA | acepta ambos y rechaza un tercero |
| CFG-08 `--help` y `--openapi` sin la variable | PASA | código 0; el documento impreso es igual a `backend/openapi.json` |
| CFG-09 mensajes sin valores | PASA | 0 apariciones en CFG-01 a CFG-05 |
| CON-01 `docker compose up` sin `API_TOKENS` | PASA | falla antes de crear el contenedor con «API_TOKENS no esta definido; crea el archivo .env…»; no queda contenedor ni `.env` en la raíz; `docker compose config` con la variable pasa |
| CON-02 salud, 401 y 200 | PASA | 200, 401, 200 |
| CON-03 búsqueda real | PASA | `q=lavand` con resultados reales y el detalle de `Lavandula angustifolia` |
| CON-04 `PORT=9090` | PASA | `/health` 200 en 9090; el 8080 no está publicado |
| CON-05 `RUST_LOG=warn` y por defecto | PASA | con `warn` no aparece «escuchando»; por defecto sí |
| CON-06 dos tokens | PASA | ambos 200 y un tercero 401 |
| CON-07 imagen sin tokens | PASA | `Config.Env` sin `API_TOKENS`; `docker history --no-trunc` sin valores; 0 archivos del sistema de archivos exportado con un token local |
| CON-08 contenido mínimo | PASA | existen `/app/catalog-api` y `/app/catalog.db`; sin cargo, rustc, ZIP, base cruda ni `.rs` (solo los directorios vacíos `usr/src` y `usr/local/src` de la imagen base de Debian) |
| CON-09 servir sin red | PASA | red Docker `--internal`: detalle con token 200 con datos, sin token 401, y la red no llega a Internet |
| CON-10 logs a nivel `trace` | PASA | 13 líneas, 0 apariciones de 6 sondas; el 401 se registra a nivel `debug` con la clase del fallo (`ausente`, `no coincide`) y sin la cabecera |

Los escenarios `Configuración por defecto` (127.0.0.1:8080), `Configuración sin secretos al depurar` y `Fallo interno` solo se comprueban con pruebas unitarias del proyecto; esta QA no las repitió.

### Rotación (9.3): `scripts/rotation_test.py`

7 comprobaciones PASS, 0 FAIL (`evidence/rotation/rotation.txt`, `evidence/rotation/run.log`). Cada estado recrea el contenedor con `docker compose up -d` y otro `API_TOKENS`, sin reconstruir.

| Caso | Estado | Matriz obtenida |
| --- | --- | --- |
| ROT-01 A: solo `<token-local-1>` | PASA | t1 200, t2 401, t3 401, sin token 401, `/health` 200 |
| ROT-02 B: `<token-local-2>,<token-local-1>` | PASA | t1 200, t2 200, t3 401, sin token 401 |
| ROT-03 C: solo `<token-local-2>` | PASA | t1 401, t2 200, t3 401 |
| ROT-04 D, E, F: segunda rotación y tres tokens | PASA | D (t3,t2): t1 401, t2 200, t3 200; E (t1,t2,t3): los tres 200; F (t1,t3): t2 401 |
| ROT-05 recreación sin reconstruir | PASA | contenedor nuevo con id distinto, «Recreate» y sin «Building» en la salida |
| ROT-06 procedimiento de Cloud Run | PASA (re-verificado) | véase la revisión de la guía más abajo y `evidence/reverify/def02-ci-rotation-sim.txt` |

### App en el emulador (9.4)

Capturas y registros en `evidence/app/`. Los `logcat` están filtrados por el PID de la app (`adb -s emulator-5554 logcat -d --pid=<pid>`).

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| APP-01 recorrido normal, local | PASA | `V1-01` a `V1-05`; el proxy registró `GET /v1/plants?limit=50&offset=0`, `?q=lavandula…` y `/v1/plants/lavandula-angustifolia`, los tres con `Authorization=Bearer <token-local-1>` y 200 (`proxy-V1.log`) |
| APP-02 recorrido normal, Cloud Run (`release`) | PASA | `V4-01` a `V4-04`; `flutter run --release --dart-define-from-file=dart_defines.local.json`, archivo creado con el bloque del paso 7 de la guía; 0 cierres inesperados |
| APP-03 token incorrecto, local | PASA | `V2-02`: «La app no está autorizada para usar el servidor. Inténtalo de nuevo más tarde.» con el botón Reintentar; el backend registró `Bearer <token-local-2>` y 401 |
| APP-04 sin token, local | PASA | `V3-02`: la misma pantalla; el proxy registró `Authorization=ausente`; `V3-resultado.txt` |
| APP-05 token incorrecto, Cloud Run | PASA | `V5-02`, `V5-resultado.txt` |
| APP-06 sin token, Cloud Run | PASA | `V6-02`, `V6-resultado.txt` |
| APP-07 detalle con 401 tras un listado correcto (CH-3) | PASA | `V1-06` a `V1-09`: la lista cargó con 200, el backend se recreó sin `<token-local-1>` y al abrir una planta el pasaporte mostró «No se pudo cargar la planta» con el mensaje de no autorizada, no «planta no encontrada»; sin cierre inesperado; Explorar conserva su lista |
| APP-08 reintentar y ausencia de reintentos automáticos | PASA | 0 peticiones nuevas en 30 s en cada variante; una petición más por cada pulsación de Reintentar; el error persiste (`V1-reintentos.txt`, `V2-reintentos.txt`, `V3-resultado.txt`) |
| APP-09 Inicio y P06 tras el 401 | PASA | `V2-03`; Inicio y «¿Qué deseas lograr?» funcionan, sin inicio de sesión, en las variantes V1 a V6 |
| APP-10 token fuera de pantalla y de `logcat` | PASA | `evidence/app/logcat-token-counts.txt`: 0 apariciones de los 5 tokens y del aleatorio en los 6 `logcat` y las 3 salidas del smoke; 0 `FATAL` o `AndroidRuntime`; las capturas revisadas no muestran ningún token |
| APP-11 smoke contra el backend local | PASA | `smoke-local.txt`: «All tests passed!», 40 s con el APK ya compilado (el primer intento falló porque el emulador se cayó, `adb: device offline`; se repitió con el emulador relanzado) |
| APP-12 smoke contra Cloud Run | PASA | `smoke-cloud-run.txt`: «All tests passed!»; el `adb uninstall` final agotó el tiempo, sin efecto en el resultado |
| APP-13 smoke sin `API_TOKEN` | PASA | `smoke-sin-define-local.txt`: falla a los 2 s de empezar la prueba, sin esperar a la red, con el mensaje «Falta API_TOKEN: la API exige un token…» |
| APP-14 peticiones de la app | PASA | solo `GET /v1/plants` y `GET /v1/plants/{id}`, con `accept` y `user-agent` como únicas otras cabeceras; 0 peticiones al abrir Inicio y P06 |
| APP-15 el token se extrae del APK (limitación) | PASA (la limitación existe) | `apk-extraction.txt`: el token de la app aparece en texto claro, 1 vez, en `lib/arm64-v8a/libapp.so` del APK `release` |
| APP-16 token fuera del repositorio | PASA | `repo-token-search.txt`: 0 archivos versionados con alguno de los 5 tokens; solo el valor ficticio `test-token-not-a-secret-000000000000` |

Verificación en un dispositivo físico, aportada por el orquestador y el usuario, no ejecutada por esta QA: el orquestador instaló, a petición del usuario, un build `release` del commit `1fa8269`, compilado contra Cloud Run con el token de la app, en un teléfono físico (SM-G998B, Android 15). El usuario confirmó el 2026-10-18 que funciona correctamente y que el catálogo carga. No hay capturas ni se ejecutó nada en ese teléfono para comprobarlo.

### Despliegue en Cloud Run, solo lectura (`scripts/gcp_readonly.sh`, `scripts/verify_step_sim.py`)

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| DEP-01 configuración del servicio | PASA | `evidence/cloud/service-config.txt`: `maxScale` 2 y sin `minScale`, `cpu-throttling: 'true'`, 1 CPU y 256 Mi, sonda `/health` en 8080, `allUsers` con `roles/run.invoker` (`service-iam.txt`), 100 % en `boticario-api-00007-fgc` |
| DEP-02 `API_TOKENS` desde Secret Manager | PASA | `secretKeyRef` `boticario-api-tokens` con `key: '1'` y sin valor; 0 apariciones de los tokens en `service-describe.yaml` y en el workflow (`token-counts.txt`); en los logs de la revisión solo la de OBS-05 |
| DEP-03 accesos HTTPS | PASA | AUT-01, 04, 05, 16, 24 en C: 200, 401 con `WWW-Authenticate: Bearer`, 404 `problem+json` |
| DEP-04 IAM de la cuenta de ejecución y del secreto | PASA | `secret-iam.txt`: solo `boticario-runtime` con `secretAccessor`; `project-iam-summary.txt`: `boticario-runtime` sin roles en el proyecto; un único secreto en el proyecto; el rol `roles/editor` de la cuenta de cómputo por defecto no incluye `secretmanager.versions.access` (`roles-secret-permissions.txt`), solo `roles/owner` lo incluye |
| DEP-05 cuenta de despliegue y proveedor WIF | PASA, parcial | `roles/run.admin` en el proyecto y condición `assertion.repository == 'sebastianrodriguez1115/boticario-ai'`; la escritura en Artifact Registry y `serviceAccountUser` no se volvieron a consultar (sin cambios en este cambio) |
| DEP-06 versiones del secreto | PASA | solo la versión 1 `enabled`; 2 elementos de 64 hex (`secret-shape.txt`, solo conteos) |
| DEP-07 workflow | PASA | `actionlint` sin hallazgos (imagen `rhysd/actionlint`, `evidence/cloud/actionlint.txt`); 6 acciones fijadas por SHA con comentario de versión; `contents: read` y `id-token: write` solo en `deploy`; `verify` antes de `deploy` (`needs`); `concurrency` con `cancel-in-progress: false`; `--set-secrets=API_TOKENS=boticario-api-tokens:1`; `API_VERIFY_TOKEN` solo por `secrets` |
| DEP-08 historial | PASA | ejecución 39176876327, intento 2: `GET /health -> 200`, `GET /v1/plants/lavandula-angustifolia -> 200`, «(sin token) -> 401»; 0 apariciones de los tokens en 2432 líneas (`gh-verify-lines.txt`, `gh-run-token-counts.txt`). El intento 1 falló en la construcción por un error externo de figshare, no en `verify` |
| DEP-09 verificación posterior simulada | PASA | `verify-step-sim.txt`: (a) token de CI contra Cloud Run, éxito; (b) token obsoleto, fallo con `curl: (56) … 401` y sin el valor; (c) servicio abierto simulado, fallo con «respondio 200 sin token»; (d) sin `API_VERIFY_TOKEN`, fallo con el mensaje claro; (e) token local contra el contenedor local, éxito |
| DEP-10 disparadores y filtros | PASA (inspección) | `on:` y `paths` coinciden con la spec; los commits `957f79f`, `1507633` y `1fa8269` solo tocan `openspec/` y no coinciden con ningún filtro, pero los dos primeros viajaron en un `push` con cambios del backend y no hay ejecución aislada para comprobarlo en vivo. No se provocó una ejecución |
| DEP-11 arranque en frío | CUBIERTO por la medición anterior (decisión del usuario) | no se ejecutó en este cambio; el usuario decidió no volver a medir y usar la medición del cambio archivado (2,577 s y 2,520 s), porque este cambio solo añade leer `API_TOKENS` al arrancar; véase «Desvíos» |

### Documentación (DOC)

| Caso | Estado | Notas |
| --- | --- | --- |
| DOC-01 preparación y secreto (paso 7) | PASA (re-verificado; antes FALLA, DEF-01) | La guía avisa de añadir `SECRET_NAME` y el bloque tiene la guarda `: "${SECRET_NAME:?…}"`: con la variable sin definir o vacía falla con su mensaje (código 1, en bash y en zsh); con la variable definida pasa. El bloque que escribe `app/dart_defines.local.json` funcionó (URL y token de 64 caracteres, permisos `-rw-------`) y el archivo se borró. Evidencia: `evidence/reverify/def01-guard.txt` |
| DOC-02 rotación | PASA (re-verificado; antes con DEF-02) | La rotación del token de la app es coherente y la nueva subsección «Rotar el token de CI» se puede seguir tal cual: sus 5 bloques, ejecutados en orden contra un doble de `gcloud` y `gh` con tokens ficticios, producen la versión 2 `<app>,<ci-nuevo>,<ci-viejo>`, actualizan `API_VERIFY_TOKEN`, producen la versión 3 `<app>,<ci-nuevo>` y desactivan las versiones 1 y 2. Evidencia: `evidence/reverify/def02-ci-rotation-sim.txt` |
| DOC-03 rollback, desmontaje y README | PASA (re-verificado; antes con DEF-03) | El desmontaje incluye el secreto y `gh secret delete API_VERIFY_TOKEN`; el README enlaza a la guía; «Revisiones y rollback» ahora avisa de las revisiones 00001 a 00006 y de las versiones desactivadas, y su comando `gcloud run revisions describe` funciona: la 00007 muestra `secretKeyRef` con `key '1'` y las 00006 y 00001 muestran `null`. Evidencia: `evidence/reverify/def03-rollback-commands.txt` |
| DOC-04 una línea por párrafo | PASA | `check-md-lines.py` sobre este informe y el plan: 0 hallazgos (repetido tras la actualización) |

Comandos del README ejecutados: `docker compose up` con el valor desde un archivo de entorno (`--env-file`, archivo de prueba fuera del repositorio, porque no se debía crear `.env`), `TOKEN=$(sed -n 's/^API_TOKENS=//p' .env | cut -d, -f1)` y las consultas con y sin token (`evidence/readme-env-flow.txt`): 200, 200 y 401. El `echo "API_TOKENS=$(openssl rand -hex 32)" > .env` literal no se ejecutó en la raíz.

#### Revisión del procedimiento de rotación de `docs/deploy/cloud-run.md` (ROT-06), sin ejecutarlo en GCP

Primera revisión: la rotación del token de la app se podía seguir tal cual; la del token de CI estaba incompleta (DEF-02). Segunda revisión, tras la corrección:

- La guía aclara que los números de versión (2 y 3) son de ejemplo, partiendo de que el secreto solo tiene la versión 1, y que el número real es el que imprime `gcloud secrets versions add` o el que muestra `gcloud secrets versions list`.
- «Rotar el token de CI» tiene su precondición (la versión actual es exactamente `<token-app>,<token-ci-viejo>`), genera `TOKEN_CI_NEW` y construye la versión con el orden correcto. La simulación con tokens ficticios confirma el resultado de cada paso (`evidence/reverify/def02-ci-rotation-sim.txt`).
- El paso 3 del token de CI explica que la verificación del workflow todavía usa el token viejo, que sigue siendo válido en esa versión; la lógica es correcta porque la versión 2 conserva ambos.
- La ambigüedad de redacción OBS-07 (la frase sobre el paso 4 tras filtrarse un token) quedó corregida en `af67029` y verificada: ahora hay una subsección «Si un token se filtra» que distingue el token de la app y el de CI.
- La simulación no prueba los despliegues entre pasos (`push` y workflow) ni los efectos reales en Cloud Run: eso no se ejecutó en GCP.

### Costo y límites (9.5)

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| COS-01 consumo de Cloud Run | PASA | `monitoring-24h.txt`: 232 peticiones en 24 h (sobre 2 millones al mes de la capa gratuita), 45,7 vCPU-s de CPU asignada (de 180 000) y 6,4 GiB-s de memoria (de 360 000); `monitoring-3h.txt`: 156 peticiones desde el inicio de la QA, de las cuales 80 fueron 401, 56 fueron 200, 14 fueron 404, 5 fueron 405 y 1 fue 400 |
| COS-02 accesos a Secret Manager | PASA, estimado | no existe ninguna métrica de accesos ni los registros `DATA_READ` están habilitados (`secretmanager-metrics.txt`); Cloud Run lee el secreto una vez por arranque de instancia y la revisión 00007 inició 1 instancia en 24 h, así que el consumo es de unos pocos accesos al mes sobre 10 000. Hay 1 versión activa (límite gratuito: 6) |
| COS-03 los 401 llegaron al contenedor | PASA | `logging-status-counts.txt` y `logging-401-sample.txt`: 80 entradas de `run.googleapis.com/requests` con `httpRequest.status=401` y `revision_name=boticario-api-00007-fgc`, con latencia de 1 ms y `responseSize` 247 (cuerpo `problem+json` de 129 bytes más cabeceras); 0 entradas 403 en el servicio. Un rechazo de IAM sería un 403 de Google sin pasar por la revisión. Entrada de ejemplo en `logging-401-entry.json`. El servicio es público a nivel de IAM (`allUsers` con `roles/run.invoker`) |
| COS-04 los logs no contienen tokens | PASA, con una salvedad | `logging-token-counts.txt`: 160 entradas de la revisión 00007, 0 apariciones de `<token-ci>` y 1 de `<token-app>`, que es la URL de una petición de AUT-19 (véase OBS-05). Las cabeceras no se registran |

## Defectos

No hay defectos de comportamiento del backend, del contenedor, del despliegue ni de la app, y ninguna spec delta se contradice en su comportamiento. Los cuatro defectos de documentación y uso de la primera ejecución (todos de severidad baja) están corregidos y re-verificados.

| ID | Severidad | Resumen | Estado | Evidencia de la re-verificación |
| --- | --- | --- | --- | --- |
| DEF-01 | Baja | La guía no decía que quien ya tiene `.env.cloud-run` debe añadir `SECRET_NAME`; sin ella los comandos fallaban con `Failed to find attribute [secret]` (afectaba a «Preparación documentada») | Corregido y re-verificado | El paso 7 avisa y añade la guarda. La guarda falla con su mensaje con la variable sin definir o vacía (bash y zsh) y pasa con la variable definida; el bloque que lee el token de la app escribió `app/dart_defines.local.json` correctamente y se borró (`evidence/reverify/def01-guard.txt`). No ejecuté el `gcloud services enable` del mismo bloque, porque es una escritura. El `.env.cloud-run` del usuario sigue sin la línea: lo probé con una copia temporal a la que añadí `SECRET_NAME`, ya borrada |
| DEF-02 | Baja | La rotación del token de CI era ambigua y los números de versión estaban fijos (afectaba a «Rotación documentada») | Corregido y re-verificado | Subsección «Rotar el token de CI» con 6 pasos y aclaración de que los números son de ejemplo. Los 5 bloques de código se ejecutaron en orden contra dobles de `gcloud` y `gh` con tokens ficticios y dieron las versiones y el secreto de GitHub esperados (`evidence/reverify/def02-ci-rotation-sim.txt`). OBS-07 (frase sobre el paso 4 al filtrarse un token) quedó corregida en `af67029` |
| DEF-03 | Baja | «Revisiones y rollback» no avisaba de que las revisiones 00001 a 00006 no tienen autorización | Corregido y re-verificado | La sección tiene el aviso sobre las revisiones anteriores a `boticario-api-00007-fgc` y sobre las versiones desactivadas, con los comandos para comprobarlo. `gcloud run revisions describe` (solo lectura) funciona: 00007 `secretKeyRef`, 00006 y 00001 `null`, que es lo que el texto describe como «sin `API_TOKENS` en `env`» (`evidence/reverify/def03-rollback-commands.txt`). No se ejecutó ningún rollback |
| DEF-04 | Baja | `docker compose down`, `ps` y `logs` fallan sin `API_TOKENS` | Corregido en la documentación y re-verificado; el comportamiento sigue igual a propósito | `README.md` y `backend/README.md` tienen los párrafos nuevos. Repetí la prueba con tokens de prueba en variables de shell y sin `.env`: con la variable fuera del entorno `ps`, `logs` y `down` fallan con «required variable API_TOKENS is missing a value» y el contenedor sigue en marcha; `API_TOKENS=x docker compose down` lo detiene y no queda ningún contenedor ni red (`evidence/reverify/def04-compose.txt`). Lo que dicen los párrafos coincide con lo observado |

## Observaciones

- OBS-01. Cabeceras `Authorization` límite: la API usa la primera cabecera si hay varias (válida y luego inválida responde 200), tolera varios espacios entre `Bearer` y el token y un espacio final, y rechaza el tabulador. Ninguna permite acceder sin un token válido y la spec no las define. Sin cambios necesarios; un proxy delante que eligiera la última cabecera sería el único riesgo, y hoy no hay ninguno.
- OBS-02. El cuerpo del 401 incluye `instance` con el camino pedido (sin la query), con el mismo contenido para todos los rechazos del mismo camino. La spec exige el mismo cuerpo que el caso de cabecera ausente en la misma petición, y se cumple.
- OBS-03. Con un token de verificación obsoleto, el paso del workflow falla con el error crudo `curl: (56) … 401` tras 5 reintentos de 3 s, sin una línea `::error::` que sugiera actualizar `API_VERIFY_TOKEN`. Cumple la spec; el mensaje podría ser más claro.
- OBS-04. En el log de GitHub Actions, el eco del comando `printf 'Authorization: Bearer %s\n'` aparece como `printf 'Authorization: ***'`: GitHub enmascara más texto que el token. Cosmético.
- OBS-05. Incidente de la QA: Cloud Run registra la URL completa, con la query, en sus logs de petición. Mi primera ejecución de AUT-19 contra Cloud Run envió `?token=<token-app>` con el token real, así que una vez ese valor quedó en una entrada de `run.googleapis.com/requests` de la revisión 00007 (UTC 2026-10-18 23:49:58, visible solo para quien lea los logs del proyecto, retención por defecto de 30 días; no se puede borrar sin una escritura en Logging). No es un defecto del producto: confirma la decisión D1 de no aceptar el token en la query. Corregí el script para que contra Cloud Run use un token incorrecto en la query y repetí la ejecución. Decisión del usuario, 2026-10-18: acepta el riesgo y no se rota el token. Motivos: la entrada solo la ve quien puede leer los logs del proyecto (hoy, solo el propietario) y la retención por defecto es de 30 días; el mismo token va en texto claro dentro del APK (`libapp.so`, confirmado por APP-15), así que el log no aumenta mucho la exposición; la rotación queda documentada para cuando haga falta. El orquestador verificó, contando apariciones sin mostrar valores, que hay exactamente 1 entrada de log con el token de la app y 0 con el de CI (coincide con `evidence/cloud/logging-token-counts.txt`). Estado: decidido, sin acción pendiente.
- OBS-06. El emulador Android se cayó dos veces durante la QA (`device offline` y `Can't find service: package`); no tiene relación con el cambio. Se relanzó y las pruebas afectadas se repitieron. Las capturas y los resultados citados son de las ejecuciones completas.
- OBS-07. Observación de la re-verificación, sin severidad de defecto. Estado: corregida en `af67029` y verificada. Problema original: en `docs/deploy/cloud-run.md`, la frase «Si un token se filtra, haz el paso 4 de inmediato» quedó tras la subsección «Rotar el token de CI», donde el paso 4 es otro. Verificación del texto actual: la frase es ahora la subsección propia «Si un token se filtra», después de las dos rotaciones y antes de «Qué sigue», y distingue los dos tokens: para el de la app, los pasos 1 a 4 de su rotación seguidos, con la lista de lo que hace cada uno (generar, crear la versión de transición, desplegar, compilar la app y, sin esperar, crear la versión final sin el viejo, fijarla, desplegar y desactivar las anteriores); para el de CI, los pasos 1 a 6 de «Rotar el token de CI» sin esperar. Ya no hay ninguna referencia ambigua a «el paso 4» (`grep` de la frase antigua: 0 coincidencias).

## Limitaciones del cambio, confirmadas por la QA

- El token se puede extraer del APK: APP-15 lo encontró en texto claro en `libapp.so` del APK `release`. Autoriza a la app, no a una persona; rotarlo y revocarlo es barato, y la revocación deja sin servicio a las apps instaladas.
- Los 401 se facturan: llegan al contenedor (COS-03: revisión 00007, latencia de 1 ms) y cuentan como peticiones de Cloud Run. Cada 401 de esta QA consumió una petición de la capa gratuita de 2 millones. `max-instances=2` y la alerta de presupuesto acotan el gasto.
- No hay protección de borde: sin límite de tasa, Cloud Armor ni App Check, un volumen alto de peticiones con o sin token llega a la API. El servicio es público a nivel de IAM (`allUsers` con `roles/run.invoker`).
- La URL completa, incluida la query, va a los logs de Cloud Run: por eso el token solo se acepta por cabecera (OBS-05).
- La comparación se prueba como constante solo por la prueba unitaria y por una medición indicativa (AUT-28); la longitud del token puede filtrarse por temporización, como dice el diseño.

## Cobertura y riesgos residuales

No se verificó o no se pudo verificar:

- Arranque en frío (DEP-11): no re-medido en este cambio; cubierto por la medición del cambio archivado por decisión del usuario.
- Incidente del token en los logs (OBS-05): riesgo aceptado por el usuario; sin rotación.
- `.env` literal del README (`echo … > .env`): no se creó en la raíz por instrucción; se probó el mismo flujo con `--env-file`.
- Ejecución real de la rotación y del rollback en Cloud Run: sin escrituras en GCP; solo se revisó la guía, se probó la lógica de rotación del token de la app en local (contenedor) y la del token de CI contra dobles de `gcloud` y `gh` con tokens ficticios.
- Postman: sin sesión, no hay colección.
- Escenarios que solo cubren pruebas unitarias del proyecto y que no repetí: `Fallo interno`, `Configuración por defecto` (127.0.0.1:8080), `Debug` sin secretos, los de `catalog-client` de listado con parámetros, consulta vacía y larga, errores de red, tiempo agotado y 5xx, y `Documento desactualizado`. Tampoco se ejecutaron `cargo test`, `flutter test` ni `flutter analyze` completos.
- Sin conectividad en la app (`flutter-app-bootstrap`): sin cambios en este cambio.
- DEP-05: roles de escritura en Artifact Registry y `serviceAccountUser` no se consultaron de nuevo.
- Verificación en el teléfono físico: la aportó el usuario, sin capturas.
- Constancia de tiempo constante: indicativa, no concluyente.
- Estado del emulador: se apagó al terminar; la aplicación `com.example.boticario_ai` ya estaba instalada en él antes de la QA y sigue instalada con el último build de depuración.

## Comprobación final de tokens

Ejecutada al terminar, con `grep -rcF` sobre `qa/` (solo conteos, sin imprimir valores):

- Token de la app `<token-app>` y token de CI `<token-ci>` (leídos de la versión 1 del secreto): 0 apariciones cada uno.
- Tokens locales `<token-local-1>`, `<token-local-2>` y `<token-local-3>`: 0 apariciones cada uno.
- Token aleatorio de la variante V5 de la app (Cloud Run, token incorrecto): 0 apariciones.
- `grep -rEn '[0-9a-f]{32,}' qa/`: todas las coincidencias son valores que no son tokens. Los 6 SHA de 40 caracteres de `evidence/cloud/workflow-uses.txt` son los SHA de las acciones fijadas del workflow. Los 3 de `evidence/cloud/service-describe.yaml` son el SHA del commit `f318165…` en la etiqueta de la imagen. Las 117 de `evidence/api/cloud/AUT-*.txt` son los identificadores de traza de la cabecera `x-cloud-trace-context` que añade Cloud Run a cada respuesta (0 coincidencias fuera de esa cabecera).
- `check-md-lines.py` sobre el plan y este informe: 0 hallazgos.
- Repetida al cerrar el informe, tras anotar las decisiones del usuario sobre OBS-05 y DEP-11: resultados en la salida final de esa ejecución (mismos conteos).
- Repetida tras la re-verificación de DEF-01 a DEF-04 (se añadió `evidence/reverify/`): 0 apariciones de los 5 tokens y del aleatorio de V5, 0 coincidencias hexadecimales nuevas (las de `evidence/reverify/` son 0) y 0 hallazgos de `check-md-lines.py`.

## Cómo re-ejecutar

Desde la raíz del repositorio, con tokens de prueba propios exportados (`TOKEN_LOCAL_1`, `TOKEN_LOCAL_2`, `TOKEN_LOCAL_3`, cada uno de `openssl rand -hex 32`) y, para Cloud Run, `TOKEN_APP` y `TOKEN_CI` leídos del secreto sin imprimirlos:

```bash
Q=openspec/changes/add-api-token-auth/qa/scripts
# API local (docker compose levantado con API_TOKENS="$TOKEN_LOCAL_1")
TARGET=local BASE_URL=http://localhost:8080 TOKEN=$TOKEN_LOCAL_1 python3 -I $Q/api_tests.py
BASE_URL=http://localhost:8080 TOKEN=$TOKEN_LOCAL_1 python3 -I $Q/timing.py
# API en Cloud Run
TARGET=cloud BASE_URL=https://boticario-api-d3xv5q3iaa-pv.a.run.app TOKEN=$TOKEN_APP TOKEN2=$TOKEN_CI python3 -I $Q/api_tests.py
# Contenedor, configuración y rotación (usan docker y recrean el servicio)
python3 -I $Q/container_tests.py
python3 -I $Q/rotation_test.py
# Despliegue, solo lectura, y verificación posterior simulada
bash $Q/gcp_readonly.sh
python3 -I $Q/verify_step_sim.py
# Consumo
python3 -I $Q/monitoring.py 24 request_count container/startup_latencies
# Proxy de registro y ayudas del emulador
python3 -I $Q/logging_proxy.py 8081 8080 <archivo-de-registro>
python3 -I $Q/adb_ui.py dump
python3 -I $Q/check-md-lines.py openspec/changes/add-api-token-auth/qa/*.md
```

Herramientas instaladas: ninguna. Se usaron `curl`, `python3`, Docker, `gcloud`, `gh`, `flutter`, `adb`, y la imagen `rhysd/actionlint` que ya estaba en Docker. Los comandos de la app (`flutter run`, `flutter test integration_test/app_test.dart`) son los del README.
