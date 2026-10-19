# Plan de pruebas: add-api-token-auth

Alcance: tareas 9.1 a 9.5 del cambio `add-api-token-auth` (QA de la autorización por token de API: backend, contenedor, despliegue en Cloud Run y app Flutter en Android). Resultados y evidencia: [`api-token-results.md`](api-token-results.md) y `evidence/`. Scripts: `scripts/`.

## Requerimiento

El usuario pidió: «solo quiero que haya una capa de autorización en el backend… un api token o algo similar», sin involucrar mucha infraestructura. La propuesta lo concreta así: la app envía un token en cada petición y la API rechaza con 401 las que no lo traen.

Decisiones del usuario que fijan el comportamiento esperado:

- El token es obligatorio siempre, también en local (U2).
- `/health` y `/openapi.json` son públicos (D2, U3).
- La API no tiene modo sin autorización.
- El token vive en Secret Manager con la versión fijada, no `latest` (U1).
- Hay un token de CI aparte, dentro de `API_TOKENS` (U5).
- Ante un 401 la app muestra el error con el reintento genérico, sin cambios de interfaz (U6).

## Criterios de aceptación

Cada escenario de las specs delta de `specs/` es un criterio. La tabla de trazabilidad del final los enumera todos con su capability y el caso que lo cubre.

## Entornos y restricciones

- Local: `docker compose` de la raíz (imagen reconstruida desde `main`, commit `f318165`) con tokens de prueba propios (`<token-local-1>`, `<token-local-2>`, `<token-local-3>`) generados con `openssl rand -hex 32`, que viven solo en el shell y en un archivo fuera del repositorio. Emulador Android `boticario_catalog_api36`. No se usa el teléfono físico.
- Cloud Run: `https://boticario-api-d3xv5q3iaa-pv.a.run.app`, revisión `boticario-api-00007-fgc`, proyecto `boticario-ai`. Los tokens reales (`<token-app>`, `<token-ci>`) se leen de la versión 1 del secreto `boticario-api-tokens` a variables de shell y no se imprimen.
- Sin escrituras en Google Cloud ni en GitHub: ninguna versión de secreto, cambio de IAM, despliegue, `push` ni `gh workflow run`. Solo lecturas de `gcloud`, `gh`, Logging y Monitoring.
- Ningún valor de token en archivos, evidencias, capturas, scripts ni informe. Los scripts leen los tokens de variables de entorno y las evidencias sustituyen cada valor por su marcador.
- La rotación (9.3) se ejecuta contra el contenedor local, no contra Cloud Run.
- Herramientas: `curl` y `python3` (el CLI de Postman 1.74 está instalado pero sin sesión iniciada, así que no hay colección), Docker Compose, `gcloud`, `gh`, `flutter`, `adb` y `uiautomator` en el emulador, e imagen `rhysd/actionlint` ya presente. No se instaló nada en el proyecto.

## Estrategia

- Caja negra sobre los escenarios de las cinco specs delta, más pruebas exploratorias de evasión y de bordes del encabezado.
- Particiones y valores límite del token: ausente, vacío, solo el esquema, válido, válido en otras mayúsculas, aleatorio de 64 hex, último carácter distinto, prefijos (63, 32 y 1 caracteres), válido más un carácter, longitud 16 KB, bytes no ASCII. Para la configuración: 0, 31, 32, 256 y 257 caracteres, `a,,b`, carácter no permitido, espacios y salto de línea final.
- Tabla de decisión ruta × credencial (cada celda es un caso de `AUT-12`, `AUT-14`, `AUT-15`, `AUT-16`, `AUT-23`):

| Ruta | Sin cabecera | Token incorrecto | Token válido |
| --- | --- | --- | --- |
| `GET /v1/plants` | 401 | 401 | 200 |
| `GET /v1/plants/{id}` existente | 401 | 401 | 200 |
| `GET /v1/plants/no-existe` | 401 | 401 | 404 |
| `GET /v1/no-existe`, `/v1`, `/v1/` | 401 | 401 | 404 |
| `POST/PUT/PATCH/DELETE /v1/plants` | 401 | 401 | 405 |
| `HEAD`, `OPTIONS /v1/plants` | 401 | 401 | HEAD 200, OPTIONS 405 |
| `GET /v1/plants?limit=abc` | 401 | 401 | 400 |
| `GET /health` | 200 | 200 | 200 |
| `GET /openapi.json` | 200 | 200 | 200 |
| Evasiones (`/V1/...`, `//v1/...`, `/x/../v1/...`, codificación porcentual) | 401 o 404, nunca datos | idem | 404 o datos solo si el camino es realmente `/v1` |

