# Plan de pruebas: enable-goal-search (cambio 3)

Alcance: tareas 6.1, 6.2, 6.3, 6.4 y 6.6 de `openspec/changes/enable-goal-search/tasks.md`. La 6.5 (revisar los nombres con el usuario) usa la evidencia de `evidence/app/review/`. El requerimiento es el propio cambio: `proposal.md`, `design.md` («Esquema real» y «Conteos reales de la API») y los deltas de `specs/` de `goal-search-screen`, `goal-results-screen`, `catalog-api` y `catalog-client`. Cada escenario de los deltas es un criterio de aceptación.

Rama `enable-goal-search`, commits del cambio 3 de `3c86408` a `839fcc1` (diff `git diff a15f1eb..HEAD`). QA ejecutada el 2026-10-27 y 2026-10-28 (UTC).

## Entorno y restricciones

- API: servicio de `docker compose -p qa-goal-search up --build -d` desde la raíz, que construye la imagen nueva con la semilla completa (2.354 plantas), en `http://127.0.0.1:8080` y, para el emulador, `http://10.0.2.2:8080`.
- Token: aleatorio (`openssl rand -hex 32`), pasado solo por la variable de entorno `API_TOKENS` y, a los scripts, por `QA_TOKEN`. En artefactos se escribe siempre `<token-app>`. No se leyó ni usó `.env`, `.env.cloud-run` ni ninguna credencial de Cloud Run.
- Oráculo independiente: `data/build/catalog.db` (solo lectura, `sqlite3 -readonly`). Las comprobaciones de API comparan la respuesta con consultas SQL propias y con una ordenación propia, no con el código del producto.
- Base modificada: una copia de `catalog.db` en una carpeta temporal fuera del proyecto, con los casos que la base real no tiene (objetivo y subárea vacíos, planta sin datos de seguridad ni imagen, revisión pendiente en un solo objetivo, nombres con acentos). Se sirve con la misma imagen en otro puerto y, para la interfaz, en el puerto 8080 en lugar del servicio normal.
- App: emulador Android `boticario_catalog_api36` (`emulator-5556`, 1080x1920 a 480 dpi, es decir 360x640 dp, Android 16), compilación de depuración con `--dart-define=API_BASE_URL=http://10.0.2.2:8080` y `--dart-define=API_TOKEN=<token-app>`. No se usó el teléfono físico `R5CR70M9GEE` ni el emulador `DADM_GraphicsSound_API35`, que ya estaba en marcha. Se guía con `adb`, `uiautomator` y capturas.
- Playwright no aplica: la app es nativa Android (Flutter) y no tiene destino web ni compilación web. Se registra como limitación.
- Postman: el CLI `postman` 1.74 ejecuta colecciones locales sin sesión, con el token en una variable secreta pasada por `--env-var`. Newman no se instaló.
- Herramientas instaladas fuera del proyecto: Pillow (en una carpeta temporal, para clasificar capturas). Nada se añadió al proyecto ni a la carpeta de QA.
- No se modificó código del producto, specs, `design.md`, `tasks.md` ni `data/seed/`.
- Wikimedia: las miniaturas se cargan desde la app, al desplazar las listas, con pausas entre pasos; las pruebas directas se limitaron a unas pocas peticiones de comprobación.

## Decisiones ya tomadas (se verifican, no se reportan como defectos)

- `GET /v1/goals` devuelve un array en la raíz.
- Orden por `displayName` normalizado, luego científico normalizado y luego id. No es un ranking.
- Se ocultan las filas de `plant_goal` con `pending_review` (hoy solo el hipérico en `relajacion-estres`).
- Las 11 filas de área con «; » se muestran tal cual y cuentan como una.
- La miniatura de la tarjeta es de 500 px; `Foto: <autor> · <licencia>` solo con la imagen cargada; `Foto: autor no disponible · <licencia>` sin autor; arte local sin imagen o si falla.
- `Precaución` solo con nivel alto o medio; nada con bajo ni con nivel nulo; `Sin datos de precauciones (esto no significa que sea segura)` solo con `hasSafety` falso.
- El `displayName` puede ser el nombre científico y sale una sola vez.
- El aviso y `Ver más detalles` van al final del scroll de P07.
- El pasaporte abierto desde P07 dice «Volver» y P07 conserva páginas y scroll.

## Estrategia

