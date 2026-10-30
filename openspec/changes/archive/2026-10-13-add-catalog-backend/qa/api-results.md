# Resultados de QA: API y CLI del catálogo

Cambio OpenSpec `add-catalog-backend`, commit `c4f7939`, entorno local (macOS, `rustc 1.99.0` vía mise, API release en `127.0.0.1:18100`, datos reales USDA: 2376 plantas). Fecha: 2026-10-12.

## Resumen ejecutivo

**Primera ejecución (commit `c4f7939`):** 73 casos, 64 PASS, 5 FAIL, 4 NOT RUN. Los 5 FAIL eran 4 defectos (1 media, 3 bajas), sin ningún 500 provocado por entradas de cliente.

**Re-ejecución tras las correcciones (commit `7e13c1e`):** se repitieron los casos afectados (ENV-015, ENV-016, API-034, API-035 y API-036) y toda la batería de regresión (`run-api-tests.sh`, `run-env-tests.sh`, `run-cli-tests.sh`, Newman, validación Ajv y la prueba `cargo test -p catalog-api openapi`). Resultado final: **69 PASS, 0 FAIL, 4 NOT RUN** sobre 73 casos. Solo CONC-001 (carga ligera) no se repitió y conserva su PASS original. Los cuatro defectos quedan **Corregidos (verificados)**. No hay regresiones; sí un cambio de comportamiento a tener en cuenta (observación O-1: `q` con tabulador o salto de línea ahora da 400).

El comportamiento especificado se cumple: los escenarios de la spec de `catalog-api` pasan contra la base real, el recorrido paginado con `limit=100` devuelve exactamente las 2376 plantas únicas en el orden de la base, el barrido de las 2376 fichas de detalle coincide con la base (18931 usos, 6740 partes, 5296 nombres, 1180 plantas con usos, 34 sin familia) y 2409 respuestas reales validan contra los esquemas del `openapi.json` (también contra el nuevo, con los 405 documentados). La CLI cumple la idempotencia de `download`, el mismo hash en `build` y `rederive` (`48d71b6b...`), los fallos con código 1 y la capa cruda es idéntica celda a celda a los 16 CSV del ZIP.

Estado de los defectos (detalle más abajo):

- D-001 (media): arranque lento e inundación de logs con una base ilegible. **Corregido (verificado)**: ahora sale con código 1 en menos de 1 s con una sola línea de error que incluye la ruta.
- D-002 (baja): un carácter NUL en `q` alteraba la búsqueda. **Corregido (verificado)**: NUL y demás caracteres de control dan 400 con `param = q`.
- D-003 (baja): `offset` aceptaba valores fuera de `int32`. **Corregido (verificado)**: 200 hasta 2147483647 y 400 con `param = offset` desde 2147483648.
- D-004 (baja): el OpenAPI no documentaba el 405 ni `/openapi.json`. **Corregido (verificado)**: el 405 está en todas las rutas, `/openapi.json` es una ruta y el 404 de rutas desconocidas figura en `info.description`.

## Tabla de resultados

Pasos, esperado y evidencia de cada caso están en `test-plan-api.md`. La evidencia cruda está en `evidence/` con el ID como prefijo.