- Transición de estados para la rotación: A = `{viejo}`, B = `{nuevo, viejo}` (ambos aceptan), C = `{nuevo}` (el viejo da 401), D = `{nuevo2, nuevo}` (segunda rotación). Se recorre A → B → C → D en el contenedor local, reiniciando el contenedor entre estados, y se repite la misma matriz de peticiones en cada estado.
- Prioridad por riesgo: (1) que ninguna ruta de datos responda sin token válido, en local y en Cloud Run; (2) que ningún token se filtre a respuestas, logs, imagen, pantalla, `logcat` o artefactos; (3) que la app siga estable ante el 401; (4) que no se pueda arrancar abierto; (5) rotación y documentación operativa; (6) costo y límites.
- Pirámide: no se repiten las pruebas unitarias ni de integración del backend (`auth.rs`, `config.rs`, `http.rs`, `tests/token_logs.rs`) ni las de la app (`catalog_repository_test.dart` y otras). Aquí se ejercita el contrato desde fuera, la imagen real, Cloud Run y los flujos de usuario en el emulador. Los escenarios que solo se pueden comprobar por prueba unitaria se marcan como tales en la trazabilidad.
- Funcionalidad nueva que se prueba de forma exploratoria con charters:
  - CH-1: intentar obtener datos de `/v1` sin token por rutas alternativas (mayúsculas, codificación, doble barra, métodos, cabeceras duplicadas).
  - CH-2: intentar que un token aparezca en cualquier salida (respuestas, `instance` del problema, logs `trace`, `logcat`, pantalla, APK de depuración).
  - CH-3: la app con el token rotado en mitad de la sesión (detalle con 401 tras un listado correcto).

## Casos de API (9.2)

Técnicas: EP partición de equivalencia, VL valor límite, TD tabla de decisión, EXP exploratoria, INS inspección. Se ejecutan con `scripts/api_tests.py` contra el contenedor local (L) y contra Cloud Run (C). Resultado esperado = lo que exige el escenario citado.

