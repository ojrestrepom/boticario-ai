# Resultados de QA: remove-api-provenance

Fecha: 2026-10-14. Plan: [`test-plan-provenance.md`](test-plan-provenance.md). Evidencias resumidas en [`evidence/`](evidence/) (`QPROV-*.txt`) y scripts de re-ejecución en [`scripts/`](scripts/).

## Entorno

- macOS en Apple Silicon (arm64), mise con Rust 1.99.0, Docker Engine 29.8.2 y Docker Compose.
- Código bajo prueba: commit `d4409a0` (código y OpenAPI) sobre `cd48f68` (documentación y Purpose); el árbol de trabajo solo difiere en `tasks.md`. Base: `data/build/catalog.db` (SHA-256 `3b784dc1eb15…99d01dd`), 2376 plantas.
- Línea base para las pruebas diferenciales: el commit `cd48f68` (`git archive`) compilado en el scratch y servido sobre una copia de la misma base.
- Herramientas: `curl`, `sqlite3`, Python 3 (barrido, comparación y comprobador de enlaces, en el scratch y copiados a `scripts/`), `docker`. No se instaló nada en el proyecto. Para construir el catálogo de fixtures se usó un proyecto Cargo auxiliar en el scratch con una dependencia de ruta a `catalog-ingest` (feature `test-fixtures`), fuera del repo.
- Sin Postman ni Playwright: la API es de solo lectura, sin credenciales ni interfaz web, y `curl` más scripts bastan. Autenticación y autorización no aplican (la spec exige acceso sin credenciales).
- Servidores usados: nativo en 18095 (código nuevo), 18096 (fixtures), 18097 y 18098 (código anterior, base real y fixtures) y 18099 (base sin atribución); Docker en 18100. Todos detenidos al terminar. El proceso `catalog-api` que escucha en el puerto 8080 no es de esta QA (ya estaba arrancado antes) y no se tocó.

## Resumen

31 casos: 31 PASS, 0 FAIL, 0 NOT RUN (de los cuales PROV-22 y PROV-29 se repitieron tras la corrección de la propuesta, ronda 2).

- Ronda 1: 29 PASS, 1 FAIL (PROV-29, DEF-01) y 1 NOT RUN (PROV-22). Ronda 2: DEF-01 se corrigió en la propuesta (delta `specs/backend-container/spec.md`) y se verificó; PROV-22 se ejecutó con una construcción sin caché.
- No queda ningún defecto abierto. DEF-01 (severidad media, coherencia de specs) está resuelto.
- Observaciones: OBS-01 y OBS-02 (sin acción obligatoria).
- La API se comporta exactamente como pide la spec delta: las 2376 respuestas de detalle son idénticas a las anteriores salvo por lo que el cambio elimina.

## Resultados por caso