| ID | Resultado (c4f7939) | Re-ejecución (7e13c1e) | Descripción |
|---|---|---|---|
| API-001 | PASS | PASS | GET /healthz responde 200 con status ok |
| API-002 | PASS | PASS | GET /v1/sources trae usda/CC0 y coincide con la base |
| API-003 | PASS | PASS | Listado sin q: 20 elementos, total 2376, orden por nombre científico |
| API-004 | PASS | PASS | Elemento: id, nombre científico, nombres comunes con idioma y family (null si no existe) |
| API-005 | PASS | PASS | Recorrido completo limit=100: 2376 elementos únicos, sin omisiones, orden total |
| API-006 | PASS | PASS | Desplazamiento: limit=5&offset=10 devuelve los elementos 11..15 del orden |
| API-007 | PASS | PASS | offset >= total: lista vacía, total conservado; offset=total-1: 1 elemento |
| API-008 | PASS | PASS | Valores límite válidos de limit (1 y 100) |
| API-009 | PASS | PASS | limit inválido (0, -1, 101, abc, vacío, 1e3, 1.5, desbordado) -> 400 problem+json con param=limit |
| API-010 | PASS | PASS | offset inválido (-1, abc, 1.5, vacío, desbordado) -> 400 problem+json con param=offset |
| API-011 | PASS | PASS | q de 200 caracteres admitido (también multibyte), 201 -> 400 con param=q |
| API-012 | PASS | PASS | q=lavandula: plantas con la subcadena y total de la base |
| API-013 | PASS | PASS | Búsqueda por nombre común (peppermint, rosemary) |
| API-014 | PASS | PASS | Insensibilidad a mayúsculas, acentos (NFC y NFD) y espacios repetidos o exteriores |
| API-015 | PASS | PASS | q vacío o solo espacios == sin q |
| API-016 | PASS | PASS | % y _ (y \) son texto literal; Paperbark Tea_tree se encuentra |
| API-017 | PASS | PASS | Sin coincidencias: 200, lista vacía, total 0 |
| API-018 | PASS | PASS | Paginación estable dentro de una búsqueda (q=a, limit=50) |
| API-019 | PASS | PASS | Detalle de plantas de referencia coincide con la base (conteos, familia, atribución, claves) |
| API-020 | PASS | PASS | Detalle de lavandula-angustifolia idéntico a la base (usos+citas, partes, nombres) |
| API-021 | PASS | PASS | Planta sin usos: lista de usos vacía |
| API-022 | PASS | PASS | Planta sin familia: family == null en el detalle |
| API-023 | PASS | PASS | Id inexistente: 404 problem+json |
| API-024 | PASS | PASS | Ruta desconocida: 404 problem+json |
| API-025 | PASS | PASS | POST/PUT/DELETE/PATCH -> 405 problem+json con Allow: GET (recursos de /v1, /healthz y /openapi.json) |
| API-026 | PASS | PASS | HEAD/OPTIONS observados (ver API-026.note) |
| API-027 | PASS | PASS | /openapi.json 200 y JSON idéntico a backend/openapi.json |
| API-028 | PASS | PASS | Todas las claves JSON en camelCase |
| API-029 | PASS | PASS | Barrido de las 2376 plantas: todas 200; 18931 usos, 6740 partes, 5296 nombres; 1180 con usos; 34 sin familia |
| API-030 | PASS | PASS | Robustez: ningún 5xx ni fuga de detalles internos (códigos observados en API-030.note) |
| API-031 | PASS | PASS | Errores conservan application/problem+json con Accept inesperado |
| API-032 | PASS | PASS | Cuerpo de error: type, title, status, detail, param e instance (RFC 9457) |
| API-033 | PASS | PASS | Ninguna petición modifica la base (md5 antes/después, sin archivos -wal/-journal) |
| API-034 | FAIL | PASS | offset respeta el formato int32 que declara el OpenAPI (2147483648 -> 400) |
| API-035 | FAIL | PASS | q con carácter NUL se comporta como texto inexistente (0 coincidencias) o da 400 |
| API-036 | FAIL | PASS | El OpenAPI documenta los códigos observados (405) y la ruta /openapi.json |
| ENV-001 | PASS | PASS | Sin HOST ni PORT escucha en 127.0.0.1:8080 (base por defecto data/build/catalog.db) |
| ENV-002 | PASS | PASS | Base ausente: sale con código 1 y el mensaje indica ruta y cómo construirla |
| ENV-003 | PASS | PASS | schema_version distinta: no arranca, indica versión encontrada y soportada |
| ENV-004 | PASS | PASS | Bases inválidas (schema_version no numérica, metadata vacía o ausente, archivo basura, vacío, directorio): salen con código 1 y mensaje, sin pánico |
| ENV-005 | PASS | PASS | El argumento --db tiene prioridad sobre CATALOG_DB |
| ENV-006 | PASS | PASS | PORT/HOST inválidos o puerto ocupado: salen con código 1 y mensaje sin pánico |
| ENV-007 | PASS | PASS | catalog-api --openapi imprime el documento versionado |
| ENV-008 | PASS | PASS | Argumento desconocido no arranca el servidor; --help sale con 0 |
| ENV-009 | PASS | PASS | La API funciona con la base de solo lectura (0444) en directorio sin escritura y no crea archivos auxiliares |
| ENV-010 | PASS | PASS | Empate de nombre científico (5 plantas con el mismo nombre en una copia): orden por id y paginación sin repetidos ni omisiones |
| ENV-011 | PASS | PASS | Dato aportado por dos fuentes (copia con fuente fixture2 añadida): el detalle indica ambas |
| ENV-012 | PASS | PASS | Base con una única fuente distinta de USDA (copia con la fuente renombrada) funciona sin cambios de código |
| ENV-013 | PASS | PASS | Fallo interno (tablas rotas en una copia): 500 problem+json genérico sin detalles; el detalle va al log; el servicio sigue vivo |
| ENV-015 | FAIL | PASS | El arranque con una base ilegible (no SQLite, directorio) falla rápido |
| ENV-016 | FAIL | PASS | El arranque con una base que no es SQLite no inunda la salida con errores repetidos |
| ENV-014 | PASS | PASS | La base real data/build/catalog.db no cambió durante las pruebas de entorno |
| CLI-001 | PASS | PASS | download es idempotente: segunda ejecución dice 'ya estaba', sin tocar el ZIP |
| CLI-002 | PASS | PASS | build, build y rederive producen el mismo hash (y el de referencia 48d71b6b...) |
| CLI-003 | PASS | PASS | La base reconstruida en un directorio temporal tiene el mismo volcado SQL que data/build/catalog.db |
| CLI-004 | PASS | PASS | catalog.db solo esquema neutral; raw.db conserva las 16 tablas del ZIP celda a celda |
| CLI-005 | PASS | PASS | rederive funciona sin el ZIP (solo con raw.db) y da el mismo hash |
| CLI-006 | PASS | PASS | Cambio en un dato del crudo -> hash distinto |
| CLI-007 | PASS | PASS | build sin .cache falla (código 1) indicando el paso de descarga y no deja base |
| CLI-008 | PASS | PASS | rederive sin raw.db falla (código 1) indicando la importación cruda y no deja base |
| CLI-009 | PASS | PASS | Insumo alterado (checksum, tamaño, vacío): build falla con código 1, lo indica y no deja base |
| CLI-010 | PASS | PASS | Tras un build fallido sobre un directorio con base previa no quedan temporales (ver CLI-010.note) |
| CLI-011 | PASS | PASS | Configuración de fuentes inválida (fuente desconocida, archivo ausente, TOML inválido) falla con código 1 y mensaje |
| CLI-012 | PASS | PASS | Argumentos inválidos terminan con código distinto de 0 y sin pánico; --help sale con 0 |
| CLI-013 | PASS | PASS | data/build/catalog.db no cambió durante las pruebas de la CLI |
| CONTRACT-001 | PASS | PASS | 2409 respuestas reales (25 páginas, 2376 detalles, fuentes, salud, 400, 404, 405) validan contra los esquemas de `openapi.json` |
| NEWMAN-001 | PASS | PASS | Colección Newman: 29 peticiones, 76 aserciones, 0 fallos |
| OPENAPI-001 | PASS | PASS | `cargo test -p catalog-api openapi`: el documento versionado coincide con el generado (5 pruebas) |
| CONC-001 | PASS | no repetido | 900 peticiones con 30 en paralelo: todas 200 |
| NR-001 | NOT RUN | NOT RUN | Documento desactualizado: exige modificar el producto |
| NR-002 | NOT RUN | NOT RUN | Compatibilidad dentro de `/v1`: regla de proceso, sin comportamiento observable |
| NR-003 | NOT RUN | NOT RUN | Requisitos de ingesta que exigen datos o adaptadores inconsistentes: los cubren los tests del workspace |
| NR-004 | NOT RUN | NOT RUN | `build` sin acceso a la red: no se pudo observar la red; verificación indirecta |