| ID | Caso | Técnica | Pasos | Esperado | Env |
| --- | --- | --- | --- | --- | --- |
| AUT-01 | Token válido en el listado | EP | `GET /v1/plants?limit=2` con `Bearer <token>` | 200, `application/json`, `items` con 2 elementos | L, C |
| AUT-02 | Token válido en el detalle | EP | `GET /v1/plants/lavandula-angustifolia` con token | 200 con el detalle | L, C |
| AUT-03 | Esquema en otras mayúsculas | EP | `bearer`, `BEARER`, `BeArEr` con el token válido | 200 en los tres | L, C |
| AUT-04 | Cabecera ausente | EP | `GET /v1/plants` sin `Authorization` | 401, `application/problem+json`, `WWW-Authenticate: Bearer`, sin datos | L, C |
| AUT-05 | Token incorrecto | EP | Token aleatorio de 64 hex | 401 con el mismo cuerpo y cabeceras que AUT-04 | L, C |
| AUT-06 | Último carácter distinto | VL | Token válido con el último carácter cambiado | 401 idéntico a AUT-04 | L, C |
| AUT-07 | Prefijos del token válido | VL | Primeros 63, 32 y 1 caracteres | 401 idéntico a AUT-04 | L, C |
| AUT-08 | Token válido más un carácter, otras mayúsculas | VL | Token + `x`; token en mayúsculas | 401 idéntico | L, C |
| AUT-09 | Esquema distinto | EP | `Basic <base64>`, token sin esquema, `Token <token>` | 401 idéntico | L, C |
| AUT-10 | Cabecera degenerada | VL | `Authorization:` vacía, `Bearer`, `Bearer ` sin token | 401 idéntico | L, C |
| AUT-11 | Ruta inexistente | TD | `GET /v1/no-existe` sin token y con token | 401 sin token; 404 `problem+json` con token | L, C |
| AUT-12 | Raíz del prefijo | TD | `GET /v1` y `/v1/` sin token y con token | 401 sin token; 404 con token | L, C |
| AUT-13 | Escrituras sin token | TD | `POST`, `PUT`, `PATCH`, `DELETE /v1/plants` sin token | 401, no 405, sin modificar nada | L, C |
| AUT-14 | Escrituras con token | TD | Los mismos métodos con token | 405 `application/problem+json` | L, C |
| AUT-15 | `HEAD` y `OPTIONS` | TD | Sin token y con token | 401 sin token; `HEAD` 200 con token | L, C |
| AUT-16 | Rutas públicas | TD | `/health` y `/openapi.json` sin token, con token y con token incorrecto | 200 en todos, mismo cuerpo de `/health` con y sin token | L, C |
| AUT-17 | Cuerpo y cabeceras idénticos entre rechazos | EP | Comparar byte a byte cuerpo y cabeceras (sin `date`) de AUT-04 a AUT-10 en la misma ruta | Un único cuerpo y un único conjunto de cabeceras | L, C |
| AUT-18 | Ninguna respuesta refleja el token | EXP | Buscar el token válido, el incorrecto y los prefijos en cuerpo y cabeceras de todas las respuestas del script | 0 apariciones | L, C |
| AUT-19 | Token por canales no admitidos | EXP | `?token=<token>`, `X-Api-Key`, `Proxy-Authorization` con el token válido | 401; `instance` no incluye la query | L, C |
| AUT-20 | Cabeceras `Authorization` duplicadas | EXP | Válida y luego inválida; inválida y luego válida | Se registra el comportamiento; ningún dato con la inválida sola | L, C |
| AUT-21 | Separadores entre esquema y token | VL | Dos espacios; tabulador | Se registra el comportamiento | L, C |
| AUT-22 | Cabecera no ASCII y cabecera enorme | VL | `Authorization` con bytes no ASCII; valor de 16 KB | Nunca 200 ni 5xx; 401 o rechazo del frontal | L, C |
| AUT-23 | Evasión de ruta (CH-1) | EXP | `/V1/plants`, `//v1/plants`, `/x/../v1/plants` con `--path-as-is`, `/%76%31/plants`, `/v1%2Fplants`, `/v1/plants/`, `/v1x`, `/v1;a/plants` sin token | Nunca datos del catálogo (401 o 404) | L, C |
| AUT-24 | Errores del contrato con token | EP | `limit=abc`, `/v1/plants/no-existe`, y `limit=abc` sin token | 400 y 404 `problem+json`; 401 sin token (la autorización precede) | L, C |
| AUT-25 | Documento OpenAPI | INS | `GET /openapi.json`: esquema Bearer, seguridad en `/v1`, ninguna en `/health` ni `/openapi.json`, respuesta 401 `problem+json`, rutas solo `/health`, `/openapi.json` y `/v1/*`, sin token; comparar con `backend/openapi.json` | Coincide con lo que exige la spec y con el archivo versionado | L, C |
| AUT-26 | Consistencia | EXP | 20 peticiones alternando válida e inválida | Las válidas siempre 200 y las inválidas siempre 401 | L, C |
| AUT-27 | La cabecera llega intacta a la API en Cloud Run | INS | Token válido de la app y de CI → 200 (solo es posible si `Authorization` llega byte a byte); el 401 lleva el cuerpo de la API, no el de Google | 200 con ambos; cuerpo `problem+json` de la API | C |
| AUT-28 | Tiempo según la posición de diferencia (indicativo) | EXP | 3000 peticiones por variante con una conexión persistente: primer carácter distinto frente a último distinto | Sin diferencia sistemática medible; no es prueba de tiempo constante | L |

## Casos de configuración y contenedor (9.2)

