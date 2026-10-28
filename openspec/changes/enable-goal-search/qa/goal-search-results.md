# Resultados de QA: enable-goal-search (cambio 3)

Alcance: tareas 6.1, 6.2, 6.3, 6.4 y 6.6 de `tasks.md`. El plan, con sus casos y la trazabilidad, está en `test-plan-goal-search.md`. Rama `enable-goal-search`, commits `3c86408` a `839fcc1`. QA ejecutada el 2026-10-27 y 2026-10-28 (UTC). La 6.5 (revisar los nombres con el usuario) queda para el orquestador con la evidencia de `evidence/app/review/`.

## Resumen

- 6.1: plan escrito, con 109 escenarios de los cuatro deltas trazados a casos (el script `scripts/traceability.py` falla si alguno queda sin caso). Cumplida.
- 6.2: 24 casos de API con 308 comprobaciones que pasan, 0 que fallan y 32 observaciones, más la colección de Postman (29 peticiones, 138 aserciones, 0 fallos) y un control negativo. Cumplida sin defectos.
- 6.3: 18 casos de interfaz en el emulador `boticario_catalog_api36`. Todos pasan salvo UI-18 (DEF-01, severidad baja: el título `Recomendaciones` se parte a mitad de palabra con el texto al 200 %). Cumplida con ese defecto registrado.
- 6.4: las 175 plantas con objetivo y las 287 tarjetas de las once listas de P07 (cinco objetivos y seis subáreas) revisadas por censo, sin lenguaje de eficacia ni dosis, sin plantas tóxicas y con la atribución de cada miniatura mostrada completa. Hay observaciones de contenido para la 6.5. Cumplida.
- 6.6: este informe. `openspec validate enable-goal-search --strict` pasa. El Markdown se verificó con `check-md-lines.py`.

Números: 109 escenarios, 108 con estado PASA y 1 con FALLA (el de texto aumentado de P07, por DEF-01).

## Defectos

### DEF-01 (baja): el título de P07 se parte a mitad de palabra con el texto al 200 %

- Requerimiento: `goal-results-screen`, «Adaptación accesible de P07», escenario «Texto aumentado» (contenido esencial legible).
- Pasos: en el emulador (360x640 dp), `adb shell settings put system font_scale 2.0`; abrir Inicio, `Buscar por objetivo`, `Mejorar el sueño`.
- Obtenido: el título se dibuja como `Recomendacion` y `es` en dos líneas (la palabra se corta porque el ancho disponible entre los botones laterales no admite la palabra entera).
- Esperado: título legible sin partir la palabra (por ejemplo, reducir el tamaño del título o reservar menos ancho a los lados).
- Evidencia: `evidence/app/flows/200pct-p07-primera.png` y `evidence/app/flows/scale.txt`.
- No hay desbordes ni excepciones de renderizado en el registro, el resto del contenido es alcanzable con scroll y todos los controles miden 48 dp o más.

No se encontraron más defectos.

## Observaciones (no son defectos)