- Caja negra con particiones de equivalencia por objetivo (sin subáreas, con subáreas, vacío, desconocido) y por tipo de planta (nivel alto, medio, bajo, sin nivel, sin datos, con y sin imagen, con y sin autor, con nombre científico, en dos objetivos, en dos subáreas).
- Valores límite de `limit` (0, 1, 19, 20, 99, 100, 101, no numérico, vacío) y de `offset` (0, total menos uno, total, total más uno, muy grande, negativo, no numérico).
- Tabla de decisión objetivo × subárea × token (más abajo) cubierta por API-06, API-07 y API-17.
- Transición de estados de la navegación: Inicio, P06, subáreas, P07, pasaporte, y vuelta con el botón de la app, con Atrás del sistema y con la pestaña Inicio.
- Censo: la API se compara con la base para las 175 plantas con objetivo, y la interfaz se compara tarjeta por tarjeta con la API en las doce listas (seis objetivos y seis subáreas, 422 tarjetas). Es más fuerte que un muestreo y es barato porque la API es local.
- Pirámide: lo que ya cubren las pruebas del producto (parser, política de imágenes, textos fijos, estados con cliente falso) no se duplica en el emulador; se ejecuta como regresión (REG-01) y la interfaz se centra en el flujo real contra el backend real.
- Pruebas exploratorias con charters al final.

## Tabla de decisión objetivo × subárea × token

| Objetivo | Subárea | Token válido | Sin token | Token incorrecto |
|---|---|---|---|---|
| con subáreas (`otros-objetivos`) | ausente | 200, unión | 401 | 401 |
| con subáreas | válida (`digestion`) | 200, filtrada | 401 | 401 |
| con subáreas | ajena (`no-existe`, `digestion` de otro objetivo) | 400 `param=subarea` | 401 | 401 |
| sin subáreas (`mejorar-el-sueno`) | ausente | 200 | 401 | 401 |
| sin subáreas | cualquiera | 400 `param=subarea` | 401 | 401 |
| desconocido | ausente o cualquiera | 404 | 401 | 401 |

## Casos

Los scripts están en `scripts/`; la evidencia, en `evidence/api/` y `evidence/app/`. Cada comprobación de `evidence/api/results.tsv` lleva el caso al que pertenece.

### API (tarea 6.2)