| ID | Caso | Técnica | Pasos | Esperado | Escenario |
| --- | --- | --- | --- | --- | --- |
| CFG-01 | Variable ausente | EP | `docker run` de la imagen sin `API_TOKENS` | Código 2; mensaje que nombra `API_TOKENS`; no sirve ninguna ruta | Variable ausente o vacía |
| CFG-02 | Vacía y solo espacios | EP | `API_TOKENS=""` y `"   "` | Código 2 con el mismo mensaje | Variable ausente o vacía |
| CFG-03 | 31 y 257 caracteres | VL | Un token de 31 y otro de 257 | Código 2; el mensaje indica el límite y no contiene el valor | Token demasiado corto |
| CFG-04 | 32 y 256 caracteres | VL | Un token de 32 y otro de 256 | Arranca y acepta el token | Un token válido |
| CFG-05 | Elemento vacío y carácter no permitido | EP | `<t>,,<t>`, `<t>,`, `,<t>`, token con `@`, con espacio interior, con `é` | Código 2 sin el valor | Elemento vacío o carácter no permitido |
| CFG-06 | Un token de 64 hex | EP | Arrancar con `<token-local-1>` | Arranca, acepta ese token y rechaza otro | Un token válido |
| CFG-07 | Dos tokens con espacios y salto de línea | EP | `<t1> , <t2>\n` y `<t1>,<t2>\r\n` | Acepta ambos | Varios tokens para rotar |
| CFG-08 | Ayuda y OpenAPI sin variable | EP | `--help` y `--openapi` sin `API_TOKENS` | Código 0 e imprime la ayuda o el documento | Ayuda y OpenAPI sin tokens |
| CFG-09 | Los mensajes de error no contienen el valor | EXP | Revisar la salida de CFG-01 a CFG-05 | 0 apariciones del valor | Varios |
| CON-01 | Compose sin `API_TOKENS` | EP | `docker compose up` con `API_TOKENS` fuera del entorno y sin `.env` | Falla antes de crear el contenedor con un mensaje que nombra `API_TOKENS`; no queda contenedor | Sin token configurado |
| CON-02 | Salud, 401 y 200 con compose | EP | `docker compose up -d` con `<token-local-1>`; `/health`, `/v1/plants` sin y con token | 200, 401, 200 | Salud y datos; Consulta sin token |
| CON-03 | Búsqueda real | EP | `/v1/plants?q=lavand` y `/v1/plants/lavandula-angustifolia` con token | 200 con datos reales del catálogo | Búsqueda real |
| CON-04 | Otro puerto | EP | `PORT=9090` | `/health` 200 en 9090 y 8080 no publicado | Otro puerto |
| CON-05 | Otro nivel de logs | EP | `RUST_LOG=warn` y valor por defecto | Con `warn` no aparece «escuchando»; por defecto sí | Otro nivel de logs |
| CON-06 | Tokens por entorno | EP | Contenedor con dos tokens | Cualquiera de los dos 200; otro valor 401 | Tokens por entorno |
| CON-07 | Imagen sin tokens | INS | `docker image inspect`, `docker history --no-trunc` y el sistema de archivos exportado | `API_TOKENS` sin valor por defecto; 0 apariciones de los tokens locales | Sin tokens en la imagen |
| CON-08 | Contenido mínimo | INS | Listar el sistema de archivos exportado | Sin base cruda, ZIP, `cargo`, `rustc` ni código fuente; con el binario y la base | Contenido mínimo |
| CON-09 | Servir sin red | INS | API en una red Docker interna (`--internal`, sin salida) y consulta desde un contenedor `alpine` de esa red | 200 con token en el detalle; 401 sin él | Servir sin red |
| CON-10 | Logs a nivel `trace` | EXP (CH-2) | `RUST_LOG=trace`, peticiones con token válido, inválido y sin token; contar apariciones en `docker logs` | 0 apariciones de cualquier token | El token no se registra |

## Casos de rotación (9.3)

| ID | Caso | Técnica | Pasos | Esperado |
| --- | --- | --- | --- | --- |
| ROT-01 | Estado A (solo el viejo) | TE | `API_TOKENS=<token-local-1>`; matriz: `<token-local-1>`, `<token-local-2>`, sin token | 200, 401, 401 |
| ROT-02 | A → B (ambos) | TE | Recrear el contenedor con `<token-local-2>,<token-local-1>`; misma matriz | 200, 200, 401 |
| ROT-03 | B → C (retirar el viejo) | TE | Recrear solo con `<token-local-2>`; misma matriz | 401 con `<token-local-1>`, 200 con `<token-local-2>` |
| ROT-04 | C → D (segunda rotación, orden y posición) | TE | `<token-local-3>,<token-local-2>`; luego pasar `<token-local-2>` en primera y última posición con tres tokens | Todos los presentes aceptan, el retirado no |
| ROT-05 | Recreación con el mismo comando que el procedimiento | INS | Comprobar que `docker compose up -d` con otro `API_TOKENS` recrea el contenedor sin reconstruir | El contenedor nuevo toma el valor nuevo |
| ROT-06 | Procedimiento documentado de Cloud Run | INS | Leer `docs/deploy/cloud-run.md` («Rotación del token», pasos 1 a 4 y rotación del token de CI) sin ejecutar nada en GCP; comprobar la sintaxis de los comandos de lectura | Cada paso se puede seguir tal cual; se anota lo ambiguo |

## Casos de la app en el emulador (9.4)

La app se compila con `--dart-define` de `API_BASE_URL` y `API_TOKEN`. El backend local es `http://10.0.2.2:8080` desde el emulador. Las capturas se guardan en `evidence/app/` y el `logcat` filtrado en `evidence/app/`.