## Defectos

Se conservan la descripción y los pasos de reproducción de la primera ejecución (commit `c4f7939`); el estado y la verificación posterior están al inicio de cada defecto.

### D-001 (media): arranque lento e inundación de logs con una base ilegible

- **Estado: Corregido (verificado)** en `7e13c1e`. Re-ejecución (ENV-015 y ENV-016, `evidence/ENV-004d.rerun.*`, `ENV-004f.rerun.*`, `ENV-015.rerun.note`, `ENV-016.rerun.note`): con un archivo que no es SQLite y con una ruta que es un directorio, el proceso sale con código 1 en menos de 1 s (0 s medidos; antes 30 s), con 0 líneas en stdout (antes 722.758) y una sola línea en stderr que incluye la ruta (`no se pudo arrancar: fallo de almacenamiento: base del catálogo en <ruta>: file is not a database` y `no se pudo abrir la base del catálogo en <ruta>: disk I/O error`). Los demás fallos de arranque (ENV-002, ENV-003, ENV-004a a ENV-004e, ENV-006) no cambiaron.

- Requisito afectado: `catalog-api`, "Arranque y configuración" (el arranque debe fallar con un mensaje claro). La spec solo exige mensajes claros para base ausente y esquema incompatible, de modo que el defecto está en la calidad operativa del fallo, no en un escenario literal.
- Casos: ENV-015 y ENV-016.
- Pasos para reproducir: `printf 'esto no es sqlite\n' > /tmp/basura.db`; `CATALOG_DB=/tmp/basura.db PORT=18102 backend/target/release/catalog-api > salida.txt 2> error.txt; echo $?; wc -l salida.txt`. Variante: `CATALOG_DB=/tmp` (un directorio).
- Esperado: salida inmediata (o en pocos segundos) con código 1 y un mensaje claro, con pocas líneas de log.
- Observado: el proceso tarda unos 30 s en salir (31 s con un directorio); durante ese tiempo escribe 722.758 líneas (69.384.768 bytes) `ERROR r2d2: file is not a database` en la salida estándar (con un directorio, `disk I/O error`, 28 líneas) y termina con código 1 y el mensaje `no se pudo arrancar: fallo de almacenamiento: timed out waiting for connection: file is not a database`. Es el reintento del pool de conexiones hasta agotar su tiempo de espera. Con un archivo vacío falla al instante (`no such table: metadata`), así que el problema solo aparece cuando falla la apertura misma.
- Impacto: en un contenedor, un volumen mal montado o una base truncada llenaría los logs y retrasaría la señal de fallo. No afecta a las peticiones.
- Evidencia: `evidence/ENV-004d.stderr`, `ENV-004d.stdout.sample`, `ENV-004d.stdout.lines`, `ENV-004d.secs`, `ENV-004f.*`, `ENV-015.note`, `ENV-016.note`.

