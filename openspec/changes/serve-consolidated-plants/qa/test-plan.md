# Plan de pruebas: serve-consolidated-plants (cambio 2)

Alcance: tareas 11.1 a 11.4 de `openspec/changes/serve-consolidated-plants/tasks.md`. El requerimiento es el propio cambio: `proposal.md`, `design.md` (D1 a D14, «Esquema real» y Risks) y los deltas de `specs/` de `catalog-api`, `catalog-client`, `explore-screen`, `plant-passport`, `catalog-seed` y `catalog-ingest`. Cada escenario de los deltas es un criterio de aceptación.

Rama `consolidate-catalog-seed`, commits del cambio 2 de `fa38fde` a `c8809f0` (diff `git diff 7e6cbfe..HEAD`). QA ejecutada el 2026-10-27 y 2026-10-28 (UTC).

## Entorno y restricciones

- API: servicio de `docker compose up --build -d` desde la raíz, con la base de la semilla completa construida por la propia imagen (2.354 plantas, 650 alias, 10 fuentes), en `http://127.0.0.1:8080` y, para el emulador, `http://10.0.2.2:8080`.
- Token: aleatorio (`openssl rand -hex 32`), pasado solo por la variable de entorno `API_TOKENS` y, a los scripts, por `QA_TOKEN`. En artefactos se escribe siempre `<token-app>`. No se leyó ni usó `.env.cloud-run`.
- Oráculo independiente: `data/build/catalog.db` (solo lectura, `sqlite3 -readonly`). Las comprobaciones de API comparan la respuesta con consultas SQL propias, no con el código del producto.
- App: emulador Android `boticario_catalog_api36` (`emulator-5554`, 1080x1920 a 480 dpi, es decir 360x640 dp, Android 16). No se usó el teléfono físico `R5CR70M9GEE`. Se compiló el APK de depuración con `--dart-define=API_TOKEN=...` y se guió con `adb` y `uiautomator`.
- Playwright no aplica: la app es nativa Android y no tiene destino web.
- Postman: el CLI `postman` 1.74 ejecuta colecciones locales sin sesión (la sesión solo hace falta para publicar resultados en la nube), con el token en un environment local con variable de tipo `secret` fuera de la carpeta de QA.
- No se modificó código del producto, specs, `design.md`, `tasks.md` ni `data/seed/`. No se instaló nada en el proyecto.
- Wikimedia: las imágenes reales se cargaron con moderación (unas pocas plantas); no se hizo ningún barrido.

## Estrategia

- Caja negra por particiones de equivalencia por tipo de planta (tabla siguiente), valores límite (consulta vacía, de 200 y de 201 caracteres, `limit` y `offset` en los extremos, `%` y `_`), tabla de decisión para `safety` (nivel alto, medio, bajo, sin nivel, sin datos) y para `image` (CC BY-SA, dominio público, sin imagen, falla la descarga, host no permitido) y transición de estados en el pasaporte (cambio de pestaña, regreso, texto al 200 %).
- Censo: el detalle de las 2.354 plantas se compara campo por campo con la base. Es más barato y más fuerte que un muestreo, porque la API es local y de solo lectura.
- Pirámide: no se repiten en la interfaz los escenarios que ya cubren las pruebas unitarias del producto (parser, política de imágenes, textos fijos); se ejecutan como regresión (APP-16, API-18, SED-03, ING-03) y la interfaz se centra en el flujo real contra el backend real.
- Pruebas exploratorias con charters (sección final) para lo que los casos guionados no cubren.

## Particiones por tipo de planta

