# Resultados de QA: consolidate-catalog-seed

Alcance: tareas 10.1 a 10.4. Plan, casos y trazabilidad en [`test-plan-consolidate-catalog-seed.md`](test-plan-consolidate-catalog-seed.md). Tabla completa de IDs anterior a destino en [`informe-ids.md`](informe-ids.md). Evidencia en `evidence/`, scripts en `scripts/` y colección Postman en `postman/`. Ejecución: 2026-10-25 y 2026-10-26 (UTC), rama `consolidate-catalog-seed` en `8647a01`.

## Resumen

- 10.1: cada uno de los 2.376 IDs anteriores tiene destino o ausencia justificada (2.375 son el mismo ID o un alias; 1 está ausente y justificado). Cambian 629 IDs (527 renombrados, 101 fusionados y 1 ausente), algo más que el «unos 500 a 600» estimado. Las plantas sin usos bajan de 1.196 (50,3 %) a 923 (39,2 %). La base se reconstruye con el mismo hash. Hay 26 plantas que antes tenían usos y ahora no (DEF-03).
- 10.2: ningún ID fijado fuera del catálogo se rompe. `lavandula-angustifolia` existe y la API la sirve con 200 y 13 usos. Los IDs anteriores que quedan en fixtures, tests, specs y documentación se justifican o se propone su actualización (tabla más abajo). El smoke de la app sí fija un valor que cambió (`English Lavender`).
- 10.3: el contrato HTTP no cambia y todas las respuestas lo cumplen (2.354 detalles, 24 páginas del listado, errores 400, 401 y 404, y Newman con 65 aserciones). Manzanilla (40 usos) y menta (31 usos) ya tienen usos. Fallan tres criterios de comportamiento relacionados con nombres (DEF-01, DEF-02, DEF-04).
- 10.4: `flutter analyze` y `flutter test` (209 pruebas) pasan. El smoke de integración falla por el contenido nuevo (DEF-01); con ese único valor ajustado en una copia desechable, el resto del flujo pasa.
- Defectos: 7 (1 alta, 4 media y 2 baja). Ninguno es de seguridad ni de contrato de forma. Los listados con evidencia están en «Defectos».

## Desvíos respecto de las tareas

- Postman: el CLI de Postman 1.74 está instalado pero sin sesión, así que las colecciones se ejecutaron con Newman 6.2.1 vía `npx` (nada se instaló en el proyecto). Además hay un script en Python que valida el contrato con un validador de esquemas propio.
- 10.4: la app solo tiene la plataforma Android y no se usó ningún dispositivo. El smoke se ejecutó en el entorno de host de `flutter test` con `-d flutter-tester`, que sí hace peticiones HTTP reales a la API local. Esto prueba el flujo de la app y su lógica contra datos reales, pero no un teléfono (rendimiento, teclado, radios). Es el mismo flujo que el de Android; no se probó en Android.
- 10.1: la base anterior se construyó en un worktree de `main` y ese worktree se eliminó al terminar, como pedía la tarea. La reconstrucción está descrita en el plan.
- Compilación: el binario de la API y el `catalog-ingest` se compilaron con `CARGO_TARGET_DIR` fuera del repositorio. `backend/target` no se tocó.

## Resultados por caso