### D-002 (baja): un NUL en `q` altera la búsqueda

- **Estado: Corregido (verificado)** en `7e13c1e`. Re-ejecución (API-035, `evidence/API-035.rerun.*`): `q` con `%00zzzz`, `a%00zzzz`, `lavandula%00zzzz`, `a%00`, `%0A`, `a%0Ab`, `%09`, `blue%09gum`, `%1F`, `%7F` y `%C2%85` da 400 `application/problem+json` con `param = q` y `detail` "q no puede contener caracteres de control". Los espacios Unicode que no son de control (NBSP exteriores) siguen dando 200. Efecto colateral en la observación O-1.

- Requisito afectado: "Listado y búsqueda de plantas" (`q` filtra por subcadena; ninguna otra cosa que no sea texto literal debe actuar como patrón).
- Caso: API-035.
- Pasos para reproducir (API en 18100): `curl -s 'http://127.0.0.1:18100/v1/plants?q=%00zzzz&limit=1' | jq .total`; `curl -s 'http://127.0.0.1:18100/v1/plants?q=a%00zzzz&limit=1' | jq .total`.
- Esperado: 0 en ambos (ningún nombre contiene `zzzz`), o un 400 por carácter no válido.
- Observado: 2376 y 1225. El patrón `LIKE` llega a SQLite con el NUL y SQLite lo trunca ahí: `%\0zzzz%` pasa a ser `%` (todo el catálogo) y `%a\0zzzz%` pasa a ser `%a` (nombres que terminan en `a`; coincide con el total 1225, que no es el de `q=a`, 2280). `q=lavandula%00zzzz` da 0 por la misma razón (`%lavandula`).
- Impacto: bajo; el cliente legítimo no envía NUL. No hay fuga de datos ni error 5xx.
- Evidencia: `evidence/API-035.note`, `API-035.q__00zzzz_.body`, `API-035.q_a_00zzzz_.body`.

### D-003 (baja): `offset` acepta valores fuera de `int32`

- **Estado: Corregido (verificado)** en `7e13c1e`. Re-ejecución (API-034, `evidence/API-034.rerun.*`): `offset=2147483647` da 200 con `items` vacío y `total` 2376; `2147483648`, `4294967295` y `4294967296` dan 400 `application/problem+json` con `param = offset`. El documento declara `maximum: 2147483647`.

- Requisito afectado: "Documento OpenAPI" (el documento describe lo que la API hace) y "Paginación".
- Caso: API-034.
- Pasos para reproducir: `curl -s 'http://127.0.0.1:18100/v1/plants?offset=2147483648&limit=1'` y `...offset=4294967295...`; luego `...offset=4294967296...`.
- Esperado: según `openapi.json` (`type: integer, format: int32, minimum: 0`), el máximo es 2147483647 y 2147483648 debería ser 400.
- Observado: 200 con `items` vacío y `"offset":2147483648` (y también con 4294967295); el 400 (`offset es demasiado grande`) aparece desde 4294967296. El código usa `u32`, que utoipa documenta como `int32`. La respuesta 200 con `offset` 4294967295 también incumple el `format: int32` del esquema `PageDto`, aunque el validador de esquemas no lo señaló porque no se probó con ese valor en CONTRACT-001.
- Impacto: mínimo; basta alinear el esquema (`format: int64`/`uint32`) o el límite.
- Evidencia: `evidence/API-034.*`, `evidence/API-010-big.*`.