| ID | Caso | Técnica | Pasos | Esperado |
| --- | --- | --- | --- | --- |
| APP-01 | Recorrido normal con backend local | EP | `flutter run` con `API_TOKEN=<token-local-1>`; Inicio → Explorar → buscar `lavandula` → abrir el pasaporte → volver | Lista y pasaporte con datos; sin error |
| APP-02 | Recorrido normal con Cloud Run | EP | Compilación `release` con la URL de Cloud Run y `<token-app>` desde `app/dart_defines.local.json` (paso 7 de la guía); mismo recorrido | Lista y pasaporte con datos |
| APP-03 | Token incorrecto, local | EP | Backend con `<token-local-1>`; app con `<token-local-2>` | Explorar muestra el error de «no autorizada» con el botón Reintentar; sin cierre inesperado |
| APP-04 | Sin token, local | EP | App sin `API_TOKEN` | El mismo error y la misma interfaz que APP-03 |
| APP-05 | Token incorrecto, Cloud Run | EP | App con un token aleatorio y la URL de Cloud Run | El mismo error |
| APP-06 | Sin token, Cloud Run | EP | App sin `API_TOKEN` y con la URL de Cloud Run | El mismo error |
| APP-07 | Detalle con 401 tras un listado correcto (CH-3) | EXP | Backend con `<token-local-2>,<token-local-1>`; app con `<token-local-1>`; abrir Explorar; recrear el backend solo con `<token-local-2>`; abrir una planta | El pasaporte muestra «no autorizada», no «planta no encontrada», sin cierre inesperado |
| APP-08 | Reintentar y ausencia de reintentos automáticos | EP | En APP-03 contar peticiones en el log del backend; esperar 30 s; pulsar Reintentar | Sin peticiones adicionales mientras no se pulsa; una más por pulsación; el error persiste |
| APP-09 | Inicio y P06 tras el 401 | EP | Tras APP-03, volver a Inicio y abrir P06 | Siguen funcionando; no se pide inicio de sesión |
| APP-10 | Token fuera de pantalla y de `logcat` | EXP (CH-2) | Revisar capturas y `adb logcat` de APP-01 a APP-07 | 0 apariciones de cualquier token en `logcat`; las capturas no lo muestran |
| APP-11 | Smoke contra el backend local | EP | `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_TOKEN=<token-local-1>` | El smoke pasa |
| APP-12 | Smoke contra Cloud Run | EP | El mismo con `API_BASE_URL` de Cloud Run y `<token-app>` | El smoke pasa |
| APP-13 | Smoke sin el define | EP | El mismo sin `API_TOKEN`, contra un backend real | Falla enseguida con el mensaje claro del define faltante, sin esperar al tiempo de espera de la red |
| APP-14 | Peticiones de la app | INS | Contar en el log del backend las peticiones de APP-01 por ruta | Solo `GET /v1/plants` y `GET /v1/plants/{id}`; ninguna en Inicio ni P06 |
| APP-15 | El token se puede extraer del APK (limitación) | INS | Buscar el token de prueba en el APK compilado con `grep -c` | Se encuentra: demuestra la limitación declarada |
| APP-16 | Token fuera del repositorio | INS | `git grep -F` con cada token real y local; `grep -rn API_TOKEN app/ --include=*.dart` | 0 apariciones de tokens reales; solo valores ficticios marcados |

## Casos de despliegue (Cloud Run, solo lectura)