### 10.1 Base anterior frente a la nueva

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| BAS-01 reconstrucción | PASA | `evidence/base/rebuild-new.log`: 2.354 plantas, 650 alias, hash `4be91c43...5d639`, igual al de `data/build/catalog.db` |
| BAS-02 comparación de bases | PASA | `evidence/ids/id-map-summary.json`. Plantas 2.376 a 2.354; sin usos 1.196 a 923; usos 18.931 a 24.286; alias 0 a 650 |
| BAS-03 destino de cada ID anterior | PASA | `evidence/ids/id-map.tsv` y `informe-ids.md`: 1.747 conservan su ID (57 de ellos absorben a otros), 628 pasan a alias, 1 ausente (`malachra-alaceaefolia`) |
| BAS-04 integridad de alias | PASA | `evidence/ids/checks.txt`: ningún alias es ID de otra planta, todos apuntan a una planta existente, ningún ID es planta y alias a la vez; los 6 IDs conservados con signo híbrido distinto (`x` a `×`) siguen siendo la misma especie |
| BAS-05 ausencia justificada | PASA | `malachra-alaceaefolia` (USDA 1402, `unmatched`): su paquete no trae ningún ref (una fila `usda_taxon`, sin usos, nombres ni partes) y no resuelve en WCVP ni WFO; `tools/catalog-seed/README.md` (estado final) la deja fuera de la semilla. Antes tenía 0 usos |
| BAS-06 comparación de usos | FALLA | 304 plantas ganan usos (entre ellas manzanilla de 0 a 40 y menta de 0 a 31), pero 26 plantas con usos antes quedan con 0 (DEF-03). `evidence/ids/lost-uses-reasons.tsv` |
| BAS-07 casos clave | PASA | `rosmarinus-officinalis` a `salvia-rosmarinus`, `matricaria-recutita` a `matricaria-chamomilla`, `mentha-x-piperita-subsp-nothosubsp-piperita` a `mentha-x-piperita` |

Cifras de las fusiones. 76 plantas nuevas reciben más de un ID anterior. Por la relación que USDA tenía con el aceptado de WCVP, los 628 alias se reparten así: 234 sinónimos homotípicos, 175 heterotípicos resueltos al aceptado y 118 nombres aceptados cuyo slug cambia (autónimos, rangos y variantes ortográficas), más los fusionados. Los 61 IDs nuevos sin origen anterior son especies de la EMA y miembros separados por la regla de colisiones (`evidence/ids/new-only.txt`); los 22 alias que no vienen de un ID anterior están en `evidence/ids/extra-alias.txt`.

### 10.2 IDs fijados fuera del catálogo

`scripts/grep_ids.py` busca los 2.376 IDs anteriores como palabras completas en los archivos versionados (fuera de `data/seed/`, de esta carpeta `qa/` y de `openspec/changes/archive/`). Resultado: 531 coincidencias (468 sobre IDs que no cambian, 58 sobre alias y 5 sobre el ausente); detalle en `evidence/ids/grep-ids.tsv`.