| Tipo | Planta | Qué ejercita |
|---|---|---|
| Completa | `lavandula-angustifolia` | todos los campos, imagen de dominio público, 2 objetivos, nivel medio |
| Completa con CC BY-SA | `hypericum-perforatum`, `prunus-amygdalus`, `abelmoschus-manihot` | imagen con autor y licencia CC BY-SA |
| Pendiente de revisión | `hypericum-perforatum` | objetivo `relajacion-estres` omitido, nivel alto |
| Vacía | `angelica-laxiflora` | sin descripción, origen, aceite, grupos, objetivos, seguridad ni imagen |
| Tóxica (nivel alto) | `aconitum-napellus`, `ricinus-communis`, `abrus-precatorius` | aviso en `General`, `Precauciones` con nivel `Alto`, sin objetivos |
| Sin nivel | `eucalyptus-globulus` | `safety` con `level` nulo, `otros-objetivos` con subárea |
| Solo género | `lavandula-sp`, `aloe-spp`, `crataegus-sp`, `ephedra-spp`, `acinos-sp` | pocos o ningún dato, sin seguridad |
| Separada por colisión | `citrus-x-paradisi`, `brassica-oleracea-var-italica`, `foeniculum-vulgare-var-dulce` | identidad separada, textos de TPPT «no tóxica» |
| Con alias | `salvia-rosmarinus` (`rosmarinus-officinalis`), `matricaria-chamomilla` (`matricaria-recutita`), `mentha-x-piperita` | resolución de ID y búsqueda por alias |
| Sin imagen | `bergamota` (`citrus-x-bergamia`), `cinnamomum-burmanni`, `acinos-sp` | arte local, sin pie, `image` nulo |
| Sin nombre en español | `abutilon-theophrasti` (1.195 plantas) | `displayName` científico, `Velvetleaf` entre los comunes |
| Con citas sin resolver | `matricaria-chamomilla`, `ricinus-communis`, `alstonia-scholaris` | referencias con `resolved` falso |
| EMA fuera de USDA | `pelargonium-sidoides`, `rhodiola-rosea`, `tilia-cordata` | datos solo de la EMA |

## Casos

Los scripts están en `scripts/`; la evidencia, en `evidence/api/` y `evidence/app/`. Cada comprobación de `evidence/api/results.tsv` lleva el caso al que pertenece.

### API (tarea 11.2)

| ID | Técnica | Precondición | Pasos | Resultado esperado |
|---|---|---|---|---|
| API-01 | particiones, valores límite | API en marcha | `GET /v1/plants` por defecto y recorrido de las 24 páginas de 100 | 200, esquema `PageDto`, `total` 2.354, `displayName` en cada elemento, `displayName` igual a la semilla, comunes con el `displayName` primero y el resto por texto e idioma, sin comunes destacados si es científico, orden por nombre científico e id |
| API-02 | censo | ídem | `GET /v1/plants/{id}` de las 2.354 plantas | 200 y esquema `PlantDto`, campos siempre presentes, sin `reviewFlags`, sin códigos de flag, sin campos de fuente, sin `Content-Location` |
| API-03 | censo, oráculo | ídem | comparar `displayName`, `names` y `synonyms` con `plant_profile`, `plant_name` | científicos antes que comunes, `displayName` primero, sinónimos sin el aceptado y ordenados |
| API-04 | censo, oráculo | ídem | comparar `description`, `origin`, `oil`, `family`, `parts` con la base | iguales; `description` de hasta 400 caracteres |
| API-05 | censo, oráculo | ídem | comparar `useGroups` y `uses` con `plant_use_group` y `plant_use_group_ref` | solo grupos con `pending_review` en 0, orden por `count` y actividad, cita completa en `useGroups`, etiqueta en `uses`, sin resolver con `id` nulo y «(sin resolver)» |
| API-06 | censo, oráculo | ídem | comparar `goals` con `plant_goal` | sin objetivos pendientes (solo el de `hypericum-perforatum`), orden por nombre, subárea solo en `otros-objetivos` |
| API-07 | tabla de decisión | ídem | comparar `safety` con `plant_safety` | `null` solo sin fila, nivel `alto`, `medio`, `bajo` o `null`, eucalipto con objeto y nivel nulo |
| API-08 | censo, oráculo | ídem | comparar `image` con `plant_image` | igual a la fila, `null` sin fila, licencia y página siempre, CC BY con autor y `attributionRequired` verdadero |
| API-09 | censo, oráculo | ídem | comparar `credits` con `source` y con las fuentes que respaldan cada dato | sin repeticiones, ordenados por nombre, `licenseUrl` de `source.license_url` (oficial de CC en Wikipedia, EFSA y WCVP; nulo en EMA y TPPT), todas las fuentes de los datos servidos y ninguna de más |
| API-10 | particiones | ídem | `GET` de los 650 alias, del alias de romero, de un canónico, de un inexistente y de un alias sin token | 200 con `id` canónico y `Content-Location`, 404 `problem+json`, 401, ningún alias en el listado |
| API-11 | autenticación | ídem | `/v1/plants` y detalle sin token, con token incorrecto, con esquema Basic y con token vacío; `/health` y `/openapi.json` | 401 con `WWW-Authenticate: Bearer`; `/health` y `/openapi.json` sin token; OpenAPI sin nombres de dataset ni flags |
| API-12 | particiones, valores límite | ídem | búsquedas por sinónimo, alias, puntuación, mayúsculas, acentos, espacios, `%`, `_`, 200 y 201 caracteres, los 357 nombres anteriores de la QA del cambio 1 y 32 consultas contra un oráculo SQL | la planta aparece una sola vez, total coherente, el alias no se devuelve como nombre, `mentha piperita` da 0 (límite conocido), 357 de 357 recuperados |
| API-13 | particiones | ídem | detalle de lavanda, manzanilla, menta, hipérico, tóxica, eucalipto, sin datos, sin nombre en español | valores del diseño y de los escenarios |
| API-14 | barrido | ídem | expresiones regulares de efecto, dosis y seguridad sobre los textos servidos de las 2.354 plantas | informe de coincidencias para revisión manual |
| API-15 | prueba de escenario | imagen del backend | contenedor en una red `--internal` sin salida y petición desde otro contenedor de la misma red | 200 con los datos de `image`, porque la API no consulta la red |
| API-16 | Postman | colección y environment local | `postman collection run postman/serve-consolidated-plants.collection.json -e <environment>` | 22 peticiones y sus aserciones pasan |
| API-17 | exploratoria | ídem | ids con mayúsculas, barra final, espacios, inyección, 3.000 caracteres, `q` repetido, `%00`, emoji, `offset` mayor que el total | respuestas controladas (200, 400 o 404), nunca 5xx |
| API-18 | regresión | Rust | `cargo test -p catalog-api` | pruebas del producto en verde (incluye el orden en empate y el detalle sin créditos que la base real no puede ejercitar) |