| ID | Técnica | Precondición | Pasos | Resultado esperado |
|---|---|---|---|---|
| API-01 | particiones | API con la base real | `GET /v1/goals` | 200, array en la raíz, seis objetivos en orden con nombres de P06, `plantCount` 17, 8, 32, 52, 8 y 135, esquema de `openapi.json` |
| API-02 | particiones | ídem | leer `subareas` de `otros-objetivos` | seis subáreas en orden con 68, 42, 22, 20, 17 y 1; la unión cuenta 135 (la suma de subáreas es 170) |
| API-03 | particiones | ídem | `GET /v1/goals/{id}/plants` de los seis objetivos | 200, esquema, `goal`, `subarea` nula, `limit` 20, `offset` 0, `total` correcto, solo los nueve campos del contrato |
| API-04 | particiones | ídem | las seis subáreas con `?subarea=` | `subarea` con id y nombre, solo plantas de esa subárea, `areas` solo las de esa subárea |
| API-05 | particiones | ídem | `otros-objetivos` sin `subarea` | cada planta una vez, 135, `areas` reunidas |
| API-06 | particiones, tabla de decisión | ídem | subárea ajena, inexistente, vacía, en mayúsculas, con espacio, sobre objetivo sin subáreas | 400 `problem+json` con `param` igual a `subarea` |
| API-07 | particiones | ídem | objetivo inexistente, con mayúsculas, con caracteres reservados, muy largo | 404 `problem+json` que no refleja el id |
| API-08 | valores límite | ídem | `limit` y `offset` en los extremos y fuera de rango | 200 o 400 con `param`, mismas reglas que `GET /v1/plants` |
| API-09 | particiones | ídem | recorrer cada objetivo con `limit` 5 y 7 | cada planta una vez y la unión tiene `total` elementos |
| API-10 | oráculo | ídem | comparar el orden con una ordenación propia | por `displayName` normalizado, científico normalizado e id, sin distinguir mayúsculas ni acentos |
| API-11 | oráculo | ídem | comparar `plantCount` con `total` en objetivos y subáreas | iguales |
| API-12 | oráculo | ídem | hipérico en `relajacion-estres`, en el detalle y en el listado | ausente de `relajacion-estres` (17), 200 en el detalle, presente en los otros objetivos; ningún otro flag oculta |
| API-13 | oráculo | ídem | unión de los seis objetivos contra la base y contra las plantas tóxicas | 175 plantas, ninguna de `objetivos-omitidos-por-toxicidad` ni `conium-maculatum`, 71 en dos objetivos con áreas propias |
| API-14 | censo | ídem | comparar cada planta de cada objetivo con la base | científico, familia, nombres comunes, áreas, nivel, `hasSafety` e imagen iguales |
| API-15 | tabla de decisión | ídem | eucalipto y distribución de niveles | nivel nulo con `hasSafety` verdadero; 13 alto, 30 medio, 21 bajo, 111 sin nivel |
| API-16 | oráculo | ídem | buscar lenguaje de dosis o eficacia en las áreas | ninguna de las 16 áreas lo contiene; las compuestas salen tal cual |
| API-17 | tabla de decisión | ídem | sin token, incorrecto, esquema Basic, token en otra cabecera o en la query | 401 `problem+json` con `WWW-Authenticate: Bearer` y antes que el 404 |
| API-18 | particiones | ídem | POST, PUT, PATCH y DELETE con y sin token; HEAD y OPTIONS | 405 con `Allow: GET` con token, 401 sin token |
| API-19 | contrato | ídem | comparar `/openapi.json` con el versionado y con `a15f1eb` | igual al versionado; solo se añaden las dos rutas y los seis esquemas; Bearer, 401, 400, 404, 405 y 500 como `problem+json` |
| API-20 | regresión | ídem | `GET /v1/plants` y `GET /v1/plants/{id}` | mismo contrato y mismos campos |
| API-21 | contrato | ídem | rutas sin `/v1`, con barra final, con segmentos de más | ninguna ruta pública nueva |
| API-22 | idempotencia | ídem | cinco GET iguales, tiempos | mismo cuerpo byte a byte, menos de 500 ms |
| API-23 | seguridad | servicio con `RUST_LOG=debug` | peticiones con token válido, incorrecto, sin token y POST | el log no contiene el token ni la palabra Bearer |
| API-24 | particiones | base modificada | objetivo vacío, subárea vacía, planta sin seguridad ni imagen, pendiente en un solo objetivo, nombres con acentos | `plantCount` 0 y lista vacía; subárea omitida; `hasSafety` falso; la planta sigue donde su fila no está pendiente; orden `abedul`, `Abutilon theophrasti`, `Árnica`, `Zarzaparrilla` |

La colección de Postman `postman/enable-goal-search.collection.json` (29 peticiones, 138 aserciones) repite los casos centrales (API-01 a API-06, API-08, API-10, API-12, API-13, API-15, API-17, API-18 y API-20) como contrato ejecutable y se corre también contra la base modificada como control negativo.

### Interfaz (tarea 6.3)