| Lugar | Coincidencia | Estado del ID | Veredicto |
| --- | --- | --- | --- |
| `.github/workflows/deploy-backend.yml:145` | `lavandula-angustifolia` | existe | Justificada. La API local devuelve 200 con 13 usos |
| `docs/deploy/cloud-run.md` | `lavandula-angustifolia` | existe | Justificada |
| `backend/catalog-api/tests/real_catalog.rs` | `lavandula-angustifolia` (y la búsqueda `lavand`) | existe | Justificada. `cargo test -p catalog-api --test real_catalog -- --ignored` pasa contra la base nueva (`evidence/base/real_catalog_test.txt`) |
| `backend/catalog-api/src`, `tests/fixture_end_to_end.rs`, `catalog-ingest/tests` | `lavandula-angustifolia`, `lavandula-latifolia`, `zea-mays`, `calendula-officinalis`, `conium-maculatum`, `thymus-vulgaris`, `aloe-vera` | existen | Justificadas: fixtures y pruebas propias con semillas de fixture, no con la base real |
| `backend/catalog-core/src/normalize.rs:61` | `mentha-x-piperita-subsp-nothosubsp-piperita` | alias de `mentha-x-piperita` | Justificada: es un caso de prueba del slug, no un dato del catálogo |
| `app/test/fixtures/api/plant_rosmarinus-officinalis.json`, `fake_catalog_api.dart:59`, `plant_passport_page_test.dart:21`, `catalog_json_parser_test.dart:101`, `catalog_repository_test.dart:342` | `rosmarinus-officinalis` | alias de `salvia-rosmarinus` | Justificada mientras los fixtures sean estáticos (los tests de la app pasan). Con la API real ese ID da 404 hasta que el cambio 2 resuelva alias. Propuesta: pasar los fixtures a `salvia-rosmarinus` al regenerarlos en el cambio 2 o 3 |
| `app/test/fixtures/api/list_lavandula.json:51,77`, `app/test/app/app_test.dart:218,220`, `explore_page_test.dart:245` | `lavandula-x-hybrida` y `rosmarinus-x-lavandulaceus` | alias de `lavandula-x-heterophylla` y de `salvia-x-lavandulacea` | Igual que la anterior: fixtures estáticos que no se rompen. Propuesta: actualizarlos a los IDs nuevos |
| `app/integration_test/catalog_smoke.dart:36,81` y `README.md:127` (descripción del smoke) | `English Lavender` como primer nombre común de `lavandula-angustifolia` | el ID existe, el nombre ya no es el primero | No justificada: el smoke falla (APP-03, DEF-01). Propuesta: ajustar el valor esperado en el smoke y en el `README.md` cuando se decida el orden de nombres (el cambio 2 introduce `displayName`) |
| `app/test/**` (33 líneas con `English Lavender`) y `openspec/specs/plant-passport/spec.md:14`, `openspec/specs/catalog-client/spec.md:116` | `English Lavender` | n/a | Justificadas: fixtures y specs principales que describen el contrato anterior; los deltas de los cambios 1 y 2 las sustituyen al archivarse |
| `docs/data/modelo-de-datos.md:201,240`, `docs/data/usda-catalog.md:65` | `matricaria-recutita`, `rosmarinus-officinalis` | alias | Justificadas: describen precisamente el cambio de IDs. Actualización propuesta en `modelo-de-datos.md:240`: «unos 500» pasa a 629 (DEF-07) |
| `openspec/changes/consolidate-catalog-seed/{proposal,design,specs}`, `openspec/changes/serve-consolidated-plants/{tasks.md,specs}` | `rosmarinus-officinalis`, `matricaria-recutita`, `rosmarinus-x-lavandulaceus` | alias | Justificadas: los usan como ejemplos del cambio de IDs |
| `tools/catalog-seed/{README.md,control.txt}`, `tools/catalog-seed/tests/**` | `matricaria-recutita`, `rosmarinus-officinalis`, `cinnamomum-zeylanicum`, `citrus-limon`, `prunus-dulcis`, `thevetia-peruviana`, `citrus-meyerii`, `rosmarinus-x-lavandulaceus` y otros | alias | Justificadas: son los IDs de USDA que las herramientas y sus pruebas usan como entrada, y fixtures (`bundle_matricaria.json`) de la resolución |
| `tools/catalog-seed/README.md:882,884,888`, `generation/README.md:69` | `malachra-alaceaefolia` | ausente | Justificadas: documentan que queda fuera de la semilla |
| `tools/catalog-seed/README.md:1025` | «1.748 se conservan como ID, 628 pasan a alias y ninguno se pierde» | n/a | Cifra del paso de universo: el estado final es 1.747, 628 y 1 ausente. Propuesta: aclarar o actualizar (DEF-07) |

Sin coincidencias de IDs en `app/lib` (la app no fija IDs) ni en `Dockerfile`, `compose.yaml` y `README.md` de la raíz. `backend/catalog-ingest/tests/fixtures/plant_catalog.json` (mencionado en la propuesta) ya no existe en el árbol.

### 10.3 API local