| ID | Resultado | Evidencia resumida |
|---|---|---|
| PROV-01 | PASS | Barrido de las 2376 plantas: 0 claves `sources` en cualquier nivel (recorrido recursivo). Claves vistas: `id`, `scientificName`, `family`, `names[text,kind,language]`, `parts[label]`, `uses[activity,language,reference[id,citation]]`. El listado tampoco tiene `sources`. `evidence/QPROV-barrido-2376.txt` |
| PROV-02 | PASS | `family` es texto en 2342 plantas y `null` en 34 (por ejemplo `chondrus-crispus`, `aspidixia-angulata`); ningún objeto. La clave está presente con valor `null` (`"family":null`). `evidence/QPROV-detalle-muestras.txt` |
| PROV-03 | PASS | Diferencial contra `cd48f68` sobre las 2376 plantas: 0 diferencias tras quitar `sources` y aplanar `family.value`; el orden de las claves de primer nivel (`id`, `scientificName`, `family`, `names`, `parts`, `uses`) coincide, y el de las listas también |
| PROV-04 | PASS | 1196 plantas con `uses: []` (por ejemplo `abies-sachalinensis`, que además tiene familia); las demás traen `activity`, `language` y `reference{id,citation}`. `evidence/QPROV-detalle-muestras.txt` |
| PROV-05 | PASS | `lavandula-angustifolia`: 200 `application/json`, `family` `Lamiaceae`, nombre científico (`la`) y común `English Lavender` (`en`), partes Flower, Leaf, Plant y Seed, y usos con referencia `Steinmetz` y su cita |
| PROV-06 | PASS | `/v1/plants/nope`, `/v1/plants/LAVANDULA-ANGUSTIFOLIA` y `/v1/plants/%20`: 404 `application/problem+json`, iguales al código anterior |
| PROV-07 | PASS | Listado completo idéntico (2376 elementos, mismo orden, mismo `total`). 16 consultas de búsqueda, paginación y errores con estado, `content-type` y cuerpo idénticos al anterior (`q=lavand` total 7; `q=zzzzqq` vacío; `limit=0`, `limit=101`, `limit=abc` y `offset=-1` dan 400 con `param`; `offset=99999` da 200 con lista vacía) |
| PROV-08 | PASS | `GET /healthz` 200 `{"status":"ok"}`; `HEAD /healthz` 200 |
| PROV-09 | PASS | `/openapi.json` servido (nativo y Docker) igual semánticamente a `backend/openapi.json`; `catalog-api -- --openapi` regenera el archivo idéntico byte a byte. El servidor lo sirve compacto y el archivo está formateado, por eso `cmp` directo no aplica |
| PROV-10 | PASS | 0 apariciones de `SourceDto`, `FamilyDto`, `/v1/sources`, `sources` ni `Source` en el documento; `paths` = `/healthz`, `/openapi.json`, `/v1/plants`, `/v1/plants/{id}`; `PlantDto.family` = `{"type":["string","null"]}`. El diff de `cd48f68` a `d4409a0` solo elimina esas piezas y ajusta descripciones |
| PROV-11 | PASS | `GET /v1/sources`: 404, `content-type: application/problem+json`, cuerpo `{"type":"about:blank","title":"Not Found","status":404,"detail":"el recurso solicitado no existe","instance":"/v1/sources"}`, con la misma forma que `/v1/nada`. `evidence/QPROV-sources-404.txt` |
| PROV-12 | PASS | Observado: `HEAD`, `POST`, `PUT` y `OPTIONS` sobre `/v1/sources` responden 404 `application/problem+json` sin cabecera `Allow` (el router trata la ruta como desconocida; en contraste, `POST /v1/plants` da 405 con `Allow: GET`). `GET /v1/sources/`, `/v1/sources/usda` y `/v1/sources?x=1` también dan 404 |
| PROV-13 | PASS | `fixture_end_to_end.rs` pasa. Ingiere `alpha` y `beta` (la lavanda en ambas), sirve la base con el router real y comprueba: `/healthz` 200, `/v1/sources` 404, total 2 con ids `lavandula-angustifolia` y `matricaria-chamomilla`, partes `Flower, Leaf, Root` (unión de ambas fuentes), el uso `Sedative` y que el JSON no contiene `"sources"` |
| PROV-14 | PASS | Con el binario real sobre el catálogo `alpha`+`beta`: la lavanda aparece una sola vez en el listado (total 2) y su detalle une 5 nombres, 3 partes y 3 usos de las dos fuentes sin `sources`; el código anterior daba las mismas 12 claves `sources` que ahora no están y el resto es idéntico. `evidence/QPROV-multifuente-http.txt` |
| PROV-15 | PASS | Con las cuatro tablas de atribución vaciadas, las 2376 respuestas de detalle son idénticas a las de la base completa: la API ya no las consulta |
| PROV-16 | PASS | `rederive` en una copia: `fuentes: 1`, `plantas: 2376`, `hash: 48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`; el `catalog.db` resultante es idéntico byte a byte (SHA-256 `3b784dc1…01dd`) al de `data/build`. `evidence/QPROV-base-y-hash.txt` |
| PROV-17 | PASS | `build` desde el ZIP cacheado (copia en el scratch): mismo hash y mismo SHA-256 |
| PROV-18 | PASS | Catálogo de fixtures `alpha`+`beta` construido con el código nuevo y con el anterior: archivo idéntico (SHA-256 `9c08c350…17f6`) y las 11 tablas idénticas una por una |
| PROV-19 | PASS | Filas: `source` 1, `plant_source_id` 2376, `plant_name_source` 5296, `plant_part_source` 6740, `plant_use_source` 18931, `reference_source` 32; `plant.family_source_id` no nulo en 2342 plantas (las 34 sin familia lo tienen nulo, como exige la restricción) |
| PROV-20 | PASS | `cargo test --workspace`: 59 + 1 + 2 + 1 (api), 7 + 6 (core) y 84 (ingest) en verde; con `-- --ignored`, `lavender_is_found_in_the_real_catalog`, `asset_plants_match_the_built_catalog` y `real_catalog_matches_reference_values` en verde. `stores_attribution_and_links`, `two_sources_in_one_raw_db_are_attributed`, `core_api_and_openapi_do_not_name_any_dataset` y `versioned_document_matches_the_generated_one` pasan. `cargo fmt --all --check` y `cargo clippy --all-targets --workspace -- -D warnings` sin avisos. `evidence/QPROV-cargo-test.txt` |
| PROV-21 | PASS | `docker compose build` con el árbol actual: todas las capas `CACHED` (la imagen ya correspondía al código actual). `PORT=18100 docker compose up -d`: `/healthz` 200; detalle de la lavanda sin `sources` y con `family` texto; `/v1/plants?q=lavand` con datos; `/v1/sources` 404 `application/problem+json`; `/openapi.json` igual a `backend/openapi.json`; el barrido de las 2376 plantas da el mismo resultado que el nativo (0 diferencias, 34 `family: null`). `docker compose down` elimina contenedor y red |
| PROV-22 | PASS | Ronda 1: la construcción con caché no imprime `hash:` (NOT RUN; el `catalog.db` de la imagen ya tenía el SHA-256 `3b784dc1…01dd`, igual al nativo). Ronda 2: `docker compose --progress=plain build --no-cache` (exit 0) imprime `#17 2.438 plantas: 2376` y `#17 2.438 hash: 48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`. Otro agente observó la misma línea en una construcción real no cacheada. `evidence/QPROV-docker-hash-nocache.txt` |
| PROV-23 | PASS | `grep -rn "v1/sources" README.md backend/README.md docs` sin resultados. En el resto del repo (sin `archive/`) solo aparece en la propia carpeta del cambio, en los tests (`http.rs`, `fixture_end_to_end.rs`) y en las specs principales `catalog-api` (requisito que el delta elimina) y `backend-container` (ver DEF-01) |
| PROV-24 | PASS | Ninguna frase de `README.md`, `backend/README.md` ni `docs/` dice que la API expone fuentes. `docs/data/modelo-de-datos.md`: la sección 2 explica que «la procedencia es interna al backend y la API no la expone», la sección 7 añade «La API no indica el origen» y no queda ninguna mención a `sources` en el detalle. El `README.md` cita «fuentes verificables» solo en la lista de ideas futuras del chat, sin relación con la API |
| PROV-25 | PASS | 93 enlaces relativos y anclajes en 9 archivos (`README.md`, `backend/README.md`, `docs/**/*.md`), 0 rotos; el control negativo detecta 3 de 3 roturas sembradas. `scripts/links.py` |
| PROV-26 | PASS | En el diff de la documentación (`README.md`, `backend/README.md`, `docs/data/modelo-de-datos.md`, `## Purpose`) cada párrafo y cada elemento de lista está en una sola línea (párrafos nuevos de 313 y 432 caracteres sin saltos manuales) |
| PROV-27 | PASS | `openspec validate remove-api-provenance --strict`: «Change 'remove-api-provenance' is valid» |
| PROV-28 | PASS | `## Purpose` de `openspec/specs/catalog-api/spec.md`: «…que sirve el catálogo de plantas desde la base neutral…»; `grep -n "sus fuentes"` sin resultados |
| PROV-29 | PASS | Ronda 1: FAIL, porque `openspec/specs/backend-container/spec.md` exige `GET /v1/sources` en dos escenarios (líneas 12 y 45) sin delta en el cambio (DEF-01). Ronda 2: existe `specs/backend-container/spec.md` con MODIFIED de «Imagen autocontenida» y «Arranque con un solo comando»; «Servir sin red» usa `GET /v1/plants/lavandula-angustifolia` (200 con el detalle) y «Búsqueda real» usa `/v1/plants?q=lavand` y `/v1/plants/lavandula-angustifolia`; los escenarios y la redacción no modificados («Contenido mínimo», «Salud y datos») se conservan iguales a la spec vigente; `openspec validate remove-api-provenance --strict` es válido. Los endpoints del nuevo texto se comprobaron contra la imagen en PROV-21 (200 con datos); no se repitió «Servir sin red» con `--network none` |
| PROV-30 | PASS (con OBS-02) | `info.description` de `backend/openapi.json` dice «Dentro de `/v1` solo habrá cambios aditivos»; es la regla general vigente y no contradice la excepción acotada (aplica solo sin consumidores, registrada en un cambio de OpenSpec) |
| PROV-31 | PASS (con OBS-01) | El catálogo de fixtures devuelve en la lavanda dos nombres científicos que difieren solo en espacios y mayúsculas (`LAVANDULA  angustifolia` de `beta` y `Lavandula angustifolia` de `alpha`); `lavender`, aportado por ambas, aparece una vez. En la base real ninguna planta tiene más de un nombre científico |