| ID | Técnica | Precondición | Pasos | Resultado esperado |
|---|---|---|---|---|
| UI-01 | particiones | app con API real | abrir Inicio, `Buscar por objetivo` | título, subtítulo y seis filas en orden, sin `Concentración`, sin conteos, cada fila un botón, ninguna seleccionada |
| UI-02 | censo | ídem | abrir P07 de cada uno de los cinco objetivos sin subáreas y desplazar hasta el final | subtítulo `Para: <nombre>`, tantas tarjetas como `total`, texto igual a la API y en su orden, fin de lista, aviso y `Ver más detalles` al final, pie de carga entre páginas |
| UI-03 | censo | ídem | `Otros objetivos` y cada una de las seis subáreas | pantalla de subáreas con título y seis botones; P07 de cada subárea con sus conteos reales (68, 42, 22, 20, 17 y 1) y `Para: <subárea>` |
| UI-04 | tabla de decisión | ídem | buscar tarjetas con nivel alto, medio, bajo y sin nivel | `Precaución` solo con alto y medio; nada con bajo ni con el eucalipto (nivel nulo) |
| UI-05 | tabla de decisión | ídem | clasificar la miniatura de cada tarjeta | con imagen cargada, `Foto: <autor> · <licencia>` exacto; sin imagen, arte local sin crédito; nunca foto sin crédito ni crédito con arte |
| UI-06 | transición de estados | ídem | abrir `Ver más detalles`; cerrar con `Cerrar`, deslizando y con Atrás del sistema | hoja `Sobre estas recomendaciones` con el texto fijo, sin cambiar de ruta, P07 intacto |
| UI-07 | transición de estados | ídem | bajar por la lista, abrir una planta, volver | el pasaporte de esa planta con «Volver»; P07 en la misma posición y con las mismas tarjetas sin recargar |
| UI-08 | transición de estados | ídem | Inicio, P06, `Otros objetivos`, `Digestión`, planta y Atrás en cada paso, con el botón de la app y con el del sistema | pasaporte, P07, subáreas, P06 e Inicio en ese orden; subtítulo conservado |
| UI-09 | transición de estados | ídem | pestaña Inicio desde subáreas, P07 y pasaporte; Favoritos, Historial y Perfil en P06 | Inicio vuelve a la raíz con la pila limpia; las otras tres no hacen nada |
| UI-10 | transición de estados | API detenida o pausada | abrir P06, subáreas y P07 con la API detenida; `Reintentar` con ella en marcha; pausar la API al cargar la segunda página | error legible con `Reintentar` y las tarjetas aparecen al reintentar; el pie conserva lo cargado |
| UI-11 | tabla de decisión | app compilada con un token incorrecto | abrir P06 y P07 | error de no autorizado sin el token |
| UI-12 | valores límite | texto del sistema al 200 % | P06, subáreas, P07, tarjeta con marca, hoja y pasaporte | contenido legible y alcanzable, sin recorte ni desbordes |
| UI-13 | inspección | ídem | volcado de accesibilidad de P06, subáreas y P07 | filas y tarjetas con 48 dp o más y etiqueta distinguible; la tarjeta se lee una vez con nombre, línea de la EMA, marca y atribución; la imagen no duplica la lectura |
| UI-14 | particiones | base modificada servida en el puerto 8080 | P06, subáreas, P07 del objetivo vacío, de `mejorar-el-sueno` (lavanda sin seguridad ni imagen) | fila del objetivo vacío, vacío explícito, subárea omitida, tarjeta con `Sin datos de precauciones (esto no significa que sea segura)` y arte local sin atribución |
| UI-15 | seguridad | `adb logcat` limpio al empezar | recorrer los flujos y guardar el registro | el registro no contiene el token ni excepciones de desborde |
| UI-16 | revisión | código y red | revisar `PlantImagePolicy`, medir el tráfico de la app al cargar una lista | la URL pedida es `500px-<archivo>` de `upload.wikimedia.org`; el tráfico por imagen es de decenas de KB, no de megabytes |
| UI-17 | revisión | ídem | revisar las peticiones de la app | solo los dos endpoints de objetivos, los de plantas y las miniaturas; nada se registra ni persiste al abrir la hoja ni al elegir objetivos |
| UI-18 | inspección | texto del sistema al 200 % | mirar los títulos de P06, subáreas, P07, hoja y pasaporte | ningún título parte una palabra a mitad |

Regresión del producto:

| ID | Técnica | Precondición | Pasos | Resultado esperado |
|---|---|---|---|---|
| REG-01 | regresión | SDK de Flutter | `flutter test test/` desde `app/` | todas las pruebas del producto pasan; cubren el cliente (URL y cabeceras exactas, errores, parseo estricto), la política de imágenes, los estados con cliente falso y las tarjetas de cuatro áreas, sin miniatura derivable y host no permitido |

### Contenido real (tarea 6.4)

| ID | Técnica | Precondición | Pasos | Resultado esperado |
|---|---|---|---|---|
| CON-01 | censo | las doce listas recorridas en la interfaz | leer el texto visible de las 422 tarjetas | solo nombre, científico, línea de la EMA y marca; sin lenguaje de eficacia ni dosis, sin textos del mockup, sin puntuaciones ni posiciones |
| CON-02 | revisión experta | lista de las 175 plantas | revisar los nombres y los niveles buscando plantas tóxicas o de riesgo conocido | ninguna planta tóxica; las de riesgo conocido llevan `Precaución` o se anotan como observación |
| CON-03 | censo | ídem | revisar los 32 `displayName` científicos, los empates y los nombres comunes | el científico sale una sola vez; los nombres comunes son nombres en español; las incoherencias se registran |
| CON-04 | censo | ídem | comparar la atribución de cada miniatura mostrada con la API | cada miniatura lleva autor y licencia de su `image`; ninguna tarjeta con arte local la muestra |