Entorno: `catalog-api` de release en `127.0.0.1:8080`, base nueva, token de prueba de la ejecución. Recuento del script `scripts/api_tests.py` (`evidence/api/results.tsv`): 107 comprobaciones, 103 pasan, 5 fallan (por 3 causas) y 4 son observaciones, y Newman: 17 peticiones, 65 aserciones, 0 fallos (`evidence/api/newman-run.txt`).

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| API-01 listado | PASA | `evidence/api/API-01.txt`: 200, `application/json`, cumple `PageDto_PlantSummaryDto`, limit 20, offset 0, total 2.354, orden por nombre científico e ID |
| API-02 paginación | PASA | `evidence/api/API-02.txt`: 24 páginas de 100 cubren los 2.354 IDs en el orden de la base y sin duplicados; `total` constante; `offset=2354` da lista vacía; `limit=1&offset=5` da el sexto; `limit` 0, 101, `abc`, vacío, `offset=-1` y `offset=2147483648` dan 400 `problem+json` con el esquema de error |
| API-03 búsqueda | FALLA parcial | `evidence/api/API-03.txt`: pasan 25 de 28. Pasan nombre científico exacto, con mayúsculas y en fragmento; sinónimo `rosmarinus officinalis` (encuentra `salvia-rosmarinus`); nombre aceptado; `manzanilla`, `menta`, `lavanda`, `romero`, `hipérico` y `hiperico` (con y sin acento), `hierba de san juan`; `english lavender`; espacios repetidos; `Mentha × piperita`; sin coincidencias; vacío; `%` y `_` como texto; 201 caracteres y carácter de control con 400; 300 plantas al azar por nombre científico y 300 por nombre común en español. Fallan `matricaria recutita`, `mentha piperita` y `mentha x piperita` con 0 resultados (DEF-04, DEF-05) |
| API-04 nombres anteriores | FALLA | `evidence/api/API-04.txt`: buscar el nombre científico anterior de los 628 IDs que pasaron a alias encuentra la planta nueva en 271 y no en 357 (`evidence/api/API-04-old-names-not-found.tsv`). De los 264 nombres que la planta lista como sinónimo, 262 se encuentran y 2 no (`Rosmarinus x lavandulaceus`, `Rosmarinus x mendizabalii`, por la `x`) |
| API-05 detalles | PASA | `evidence/api/API-05-*.txt`: manzanilla (40 usos), menta (31), lavanda (13) e hipérico (24) con 200, `PlantDto` válido, usos todos en `es`, referencia con ID y cita, sin repetidos; `lavandula-sp` (solo género) con 200, 0 usos y nombres comunes |
| API-06 404 y 401 | PASA | `evidence/api/API-06.txt`: 404 `problem+json` para `no-existe`, `rosmarinus-officinalis`, `matricaria-recutita`, mayúsculas, espacio final y `malachra-alaceaefolia`; 401 con `WWW-Authenticate: Bearer` y cuerpo igual (salvo `instance`) en 5 rutas por 2 credenciales; `/health` y `/openapi.json` públicos. El 404 de un ID anterior es esperado: resolver alias es el cambio 2 |
| API-07 barrido de detalles | FALLA parcial | `evidence/api/API-07.txt`: los 2.354 detalles responden 200 y cumplen `PlantDto`; 24.286 usos y 15.144 nombres coinciden con la base; 923 plantas sin usos; todos los usos en `es`. Falla el primer nombre común (DEF-01) y quedan dos observaciones (DEF-02 y DEF-06) |
| API-08 contrato | PASA | `evidence/api/API-08.txt`: `/openapi.json` servido igual a `backend/openapi.json`, igual al de `main` (el contrato no cambia), 4 rutas, `/health` válido, `POST`, `PUT` y `DELETE` dan 405 con `Allow: GET` |
| NEW-01 Newman | PASA | `postman/consolidate-catalog-seed.collection.json`, `evidence/api/newman-run.txt`: 17 peticiones, 65 aserciones, 0 fallos. Incluye manzanilla y menta con usos |

### 10.4 App

| Caso | Estado | Evidencia y notas |
| --- | --- | --- |
| APP-01 `flutter analyze` | PASA | `evidence/app/flutter-analyze.txt`: «No issues found!» |
| APP-02 `flutter test` | PASA | `evidence/app/flutter-test.txt`: 209 pruebas, todas pasan. Usan fixtures estáticos, así que no ejercen el contenido nuevo |
| APP-03 smoke contra la API local | FALLA | `evidence/app/smoke-original-fails.txt`: tras abrir Home y Explorar, la búsqueda `lavandula` carga datos reales (sin pantalla de carga ni de error) pero el flujo no encuentra la fila `English Lavender` (`catalog_smoke.dart:81`). Causa: contenido nuevo, el orden de nombres (DEF-01). No es un fallo de autenticación, de red ni de la app |
| APP-04 aislamiento de causa | PASA | `evidence/app/smoke-patched-passes.txt` y `smoke-patch.diff`: en una copia de la rama (worktree del scratchpad, ya eliminado) con `_lavenderCommon = 'Echter Lavendel'`, el smoke completo pasa (Home, búsqueda, Explorar, pasaporte y todos los regresos). El único cambio necesario es ese valor |

