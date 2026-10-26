# Plan de pruebas: consolidate-catalog-seed

Alcance: tareas 10.1 a 10.4 del cambio `consolidate-catalog-seed` (QA del catálogo construido desde la semilla consolidada, sus IDs, la API local y la app). La 10.5 (revisión manual de una muestra de 30 plantas) queda fuera. Resultados y defectos: [`consolidate-catalog-seed-results.md`](consolidate-catalog-seed-results.md). Tabla completa de IDs: [`informe-ids.md`](informe-ids.md). Evidencia en `evidence/`, scripts en `scripts/` y colección Postman en `postman/`.

## Requerimiento y criterios de aceptación

El cambio sustituye el catálogo construido desde el ZIP de USDA (2.376 plantas, nombres y usos literales en inglés) por una semilla consolidada en `data/seed/` (2.354 plantas, textos en español, IDs tomados del nombre aceptado de WCVP y alias con los IDs anteriores). El contrato HTTP de `/v1` no cambia (`backend/openapi.json`). Los criterios salen de `proposal.md`, `design.md`, las specs delta (`catalog-ingest`, `backend-container`, `plant-passport` y `catalog-seed`, en especial «Identificadores públicos fijos y únicos») y del grupo 10 de `tasks.md`:

- 10.1: comparar la base anterior con la nueva (plantas, plantas sin usos, IDs que cambian, perdidos o fusionados, alias). Cada ID anterior tiene destino (el mismo ID o un alias) o una ausencia justificada.
- 10.2: cada ID fijado fuera del catálogo (workflow de despliegue, `real_catalog.rs`, fixtures y tests de la app, specs, documentación) queda justificado o actualizado, y `lavandula-angustifolia` existe.
- 10.3: la API local cumple el contrato con la base nueva en listado, paginación, búsqueda (científico, común en español, sinónimo), detalles (manzanilla, menta, lavanda, hipérico, solo género), 404 y 401; manzanilla y menta tienen usos.
- 10.4: `flutter analyze`, `flutter test` y el smoke de integración pasan sin cambios, o cada fallo se documenta con su causa.

## Entornos y restricciones

- Base nueva: `data/build/catalog.db` (2.354 plantas, hash `4be91c438ced8f41a07bc4873cc7562c869b5c16af44570d934f851bb7d5a639`), sin reconstruir; se reconstruyó aparte en el scratchpad (`--out`) solo para comprobar el hash.
- Base anterior: construida en un `git worktree` desprendido de `main` (`63b7bed`) en el scratchpad, con `catalog-ingest build` y el ZIP de USDA de `data/.cache/` copiado al worktree (sin red). Dio 2.376 plantas y el hash `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`. No se tocó `data/build/` del repositorio. El worktree se eliminó al terminar (el mapa de IDs queda en `evidence/ids/`).
- API: binario de release de `catalog-api` compilado desde la rama con `CARGO_TARGET_DIR` en el scratchpad (no se escribió en `backend/target`), en `127.0.0.1:8080` con la base nueva y un token aleatorio de la ejecución (`openssl rand -hex 32`, guardado en un archivo del scratchpad con permisos 600). El token no aparece en archivos, evidencias ni informe; las evidencias llevan `<token>`. La API se detuvo al terminar.
- App: Flutter en `app/`. No se usó ningún dispositivo ni emulador. El proyecto solo tiene la plataforma Android, así que no hay destino de escritorio (`flutter devices` solo ofrece macOS y Chrome, ambos «no soportados por este proyecto»). El smoke se ejecutó en el entorno de host de `flutter test` (`-d flutter-tester`), con red real hacia la API local.
- Sin GCP, sin GitHub, sin lectura de `.env.cloud-run`, sin commits. Solo se escribió en `qa/` y en el scratchpad.
- Herramientas: `python3` (scripts), `sqlite3`, `curl`, Newman 6.2.1 vía `npx` (no se instaló en el proyecto), Flutter del sistema y `mise`. El CLI de Postman 1.74 está instalado pero sin sesión, por eso se usó Newman.

## Estrategia

- 10.1: comparación de las dos bases por ID (mismo ID, alias, ausente), con el nombre científico de ambos lados, la relación taxonómica de USDA tomada de los paquetes (`data/work/bundles`) y los `reviewFlags`; comprobaciones de integridad de alias; plantas con usos antes y ahora; reconstrucción determinista.
- 10.2: búsqueda de todos los IDs anteriores (2.376) como palabras completas en los archivos versionados, fuera de `data/seed/`, de `qa/` y de `openspec/changes/archive/`, y clasificación de cada coincidencia según el estado del ID en la base nueva.
- 10.3: caja negra sobre el contrato. Particiones y valores límite de `limit`, `offset` y `q` (vacío, espacios, `%`, `_`, 201 caracteres, carácter de control), recorrido completo de la paginación, barrido de los 2.354 detalles con validación de esquema, tabla de decisión ruta por credencial para el 401, y comparación de la respuesta con la base.
- 10.4: ejecución de las tres pruebas de la app y, ante un fallo, aislamiento de la causa con una copia desechable de la rama en el scratchpad.

## Casos

La técnica y los pasos exactos de cada caso están en el script indicado. El resultado esperado es el de la columna.