### Semilla e ingesta (tareas 11.1 y 11.4)

| ID | Técnica | Pasos | Resultado esperado |
|---|---|---|---|
| SED-01 | oráculo | `scripts/seed_ingest_checks.py`: comparar `sources.json`, `data/seed/manifest.json` y `source.license_url` | iguales; URL oficiales de CC; nulo en Commons, EMA y TPPT; solo cambió el manifiesto desde `7e6cbfe` y solo en líneas `licenseUrl` |
| SED-02 | valores límite | mismo script: `licenseUrl` con `http://`, vacío, solo espacios, `https://`, con espacio, `ftp://`, número, booleano, lista | el validador rechaza nombrando fuente y campo; acepta `null`, https y ausente |
| SED-03 | regresión | `python3 -B -I -m unittest discover -s tools/catalog-seed/tests` | todas las pruebas pasan (insumo íntegro, alterado, snapshot, retirar fuente, fuente fuera de la lista) |
| ING-01 | caja negra | `catalog-ingest build` sobre una copia de la semilla | `source.license_url` igual a la base del servicio |
| ING-02 | negativa | mismo comando con `licenseUrl` `http://` en `wikipedia_es` | falla nombrando la fuente, código de salida 1, no escribe base |
| ING-03 | regresión | `cargo test -p catalog-ingest` | pruebas del producto en verde (trazabilidad de uso y objetivo, dato sin fuente) |
| IND-01 | regresión | `cargo test -p catalog-api --test source_independence` | 3 pruebas en verde (OpenAPI y código sin nombres de dataset) |

### App en el emulador (tarea 11.3)