## Defectos

Severidad: crítica (rompe el funcionamiento principal o la seguridad), alta (contradice un criterio de aceptación o rompe una prueba del cambio con efecto visible), media (degrada contenido o búsqueda sin romper el contrato), baja (documentación o detalle). El contrato HTTP de `/v1` no se ve afectado por ninguno.

### DEF-01 (alta): el nombre principal que muestra la app no es el nombre para mostrar de la semilla; el smoke falla

- Requerimiento: `plant-passport`, escenario «Cabecera y pestañas iniciales» (el delta de este cambio dice que el primer nombre común en la API es el nombre para mostrar de la semilla, `Lavanda`); tarea 10.4 («pasan sin cambios»). Contradice un criterio de aceptación.
- Obtenido: la API ordena los nombres por texto (`ORDER BY text, language, id` en `backend/catalog-api/src/repository.rs:228`) y la app usa el primero como principal (`displayNamesFor`, `app/lib/features/catalog/domain/plant_summary.dart:15`). Para `lavandula-angustifolia` los nombres comunes salen `Echter Lavendel` (de), `English Lavender`, `Lavanda` (es), `True lavender`, `lavanda`; la app mostraría «Echter Lavendel» y no «Lavanda». En 1.024 de las 2.354 plantas el primer nombre común no es el `display_name` de la base (699 en inglés, 282 en español, 41 en alemán); solo 711 plantas tienen un nombre en español como primero. Ejemplo: `abrus-precatorius` se mostraría como «Coral Beadplant» y no como «Coralillo asiático».
- Esperado: el nombre principal es el nombre para mostrar de la semilla.
- Reproducir: con la API local y un token, `GET /v1/plants/lavandula-angustifolia` y mirar el primer elemento de `names` con `kind` `common`; o `flutter test integration_test/app_test.dart -d flutter-tester --dart-define=API_BASE_URL=http://127.0.0.1:8080 --dart-define=API_TOKEN=<token>`.
- Evidencia: `evidence/api/API-05-lavandula-angustifolia.txt`, `evidence/api/API-07-first-common-mismatch.tsv` (1.023 plantas, sin la cabecera), `evidence/app/smoke-original-fails.txt`.
- Nota: el cambio 2 (`serve-consolidated-plants`) expone `displayName`, lo que lo resolvería; hasta entonces el cambio 1 deja la app con el nombre equivocado y el smoke roto. Para este cambio hay que decidir entre ordenar los nombres con el de mostrar primero, o aceptar el estado y ajustar el smoke y el escenario de la spec.

### DEF-02 (media): 1.194 plantas sirven su nombre científico como nombre común

- Requerimiento: `plant-passport`, escenario «Planta sin nombre común» (el principal es el científico y no se muestra secundario); `catalog-ingest`, escenario «Nombre para mostrar explícito».
- Obtenido: cuando el `displayName` es el nombre científico (flag `sin-nombre-comun-es`), la construcción lo escribe también como nombre común de idioma `la`. La API lo sirve en `commonNames` y en `names`. En 625 plantas es el único «nombre común»; la app ve un nombre común y muestra el científico dos veces, como principal y como secundario (en la fila de Explorar, «Abutilon theophrasti, Abutilon theophrasti»). En las otras 569 puede quedar como principal por el orden alfabético.
- Esperado: sin nombre común real, `commonNames` vacío (como con la base anterior) y la app muestra solo el científico.
- Reproducir: `GET /v1/plants?q=abutilon%20theophrasti`: el primer `commonNames` es `{"text":"Abutilon theophrasti","language":"la"}`. En la base: `select text, kind, language from plant_name where plant_id='eleutherococcus-nodiflorus'`.
- Evidencia: `evidence/api/API-07-sci-as-common.txt` (lista de los 1.194) y `evidence/api/API-07.txt`.