| ID | Caso | Técnica | Pasos | Esperado | Escenario |
| --- | --- | --- | --- | --- | --- |
| DEP-01 | Configuración del servicio | INS | `gcloud run services describe` | `min-instances` 0, `max-instances` 2, CPU solo durante la petición, 1 vCPU, 256 MiB, sonda `/health`, `allUsers` como invocador | Escala a cero; Facturación; Recursos; Sonda; Acceso público |
| DEP-02 | `API_TOKENS` desde Secret Manager | INS | `describe` y comparar con los tokens reales | `secretKeyRef` con `key: "1"`; 0 apariciones de los valores en la descripción, en el workflow y en los logs de la revisión | Token desde Secret Manager |
| DEP-03 | Accesos HTTPS | TD | AUT-01, AUT-04, AUT-05, AUT-16, AUT-24 contra la URL pública, más `GET /v1/plants/no-existe` con token | 200, 401 con `WWW-Authenticate: Bearer`, 404 `problem+json` | Salud; Acceso público; sin token rechazado; Error del contrato |
| DEP-04 | IAM de la cuenta de ejecución y del secreto | INS | `get-iam-policy` del proyecto y del secreto; lista de secretos | La cuenta de ejecución sin roles en el proyecto y con `secretAccessor` solo en este secreto; sin otras identidades con acceso al valor salvo el propietario | Cuenta de ejecución sin roles; Acceso solo a su secreto |
| DEP-05 | Roles de la cuenta de despliegue y proveedor WIF | INS | `get-iam-policy` y `describe` del proveedor | Sin cambios: Cloud Run admin, escritura en el repositorio y `serviceAccountUser`; condición del repositorio | Permisos mínimos de despliegue; Proveedor restringido |
| DEP-06 | Versiones del secreto | INS | `gcloud secrets versions list` | Solo la versión 1, `enabled`; formato de 2 elementos de 64 hex (conteo y longitud, sin valores) | Token desde Secret Manager |
| DEP-07 | Workflow | INS | Leer el YAML y ejecutar `actionlint` | Acciones fijadas por SHA con comentario, permisos `contents: read` e `id-token: write`, `verify` antes de `deploy`, `--set-secrets` con versión numérica, `API_VERIFY_TOKEN` solo por `secrets`, sin `latest` | Acciones fijadas; Cambio del backend; Verificaciones fallidas; Despliegues concurrentes |
| DEP-08 | Historial de ejecuciones | INS | `gh run list/view` de las ejecuciones del `push` `f318165`; contar apariciones de los tokens reales en el log | `verify` en verde, líneas 200, 200 y 401, 0 apariciones de los tokens | Verificación posterior satisfactoria |
| DEP-09 | Verificación posterior simulada | EXP | Extraer el paso «Verificar el servicio desplegado» y ejecutarlo en local con `bash`: (a) token de CI correcto contra Cloud Run; (b) token aleatorio (obsoleto); (c) servidor local que responde 200 a todo (servicio abierto); (d) sin `API_VERIFY_TOKEN` | (a) éxito; (b) fallo con 401 sin el valor en la salida; (c) fallo por 200 sin token; (d) fallo con el mensaje claro | Verificación fallida; Autorización inactiva; Token obsoleto |
| DEP-10 | Disparadores y filtros | INS | Leer `on:` y `paths`; `git show --stat` de los commits del rango | Coincide con la spec | Cambio ajeno al backend; Cambio del toolchain; Ejecución manual |
| DEP-11 | Arranque en frío | TE | No se re-mide en este cambio | Cubierto por la medición previa del cambio archivado (decisión del usuario); no se ejecuta aquí | Primera petición tras inactividad |
| DOC-01 | Preparación y secreto | INS | Seguir el paso 7 de `docs/deploy/cloud-run.md` en lo que es de solo lectura (`versions access`, escritura de `dart_defines.local.json`) | Se puede seguir tal cual | Preparación documentada |
| DOC-02 | Rotación | INS | ROT-06 | Pasos en orden: añadir el nuevo junto al viejo, desplegar, actualizar GitHub y la app, retirar | Rotación documentada |
| DOC-03 | Rollback, desmontaje y README | INS | Leer «Revisiones y rollback» y «Desmontaje»; enlaces del `README.md` | El desmontaje incluye el secreto; el rollback advierte de las versiones desactivadas; el README enlaza | Rollback; Desmontaje; README enlaza |
| DOC-04 | Una línea por párrafo | INS | `python3 -I scripts/check-md-lines.py` sobre el plan y el informe | 0 hallazgos | Regla de `AGENTS.md` |

## Casos de costo y límites (9.5)

| ID | Caso | Pasos | Esperado |
| --- | --- | --- | --- |
| COS-01 | Consumo de Cloud Run | Monitoring de solo lectura (`request_count` por código, CPU y memoria asignadas, tiempo de instancia facturable) desde el comienzo de la QA | Muy por debajo de la capa gratuita (2 millones de peticiones, 180 000 vCPU-s y 360 000 GiB-s al mes) |
| COS-02 | Accesos a Secret Manager | Métrica de accesos de Monitoring o registros de auditoría si están disponibles | Menos de 10 000 accesos al mes; una versión activa |
| COS-03 | Los 401 llegaron al contenedor | `gcloud logging read` de `run.googleapis.com/requests` de la revisión 00007 con `httpRequest.status=401` | Hay entradas 401 de la revisión `boticario-api-00007-fgc`; no son un rechazo de IAM (que daría 403 de Google y no pasaría por la revisión) |
| COS-04 | Los logs no contienen tokens | Contar apariciones de los tokens reales en las entradas de la revisión | 0 |

## Trazabilidad escenario → caso

Los casos marcados «unit» se cubren con pruebas del proyecto que esta QA no repite; se citan para que ningún escenario quede sin dueño. «Proceso» indica un escenario que no es comportamiento observable.