| ID | Técnica | Pasos | Resultado esperado |
|---|---|---|---|
| APP-01 | smoke | `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_TOKEN=<token-app>` | pasa, encontrando la fila `Lavanda` y recorriendo `General`, `Propiedades` y `Usos` |
| APP-02 | partición | Explorar: lista inicial, búsqueda `lavandula`, `abutilon`, `salvia` | nombres en español como principal y científico como secundario; científico solo si coinciden; sin imágenes en las filas |
| APP-03 | partición | pasaporte de lavanda: cabecera, tres pestañas, textos, aviso fijo, grupos, `Fuentes`, pie de imagen | según los escenarios de `plant-passport` |
| APP-04 | partición | pasaporte de `aconitum-napellus` | aviso `Precauciones de nivel alto` en `General`, `Alto` y texto en `Propiedades`, «No hay objetivos...» |
| APP-05 | partición | pasaporte de `eucalyptus-globulus` | `Precauciones` con texto y citas sin etiqueta de nivel, sin aviso en `General`, `Otros objetivos` con subárea |
| APP-06 | partición | pasaporte de `angelica-laxiflora` | cada campo vacío lo dice, aviso fijo de `Usos` con el vacío explícito, `Precauciones` sin datos, `Fuentes` sin fuentes |
| APP-07 | partición | pasaporte de `abutilon-theophrasti` | principal científico, `Nombre común: No hay nombre común en español registrado`, `Velvetleaf (en)` entre los otros |
| APP-08 | partición | pasaporte con grupos con citas sin resolver (`alstonia-scholaris`, `ricinus-communis`) | cita «(sin resolver)» en estilo atenuado, grupo visible |
| APP-09 | partición | pasaporte de `hypericum-perforatum` | `Propiedades` sin `Relajación / Estrés` |
| APP-10 | transición | tocar `Abrir en el navegador` de la imagen y de una licencia | abre el navegador del sistema; la URL sigue visible como texto |
| APP-11 | falla de red | bloquear el host de las imágenes y abrir un pasaporte con imagen | arte local, sin pie de atribución, ficha completa y sin error |
| APP-12 | compatibilidad | proxy que quita los campos nuevos (`scripts/old_backend_proxy.py`) y APK apuntando a él | Explorar y pasaporte funcionan, nombre desde el primer nombre común, usos derivados de `uses` |
| APP-13 | accesibilidad | `font_scale` 2,0 en 360x640 dp: lavanda y tóxica | texto legible, desplazable y sin truncar; controles alcanzables |
| APP-14 | tráfico | medir los bytes recibidos al abrir un pasaporte con imagen original pesada | la descarga es de la miniatura (cientos de KB), no del original (varios MB) |
| APP-15 | barrido | `adb logcat` guardado | no contiene el token |
| APP-16 | regresión | `flutter test` | pruebas del producto en verde (cliente, parser, política de imágenes, pasaporte) |

### Revisión manual (tarea 11.4)

| ID | Técnica | Pasos | Resultado esperado |
|---|---|---|---|
| REV-01 | revisión a mano | 30 plantas (la muestra del cambio 1, tarea 10.5: piloto, tóxicas, solo género, separadas y fusionadas por colisión, EMA fuera de USDA, fase 2) en la API con `scripts/sample_view.py` | sin lenguaje de efecto, dosis, ausencias presentadas como seguridad ni atribuciones faltantes; citas sin resolver marcadas; actividades sensibles tal como llegan |
| REV-02 | revisión a mano | las plantas de la muestra recorridas en la app (`evidence/app/passport-*.txt`) | lo mismo que REV-01 más el aviso fijo de `Usos` |

## Trazabilidad

Cada escenario de los seis deltas aparece al menos una vez (tabla generada por `scripts/traceability.py`, que falla si algún escenario no tiene caso).