### DEF-03 (media): 26 plantas que tenían usos quedan sin ninguno

- Requerimiento: motivo de la propuesta («se pierden las filas registradas bajo sinónimos») y `catalog-seed`, asignación de filas de uso al aceptado. No contradice un criterio numerado, pero revierte el objetivo del cambio para esas plantas.
- Obtenido: de las 26, 9 son plantas de solo género (por ejemplo `eucalyptus-sp`, `gossypium-sp`, con 4 y 10 usos antes); la spec no dice qué usos deben tener, así que se reporta como observación. Las otras 17 son especies. En 8 la causa está en la asignación: las filas de ETHNOBOT quedan `sin-resolver` o `fuera-del-universo` en `data/work/usda/assignment-report.json`, aunque la planta existe como sinónimo del aceptado: `eupatorium-odoratum` a `chromolaena-odorata` (31 usos antes, 38 filas sin resolver; el paquete tiene `usda:1279` como sinónimo homotípico), `senecio-aureus` a `packera-aurea` (17), `piper-angustifolium` a `piper-aduncum-var-aduncum` (24), `cimicifuga-foetida` a `actaea-cimicifuga` (16), `justicia-procumbens` a `rostellularia-procumbens` (16), `chrysanthemum-balsamita` a `tanacetum-balsamita-var-balsamitoides` (11), `origanum-creticum` (4) y `satureja-obovata` a `satureja-cuneifolia` (1). En las otras 9 (1 a 3 usos antes: `actaea-pachypoda`, `dalbergia-nitidula`, `dictamnus-hispanicus`, `duboisia-leichhardtii`, `eucalyptus-cladocalyx`, `hyacinthus-orientalis`, `inocarpus-edulis`, `lycopodium-selago`, `strophanthus-gratus`) no hay fila sin asignar; la causa no se determinó (parece que el registro no generó grupos).
- Esperado: las filas de USDA de un nombre que la propia semilla resuelve a la planta se asignan a ella (escenario «Sinónimo resuelto»).
- Reproducir: `GET /v1/plants/chromolaena-odorata` (0 usos) frente a la base anterior (`eupatorium-odoratum`, 31 usos). Tabla: `evidence/ids/lost-uses-reasons.tsv`.
- Evidencia: `evidence/ids/lost-uses.tsv`, `evidence/ids/lost-uses-reasons.tsv`.

### DEF-04 (media): buscar por el nombre científico anterior no encuentra la planta en 357 de 628 casos, entre ellos `Matricaria recutita`

- Requerimiento: tarea 10.3 (búsqueda por sinónimo) y `catalog-seed`, regla de colisiones (un heterotípico fusionado deja su nombre como sinónimo y alias). La propuesta cita `matricaria-recutita` como ejemplo del cambio. Contradice la regla de colisiones en parte (véase abajo); en el resto es una regresión de la búsqueda frente a la API anterior, que encontraba estas plantas por el nombre de USDA.
- Obtenido: solo los sinónimos que el registro lista (sobre todo homotípicos de WCVP) están en los nombres de la planta, y la API busca en nombres. `q=matricaria recutita` y `q=mentha piperita` dan 0 resultados. De los 357 nombres anteriores no encontrados, 181 eran heterotípicos resueltos al aceptado, 135 nombres que USDA tenía como aceptados y 41 homotípicos. Entre las 45 plantas con el flag `fusion-heterotipica`, hasta 15 no listan alguno de los nombres fusionados como sinónimo (por ejemplo `cascabela-thevetia` sin `Thevetia neriifolia`), lo que contradice «su nombre queda como sinónimo y alias».
- Esperado: el nombre anterior de una planta (la API anterior lo encontraba) sigue encontrando la planta, o al menos el que la regla de colisiones manda conservar.
- Reproducir: `GET /v1/plants?q=matricaria%20recutita` (0 resultados) y `GET /v1/plants/matricaria-chamomilla` (no hay `Matricaria recutita` en `names`).
- Evidencia: `evidence/api/API-03.txt`, `evidence/api/API-04.txt`, `evidence/api/API-04-old-names-not-found.tsv`.