## Defectos

### DEF-01 (media, RESUELTO): la spec `backend-container` seguía exigiendo `GET /v1/sources` al archivar el cambio

- Estado: resuelto y verificado en la ronda 2 (ver PROV-29). Lo que sigue es el hallazgo original.

- Requerimiento afectado: coherencia de las specs con el requisito eliminado «Consulta de fuentes» (`catalog-api`); capability `backend-container`.
- Pasos para reproducir: `grep -n "v1/sources" openspec/specs/backend-container/spec.md`.
- Obtenido: dos escenarios de la spec principal dependen del endpoint eliminado. «Servir sin red» (línea 12): «se consulta `GET /v1/sources`» y «la API responde 200 con las fuentes del catálogo». «Búsqueda real» (línea 45): «se consulta `/v1/plants?q=lavand` y `/v1/sources`» y «ambas responden 200 y devuelven plantas y fuentes del catálogo real». El cambio solo trae el delta `specs/catalog-api/spec.md`; la propuesta dice que solo se modifica `catalog-api`.
- Esperado: que ninguna spec vigente exija un comportamiento que el cambio elimina. Tras sincronizar o archivar, esos dos escenarios serían insatisfacibles (el endpoint responde 404) y cualquier verificación de la imagen basada en la spec fallaría.
- Corrección aplicada por el equipo (verificada): añadir `specs/backend-container/spec.md` al cambio con un MODIFIED de «Imagen autocontenida» y del requisito que contiene «Búsqueda real», sustituyendo `/v1/sources` por `/v1/plants?q=lavand` (y el detalle de una planta); actualizar la sección «Impact» de la propuesta.
- Impacto en la práctica: ninguno en el comportamiento actual de la imagen (PROV-21 pasa); es solo coherencia documental, pero bloquearía una verificación futura basada en la spec.