| ID | Cubre | Técnica | Pasos y resultado esperado |
| --- | --- | --- | --- |
| BAS-01 | 10.1, `catalog-ingest` Construcción determinista | Reconstrucción | `catalog-ingest build --seed data/seed --out <tmp>` imprime 2.354 plantas y el mismo hash que `data/build/catalog.db` |
| BAS-02 | 10.1 | Comparación | Plantas, plantas sin usos y usos de las dos bases (`scripts/compare_bases.py`); la nueva tiene menos plantas sin usos |
| BAS-03 | 10.1, `catalog-seed` IDs fijos | Partición por destino | Cada uno de los 2.376 IDs anteriores es el mismo ID, alias de otra planta, o ausente con justificación |
| BAS-04 | 10.1, `catalog-ingest` Identificador | Integridad | Ningún alias es ID de otra planta; todo alias apunta a una planta; ningún ID anterior es a la vez planta y alias; un ID conservado nunca cambia de especie |
| BAS-05 | 10.1 | Cobertura de ausentes | Cada ausencia queda justificada con la documentación de la semilla |
| BAS-06 | 10.1, objetivo del cambio | Comparación de usos | Plantas con usos antes y sin usos ahora (regresión) y plantas sin usos antes y con usos ahora |
| BAS-07 | 10.1 | Casos clave | `rosmarinus-officinalis` es alias de `salvia-rosmarinus`, `matricaria-recutita` de `matricaria-chamomilla`, `mentha-x-piperita-subsp-nothosubsp-piperita` de `mentha-x-piperita` |
| IDS-01 | 10.2 | Búsqueda textual | `scripts/grep_ids.py` lista cada coincidencia de un ID anterior con su estado en la base nueva |
| IDS-02 | 10.2 | Revisión | Cada coincidencia con alias o ausente se justifica o se propone su actualización |
| IDS-03 | 10.2, despliegue | Verificación | `lavandula-angustifolia` existe en la base y la API la sirve con 200 (workflow `deploy-backend.yml`, `real_catalog.rs`) |
| API-01 | 10.3, contrato | Esquema | `GET /v1/plants` 200, `application/json`, cumple `PageDto_PlantSummaryDto`, `limit` 20, `offset` 0, `total` 2.354, orden por nombre científico e ID |
| API-02 | 10.3 | Valores límite | Recorrido completo con `limit=100` (24 páginas) cubre los 2.354 IDs en orden y sin duplicados; `offset` igual al total da lista vacía; `limit` 0, 101, `abc`, vacío, `offset` negativo o desbordado dan 400 `problem+json` con el esquema de error |
| API-03 | 10.3 | Equivalencia | Búsqueda por nombre científico, mayúsculas, fragmento, sinónimo (`rosmarinus officinalis`), nombre aceptado, común en español con y sin acento, común en inglés, espacios repetidos, híbridos con `x` y con `×`, sin coincidencias, vacío, `%`, `_`, 201 caracteres y carácter de control; 300 plantas al azar se encuentran por su nombre científico y 300 por un nombre común en español |
| API-04 | 10.3, `catalog-seed` alias | Búsqueda por nombre anterior | Buscar el nombre científico anterior de cada ID que pasó a alias (628) encuentra la planta nueva; los que la planta lista como sinónimo deben encontrarse siempre |
| API-05 | 10.3, `plant-passport` Usos | Detalle | Manzanilla, menta, lavanda, hipérico y `lavandula-sp` (solo género): 200, cumple `PlantDto`, `id` igual al pedido; manzanilla, menta, lavanda e hipérico con usos en `es`, cada uno con referencia; sin usos repetidos |
| API-06 | 10.3, `api-token-auth` | Tabla de decisión | 404 `problem+json` para ID inexistente, ID anterior (alias), mayúsculas, espacio final y la planta ausente; 401 con `WWW-Authenticate: Bearer` y el mismo cuerpo para 5 rutas por 2 credenciales (sin token y token incorrecto); `/health` y `/openapi.json` públicos |
| API-07 | 10.3, contrato, `plant-passport` | Barrido | Los 2.354 detalles responden 200 y cumplen `PlantDto`; usos, nombres y plantas sin usos coinciden con la base; todos los usos en `es`; el primer nombre común de la API es el nombre para mostrar de la semilla (escenario «Cabecera y pestañas iniciales»); citas completas |
| API-08 | 10.3, contrato | Comparación | `/openapi.json` servido es igual a `backend/openapi.json` y este igual al de `main`; solo las 4 rutas del contrato; `/health` cumple su esquema; `POST`, `PUT` y `DELETE` dan 405 con `Allow: GET` |
| NEW-01 | 10.3 | Newman | `postman/consolidate-catalog-seed.collection.json`: 17 peticiones con 65 aserciones (estado, `content-type`, esquema del `openapi.json`, `WWW-Authenticate`, manzanilla y menta con usos) |
| APP-01 | 10.4 | Estático | `flutter analyze` sin incidencias |
| APP-02 | 10.4 | Unitarias y widget | `flutter test` completo sin fallos |
| APP-03 | 10.4 | Smoke real | `flutter test integration_test/app_test.dart -d flutter-tester` con `API_BASE_URL` y `API_TOKEN` pasa sin cambios |
| APP-04 | 10.4 | Aislamiento de causa | Misma prueba en una copia de la rama en el scratchpad cambiando solo el nombre común esperado de la lavanda al que devuelve la API, para ver si el resto del flujo funciona con el contenido nuevo |

## Trazabilidad

| Criterio | Casos |
| --- | --- |
| `catalog-ingest`: construcción determinista, identificador público, esquema ampliado | BAS-01, BAS-04 |
| `catalog-seed`: identificadores públicos fijos y únicos, alias | BAS-03, BAS-04, BAS-07, API-04 |
| `catalog-seed`: sinónimo y alias de los fusionados | API-03, API-04 |
| `backend-container`: despliegue verifica `lavandula-angustifolia` | IDS-03, API-05 |
| `plant-passport`: cabecera con el nombre para mostrar, planta sin nombre común, usos con cita | API-05, API-07, APP-03, APP-04 |
| Contrato HTTP sin cambios | API-01 a API-08, NEW-01 |
| Tareas 10.1 a 10.4 | los casos de su grupo |