- OBS-01: miniaturas que no cargan de forma intermitente. En el barrido completo de las once listas, 28 de 252 tarjetas con imagen en la API (11 %) mostraron el arte local sin crédito porque la miniatura no había llegado mientras la tarjeta estuvo en pantalla (18 de ellas en `Vías urinarias y genitales`). Es el comportamiento que fija la spec (arte local y sin atribución si no carga). Repetido más tarde con la app recién iniciada, la misma lista cargó 41 de 41 y `Cuidado de la piel` 27 de 27; `Taraxacum officinale` y `Juniperus communis` cargaron al volver a verlas. El fallo es transitorio y no se reintenta solo mientras la tarjeta sigue construida. Las comprobaciones directas de esas URL desde el Mac devolvieron 200. Evidencia: `evidence/app/lists/*.json`, `evidence/app/lists-repeticion/`.
- OBS-02: salto de diseño al llegar la miniatura. La tarjeta crece unos 10 dp cuando la imagen carga (aparece la línea `Foto: ...`), y el contenido de debajo se desplaza. Es consecuencia de mostrar la atribución solo con la imagen cargada.
- OBS-03: la hoja `Sobre estas recomendaciones` se cierra con `Cerrar`, con Atrás del sistema y arrastrando desde el asa, pero no arrastrando el cuerpo del texto (el gesto lo consume el `SingleChildScrollView`). La spec dice «deslizándola»: se cumple con el asa. Evidencia: `evidence/app/flows/sheet.txt`.
- OBS-04: al 200 % la cabecera y la barra inferior en dos filas ocupan buena parte de la pantalla de 640 dp y dejan una franja central pequeña para las filas y las tarjetas (alcanzables con scroll). Evidencia: `evidence/app/flows/200pct-p06.png` y `200pct-p07-primera.png`.
- OBS-05: en P06, a 360x640 dp y al 100 %, la fila `Otros objetivos` queda parcialmente tapada por la barra inferior en la primera pantalla (se alcanza con scroll). Evidencia: `evidence/app/review/p06-buscar-por-objetivo.png` y `p06-buscar-por-objetivo-final-del-scroll.png`.
- OBS-06: contenido para la revisión de nombres (6.5), todos de la semilla y no de la app: `arnica-montana` se muestra como `Hierba de las caídas` (el nombre habitual es `Árnica`, el que usa el ejemplo de la spec); `silybum-marianum` como `Cardo de maria` (sin tilde); `capsella-bursa-pastoris` como `Mostaza salvaje` (habitual `Bolsa de pastor`); `Gamaza` y `Mallee azul` son nombres poco habituales; cinco nombres principales se repiten entre plantas distintas (`Manzanilla`, `Ortiga`, `Gordolobo`, `Primavera`, `Regaliz`) y se distinguen por el nombre científico; `grindelia-robusta` tiene un nombre común `grindelia` pero su nombre principal es el científico, como las otras tres Grindelia; las ilustraciones botánicas de Köhler salen como `Foto: ...`. Evidencia: `evidence/app/content-review.txt`.
- OBS-07: sobre la marca de precaución (decisión ya tomada, solo para la 6.5): el arnica (`bajo`), el eucalipto común y el de Smith, la cáscara sagrada y el sen (sin nivel) no muestran `Precaución`. Son plantas con advertencias conocidas (uso interno del arnica, ingestión del aceite de eucalipto, laxantes antraquinónicos). La marca depende del nivel que trae la semilla.
- OBS-08: contrato de la API fuera de la spec: el esquema `bearer` en minúsculas y con espacios dobles se acepta; `HEAD` responde 200 sin cuerpo y `OPTIONS` 405 con `Allow: GET`; un parámetro desconocido se ignora; pedir directamente una subárea omitida por vacía responde 200 con lista vacía; la barra final (`/v1/goals/`) responde 404; un `offset` de 4.294.967.296 responde 400 (igual que `GET /v1/plants`). Evidencia: `evidence/api/API-08.txt`, `API-17.txt`, `API-18.txt`, `API-21.txt` y `API-24.txt`.
- OBS-09: el pie `Cargando más resultados` no se alcanzó a ver porque las páginas llegan en menos de un segundo; el pie de error y su `Reintentar` sí se verificaron (UI-10). El estado de carga de P06 y de P07 se verificó pausando la API (el error de tiempo agotado salió a los 10 s). Evidencia: `evidence/app/flows/loading-p06.txt` y `loading-p07.txt`.
- OBS-10: las capturas son de una compilación de depuración y llevan la cinta `DEBUG` en la esquina superior derecha.
- OBS-11: con el nivel de log por defecto (`info`) la API solo registra el arranque, sin peticiones. Con `RUST_LOG=debug` registra los 401 con el motivo y la ruta, sin el token (API-23).

## Resultados por caso

Cada caso tiene su evidencia en la ruta indicada. Las comprobaciones de API están una por una en `evidence/api/results.tsv`.