### D-004 (baja): el OpenAPI no documenta el 405 ni `/openapi.json`

- **Estado: Corregido (verificado)** en `7e13c1e`. Re-ejecución (API-036, `evidence/API-036.rerun.*`): las cinco rutas (`/healthz`, `/openapi.json`, `/v1/plants`, `/v1/plants/{id}`, `/v1/sources`) declaran el 405 con `application/problem+json`; `/openapi.json` es una ruta del documento; `info.description` dice "Las rutas desconocidas responden 404 y los métodos distintos de `GET` responden 405, ambos como `application/problem+json`". El 404 por ruta sigue solo en `/v1/plants/{id}`: me parece suficiente, porque es la única ruta con un 404 propio (recurso inexistente) y el 404 de rutas desconocidas es global y queda descrito en `info.description`. El documento servido en `/openapi.json` coincide con `backend/openapi.json`, y las 2409 respuestas reales siguen validando contra los esquemas.

- Requisito afectado: "Documento OpenAPI" y "Errores estandarizados" (el 405 es un error estándar de la spec).
- Caso: API-036.
- Pasos para reproducir: `jq '[.paths[][]?.responses|has("405")]|any' backend/openapi.json` devuelve `false`; `jq '.paths|keys' backend/openapi.json` no incluye `/openapi.json`; `curl -si -X POST http://127.0.0.1:18100/v1/plants` devuelve 405 con `Allow: GET`.
- Esperado: el 405 y su cabecera `Allow` documentados al menos en las rutas de `/v1`; el 404 de rutas desconocidas es global y está documentado solo en `/v1/plants/{id}` (comportamiento aceptable pero incompleto); la ruta `/openapi.json` descrita o excluida expresamente.
- Observado: ninguno de los dos aparece. El resto del contrato coincide: cada código documentado se pudo provocar (200, 400 por parámetro y por id con bytes inválidos `%FF`, 404, 500 con la base rota de ENV-013) y no se observó ningún otro código en las rutas de `/v1` salvo 405 y 414 (URI de 100.000 caracteres, respuesta del servidor HTTP sin cuerpo).
- Evidencia: `evidence/API-025.*`, `evidence/API-030.note`, `backend/openapi.json`.

## Observaciones (sin severidad)

- Parámetros repetidos: gana el último (`limit=1&limit=2` devuelve 2 elementos; `q=lavandula&q=rosemary` busca `rosemary`). Los nombres de parámetro distinguen mayúsculas (`LIMIT`, `Q` se ignoran). `limit=007` y `limit=%2B5` se aceptan como 7 y 5.
- `q` de 300 espacios devuelve 400 (el límite de 200 se aplica antes de normalizar), aunque la spec dice que un `q` solo de espacios lista todo; es coherente con la decisión de limitar `q` a 200 caracteres.
- El campo `instance` del 404 repite la ruta pedida completa (un id de 10.000 caracteres produce un cuerpo de 10 KB); con 100.000 caracteres el servidor responde 414 sin cuerpo.
- `HEAD` responde 200 y `OPTIONS` responde 405 con `Allow: GET`. No hay cabeceras CORS (no se pidieron).
- Cualquier cabecera `Accept` recibe `application/json`; los errores conservan `application/problem+json`. No hay negociación de contenido (ni 406).
- Los ids distinguen mayúsculas: `LAVANDULA-ANGUSTIFOLIA` da 404.
- Los errores de configuración de la CLI y de la API terminan con código 2 (argumentos, `PORT` inválido) y los de ejecución con código 1.
- Un `build` fallido sobre un directorio con una base válida previa conserva esa base intacta (sin temporales); no es una base parcial.
- O-1 (cambio de comportamiento, posible regresión menor): desde `7e13c1e`, `q` con tabulador, salto de línea u otro carácter de control da 400. En `c4f7939` esos caracteres se trataban como espacios (API-014 y API-015 usaban un tabulador y pasaban). La spec habla de "espacios repetidos o exteriores" sin precisar si el tabulador cuenta, y el coordinador pidió rechazar los controles, por lo que no lo registro como defecto; los casos API-014 y API-015 se ajustaron (sin tabulador) y el tabulador pasó a API-035. Conviene que el cliente recorte el texto antes de enviarlo.
- Los NBSP y otros espacios Unicode que no son de control siguen aceptándose en `q`.
- Apagado ordenado: al enviar SIGTERM la API registra `apagado completado`.