| Capability | Requisito | Escenario | Casos |
|---|---|---|---|
| `catalog-api` | Listado y búsqueda de plantas | Listado sin búsqueda | API-01 API-16 APP-02 |
| `catalog-api` | Listado y búsqueda de plantas | Contenido de cada elemento | API-01 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Nombre para mostrar en el listado | API-01 API-03 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Planta sin nombre común | API-01 API-03 API-13 |
| `catalog-api` | Listado y búsqueda de plantas | Orden estable en empate | API-01 (la base no tiene nombres cientificos repetidos: el empate solo se cubre con la prueba del producto, API-18) |
| `catalog-api` | Listado y búsqueda de plantas | Consulta vacía | API-12 |
| `catalog-api` | Listado y búsqueda de plantas | Caracteres de patrón literales | API-12 API-16 API-17 |
| `catalog-api` | Listado y búsqueda de plantas | Búsqueda por nombre científico | API-12 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Búsqueda por nombre común | API-01 API-12 API-13 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Búsqueda por sinónimo | API-01 API-12 API-13 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Búsqueda por identificador anterior | API-12 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Alias con puntuación en la consulta | API-12 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Alias sin duplicar resultados | API-01 API-12 API-13 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Consulta sin letras ni dígitos | API-12 |
| `catalog-api` | Listado y búsqueda de plantas | Búsqueda insensible a mayúsculas, acentos y espacios | API-01 API-12 API-13 API-16 |
| `catalog-api` | Listado y búsqueda de plantas | Sin coincidencias | API-12 API-17 |
| `catalog-api` | Detalle de planta | Planta existente | API-02 API-13 API-16 |
| `catalog-api` | Detalle de planta | Sin información de procedencia | API-02 API-11 |
| `catalog-api` | Detalle de planta | Cita de `uses` sin cambios | API-05 API-13 API-16 |
| `catalog-api` | Detalle de planta | Planta sin usos | API-02 API-13 API-16 |
| `catalog-api` | Detalle de planta | Familia presente | API-02 API-04 |
| `catalog-api` | Detalle de planta | Familia ausente | API-02 API-04 API-13 |
| `catalog-api` | Detalle de planta | Identificador inexistente | API-10 API-16 API-17 |
| `catalog-api` | Independencia de la fuente de datos | Base construida con otra fuente | IND-01 API-18 (solo pruebas del producto) |
| `catalog-api` | Independencia de la fuente de datos | Atribución en las respuestas | API-09 API-13 |
| `catalog-api` | Independencia de la fuente de datos | Contrato sin nombres de dataset | API-11 IND-01 |
| `catalog-api` | Nombre para mostrar y orden de los nombres comunes | Nombre para mostrar primero | API-03 API-13 |
| `catalog-api` | Nombre para mostrar y orden de los nombres comunes | Sin nombre común | API-01 API-03 API-13 |
| `catalog-api` | Nombre para mostrar y orden de los nombres comunes | Solo nombres en otros idiomas | API-03 API-13 |
| `catalog-api` | Nombre para mostrar y orden de los nombres comunes | Varios nombres en otros idiomas | API-03 API-13 |
| `catalog-api` | Contenido consolidado del detalle | Planta con todos los campos | API-13 API-16 |
| `catalog-api` | Contenido consolidado del detalle | Planta con campos vacíos | API-13 API-16 |
| `catalog-api` | Contenido consolidado del detalle | Grupos de uso | API-05 API-13 |
| `catalog-api` | Contenido consolidado del detalle | Seguridad sin datos | API-07 API-13 |
| `catalog-api` | Contenido consolidado del detalle | Seguridad sin nivel | API-07 API-13 API-16 APP-05 |
| `catalog-api` | Contenido consolidado del detalle | Cita completa en los grupos de uso | API-05 API-13 API-16 |
| `catalog-api` | Contenido consolidado del detalle | Grupo de uso con una cita sin resolver | API-05 APP-08 |
| `catalog-api` | Contenido consolidado del detalle | Objetivo de la EMA | API-06 API-13 APP-03 |
| `catalog-api` | Contenido consolidado del detalle | Subárea de otros objetivos | API-06 APP-05 |
| `catalog-api` | Imagen con atribución en el detalle | Imagen con licencia | API-08 API-13 |
| `catalog-api` | Imagen con atribución en el detalle | Sin imagen | API-08 API-13 |
| `catalog-api` | Imagen con atribución en el detalle | Sin acceso a la red | API-15 |
| `catalog-api` | Créditos neutrales a nivel de planta | Créditos de una planta con varias fuentes | API-09 API-13 |
| `catalog-api` | Créditos neutrales a nivel de planta | URL de licencia por fuente | API-09 API-13 |
| `catalog-api` | Créditos neutrales a nivel de planta | Sin repeticiones | API-09 API-13 |
| `catalog-api` | Créditos neutrales a nivel de planta | Descripción derivada de Wikipedia | API-09 API-13 |
| `catalog-api` | Créditos neutrales a nivel de planta | Planta sin créditos | API-09 (0 plantas sin creditos en la base real: solo la prueba del producto, API-18) |
| `catalog-api` | Identificadores anteriores | Alias de un renombre | API-10 API-16 |
| `catalog-api` | Identificadores anteriores | Identificador canónico | API-10 API-16 |
| `catalog-api` | Identificadores anteriores | Identificador desconocido | API-10 API-16 |
| `catalog-api` | Identificadores anteriores | Alias sin autorización | API-10 API-11 API-16 |
| `catalog-api` | Identificadores anteriores | Alias fuera del listado | API-10 API-16 |
| `catalog-api` | Contenido pendiente de revisión no se sirve | Objetivo condicionado | API-06 API-13 API-16 APP-09 |
| `catalog-api` | Contenido pendiente de revisión no se sirve | Grupo sin ninguna cita resuelta | API-05 |
| `catalog-api` | Contenido pendiente de revisión no se sirve | Grupo con una cita resuelta y otra sin resolver | API-05 APP-08 |
| `catalog-api` | Contenido pendiente de revisión no se sirve | Planta con otros flags | API-02 API-13 REV-01 |
| `catalog-api` | Contenido pendiente de revisión no se sirve | Sin flags en las respuestas | API-02 API-11 |
| `catalog-client` | Consumo de la API v1 del catálogo | Listado con parámetros | APP-02 APP-16 |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta con caracteres especiales | APP-16 |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta vacía | APP-16 |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta larga | APP-16 |
| `catalog-client` | Consumo de la API v1 del catálogo | Detalle por identificador | APP-03 APP-16 |
| `catalog-client` | Consumo de la API v1 del catálogo | Token en cada petición | APP-02 APP-03 APP-16 |
| `catalog-client` | Consumo de la API v1 del catálogo | Sin otros endpoints, hosts ni datos de usuario | APP-16 APP-14 |
| `catalog-client` | Consumo de la API v1 del catálogo | Imagen de un host permitido | APP-14 APP-16 |
| `catalog-client` | Consumo de la API v1 del catálogo | Imagen de un host no permitido | APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Listado válido | APP-02 APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Detalle válido | APP-03 APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Precauciones sin nivel | APP-05 APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Cita sin resolver | APP-08 APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Familia nula | APP-06 APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Campos desconocidos | APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Campo requerido ausente o de tipo erróneo | APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Backend anterior sin los campos nuevos | APP-12 APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | Campo nuevo con tipo erróneo | APP-16 |
| `catalog-client` | Parseo estricto de las respuestas | JSON inválido | APP-16 |
| `catalog-client` | Nombre para mostrar | Planta con nombre común | APP-02 APP-03 |
| `catalog-client` | Nombre para mostrar | Planta sin nombre común | APP-02 APP-06 APP-07 |
| `catalog-client` | Nombre para mostrar | Backend sin nombre para mostrar | APP-12 APP-16 |
| `catalog-client` | Nombre para mostrar | Idioma del nombre común | APP-16 APP-07 |
| `explore-screen` | Composición y contenido de Explorar | Vista inicial | APP-02 |
| `explore-screen` | Composición y contenido de Explorar | Arte local | APP-02 |
| `explore-screen` | Composición y contenido de Explorar | Planta sin nombre común | APP-02 |
| `explore-screen` | Composición y contenido de Explorar | Nombre en español | APP-02 API-12 |
| `plant-passport` | Identidad y composición del pasaporte | Cabecera y pestañas iniciales | APP-03 |
| `plant-passport` | Identidad y composición del pasaporte | Campo de aceite no aplicable | APP-06 APP-16 |
| `plant-passport` | Identidad y composición del pasaporte | Planta sin nombre común | APP-06 APP-07 |
| `plant-passport` | Identidad y composición del pasaporte | Carga del pasaporte | APP-16 (solo pruebas del producto) |
| `plant-passport` | Identidad y composición del pasaporte | Atribución sin procedencia por campo | APP-03 APP-04 REV-02 |
| `plant-passport` | General con vacíos explícitos | Campos de P05 presentes | APP-03 |
| `plant-passport` | General con vacíos explícitos | Datos generales ausentes | APP-06 |
| `plant-passport` | General con vacíos explícitos | Parte registrada | APP-03 |
| `plant-passport` | General con vacíos explícitos | Familia y nombres comunes | APP-03 APP-05 |
| `plant-passport` | General con vacíos explícitos | Sin partes ni nombres comunes | APP-06 |
| `plant-passport` | General con vacíos explícitos | Planta sin nombre en español | APP-07 |
| `plant-passport` | General con vacíos explícitos | Aviso de nivel alto | APP-04 |
| `plant-passport` | General con vacíos explícitos | Sin aviso para otros niveles | APP-03 APP-05 |
| `plant-passport` | General con vacíos explícitos | Sin lista de referencias en General | APP-03 |
| `plant-passport` | Propiedades sin inferencia de eficacia | Planta con objetivos de la EMA | APP-03 APP-05 |
| `plant-passport` | Propiedades sin inferencia de eficacia | Objetivo de otros objetivos | APP-05 |
| `plant-passport` | Propiedades sin inferencia de eficacia | Plantas sin evaluación respaldada | APP-04 APP-06 |
| `plant-passport` | Propiedades sin inferencia de eficacia | Sin lenguaje de eficacia | APP-03 APP-16 REV-02 |
| `plant-passport` | Usos como registros tradicionales trazables | Registro tradicional elegible | APP-03 |
| `plant-passport` | Usos como registros tradicionales trazables | Aviso fijo de usos tradicionales | APP-03 APP-06 |
| `plant-passport` | Usos como registros tradicionales trazables | Cita sin resolver visible | APP-08 |
| `plant-passport` | Usos como registros tradicionales trazables | Actividades sensibles tal como llegan | APP-04 REV-01 REV-02 |
| `plant-passport` | Usos como registros tradicionales trazables | Grupo sin países | APP-16 (solo pruebas del producto) |
| `plant-passport` | Usos como registros tradicionales trazables | Sin registro elegible | APP-06 |
| `plant-passport` | Usos como registros tradicionales trazables | Muchos usos | APP-03 APP-13 |
| `plant-passport` | Accesibilidad del pasaporte | Ficha accesible con texto aumentado | APP-13 |
| `plant-passport` | Accesibilidad del pasaporte | Imagen descrita | APP-03 |
| `plant-passport` | Accesibilidad del pasaporte | Nivel de precauciones sin depender del color | APP-04 APP-05 |
| `plant-passport` | Imagen de cabecera con atribución | Imagen con licencia CC BY-SA | APP-03 APP-14 |
| `plant-passport` | Imagen de cabecera con atribución | Imagen sin atribución obligatoria | APP-03 |
| `plant-passport` | Imagen de cabecera con atribución | Sin imagen | APP-06 |
| `plant-passport` | Imagen de cabecera con atribución | Falla la descarga de la imagen | APP-11 |
| `plant-passport` | Imagen de cabecera con atribución | Abrir la página del archivo | APP-10 |
| `plant-passport` | Precauciones con nivel opcional y citas | Precauciones de nivel alto | APP-04 |
| `plant-passport` | Precauciones con nivel opcional y citas | Precauciones sin nivel | APP-05 |
| `plant-passport` | Precauciones con nivel opcional y citas | Precauciones sin datos | APP-06 |
| `plant-passport` | Precauciones con nivel opcional y citas | Ninguna planta se presenta como segura | APP-04 APP-05 APP-06 REV-01 REV-02 |
| `plant-passport` | Sección Fuentes con licencias y atribución | Fuentes de una planta | APP-03 |
| `plant-passport` | Sección Fuentes con licencias y atribución | Fuentes visibles en cada pestaña | APP-03 APP-04 |
| `plant-passport` | Sección Fuentes con licencias y atribución | Entrada de la imagen | APP-03 |
| `plant-passport` | Sección Fuentes con licencias y atribución | Sin créditos | APP-16 (solo pruebas del producto) |
| `plant-passport` | Sección Fuentes con licencias y atribución | Sin procedencia por campo | APP-03 REV-02 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | Insumo íntegro | SED-03 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | Insumo alterado o ausente | SED-03 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | Snapshot de una fuente cambiante | SED-03 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | Retirar una fuente | SED-03 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | Fuente fuera de la lista | SED-03 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | URL de licencia de una fuente | SED-01 ING-01 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | Fuente sin URL de licencia | SED-01 SED-02 |
| `catalog-seed` | Fuentes con versión fija, checksum y licencia | URL de licencia inválida | SED-02 |
| `catalog-ingest` | Procedencia de cada dato | Trazabilidad de un uso | API-05 ING-03 |
| `catalog-ingest` | Procedencia de cada dato | Trazabilidad de un objetivo | API-06 API-09 ING-03 |
| `catalog-ingest` | Procedencia de cada dato | Dato sin fuente | ING-03 (solo pruebas del producto) |
| `catalog-ingest` | Procedencia de cada dato | URL de licencia de una fuente | SED-01 ING-01 |
| `catalog-ingest` | Procedencia de cada dato | URL de licencia inválida en el manifiesto | ING-02 |