## Observaciones

- OBS-01: al quitar la procedencia, el cliente ya no puede distinguir por qué una planta trae dos nombres científicos casi iguales cuando dos fuentes escriben el nombre distinto (la deduplicación es por texto exacto). Ya ocurría antes con `sources` por nombre y no ocurre con el catálogo real (una sola fuente); conviene tenerlo presente cuando llegue la lógica de selección de información.
- OBS-02: la descripción del documento OpenAPI no menciona la excepción de «Compatibilidad dentro de `/v1`». Es coherente porque la regla general sigue vigente, y la excepción desaparece cuando haya un primer cliente.
- OBS-03: resuelta; la construcción sin caché se ejecutó en la ronda 2 (PROV-22).

## Cobertura y riesgos residuales

- No probado: plataforma amd64 de la imagen, apagado ordenado e imagen en entornos endurecidos (no cambian con este cambio y se cubrieron en la QA de `add-backend-container`; `tests/shutdown.rs` pasa).
- No aplica: autenticación y autorización (la API es pública y de solo lectura), accesibilidad (sin interfaz) y la app Flutter (no consume la API).
- Riesgo residual: la dependencia futura de OBS-01 si se añaden fuentes con nombres casi iguales.

## Cómo re-ejecutar

- Arrancar la API: desde la raíz, `PORT=18095 mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-api`.
- Barrido y diferencial: levantar además el código anterior (`git archive cd48f68 backend mise.toml data | tar -x -C <scratch>` y arrancarlo en el puerto 18097 con una copia de `data/build/catalog.db`) y ejecutar `python3 -I scripts/crawl.py <salida.json>`.
- Enlaces: `python3 -I scripts/links.py <directorio-temporal>`.
- Base y hash: `catalog-ingest rederive --data-dir <copia con sources.toml y build/raw.db>` y `shasum -a 256` del `catalog.db`.
- Tests: desde `backend/`, `mise exec -- cargo test --workspace` y `-- --ignored`.
- Instalado: nada en el proyecto ni globalmente.