## Trazabilidad

Cada escenario de los cuatro deltas aparece al menos una vez (tabla generada por `scripts/traceability.py`, que falla si algún escenario no tiene caso).

| Capability | Requisito | Escenario | Casos |
|---|---|---|---|
| `catalog-api` | Catálogo de objetivos | Lista de objetivos | API-01 API-02 |
| `catalog-api` | Catálogo de objetivos | Objetivo con subáreas | API-02 API-05 |
| `catalog-api` | Catálogo de objetivos | Subárea sin plantas | API-24 UI-14 |
| `catalog-api` | Catálogo de objetivos | Objetivo sin plantas | API-24 UI-14 |
| `catalog-api` | Catálogo de objetivos | Coherencia con los resultados | API-11 |
| `catalog-api` | Catálogo de objetivos | Sin token | API-17 |
| `catalog-api` | Plantas por objetivo | Plantas de un objetivo | API-03 API-14 |
| `catalog-api` | Plantas por objetivo | Subárea | API-04 |
| `catalog-api` | Plantas por objetivo | Unión sin subárea | API-05 |
| `catalog-api` | Plantas por objetivo | Subárea ajena | API-06 |
| `catalog-api` | Plantas por objetivo | Objetivo desconocido | API-07 |
| `catalog-api` | Plantas por objetivo | Objetivo sin plantas | API-24 UI-14 |
| `catalog-api` | Plantas por objetivo | Datos ausentes | API-14 API-24 |
| `catalog-api` | Plantas por objetivo | Precauciones sin nivel | API-15 UI-04 |
| `catalog-api` | Plantas por objetivo | Token y método | API-17 API-18 |
| `catalog-api` | Orden y paginación de plantas por objetivo | Orden por nombre para mostrar | API-10 |
| `catalog-api` | Orden y paginación de plantas por objetivo | Orden sin distinguir acentos ni mayúsculas | API-10 API-24 |
| `catalog-api` | Orden y paginación de plantas por objetivo | Páginas sin repetición | API-09 |
| `catalog-api` | Orden y paginación de plantas por objetivo | Límite fuera de rango | API-08 |
| `catalog-api` | Orden y paginación de plantas por objetivo | Desplazamiento más allá del total | API-08 |
| `catalog-api` | Qué plantas aparecen por objetivo | Planta sin objetivos | API-13 CON-02 |
| `catalog-api` | Qué plantas aparecen por objetivo | Planta condicionada por revisión | API-12 API-24 |
| `catalog-api` | Qué plantas aparecen por objetivo | Flag sin marca de revisión del objetivo | API-12 |
| `catalog-api` | Qué plantas aparecen por objetivo | Planta en dos objetivos | API-13 API-16 |
| `catalog-api` | Contrato aditivo de objetivos | OpenAPI actualizado | API-19 |
| `catalog-api` | Contrato aditivo de objetivos | Rutas existentes intactas | API-19 API-20 |
| `catalog-api` | Contrato aditivo de objetivos | Ninguna ruta pública nueva | API-21 API-17 |
| `catalog-client` | Consumo de la API v1 del catálogo | Listado con parámetros | REG-01 |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta con caracteres especiales | REG-01 |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta vacía | REG-01 |
| `catalog-client` | Consumo de la API v1 del catálogo | Consulta larga | REG-01 |
| `catalog-client` | Consumo de la API v1 del catálogo | Detalle por identificador | REG-01 UI-07 |
| `catalog-client` | Consumo de la API v1 del catálogo | Catálogo de objetivos | REG-01 UI-01 |
| `catalog-client` | Consumo de la API v1 del catálogo | Plantas de un objetivo | REG-01 UI-02 UI-03 |
| `catalog-client` | Consumo de la API v1 del catálogo | Plantas de un objetivo sin subárea | REG-01 UI-02 |
| `catalog-client` | Consumo de la API v1 del catálogo | Token en cada petición | REG-01 UI-11 UI-15 |
| `catalog-client` | Consumo de la API v1 del catálogo | Imagen de un host permitido | UI-05 UI-16 REG-01 |
| `catalog-client` | Consumo de la API v1 del catálogo | Imagen de un host no permitido | REG-01 (la base real solo trae upload.wikimedia.org: el host no permitido solo con la prueba del producto) |
| `catalog-client` | Consumo de la API v1 del catálogo | Sin otros endpoints, hosts ni datos de usuario | UI-17 REG-01 |
| `catalog-client` | Parseo estricto de objetivos | Catálogo válido | UI-01 UI-03 REG-01 |
| `catalog-client` | Parseo estricto de objetivos | Plantas por objetivo válidas | UI-02 REG-01 |
| `catalog-client` | Parseo estricto de objetivos | Datos nulos | UI-14 UI-04 REG-01 |
| `catalog-client` | Parseo estricto de objetivos | Campo ausente o nivel desconocido | REG-01 (la API real no devuelve contratos rotos: solo la prueba del producto) |
| `catalog-client` | Parseo estricto de objetivos | Campos desconocidos | REG-01 |
| `catalog-client` | Errores de objetivos | Sin conexión o 5xx | UI-10 REG-01 |
| `catalog-client` | Errores de objetivos | No autorizado | UI-11 |
| `catalog-client` | Errores de objetivos | Objetivo no encontrado | REG-01 API-07 |
| `catalog-client` | Errores de objetivos | Reintento | UI-10 |
| `goal-results-screen` | Composición de P07 | Contenido | UI-02 |
| `goal-results-screen` | Composición de P07 | Subárea | UI-03 |
| `goal-results-screen` | Composición de P07 | Barra inferior | UI-02 UI-09 |
| `goal-results-screen` | Tarjetas derivadas del registro | Tarjeta con un área | UI-02 CON-01 |
| `goal-results-screen` | Tarjetas derivadas del registro | Más de dos áreas | UI-02 CON-01 (los datos reales traen como mucho tres; el caso de cuatro áreas solo con la prueba del producto REG-01) |
| `goal-results-screen` | Tarjetas derivadas del registro | Sin lenguaje de eficacia | CON-01 API-16 UI-02 |
| `goal-results-screen` | Tarjetas derivadas del registro | Planta sin nombre común | UI-02 CON-03 UI-14 |
| `goal-results-screen` | Tarjetas derivadas del registro | Área con dos valores unidos | UI-03 CON-01 API-16 |
| `goal-results-screen` | Tarjetas derivadas del registro | Miniatura ausente o fallida | UI-05 UI-14 |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Imagen con licencia | UI-05 CON-04 |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Imagen de dominio público | UI-05 CON-04 |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Autor desconocido | UI-05 CON-04 |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Miniatura de 500 px | UI-16 CON-04 |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Sin miniatura derivable | REG-01 (no hay imagenes sin miniatura derivable en la base real: 0 de 1.860) |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Descarga en curso o fallida | UI-05 UI-14 |
| `goal-results-screen` | Miniatura con atribución en la tarjeta | Atribución accesible | UI-13 |
| `goal-results-screen` | Marca de precaución en la tarjeta | Nivel alto o medio | UI-04 |
| `goal-results-screen` | Marca de precaución en la tarjeta | Sin datos | UI-14 (con base modificada; en la real ninguna planta con objetivo lo cumple) |
| `goal-results-screen` | Marca de precaución en la tarjeta | Nivel bajo | UI-04 |
| `goal-results-screen` | Marca de precaución en la tarjeta | Precauciones sin nivel | UI-04 |
| `goal-results-screen` | Marca de precaución en la tarjeta | Lectura accesible | UI-13 UI-04 |
| `goal-results-screen` | Orden y paginación de los resultados | Primera página | UI-02 |
| `goal-results-screen` | Orden y paginación de los resultados | Fin de lista | UI-02 |
| `goal-results-screen` | Orden y paginación de los resultados | Error al cargar más | UI-10 |
| `goal-results-screen` | Orden y paginación de los resultados | Sin sugerir relevancia | UI-02 CON-01 |
| `goal-results-screen` | Estados de P07 | Carga | UI-10 REG-01 (el estado dura milisegundos con el backend local: se verifica con la prueba del producto y con el backend pausado) |
| `goal-results-screen` | Estados de P07 | Error con reintento | UI-10 |
| `goal-results-screen` | Estados de P07 | Vacío | UI-14 |
| `goal-results-screen` | Estados de P07 | Objetivo desconocido | REG-01 (la app no ofrece un objetivo desconocido: solo la prueba del producto y la API, API-07) |
| `goal-results-screen` | Estados de P07 | Sin autorización | UI-11 |
| `goal-results-screen` | Destino de las tarjetas | Abrir el pasaporte | UI-07 |
| `goal-results-screen` | Destino de las tarjetas | Volver conservando la posición | UI-07 |
| `goal-results-screen` | Destino de las tarjetas | Atrás desde el pasaporte hasta Inicio | UI-08 |
| `goal-results-screen` | Ver más detalles | Abrir la hoja | UI-06 |
| `goal-results-screen` | Ver más detalles | Cerrar la hoja | UI-06 |
| `goal-results-screen` | Ver más detalles | Sin peticiones ni registro | UI-06 UI-17 |
| `goal-results-screen` | Adaptación accesible de P07 | Texto aumentado | UI-12 UI-18 |
| `goal-results-screen` | Adaptación accesible de P07 | Controles accesibles | UI-13 |
| `goal-search-screen` | Presentación de Buscar por objetivo | Contenido y orden de las seis filas | UI-01 |
| `goal-search-screen` | Presentación de Buscar por objetivo | Nombres y orden de la API | REG-01 (con otro nombre solo la prueba del producto; la API real lo entrega de la base, API-01) |
| `goal-search-screen` | Presentación de Buscar por objetivo | Objetivo sin icono conocido | REG-01 (la app solo conoce los seis ids reales) |
| `goal-search-screen` | Presentación de Buscar por objetivo | Presentación local sin collage | UI-01 REG-01 |
| `goal-search-screen` | Adaptación accesible de P06 | Texto normal y aumentado | UI-12 UI-01 |
| `goal-search-screen` | Adaptación accesible de P06 | Zonas seguras y controles funcionales accesibles | UI-13 (zonas seguras: el emulador no tiene notch; solo insets de la barra de gestos) |
| `goal-search-screen` | Filas de objetivos con acción | Activación de una fila sin subáreas | UI-02 |
| `goal-search-screen` | Filas de objetivos con acción | Activación de una fila con subáreas | UI-03 |
| `goal-search-screen` | Filas de objetivos con acción | Semántica de botón | UI-13 UI-01 |
| `goal-search-screen` | Filas de objetivos con acción | Sin selección persistente | UI-01 UI-08 |
| `goal-search-screen` | Catálogo de objetivos desde la API | Carga | UI-10 REG-01 |
| `goal-search-screen` | Catálogo de objetivos desde la API | Error con reintento | UI-10 |
| `goal-search-screen` | Catálogo de objetivos desde la API | Sin autorización | UI-11 |
| `goal-search-screen` | Catálogo de objetivos desde la API | Sin conteos | UI-01 |
| `goal-search-screen` | Pantalla de Otros objetivos | Lista de subáreas | UI-03 |
| `goal-search-screen` | Pantalla de Otros objetivos | Abrir una subárea | UI-03 |
| `goal-search-screen` | Pantalla de Otros objetivos | Subárea vacía | UI-14 |
| `goal-search-screen` | Pantalla de Otros objetivos | Retorno | UI-08 |
| `goal-search-screen` | Pantalla de Otros objetivos | Estados de carga y error | UI-10 |
| `goal-search-screen` | Navegación a resultados | Pila completa | UI-08 |
| `goal-search-screen` | Navegación a resultados | Pestaña Inicio | UI-09 |
| `goal-search-screen` | Navegación a resultados | Sin datos de usuario | UI-17 |
| `goal-search-screen` | Navegación a resultados | Otras pestañas sin acción | UI-09 |

## Charters exploratorios

- EXP-01: explorar el desplazamiento rápido, el cambio de pantalla durante la carga de una página y el regreso desde el pasaporte, buscando tarjetas repetidas, saltos de posición o cierres inesperados.
- EXP-02: explorar P07 con la API pausada a mitad de la carga de la segunda página, buscando un pie sin salida o la pérdida de lo ya cargado (resultado en UI-10).
- EXP-03: explorar nombres y atribuciones de las plantas cuyo `displayName` es científico y de las que tienen autor nulo, buscando textos rotos (resultado en CON-03 y CON-04).
- EXP-04: explorar los parámetros de las rutas de objetivos (repetidos, desconocidos, vacíos, mayúsculas, barra final, HEAD y OPTIONS), buscando 5xx o respuestas sin el formato de error (resultado en API-06, API-08, API-17, API-18 y API-21).

## Cómo re-ejecutar

Véase la sección final de `goal-search-results.md`.