## Charters exploratorios

- EXP-API-01: explorar los bordes de rutas y parámetros de `GET /v1/plants` y `GET /v1/plants/{id}` buscando 5xx o respuestas sin el formato de error (resultado en API-17).
- EXP-APP-01: explorar el pasaporte en 360x640 dp con la imagen cargada y sin ella, cambiando de pestaña y desplazándose, buscando contenido inalcanzable o saltos de posición (originó DEF-01).
- EXP-APP-02: explorar el pasaporte con texto al 200 % y en horizontal, buscando truncados y controles perdidos (resultado en APP-13 y en la observación OBS-08).
- EXP-APP-03: explorar el pasaporte de una planta con imagen cuyo autor es nulo (`aethusa-cynapium`), buscando un pie de atribución roto (resultado: «Autor: No disponible en fuente»).

## Cómo re-ejecutar

Todo desde la raíz del repositorio, con Docker en marcha y un token nuevo que no se guarda en ningún archivo.

```
export QA_TOKEN=$(openssl rand -hex 32)
API_TOKENS=$QA_TOKEN docker compose up --build -d
QA=openspec/changes/serve-consolidated-plants/qa
QA_DB=data/build/catalog.db python3 -I $QA/scripts/api_checks.py . $QA/evidence/api
python3 -I $QA/scripts/sample_view.py $QA/evidence/api
python3 -B $QA/scripts/seed_ingest_checks.py
python3 -I $QA/scripts/make_postman_collection.py . $QA/postman/serve-consolidated-plants.collection.json
# environment local fuera de qa/, con la variable token de tipo secret y baseUrl
postman collection run $QA/postman/serve-consolidated-plants.collection.json -e /ruta/fuera/de/qa/env.json
```

Para la app, con un emulador Android iniciado (nunca un dispositivo físico):

```
cd app
flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_TOKEN=$QA_TOKEN
flutter build apk --debug --dart-define=API_TOKEN=$QA_TOKEN
# instalar con adb y guiar con scripts/ui.py y scripts/ui_flow.py (solo emulator-5554)
```

Al terminar: `API_TOKENS=x docker compose down`, `docker rmi boticario-backend`, detener el emulador y verificar con `grep -rEn '[0-9a-f]{32,}' openspec/changes/serve-consolidated-plants/qa/` que no queda ningún token.

Herramientas que se usaron sin instalar nada en el proyecto: `postman` CLI 1.74 (ya instalado), `docker compose`, `sqlite3`, `adb` y `uiautomator` del SDK de Android, `flutter` y `python3` con la librería estándar. Playwright y Newman no hicieron falta.