### DEF-05 (baja): buscar un híbrido escrito con `x` no lo encuentra

- Requerimiento: tarea 10.3 (búsqueda por sinónimo); regresión frente a la API anterior.
- Obtenido: los nombres con `×` (43 plantas; antes 11 con `x`) no coinciden con una consulta que usa la letra `x`: `q=mentha x piperita` y `q=rosmarinus x lavandulaceus` dan 0 resultados; con `×` sí se encuentran. La normalización de búsqueda (`catalog-core/src/normalize.rs`) no equipara ambos.
- Esperado: encontrar `Mentha × piperita` al escribir `mentha x piperita`.
- Reproducir: `GET /v1/plants?q=mentha%20x%20piperita` frente a `q=mentha%20%C3%97%20piperita`.
- Evidencia: `evidence/api/API-03.txt`, `evidence/api/API-04.txt`.

### DEF-06 (media): la cita de cada uso es una etiqueta, no la cita completa

- Requerimiento: `backend/openapi.json` («Cita completa») y `plant-passport` («la cita de su referencia»). Es una decisión documentada (`design.md:99`: «El `label` de las referencias de la semilla va a `citation`»), por lo que no contradice el diseño, pero cambia lo que ve el usuario.
- Obtenido: los 24.286 usos devuelven `reference.citation` como `USDA Dr. Duke: referencia Steinmetz`, `USDA Dr. Duke: referencia NAS2`, etc. La base anterior devolvía la cita completa (`Steinmetz, E.F. 1957. codex Vegetabilis...`). La cita completa existe en la semilla (`traditionalUses[].citations[].text`) y en `plant_use_group_ref`, pero la API no la sirve. Los usos usan solo 39 referencias distintas (por ejemplo `WOI` para todos los volúmenes de «The Wealth of India»).
- Esperado: o la cita completa en `citation`, o confirmar que el cambio 2 la expone y que mientras tanto la app muestra la etiqueta.
- Reproducir: `GET /v1/plants/eleutherococcus-nodiflorus`, campo `uses[0].reference.citation`.
- Evidencia: `evidence/api/API-07.txt`, `evidence/api/API-05-*.txt`.

### DEF-07 (baja): documentación con cifras desactualizadas y 187 grupos de uso con la actividad sin traducir

- Cifras: `docs/data/modelo-de-datos.md:240`, `proposal.md:17` y `design.md:132` dicen «unos 500» IDs que cambian (son 629: 527 renombrados, 101 fusionados y 1 ausente); `tools/catalog-seed/README.md:1025` dice 1.748 conservados y ninguno perdido (son 1.747 y 1 ausente, `malachra-alaceaefolia`); la propuesta habla de unas 2.411 plantas (son 2.354).
- Traducción: en 1.033 de 17.276 grupos de uso la actividad es igual a la original; la mayoría son cognados válidos (`Anemia`, `Edema`), pero hay términos en inglés sin traducir: `Fumitory` (39 grupos), `Aperient` (22), `Gravel` (20), `Antivinous`, `Ague`, `Bilious`, `Boil`, `Corn`, `Hairblack`, `Wen`, `Stone`, `Sore`, `Flux`, `Canker` y otros (187 grupos y 228 usos de los 20 términos revisados). La revisión de la tarea 10.5 debería cubrirlo.
- Evidencia: consulta sobre `plant_use_group` (`activity = activity_source`) en `data/build/catalog.db`.

## Observaciones