## Datos verificados contra la base

- `total` sin filtro: 2376, igual que `select count(*) from plant`.
- `/v1/sources`: una fuente `usda`, licencia `CC0`, cita y URL idénticas a la tabla `source`, `checksum` `45ae44a0544586b8ac22a232beaac344`.
- Detalle de `lavandula-angustifolia`: 10 usos (actividad, idioma, id de referencia y cita), 4 partes y los nombres (`Lavandula angustifolia` científico, `English Lavender` común `en`), familia Lamiaceae, todo atribuido a `usda`.
- Totales del barrido: 18931 usos, 6740 partes y 5296 nombres (2376 científicos y 2920 comunes, de ellos 208 con idioma `und`), 1180 plantas con usos, 34 sin familia, 32 referencias en la base.
- Hash de contenido: `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d` en `build`, segundo `build` y `rederive` en un directorio temporal, igual al del informe 9.1-9.2; el volcado SQL de esa base es idéntico al de `data/build/catalog.db`.

## Limitaciones

- No se ejecutó (NOT RUN): documento OpenAPI desactualizado, compatibilidad dentro de `/v1`, requisitos de ingesta que exigen datos inconsistentes o adaptadores de fixture (metadatos incompletos, identidad repetida, colisión de slug, referencia que no resuelve, dato sin fuente, prioridad de campos de valor único) y la ausencia de red durante `build`. Los cubren los tests del workspace; esta QA no los repitió.
- El empate de nombre científico, la atribución con dos fuentes, la base de una fuente distinta de USDA y el fallo interno 500 se probaron con copias manipuladas de `catalog.db` (SQL directo en un directorio temporal), no con bases construidas por la ingesta. La base real no tiene empates ni datos de varias fuentes.
- La insensibilidad a acentos y mayúsculas se probó con las entradas listadas; no se barrió Unicode (por ejemplo `ß`, `İ` o ligaduras). Los datos de USDA son ASCII.
- No se midió rendimiento más allá de 900 peticiones con 30 en paralelo ni se probó con la API expuesta fuera de loopback.
- La ruta por defecto `127.0.0.1:8080` se probó con el puerto libre; `HOST` distinto de loopback no se probó.
- `download` solo se ejecutó con el ZIP ya verificado (no se forzó una descarga real).
- Sin pruebas de interfaz ni accesibilidad: no hay UI. La autenticación no existe por diseño; solo se comprobó que ninguna ruta la pide.

## Cómo re-ejecutar y herramientas

Los comandos están en `test-plan-api.md`. Los scripts aceptan `EV_DIR` para redirigir la evidencia; la re-ejecución se guardó con el sufijo `.rerun` (`API-034.rerun.body`, `results-api.rerun.tsv`, `newman-report.rerun.json`, `CONTRACT-001.rerun.json`, `OPENAPI-test.rerun.txt`, `api-server.rerun.log`). Scripts y archivos en `openspec/changes/add-catalog-backend/qa/`: `run-api-tests.sh`, `run-env-tests.sh`, `run-cli-tests.sh`, `check_raw.py`, `validate-contract.mjs`, `postman/` (colección generada por `generate_collection.py`, entorno con `baseUrl`) y `evidence/`.

Instalado o usado fuera del proyecto: Newman 6.2.3 mediante `npx --yes newman` (caché de npx, sin cambios en el proyecto) y el paquete `ajv` instalado con `npm i ajv` en un directorio temporal de la sesión (el script lo busca en `AJV_DIR`). Se usaron `curl`, `jq`, `sqlite3`, `python3` (solo biblioteca estándar) y Node 26. Para `OPENAPI-001` se ejecutó `cargo test -p catalog-api openapi`, que compiló artefactos de depuración en `backend/target/` (ignorado por git). En la re-ejecución se recompiló `catalog-api` (y `catalog-ingest`) en release desde `7e13c1e`. No se tocó nada fuera de la carpeta de QA; `data/build/catalog.db` conserva su md5 (`29869f77ebc296c8abdd094c0286e98f`) y los puertos 8080 y 18100 a 18104 quedaron libres (`lsof -ti`) también tras la re-ejecución.