| Caso | Estado | Evidencia |
|---|---|---|
| API-01 | PASA | evidence/api/API-01.txt |
| API-02 | PASA | evidence/api/API-02.txt |
| API-03 | PASA | evidence/api/API-03.txt |
| API-04 | PASA | evidence/api/API-04.txt |
| API-05 | PASA | evidence/api/API-05.txt |
| API-06 | PASA | evidence/api/API-06.txt |
| API-07 | PASA | evidence/api/API-07.txt |
| API-08 | PASA | evidence/api/API-08.txt |
| API-09 | PASA | evidence/api/API-09.txt |
| API-10 | PASA | evidence/api/API-10.txt |
| API-11 | PASA | evidence/api/API-11.txt |
| API-12 | PASA | evidence/api/API-12.txt |
| API-13 | PASA | evidence/api/API-13.txt |
| API-14 | PASA | evidence/api/API-14.txt |
| API-15 | PASA | evidence/api/API-15.txt |
| API-16 | PASA | evidence/api/API-16.txt |
| API-17 | PASA | evidence/api/API-17.txt |
| API-18 | PASA | evidence/api/API-18.txt |
| API-19 | PASA | evidence/api/API-19.txt |
| API-20 | PASA | evidence/api/API-20.txt |
| API-21 | PASA | evidence/api/API-21.txt |
| API-22 | PASA | evidence/api/API-22.txt |
| API-23 | PASA | evidence/api/API-23.txt |
| API-24 | PASA | evidence/api/API-24.txt |
| UI-01 | PASA | evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png |
| UI-02 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt |
| UI-03 | PASA | evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json |
| UI-04 | PASA | evidence/app/lists/*.json (texto de cada tarjeta igual al derivado de la API, con la marca) |
| UI-05 | PASA | evidence/app/lists/*.json (224 miniaturas con crédito correcto) |
| UI-06 | PASA | evidence/app/flows/sheet.txt, evidence/app/review/ver-mas-detalles-hoja.png |
| UI-07 | PASA | evidence/app/flows/passport.txt |
| UI-08 | PASA | evidence/app/flows/stack.txt, evidence/app/flows/subareas.txt |
| UI-09 | PASA | evidence/app/flows/tabs.txt |
| UI-10 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt |
| UI-11 | PASA | evidence/app/flows/auth-p06-401.txt, evidence/app/flows/auth-p07-401.txt |
| UI-12 | PASA | evidence/app/flows/scale.txt, evidence/app/flows/200pct-*.png |
| UI-13 | PASA | evidence/app/flows/a11y.txt |
| UI-14 | PASA | evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| UI-15 | PASA | evidence/app/logcat-flujos.txt |
| UI-16 | PASA | evidence/app/trafico-miniaturas.txt |
| UI-17 | PASA | revisión de dependencias y código (sin almacenamiento local), evidence/app/flutter-test.txt |
| UI-18 | FALLA | DEF-01: evidence/app/flows/200pct-p07-primera.png |
| REG-01 | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| CON-01 | PASA | evidence/app/content-review.txt |
| CON-02 | PASA | evidence/app/content-review.txt |
| CON-03 | PASA | evidence/app/content-review.txt (observaciones OBS-06) |
| CON-04 | PASA | evidence/app/content-review.txt, evidence/app/lists/*.json |

## Resultados por criterio

Un criterio es un escenario de los deltas. La tabla (generada por `scripts/traceability.py` con `scripts/case_results.json`) da el estado y la evidencia de cada uno.

| Capability | Requisito | Escenario | Casos | Estado | Evidencia |
|---|---|---|---|---|---|
| `catalog-api` | Catálogo de objetivos | Lista de objetivos | API-01 API-02 | PASA | evidence/api/API-01.txt; evidence/api/API-02.txt |
| `catalog-api` | Catálogo de objetivos | Objetivo con subáreas | API-02 API-05 | PASA | evidence/api/API-02.txt; evidence/api/API-05.txt |
| `catalog-api` | Catálogo de objetivos | Subárea sin plantas | API-24 UI-14 | PASA | evidence/api/API-24.txt; evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `catalog-api` | Catálogo de objetivos | Objetivo sin plantas | API-24 UI-14 | PASA | evidence/api/API-24.txt; evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `catalog-api` | Catálogo de objetivos | Coherencia con los resultados | API-11 | PASA | evidence/api/API-11.txt |
| `catalog-api` | Catálogo de objetivos | Sin token | API-17 | PASA | evidence/api/API-17.txt |
| `catalog-api` | Plantas por objetivo | Plantas de un objetivo | API-03 API-14 | PASA | evidence/api/API-03.txt; evidence/api/API-14.txt |
| `catalog-api` | Plantas por objetivo | Subárea | API-04 | PASA | evidence/api/API-04.txt |
| `catalog-api` | Plantas por objetivo | Unión sin subárea | API-05 | PASA | evidence/api/API-05.txt |
| `catalog-api` | Plantas por objetivo | Subárea ajena | API-06 | PASA | evidence/api/API-06.txt |
| `catalog-api` | Plantas por objetivo | Objetivo desconocido | API-07 | PASA | evidence/api/API-07.txt |
| `catalog-api` | Plantas por objetivo | Objetivo sin plantas | API-24 UI-14 | PASA | evidence/api/API-24.txt; evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `catalog-api` | Plantas por objetivo | Datos ausentes | API-14 API-24 | PASA | evidence/api/API-14.txt; evidence/api/API-24.txt |
| `catalog-api` | Plantas por objetivo | Precauciones sin nivel | API-15 UI-04 | PASA | evidence/api/API-15.txt; evidence/app/lists/*.json (texto de cada tarjeta igual al derivado de la API, con la marca) |
| `catalog-api` | Plantas por objetivo | Token y método | API-17 API-18 | PASA | evidence/api/API-17.txt; evidence/api/API-18.txt |
| `catalog-api` | Orden y paginación de plantas por objetivo | Orden por nombre para mostrar | API-10 | PASA | evidence/api/API-10.txt |
| `catalog-api` | Orden y paginación de plantas por objetivo | Orden sin distinguir acentos ni mayúsculas | API-10 API-24 | PASA | evidence/api/API-10.txt; evidence/api/API-24.txt |
| `catalog-api` | Orden y paginación de plantas por objetivo | Páginas sin repetición | API-09 | PASA | evidence/api/API-09.txt |
| `catalog-api` | Orden y paginación de plantas por objetivo | Límite fuera de rango | API-08 | PASA | evidence/api/API-08.txt |
| `catalog-api` | Orden y paginación de plantas por objetivo | Desplazamiento más allá del total | API-08 | PASA | evidence/api/API-08.txt |
| `catalog-api` | Qué plantas aparecen por objetivo | Planta sin objetivos | API-13 CON-02 | PASA | evidence/api/API-13.txt; evidence/app/content-review.txt |
| `catalog-api` | Qué plantas aparecen por objetivo | Planta condicionada por revisión | API-12 API-24 | PASA | evidence/api/API-12.txt; evidence/api/API-24.txt |
| `catalog-api` | Qué plantas aparecen por objetivo | Flag sin marca de revisión del objetivo | API-12 | PASA | evidence/api/API-12.txt |
| `catalog-api` | Qué plantas aparecen por objetivo | Planta en dos objetivos | API-13 API-16 | PASA | evidence/api/API-13.txt; evidence/api/API-16.txt |
| `catalog-api` | Contrato aditivo de objetivos | OpenAPI actualizado | API-19 | PASA | evidence/api/API-19.txt |
| `catalog-api` | Contrato aditivo de objetivos | Rutas existentes intactas | API-19 API-20 | PASA | evidence/api/API-19.txt; evidence/api/API-20.txt |
| `catalog-api` | Contrato aditivo de objetivos | Ninguna ruta pública nueva | API-21 API-17 | PASA | evidence/api/API-21.txt; evidence/api/API-17.txt |
| `catalog-client` | Consumo de la API v1 del catálogo | Listado con parámetros | REG-01 | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta con caracteres especiales | REG-01 | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta vacía | REG-01 | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta larga | REG-01 | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Consumo de la API v1 del catálogo | Detalle por identificador | REG-01 UI-07 | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/app/flows/passport.txt |
| `catalog-client` | Consumo de la API v1 del catálogo | Catálogo de objetivos | REG-01 UI-01 | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png |
| `catalog-client` | Consumo de la API v1 del catálogo | Plantas de un objetivo | REG-01 UI-02 UI-03 | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt; evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json |
| `catalog-client` | Consumo de la API v1 del catálogo | Plantas de un objetivo sin subárea | REG-01 UI-02 | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt |
| `catalog-client` | Consumo de la API v1 del catálogo | Token en cada petición | REG-01 UI-11 UI-15 | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/app/flows/auth-p06-401.txt, evidence/app/flows/auth-p07-401.txt; evidence/app/logcat-flujos.txt |
| `catalog-client` | Consumo de la API v1 del catálogo | Imagen de un host permitido | UI-05 UI-16 REG-01 | PASA | evidence/app/lists/*.json (224 miniaturas con crédito correcto); evidence/app/trafico-miniaturas.txt; evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Consumo de la API v1 del catálogo | Imagen de un host no permitido | REG-01 (la base real solo trae upload.wikimedia.org: el host no permitido solo con la prueba del producto) | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Consumo de la API v1 del catálogo | Sin otros endpoints, hosts ni datos de usuario | UI-17 REG-01 | PASA | revisión de dependencias y código (sin almacenamiento local), evidence/app/flutter-test.txt; evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Parseo estricto de objetivos | Catálogo válido | UI-01 UI-03 REG-01 | PASA | evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png; evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json; evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Parseo estricto de objetivos | Plantas por objetivo válidas | UI-02 REG-01 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt; evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Parseo estricto de objetivos | Datos nulos | UI-14 UI-04 REG-01 | PASA | evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png; evidence/app/lists/*.json (texto de cada tarjeta igual al derivado de la API, con la marca); evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Parseo estricto de objetivos | Campo ausente o nivel desconocido | REG-01 (la API real no devuelve contratos rotos: solo la prueba del producto) | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Parseo estricto de objetivos | Campos desconocidos | REG-01 | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Errores de objetivos | Sin conexión o 5xx | UI-10 REG-01 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt; evidence/app/flutter-test.txt (514 pruebas) |
| `catalog-client` | Errores de objetivos | No autorizado | UI-11 | PASA | evidence/app/flows/auth-p06-401.txt, evidence/app/flows/auth-p07-401.txt |
| `catalog-client` | Errores de objetivos | Objetivo no encontrado | REG-01 API-07 | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/api/API-07.txt |
| `catalog-client` | Errores de objetivos | Reintento | UI-10 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt |
| `goal-results-screen` | Composición de P07 | Contenido | UI-02 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt |
| `goal-results-screen` | Composición de P07 | Subárea | UI-03 | PASA | evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json |
| `goal-results-screen` | Composición de P07 | Barra inferior | UI-02 UI-09 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt; evidence/app/flows/tabs.txt |
| `goal-results-screen` | Tarjetas derivadas del registro | Tarjeta con un área | UI-02 CON-01 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt; evidence/app/content-review.txt |
| `goal-results-screen` | Tarjetas derivadas del registro | Más de dos áreas | UI-02 CON-01 (los datos reales traen como mucho tres; el caso de cuatro áreas solo con la prueba del producto REG-01) | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt; evidence/app/content-review.txt; evidence/app/flutter-test.txt (514 pruebas) |
| `goal-results-screen` | Tarjetas derivadas del registro | Sin lenguaje de eficacia | CON-01 API-16 UI-02 | PASA | evidence/app/content-review.txt; evidence/api/API-16.txt; evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt |
| `goal-results-screen` | Tarjetas derivadas del registro | Planta sin nombre común | UI-02 CON-03 UI-14 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt; evidence/app/content-review.txt (observaciones OBS-06); evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `goal-results-screen` | Tarjetas derivadas del registro | Área con dos valores unidos | UI-03 CON-01 API-16 | PASA | evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json; evidence/app/content-review.txt; evidence/api/API-16.txt |
| `goal-results-screen` | Tarjetas derivadas del registro | Miniatura ausente o fallida | UI-05 UI-14 | PASA | evidence/app/lists/*.json (224 miniaturas con crédito correcto); evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Imagen con licencia | UI-05 CON-04 | PASA | evidence/app/lists/*.json (224 miniaturas con crédito correcto); evidence/app/content-review.txt, evidence/app/lists/*.json |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Imagen de dominio público | UI-05 CON-04 | PASA | evidence/app/lists/*.json (224 miniaturas con crédito correcto); evidence/app/content-review.txt, evidence/app/lists/*.json |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Autor desconocido | UI-05 CON-04 | PASA | evidence/app/lists/*.json (224 miniaturas con crédito correcto); evidence/app/content-review.txt, evidence/app/lists/*.json |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Miniatura de 500 px | UI-16 CON-04 | PASA | evidence/app/trafico-miniaturas.txt; evidence/app/content-review.txt, evidence/app/lists/*.json |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Sin miniatura derivable | REG-01 (no hay imagenes sin miniatura derivable en la base real: 0 de 1.860) | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Descarga en curso o fallida | UI-05 UI-14 | PASA | evidence/app/lists/*.json (224 miniaturas con crédito correcto); evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Atribución accesible | UI-13 | PASA | evidence/app/flows/a11y.txt |
| `goal-results-screen` | Marca de precaución en la tarjeta | Nivel alto o medio | UI-04 | PASA | evidence/app/lists/*.json (texto de cada tarjeta igual al derivado de la API, con la marca) |
| `goal-results-screen` | Marca de precaución en la tarjeta | Sin datos | UI-14 (con base modificada; en la real ninguna planta con objetivo lo cumple) | PASA | evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `goal-results-screen` | Marca de precaución en la tarjeta | Nivel bajo | UI-04 | PASA | evidence/app/lists/*.json (texto de cada tarjeta igual al derivado de la API, con la marca) |
| `goal-results-screen` | Marca de precaución en la tarjeta | Precauciones sin nivel | UI-04 | PASA | evidence/app/lists/*.json (texto de cada tarjeta igual al derivado de la API, con la marca) |
| `goal-results-screen` | Marca de precaución en la tarjeta | Lectura accesible | UI-13 UI-04 | PASA | evidence/app/flows/a11y.txt; evidence/app/lists/*.json (texto de cada tarjeta igual al derivado de la API, con la marca) |
| `goal-results-screen` | Orden y paginación de los resultados | Primera página | UI-02 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt |
| `goal-results-screen` | Orden y paginación de los resultados | Fin de lista | UI-02 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt |
| `goal-results-screen` | Orden y paginación de los resultados | Error al cargar más | UI-10 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt |
| `goal-results-screen` | Orden y paginación de los resultados | Sin sugerir relevancia | UI-02 CON-01 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt; evidence/app/content-review.txt |
| `goal-results-screen` | Estados de P07 | Carga | UI-10 REG-01 (el estado dura milisegundos con el backend local: se verifica con la prueba del producto y con el backend pausado) | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt; evidence/app/flutter-test.txt (514 pruebas) |
| `goal-results-screen` | Estados de P07 | Error con reintento | UI-10 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt |
| `goal-results-screen` | Estados de P07 | Vacío | UI-14 | PASA | evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `goal-results-screen` | Estados de P07 | Objetivo desconocido | REG-01 (la app no ofrece un objetivo desconocido: solo la prueba del producto y la API, API-07) | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/api/API-07.txt |
| `goal-results-screen` | Estados de P07 | Sin autorización | UI-11 | PASA | evidence/app/flows/auth-p06-401.txt, evidence/app/flows/auth-p07-401.txt |
| `goal-results-screen` | Destino de las tarjetas | Abrir el pasaporte | UI-07 | PASA | evidence/app/flows/passport.txt |
| `goal-results-screen` | Destino de las tarjetas | Volver conservando la posición | UI-07 | PASA | evidence/app/flows/passport.txt |
| `goal-results-screen` | Destino de las tarjetas | Atrás desde el pasaporte hasta Inicio | UI-08 | PASA | evidence/app/flows/stack.txt, evidence/app/flows/subareas.txt |
| `goal-results-screen` | Ver más detalles | Abrir la hoja | UI-06 | PASA | evidence/app/flows/sheet.txt, evidence/app/review/ver-mas-detalles-hoja.png |
| `goal-results-screen` | Ver más detalles | Cerrar la hoja | UI-06 | PASA | evidence/app/flows/sheet.txt, evidence/app/review/ver-mas-detalles-hoja.png |
| `goal-results-screen` | Ver más detalles | Sin peticiones ni registro | UI-06 UI-17 | PASA | evidence/app/flows/sheet.txt, evidence/app/review/ver-mas-detalles-hoja.png; revisión de dependencias y código (sin almacenamiento local), evidence/app/flutter-test.txt |
| `goal-results-screen` | Adaptación accesible de P07 | Texto aumentado | UI-12 UI-18 | FALLA | evidence/app/flows/scale.txt, evidence/app/flows/200pct-*.png; DEF-01: evidence/app/flows/200pct-p07-primera.png |
| `goal-results-screen` | Adaptación accesible de P07 | Controles accesibles | UI-13 | PASA | evidence/app/flows/a11y.txt |
| `goal-search-screen` | Presentación de Buscar por objetivo | Contenido y orden de las seis filas | UI-01 | PASA | evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png |
| `goal-search-screen` | Presentación de Buscar por objetivo | Nombres y orden de la API | REG-01 (con otro nombre solo la prueba del producto; la API real lo entrega de la base, API-01) | PASA | evidence/app/flutter-test.txt (514 pruebas); evidence/api/API-01.txt |
| `goal-search-screen` | Presentación de Buscar por objetivo | Objetivo sin icono conocido | REG-01 (la app solo conoce los seis ids reales) | PASA | evidence/app/flutter-test.txt (514 pruebas) |
| `goal-search-screen` | Presentación de Buscar por objetivo | Presentación local sin collage | UI-01 REG-01 | PASA | evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png; evidence/app/flutter-test.txt (514 pruebas) |
| `goal-search-screen` | Adaptación accesible de P06 | Texto normal y aumentado | UI-12 UI-01 | PASA | evidence/app/flows/scale.txt, evidence/app/flows/200pct-*.png; evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png |
| `goal-search-screen` | Adaptación accesible de P06 | Zonas seguras y controles funcionales accesibles | UI-13 (zonas seguras: el emulador no tiene notch; solo insets de la barra de gestos) | PASA | evidence/app/flows/a11y.txt |
| `goal-search-screen` | Filas de objetivos con acción | Activación de una fila sin subáreas | UI-02 | PASA | evidence/app/lists/ (cinco objetivos), evidence/app/flows/sheet.txt |
| `goal-search-screen` | Filas de objetivos con acción | Activación de una fila con subáreas | UI-03 | PASA | evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json |
| `goal-search-screen` | Filas de objetivos con acción | Semántica de botón | UI-13 UI-01 | PASA | evidence/app/flows/a11y.txt; evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png |
| `goal-search-screen` | Filas de objetivos con acción | Sin selección persistente | UI-01 UI-08 | PASA | evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png; evidence/app/flows/stack.txt, evidence/app/flows/subareas.txt |
| `goal-search-screen` | Catálogo de objetivos desde la API | Carga | UI-10 REG-01 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt; evidence/app/flutter-test.txt (514 pruebas) |
| `goal-search-screen` | Catálogo de objetivos desde la API | Error con reintento | UI-10 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt |
| `goal-search-screen` | Catálogo de objetivos desde la API | Sin autorización | UI-11 | PASA | evidence/app/flows/auth-p06-401.txt, evidence/app/flows/auth-p07-401.txt |
| `goal-search-screen` | Catálogo de objetivos desde la API | Sin conteos | UI-01 | PASA | evidence/app/flows/p06.txt, evidence/app/review/p06-buscar-por-objetivo.png |
| `goal-search-screen` | Pantalla de Otros objetivos | Lista de subáreas | UI-03 | PASA | evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json |
| `goal-search-screen` | Pantalla de Otros objetivos | Abrir una subárea | UI-03 | PASA | evidence/app/flows/subareas.txt, evidence/app/lists/otros-objetivos-*.json |
| `goal-search-screen` | Pantalla de Otros objetivos | Subárea vacía | UI-14 | PASA | evidence/app/flows/empty.txt, evidence/app/lists-base-modificada/, evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png |
| `goal-search-screen` | Pantalla de Otros objetivos | Retorno | UI-08 | PASA | evidence/app/flows/stack.txt, evidence/app/flows/subareas.txt |
| `goal-search-screen` | Pantalla de Otros objetivos | Estados de carga y error | UI-10 | PASA | evidence/app/flows/errors.txt, evidence/app/flows/loading-p06.txt, evidence/app/flows/loading-p07.txt |
| `goal-search-screen` | Navegación a resultados | Pila completa | UI-08 | PASA | evidence/app/flows/stack.txt, evidence/app/flows/subareas.txt |
| `goal-search-screen` | Navegación a resultados | Pestaña Inicio | UI-09 | PASA | evidence/app/flows/tabs.txt |
| `goal-search-screen` | Navegación a resultados | Sin datos de usuario | UI-17 | PASA | revisión de dependencias y código (sin almacenamiento local), evidence/app/flutter-test.txt |
| `goal-search-screen` | Navegación a resultados | Otras pestañas sin acción | UI-09 | PASA | evidence/app/flows/tabs.txt |

## Contenido real de P07 (tarea 6.4)

- Alcance: en lugar de una muestra, se revisó el total: las 175 plantas que tienen objetivo en la API y las 287 tarjetas que muestra la interfaz en las once listas de P07 (los cinco objetivos sin subáreas y las seis subáreas; `Otros objetivos` abre la pantalla de subáreas, no una lista propia).
- Texto de las tarjetas: cada tarjeta de la interfaz es idéntica, en texto y en orden, a la derivada de la API (nombre, científico si es distinto, línea de la EMA con `y N más`, marca). Hubo 0 diferencias en 287 tarjetas. Las 11 filas con áreas compuestas por «; » se muestran tal cual.
- Lenguaje de eficacia o dosis: 0 coincidencias de una lista de términos de eficacia y dosis en las 287 tarjetas y en las 16 áreas distintas de la API. Las tarjetas solo contienen nombre, científico, línea de la EMA y a lo sumo una marca. No hay puntuaciones ni posiciones.
- Plantas tóxicas: ninguna de las excluidas por toxicidad ni `conium-maculatum` aparece; la unión de los seis objetivos son exactamente las 175 plantas con filas visibles de `plant_goal`. No hay en la lista plantas tóxicas conocidas (aconito, ricino, abrus). Las plantas con nivel `alto` visibles son 13 (`Hierba de San Juan`, `Ajo`, `Ginkgo`, `Ginseng`, dos `Regaliz`, `Glycyrrhiza inflata`, `Mimbrera`, `Mimbrera púrpura`, `Sauce dafnoide`, `Arándano rojo grande`, `Actaea racemosa` y `Serenoa repens`) y llevan `Precaución`.
- Nombres: los 32 con el científico como nombre principal salen una sola vez y sin nombre secundario; no hay nombres en minúscula ni con espacios sobrantes. Las incoherencias están en OBS-06.
- Miniaturas: 155 de las 175 plantas tienen imagen y 20 no. Las 224 miniaturas mostradas llevan `Foto: <autor> · <licencia>` exactamente como la API (10 tarjetas con `autor no disponible`, 6 plantas con autor nulo, y varias con `Public domain` que muestran autor y licencia igual). Ninguna tarjeta con arte local mostró crédito ni ninguna foto salió sin crédito. Todas las URL son de `upload.wikimedia.org/wikipedia/commons` (152 `.jpg`, 2 `.png` y 1 `.gif`), de modo que la política deriva la miniatura de 500 px para todas. La carga de 27 miniaturas de `Cuidado de la piel` consumió 2,6 MB en total (unos 96 KB por miniatura con el JSON), un orden de magnitud que corresponde a miniaturas de 500 px y no a los originales. Las URL exactas las fija la prueba del producto (`PlantImagePolicy.thumbnailUrl`), que se ejecutó en la regresión.

## Insumos para la 6.5 (capturas)

Todas en `evidence/app/review/`, de 1080x1920 (360x640 dp):

- `p06-buscar-por-objetivo.png` y `p06-buscar-por-objetivo-final-del-scroll.png`: P06 con las seis filas.
- `otros-objetivos-subareas.png`: `Otros objetivos` con sus seis subáreas.
- `p07-relajacion-estres.png`, `p07-mejorar-el-sueno.png`, `p07-cuidado-de-la-piel.png`, `p07-alivio-respiratorio.png` y `p07-cansancio-y-fatiga.png`: la primera pantalla de P07 de cada objetivo con P07 propio. `Otros objetivos` no tiene P07 propio: abre la pantalla de subáreas.
- `p07-otros-objetivos-subarea-digestion.png` y `p07-otros-objetivos-subarea-molestias-oculares.png`, más `...-vias-urinarias-y-genitales.png`, `...-dolor-e-inflamacion.png`, `...-boca-y-garganta.png` y `...-circulacion.png`: la primera pantalla de P07 de cada subárea.
- `p07-tarjeta-con-marca-precaucion.png`: tarjeta `Amapola de California` con `Precaución` y su miniatura con crédito (también visible en `p07-alivio-respiratorio.png` con `Ajo`).
- `ver-mas-detalles-hoja.png`: la hoja `Sobre estas recomendaciones` abierta.

Otras capturas útiles: `evidence/app/flows/p07-tarjeta-sin-datos-de-precauciones-base-modificada.png` (el texto `Sin datos de precauciones...`, solo con una base modificada), `p07-vacio-cansancio-y-fatiga.png` y `subareas-sin-molestias-oculares.png` (también de la base modificada).

## No ejecutado y limitaciones

- Playwright: no aplica; la app es nativa Android y no hay compilación web.
- Lector de pantalla (TalkBack): no se ejecutó; la semántica se verificó con el árbol de accesibilidad de `uiautomator` (etiquetas, `clickable` y tamaños).
- Zonas seguras con notch: el emulador no tiene notch; solo se vieron los insets de la barra de gestos.
- Orientación horizontal y dispositivo físico (el teléfono `R5CR70M9GEE` no se usó por indicación) y otros tamaños de pantalla: no probados.
- Backend desplegado en Cloud Run: no se probó; todo es local.
- No se capturaron las peticiones de red de la app: que no hay otros endpoints, hosts ni datos de usuario se verificó por regresión de las pruebas del producto (514 pruebas), por las dependencias de la app (sin almacenamiento local) y por el tamaño del tráfico de las miniaturas.
- Escenarios que la base real no permite: tarjeta con cuatro áreas, miniatura sin derivación posible (TIFF), host no permitido, contrato roto o nivel de seguridad desconocido, objetivo desconocido desde la interfaz y 401 en una página siguiente. Solo los cubren las pruebas del producto (REG-01) y, en la API, API-07 y API-24. `Sin datos de precauciones` se verificó con una base modificada (UI-14).
- Comportamiento con límite de peticiones de Wikimedia (429): no reproducible; no se observó.
- Riesgos residuales: miniaturas que tardan o fallan en una red real (OBS-01), título partido al 200 % (DEF-01) y nombres de la semilla (OBS-06).

## Cómo re-ejecutar

Desde la raíz del repositorio, con `API_TOKENS` aleatorio solo en el entorno:

```bash
export QA_TOKEN=$(openssl rand -hex 32)
API_TOKENS=$QA_TOKEN docker compose -p qa-goal-search up --build -d
QA_DB=$PWD/data/build/catalog.db python3 -I openspec/changes/enable-goal-search/qa/scripts/api_tests.py $PWD openspec/changes/enable-goal-search/qa/evidence/api
postman collection run openspec/changes/enable-goal-search/qa/postman/enable-goal-search.collection.json -e openspec/changes/enable-goal-search/qa/postman/local.postman_environment.json --env-var "token=$QA_TOKEN"
```

- API con la base modificada: `scripts/make_modified_db.sh data/build/catalog.db <copia>`, servir la copia con `docker run -v <copia>:/mod.db:ro -e CATALOG_DB=/mod.db -e API_TOKENS=$QA_TOKEN -p 8081:8080 boticario-backend` y correr `scripts/api_tests_modified.py` con `QA_DB=<copia>`.
- Registro de la API: `scripts/log_check.sh` con `RUST_LOG=debug`.
- Colección de Postman: se regenera con `scripts/make_postman_collection.py <repo> <salida>` desde `backend/openapi.json`.
- Interfaz: iniciar el emulador `boticario_catalog_api36`, compilar con `flutter build apk --debug --dart-define=API_BASE_URL=http://10.0.2.2:8080 --dart-define=API_TOKEN=$QA_TOKEN` desde `app/`, instalar con `adb -s emulator-5556 install -r` y correr `scripts/ui_flows.py <flujo>` (p06, subareas, sheet, passport, stack, tabs, a11y, errors, empty, scale) y `scripts/run_ui_lists.sh "<objetivo>[:<subárea>] ..."`, con `QA_PYLIB` apuntando a una carpeta con Pillow.
- Contenido: `scripts/content_review.py evidence/app`.
- Tablas: `scripts/traceability.py <repo> plan` y `results scripts/case_results.json`.
- Regresión del producto: `flutter test test/` desde `app/`.

## Herramientas instaladas y limpieza

- Instalado: Pillow, con `pip install --target` en una carpeta temporal fuera del proyecto. Se usó el CLI de Postman que ya estaba instalado. No se agregó nada al proyecto ni a esta carpeta.
- Se creó la imagen `boticario-backend`, los contenedores `qa-goal-search-api-1` y `qa-goal-search-mod`, y la red de `docker compose -p qa-goal-search`; se borraron al terminar. Se apagó el emulador `boticario_catalog_api36` y se borraron `app-debug.apk` y `app-debug.apk.sha1` de `app/build/app/outputs/flutter-apk/`.
- No se tocó el emulador `DADM_GraphicsSound_API35` ni el teléfono físico.