| Capability | Requisito | Escenario | Casos |
| --- | --- | --- | --- |
| `catalog-api` | API de solo lectura con autorización | Consulta con token | AUT-01, AUT-02, CON-02 |
| `catalog-api` | API de solo lectura con autorización | Consulta sin credenciales | AUT-04, AUT-11, CON-02 |
| `catalog-api` | API de solo lectura con autorización | Método de escritura | AUT-14 |
| `catalog-api` | Endpoint de salud | Servicio activo | AUT-16, CON-02 |
| `catalog-api` | Endpoint de salud | Salud sin token | AUT-16 |
| `catalog-api` | Errores estandarizados | Parámetro inválido | AUT-24 |
| `catalog-api` | Errores estandarizados | No autorizado | AUT-04, AUT-05, AUT-17 |
| `catalog-api` | Errores estandarizados | Recurso no encontrado | AUT-24 |
| `catalog-api` | Errores estandarizados | Método no permitido | AUT-14 |
| `catalog-api` | Errores estandarizados | Fallo interno | unit (no provocable desde fuera) |
| `catalog-api` | Documento OpenAPI | Documento al día | AUT-25 |
| `catalog-api` | Documento OpenAPI | Documento desactualizado | unit (test de deriva de la CI) |
| `catalog-api` | Documento OpenAPI | Seguridad documentada | AUT-25 |
| `catalog-api` | Arranque y configuración | Configuración por defecto | unit (`config.rs`); en contenedor CON-02 |
| `catalog-api` | Arranque y configuración | Base ausente, versión incompatible, base de solo lectura | Sin cambios en este cambio; no se repiten |
| `catalog-api` | Arranque y configuración | Tokens inválidos | CFG-01 a CFG-05, CFG-09 |
| `catalog-api` | Compatibilidad dentro de `/v1` | Campo nuevo, Cambio incompatible, Cambio incompatible sin consumidores | Proceso, sin cambios |
| `catalog-api` | Compatibilidad dentro de `/v1` | Cambio de política de acceso | DOC-03 (el cambio de OpenSpec lo registra: `proposal.md` y `design.md` D8) |
| `catalog-api` | Autorización por token de API en `/v1` | Token válido | AUT-01, AUT-02 |
| `catalog-api` | Autorización por token de API en `/v1` | Esquema en otras mayúsculas | AUT-03 |
| `catalog-api` | Autorización por token de API en `/v1` | Cabecera ausente | AUT-04 |
| `catalog-api` | Autorización por token de API en `/v1` | Token incorrecto | AUT-05 a AUT-08, AUT-17, AUT-28 |
| `catalog-api` | Autorización por token de API en `/v1` | Esquema distinto de Bearer | AUT-09, AUT-10 |
| `catalog-api` | Autorización por token de API en `/v1` | Ruta inexistente o método no permitido sin token | AUT-11, AUT-12, AUT-13, AUT-15, AUT-23 |
| `catalog-api` | Autorización por token de API en `/v1` | Rutas públicas | AUT-16 |
| `catalog-api` | Autorización por token de API en `/v1` | Ninguna ruta de datos fuera del prefijo | AUT-25 (y unit en la CI) |
| `catalog-api` | Autorización por token de API en `/v1` | El token no se registra | CON-10, AUT-18, COS-04 |
| `catalog-api` | Configuración de los tokens de API | Un token válido | CFG-04, CFG-06 |
| `catalog-api` | Configuración de los tokens de API | Varios tokens para rotar | CFG-07, ROT-02 |
| `catalog-api` | Configuración de los tokens de API | Variable ausente o vacía | CFG-01, CFG-02 |
| `catalog-api` | Configuración de los tokens de API | Token demasiado corto | CFG-03 |
| `catalog-api` | Configuración de los tokens de API | Elemento vacío o carácter no permitido | CFG-05 |
| `catalog-api` | Configuración de los tokens de API | Configuración sin secretos al depurar | unit (`Debug` de `ApiTokens`) |
| `catalog-api` | Configuración de los tokens de API | Ayuda y OpenAPI sin tokens | CFG-08 |
| `catalog-client` | Consumo de la API v1 | Listado con parámetros, Caracteres especiales, Consulta vacía, Consulta larga | unit (`catalog_repository_test.dart`); sin cambios de comportamiento |
| `catalog-client` | Consumo de la API v1 | Detalle por identificador | APP-01, APP-02, unit |
| `catalog-client` | Consumo de la API v1 | Token en cada petición | APP-01, APP-02, APP-14 (las respuestas 200 prueban la cabecera exacta), unit |
| `catalog-client` | Consumo de la API v1 | Sin otros endpoints, hosts ni datos de usuario | APP-14 |
| `catalog-client` | Errores de red y del servidor | Sin conexión, Tiempo agotado, Error del servidor, Parámetro inválido, Reintento | unit; sin cambios de comportamiento |
| `catalog-client` | Errores de red y del servidor | No autorizado | APP-03 a APP-08 |
| `catalog-client` | Errores de red y del servidor | Planta no encontrada | APP-07 (no se confunde con 401), unit |
| `catalog-client` | Token de API configurable | Token por compilación | APP-01, APP-02, APP-11, APP-12 |
| `catalog-client` | Token de API configurable | Compilación sin token | APP-04, APP-06, APP-13 |
| `catalog-client` | Token de API configurable | Token fuera del repositorio | APP-16, APP-15 |
| `flutter-app-bootstrap` | Funcionamiento local sin autenticación | Uso sin inicio de sesión | APP-01, APP-09 |
| `flutter-app-bootstrap` | Funcionamiento local sin autenticación | Funcionamiento sin conectividad | Sin cambios; no se repite |
| `flutter-app-bootstrap` | Funcionamiento local sin autenticación | Ausencia de solicitudes de negocio | APP-14 |
| `flutter-app-bootstrap` | Funcionamiento local sin autenticación | Solicitudes limitadas a la API del catálogo | APP-14 |
| `flutter-app-bootstrap` | Funcionamiento local sin autenticación | Token rechazado | APP-03, APP-09 |
| `backend-container` | Imagen autocontenida | Servir sin red | CON-09 |
| `backend-container` | Imagen autocontenida | Contenido mínimo | CON-08 |
| `backend-container` | Imagen autocontenida | Sin tokens en la imagen | CON-07 |
| `backend-container` | Arranque con un solo comando | Salud y datos | CON-02 |
| `backend-container` | Arranque con un solo comando | Búsqueda real | CON-03 |
| `backend-container` | Arranque con un solo comando | Sin token configurado | CON-01 |
| `backend-container` | Arranque con un solo comando | Consulta sin token | CON-02 |
| `backend-container` | Configuración por entorno | Otro puerto | CON-04 |
| `backend-container` | Configuración por entorno | Otro nivel de logs | CON-05 |
| `backend-container` | Configuración por entorno | Tokens por entorno | CON-06 |
| `backend-deployment` | Despliegue automático con verificación posterior | Cambio del backend en main | DEP-07, DEP-08 |
| `backend-deployment` | Despliegue automático con verificación posterior | Cambio ajeno al backend, Cambio del toolchain, Ejecución manual | DEP-10 |
| `backend-deployment` | Despliegue automático con verificación posterior | Verificaciones fallidas | DEP-07 (la ejecución 39176876327 intento 1 falló en la construcción, no en `verify`; no se provoca un fallo de `verify`) |
| `backend-deployment` | Despliegue automático con verificación posterior | Despliegues concurrentes | DEP-07 (`concurrency`) |
| `backend-deployment` | Despliegue automático con verificación posterior | Verificación posterior satisfactoria | DEP-08, DEP-09 (a) |
| `backend-deployment` | Despliegue automático con verificación posterior | Verificación posterior fallida | DEP-09 (d), (b) |
| `backend-deployment` | Despliegue automático con verificación posterior | Autorización inactiva | DEP-09 (c) |
| `backend-deployment` | Despliegue automático con verificación posterior | Token de verificación obsoleto | DEP-09 (b) |
| `backend-deployment` | Configuración del servicio en Cloud Run | Escala a cero y máximo, Facturación por petición, Recursos, Sonda de arranque | DEP-01 |
| `backend-deployment` | Configuración del servicio en Cloud Run | Token desde Secret Manager | DEP-02, DEP-06 |
| `backend-deployment` | Configuración del servicio en Cloud Run | Ruta de salud alcanzable desde fuera | DEP-03 |
| `backend-deployment` | Configuración del servicio en Cloud Run | Acceso público por HTTPS | DEP-03 |
| `backend-deployment` | Configuración del servicio en Cloud Run | Acceso por HTTPS sin token rechazado | DEP-03, AUT-27, COS-03 |
| `backend-deployment` | Configuración del servicio en Cloud Run | Error del contrato | DEP-03 |
| `backend-deployment` | Configuración del servicio en Cloud Run | Primera petición tras inactividad | DEP-11 (cubierto por la medición anterior, decisión del usuario) |
| `backend-deployment` | Identidad de despliegue sin claves | Sin claves almacenadas, Permisos mínimos de despliegue, Proveedor restringido, Acciones fijadas | DEP-05, DEP-07 |
| `backend-deployment` | Identidad de despliegue sin claves | Cuenta de ejecución sin roles | DEP-04 |
| `backend-deployment` | Identidad de despliegue sin claves | Acceso solo a su secreto | DEP-04 |
| `backend-deployment` | Documentación de preparación, operación, rollback y desmontaje | Preparación documentada | DOC-01 |
| `backend-deployment` | Documentación de preparación, operación, rollback y desmontaje | Rotación documentada | DOC-02, ROT-06 |
| `backend-deployment` | Documentación de preparación, operación, rollback y desmontaje | Rollback documentado, Desmontaje documentado, README enlaza | DOC-03 |

## Verificación de higiene de tokens

Al terminar: `grep -rcF` en `qa/` con cada token real (`<token-app>`, `<token-ci>`) y cada token local usado, y `grep -rEn '[0-9a-f]{32,}' qa/` con la explicación de cada coincidencia que no sea un token. El resultado queda en `api-token-results.md`.