- La API local no registra una línea por petición con `RUST_LOG=info`; la evidencia de la API sale de las respuestas.
- `data/work/bundles` tiene 2.355 paquetes frente a 2.354 registros: el sobrante es `malachra-alaceaefolia`, la planta ausente.
- `cynara-cardunculus-subsp-cardunculus` (un ID anterior que se conserva, 0 usos antes) ahora es la planta de la alcachofa (`Cynara scolymus` queda como alias); `cynara-cardunculus` es una planta nueva que absorbe la entrada `usda:344` del mismo nombre. Mismo ID, mismo nombre científico, otro contenido (15 usos). No es un defecto de ID, pero puede confundir al revisar fusiones.
- El 404 de los IDs anteriores (por ejemplo `rosmarinus-officinalis`) es el comportamiento esperado de este cambio; la resolución por alias es del cambio 2.
- `manzanilla` por nombre común también encuentra `chamaemelum-nobile` y `hippomane-mancinella` (nombres como «manzanilla» o «manchineel»); es una búsqueda por subcadena y no un defecto.

## Cobertura y riesgos residuales

- No se probó en Android ni en un dispositivo (restricción de la tarea): el smoke se ejecutó en el host. Rendimiento en teléfono, teclado y accesibilidad de la app quedan sin probar en este cambio.
- No se reconstruyó la imagen Docker (`docker build`, hash de la imagen): la tarea 11.5 ya lo registra; aquí solo se verificó la construcción nativa con el mismo hash.
- No se probó contra Cloud Run ni el workflow de despliegue (solo la presencia del ID que verifica y la respuesta local).
- No se evaluó la calidad del contenido (dosis, eficacia, traducciones sensibles): es la tarea 10.5.
- Las 923 plantas sin usos (39 %) se deben, en su mayoría, a que USDA no tiene filas para ellas (no hay forma de verificarlo planta por planta aquí); solo se comprobaron las 26 que perdieron usos.
- La comparación de nombres anteriores usa el nombre científico de la base anterior; los nombres comunes anteriores (en inglés) no se compararon uno a uno.

## Cómo re-ejecutar

- Base anterior: `git worktree add --detach <tmp>/main-wt main`, copiar `data/.cache/Duke-Source-CSV.zip` a `<tmp>/main-wt/data/.cache/` y, desde ahí, `CARGO_TARGET_DIR=<tmp>/target-main mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- build`. Quitar el worktree con `git worktree remove --force`.
- 10.1: `python3 -I qa/scripts/compare_bases.py <old catalog.db> data/build/catalog.db data/seed qa/evidence/ids data/work`, luego `qa/scripts/make_id_report.py qa/evidence/ids/id-map.tsv qa/evidence/ids/id-map-summary.json qa/informe-ids.md` y `qa/scripts/lost_uses_reasons.py qa/evidence/ids/lost-uses.tsv data/work/usda/assignment-report.json data/seed/plants`. `data/work` es local y no se versiona.
- 10.2: `python3 -I qa/scripts/grep_ids.py . qa/evidence/ids/id-map.tsv qa/evidence/ids/grep-ids.tsv`.
- 10.3: `API_TOKENS=$(openssl rand -hex 32)` (guardar en una variable) y `catalog-api` con `CATALOG_DB=data/build/catalog.db`; luego `QA_TOKEN=<token> QA_DB=data/build/catalog.db QA_OLD_MAP=qa/evidence/ids/id-map.tsv python3 -I qa/scripts/api_tests.py . qa/evidence/api` y `npx --yes newman@6.2.1 run qa/postman/consolidate-catalog-seed.collection.json --env-var "token=<token>"`. La colección se regenera con `qa/scripts/make_postman_collection.py`.
- 10.4: desde `app/`, `flutter analyze`, `flutter test` y `flutter test integration_test/app_test.dart -d flutter-tester --dart-define=API_BASE_URL=http://127.0.0.1:8080 --dart-define=API_TOKEN=<token>`.
- Herramientas instaladas: ninguna en el proyecto. Newman 6.2.1 se descarga con `npx` en su caché.
