# Design

## Context

Estado actual, con sus fuentes:

- `backend/catalog-api/src/http.rs` monta `/v1` con dos rutas (`/plants` y `/plants/{id}`), `/health` y `/openapi.json` fuera del prefijo, y una capa de autorización Bearer sobre todo `/v1` (`auth.rs`). Los parámetros `limit` (1 a 100, por defecto 20) y `offset` se validan a mano para devolver `problem+json` con el campo `param`. Las respuestas paginadas son `PageDto` (`items`, `total`, `limit`, `offset`). El acceso a datos es el trait síncrono `CatalogRepository` de `catalog-core` (`list_plants` y `get_plant`), que la API ejecuta con `spawn_blocking`.
- `app/lib/features/goal_search/presentation/goal_search_page.dart` es P06: seis filas fijas en el código, sin acción, con `Concentración` como quinta. El router (`app/lib/app/router.dart`) tiene `/goals` como hija de `/`, y el pasaporte cuelga de `/explore/:plantId`. El cliente HTTP (`CatalogRepository` de la app) solo conoce `listPlants` y `getPlant`. Explorar ya resuelve paginación infinita, estados de carga, error con reintento y descarte de respuestas atrasadas con un `Notifier` de Riverpod; es el patrón que se reutiliza.
- El cambio `consolidate-catalog-seed` deja en `catalog.db` `goal (id, label, position)` y `goal_subarea (id, goal_id, label, position)`, cargadas desde el mapa de objetivos, y `plant_goal` con `subarea_id` y `pending_review` (más `plant_goal_ref`), el nivel de seguridad por planta y `plant_review_flag` con `reviewFlags` estructurados (`{code, target, message}`). Los objetivos son `relajacion-estres`, `mejorar-el-sueno`, `cuidado-de-la-piel`, `alivio-respiratorio`, `cansancio-y-fatiga` y `otros-objetivos`; las subáreas, `digestion`, `vias-urinarias-y-genitales`, `dolor-e-inflamacion`, `boca-y-garganta`, `circulacion` y `molestias-oculares`. Este cambio los lee, no los define.
- El cambio `serve-consolidated-plants` define `displayName` (listado y detalle; el primer nombre común o el científico) y el objeto `image` (`url`, `pageUrl`, `author`, `license`, `licenseUrl`, `attributionRequired`), que la app carga directamente desde `commons.wikimedia.org` o `upload.wikimedia.org` por HTTPS, sin `Authorization`, con el arte local como respaldo (su D9). Para `safety` nulo su pasaporte dice «No hay datos de seguridad en las fuentes consultadas. Esto no significa que la planta sea segura.» (su D4). Este cambio adopta esas definiciones.
- Conteos de referencia de la EMA (fichas sobre 204; una ficha puede tener varias áreas): gastrointestinales 56, falta de apetito 15, estreñimiento 11, vías urinarias y genitales 45, dolor e inflamación 17, boca y garganta 16, circulación 14, molestias oculares 1, estrés y ánimo 18, sueño 13, piel 32, tos y resfriado 42, fatiga y debilidad 8. El número real de plantas por objetivo saldrá de la semilla, ya sin las plantas tóxicas y sin las ocultas por revisión; «Molestias oculares» podría quedar con 1 o 0.
- Mockups: P06 («¿Qué deseas lograr?») no define el destino de las filas ni el contenido de «Otros objetivos». P07 («Recomendaciones») muestra tarjetas con miniatura, nombre y descripción, un aviso y el botón «Ver más detalles», y no define el destino de las tarjetas ni del botón (`docs/mockups/pantallas.md`, `navegacion.md`). Las descripciones del mockup son texto de ejemplo y no se certifican.
- QA en cambios archivados: la API se probó con Postman o, si el MCP no estaba autenticado, con `curl` y un script (`qa/scripts/api_tests.py`); la app se validó en el emulador Android con `adb` (`qa/scripts/adb_ui.py`) y el smoke de integración. El proyecto es Flutter para Android y no hay Playwright para la app.

Dependencias entre cambios: este cambio se implementa después de `consolidate-catalog-seed` y de `serve-consolidated-plants` (véase `proposal.md`).

## Goals / Non-Goals

**Goals:**

- Que cada fila de P06 lleve a una lista real de plantas, sin lenguaje de eficacia y con el respaldo (la EMA) visible en la tarjeta.
- Que los nombres de los objetivos se puedan ajustar tras la revisión con el usuario sin reescribir pantallas.
- Un contrato aditivo dentro de `/v1`, con autenticación, paginación y errores como el resto.

**Non-Goals:**

- Elegir o ponderar plantas por relevancia. El orden es alfabético y la pantalla no es un ranking.
- Resolver `reviewFlags`, texto libre de búsqueda o persistencia. El pasaporte es del cambio 2.

## Decisions

### D1. Endpoints: `GET /v1/goals` y `GET /v1/goals/{goalId}/plants`

`GET /v1/goals` devuelve la lista completa, sin paginar (6 objetivos y unas 6 subáreas), con `id`, `name`, `plantCount` y `subareas` (`id`, `name`, `plantCount`). El orden de la lista es el orden de las filas de P06 y viene del mapa de objetivos. `GET /v1/goals/{goalId}/plants?subarea=&limit=&offset=` devuelve una página con `goal` (`id`, `name`), `subarea` (`id`, `name`, o `null`), `items`, `total`, `limit` y `offset`. Cada elemento lleva `id`, `displayName`, `scientificName`, `commonNames`, `family` (como el resumen del listado), más `areas` (nombres en español de las áreas de la EMA que respaldan a la planta en ese objetivo o subárea), `safetyLevel` (`alto`, `medio`, `bajo` o `null`) e `image` (el mismo objeto que el detalle del cambio 2, o `null`). Un `goalId` desconocido responde 404; una `subarea` que no pertenece al objetivo, o enviada a un objetivo sin subáreas, responde 400 con `param: subarea`; sin `subarea` en `otros-objetivos` se devuelve la unión de sus subáreas sin repetir plantas. `limit` y `offset` siguen las mismas reglas que `/v1/plants`. Ambas rutas quedan bajo `/v1`, por lo que heredan el token, el 401 y la documentación OpenAPI.

Alternativas:

- **`GET /v1/plants?goal=<id>&subarea=<id>`**: reutiliza el listado y la paginación, pero obliga a ampliar `PlantSummaryDto` con campos que solo tienen sentido con un objetivo (`areas`) o a devolver otro tipo según un parámetro, y un objetivo desconocido sería un 400 y no un 404. Se descarta por mezclar dos contratos en un recurso.
- **Una subárea como objetivo propio (`GET /v1/goals/digestion/plants`)**: evita el parámetro, pero convierte las subáreas en identificadores de primer nivel, rompe la jerarquía de la semilla (`otros-objetivos` con subárea) y obliga a la app a conocer qué identificadores son subáreas. Se descarta.
- **Un solo endpoint que devuelva objetivos con todas sus plantas**: una respuesta de cientos de plantas por objetivo. Se descarta por tamaño y porque P06 solo necesita los nombres.
- **Subárea en la ruta (`/goals/{id}/subareas/{sub}/plants`)**: es más explícito, pero duplica la ruta para un filtro opcional. Se prefiere el parámetro.

### D2. El catálogo de objetivos viene de la API

La API sirve los nombres, el orden y las subáreas; la app asocia un icono local por `id` (con un icono genérico para un identificador desconocido). Los nombres salen de `goal.label` y `goal_subarea.label`, el orden de `position` y las subáreas de `goal_subarea.goal_id`; el cambio 1 los carga desde el mapa de objetivos versionado de la semilla. Este cambio no añade tablas ni migraciones: la tarea 1.1 solo verifica que existan. El orden, el nombre y las subáreas no se duplican en la app.

Alternativas:

- **Lista fija en la app** (como hoy): evita una petición y P06 funciona sin red, pero los nombres provisionales exigirían publicar una versión de la app por cada ajuste, los conteos y la omisión de objetivos vacíos serían imposibles, y la app y la semilla podrían divergir. Se descarta porque el usuario pidió ajustar los nombres tras verlos en la app.
- **Fija en la app con conteos de la API**: dos fuentes de verdad para la misma lista. Se descarta.

Consecuencia: P06 necesita red, así que tiene estados de carga y de error con reintento (antes no hacía ninguna petición). No hay caché: la app no persiste datos.

### D3. Contenido marcado para revisión: se oculta lo condicionado

El cambio 1 dice que el objetivo `relajacion-estres` de una planta con interacciones graves en «Mental stress and mood disorders» (el hipérico) queda condicionado a revisión antes de publicarse, y lo registra como `plant_goal.pending_review = true`. Hasta que exista la capa de validación humana, `GET /v1/goals/{goalId}/plants` no devuelve las plantas con `pending_review` verdadero en ese objetivo y los conteos de `GET /v1/goals` tampoco las cuentan. La búsqueda solo lee `pending_review`; no interpreta los `reviewFlags` estructurados ni sus códigos. Los demás flags no ocultan nada. La planta sigue en Explorar y su pasaporte muestra su seguridad.

Alternativas:

- **Mostrarla con una marca de revisión**: es transparente, pero publica en una pantalla de «Recomendaciones» justo la planta que el cambio 1 decidió no publicar sin revisión, y el hipérico es el caso de interacciones farmacológicas graves. Se descarta.
- **Ignorar los flags**: contradice la decisión del cambio 1 y deja pasar el caso que más importa. Se descarta.
- **Leer el código de un `reviewFlag`**: acopla la búsqueda a los códigos del cambio 1 y a su evolución; `pending_review` ya expresa la decisión por objetivo. Se descarta.
- **Ocultar toda planta con cualquier `reviewFlag`**: dejaría fuera casi todo el catálogo (la mayoría de las plantas tiene algún flag, como identidad ambigua o ausencia de datos de seguridad) y vaciaría la búsqueda. Se descarta.

Riesgo: se pierde la planta más conocida del área. Se acepta mientras no haya revisión humana; el plan de salida es que la capa humana retire el flag y la planta reaparezca sin cambiar código.

### D4. Texto de las tarjetas: derivado del registro, sin lenguaje de eficacia

La tarjeta muestra el nombre principal (`displayName` del cambio 2), el nombre científico como secundario cuando hay nombre común, y una línea con la base del registro: «La EMA la registra en: <área>[, <área>]» con los nombres en español de las áreas (por ejemplo «Estrés mental y trastornos del ánimo»). No hay verbos de efecto («calma», «ayuda a») ni ningún texto de las tarjetas del mockup. Una planta con varias áreas dentro del objetivo muestra hasta dos y «y N más»; en «Otros objetivos» solo cuentan las áreas de la subárea elegida. El aviso del mockup se conserva tal cual: «Estas recomendaciones se basan en información especializada. Consulta detalles y precauciones.»

Alternativas:

- **Usar la descripción de la planta (cambio 2)**: es más rica, pero es texto libre generado por el LLM, puede contener lenguaje de efecto aunque el validador lo limite, y obliga a P07 a depender del detalle. Se descarta.
- **Usar los usos tradicionales**: son registros etnobotánicos, justo lo que el cambio 1 no quiere convertir en recomendaciones. Se descarta.
- **Sin línea de texto**: más seguro, pero la tarjeta pierde el porqué de la sugerencia y se aleja del mockup. Se descarta.

### D5. Seguridad: una marca en la tarjeta y el detalle en el pasaporte

La API devuelve solo `safetyLevel`; el texto y las citas de seguridad quedan en el pasaporte. La tarjeta muestra una marca «Precaución» cuando el nivel es `alto` o `medio`, y «Sin datos de seguridad (esto no significa que sea segura)» cuando es `null`: es el texto del pasaporte del cambio 2 abreviado para caber en una tarjeta, con la misma aclaración, y no se presenta como segura. El nivel `bajo` no muestra marca. La marca lleva texto, no solo color, y es parte del nombre accesible de la tarjeta.

Alternativas:

- **Solo en el pasaporte**: simplifica la tarjeta, pero una lista de «Recomendaciones» sin ninguna señal de riesgo contradice el aviso. Se descarta.
- **Texto de seguridad completo en la tarjeta**: duplica el contenido del cambio 2 y alarga las tarjetas. Se descarta.

### D6. Orden y paginación

El orden es total y estable: por `displayName` normalizado (sin mayúsculas ni acentos), luego nombre científico y luego identificador. No hay ranking: ni la fuerza de la evidencia ni el número de áreas influyen, porque ordenar por eso sería ordenar por eficacia. La paginación es la de `/v1/plants` (`limit` por defecto 20 y máximo 100, `offset`, `total`). P07 pide páginas de 20 y carga más al llegar al final de la lista, como Explorar, con pie de carga y error reintentable en el pie.

Alternativas:

- **Orden por nombre científico**: consistente con `/v1/plants`, pero el usuario ve nombres comunes y la lista parecería desordenada. Se descarta.
- **Orden por cantidad de respaldo de la EMA**: parece relevancia y sugiere eficacia. Se descarta.
- **Mostrar solo las N primeras sin paginar**: oculta plantas sin avisar (tos y resfriado tiene unas 42 fichas). Se descarta.

### D7. «Otros objetivos» es una pantalla nueva

Tocar «Otros objetivos» abre una pantalla con la lista de subáreas que devuelve `GET /v1/goals` (misma presentación de filas que P06), y cada subárea abre P07 filtrada. La regla es genérica: toda fila cuyo objetivo trae `subareas` no vacío abre la pantalla de subáreas; las demás abren P07. Una subárea sin plantas (por ejemplo, si «Molestias oculares» queda vacía tras los filtros) no se lista.

Alternativas:

- **Lista desplegable dentro de P06**: ahorra una pantalla, pero la lista de 6 filas más 6 subáreas a 200 % de texto obliga a un scroll largo y la semántica de una fila que expande y navega a la vez es confusa. Se descarta.
- **Mezclar las subáreas como filas de P06**: contradice la decisión de agruparlas bajo «Otros objetivos». Se descarta.

### D8. «Ver más detalles» abre una hoja informativa, sin navegar

El mockup no define el destino. El botón abre una hoja inferior «Sobre estas recomendaciones» que explica la base y los límites: las plantas listadas son las que la Agencia Europea de Medicamentos (EMA) registra en el área indicada, lo que se muestra no es un consejo médico ni una dosis, la marca de precaución indica advertencias de seguridad del registro, el detalle y las citas están en el pasaporte de cada planta y se debe consultar a un profesional de la salud. El texto es fijo en la app (no depende del registro). No navega a «Formular mezcla».

Alternativas:

- **Navegar a «Formular mezcla» (P08)**: el diagrama conecta P07 con P08, pero P08 no existe y no se implementa aquí. Se descarta.
- **Quitar el botón**: honesto, pero el aviso dice «Consulta detalles y precauciones» y el botón es parte del mockup. Se deja la decisión al usuario (véase Open Questions).
- **Abrir el pasaporte de la primera planta**: sin sentido para un botón general. Se descarta.

### D9. Rutas y navegación

Rutas hijas de `/goals`: `/goals/:goalId/subareas` (solo para objetivos con subáreas), `/goals/:goalId/plants` con `?subarea=<id>` opcional (P07) y `/goals/:goalId/plants/:plantId` (el pasaporte del cambio 2, que reutiliza `PlantPassportRoutePage`). El pasaporte cuelga de la ruta de goals y no de `/explore/:plantId`, para que la pila sea P06 -> (subáreas ->) P07 -> pasaporte y Atrás vuelva a la lista con su posición. Atrás de P06 vuelve a Inicio (sin cambios); la pestaña Inicio hace `go('/')` y limpia la pila. El estado de P07 (páginas cargadas y posición) se conserva mientras la pantalla está en la pila.

Alternativas:

- **Empujar `/explore/:plantId`**: reutiliza la ruta, pero mezcla las pilas de Explorar y de objetivos y el destino de Atrás deja de ser claro. Se descarta.
- **Una sola ruta `/goals/:goalId` que decida entre subáreas y resultados**: ahorra una ruta, pero esconde dos pantallas distintas bajo una URL. Se descarta.

### D10. Estados de P06 y P07

Carga (indicador con etiqueta accesible), error con `Reintentar` (reutiliza los errores legibles del cliente, incluido el de no autorizado), vacío y, para el objetivo desconocido, «Objetivo no encontrado». El vacío de P07 dice «Aún no hay plantas con información registrada para este objetivo» y no afirma que ninguna planta sirva para él ni sugiere otras. Un objetivo con `plantCount` 0 se muestra en P06 igualmente (es un nombre fijo del mapa) y abre ese vacío; solo las subáreas vacías se omiten, porque son opcionales. La app descarta las respuestas atrasadas igual que Explorar.

Alternativas: ocultar los objetivos vacíos de P06 (la fila desaparecería sin explicación y las cinco filas del mockup dejarían de ser estables) y mostrar el conteo en cada fila (parece un ranking y el número cambia con los flags). Ambas se descartan.

### D11. Miniatura con atribución corta

La tarjeta usa el objeto `image` y la carga directa del cambio 2 (su D9): solo HTTPS de `commons.wikimedia.org` o `upload.wikimedia.org`, sin `Authorization`, con el arte local de respaldo mientras carga, si falla o si no hay imagen (en ese caso sin atribución). Cuando la imagen se muestra, la tarjeta pone junto a ella el autor y la licencia como texto corto (`Foto: <autor> · <licencia>`), también si `attributionRequired` es falso, como hace el pasaporte. El enlace a la página del archivo, la URL de la licencia y la entrada de `Fuentes` quedan en el pasaporte del cambio 2. La API no sirve bytes ni consulta la red. La carga reutiliza el componente de imagen con validación de host del cambio 2 en lugar de duplicarlo.

Alternativas: miniatura sin atribución visible y todo en el pasaporte (más limpia, pero la licencia CC BY-SA pide crédito razonable junto a la imagen, y la tarjeta es donde se ve); añadir el enlace en la tarjeta (otro control táctil dentro de una tarjeta que ya es un control, y llevaría `url_launcher` a la lista); solo iconos locales (descarta el mockup y las imágenes que el cambio 1 ya recoge). Se descartan.

### D12. Estrategia de QA

API: colección de Postman con la variable secreta `token` (o `curl` y un script si el MCP no está autenticado, como en `add-api-token-auth`), con casos de objetivo válido y desconocido, subárea válida, ajena y sobre un objetivo sin subáreas, paginación, orden, 401 sin token, 405 y la ausencia de plantas tóxicas y de las ocultas por revisión. App: Playwright no aplica porque la app es Flutter para Android; la interfaz se valida en el emulador con `adb` y el smoke de integración, como en los cambios archivados. Si el usuario quiere Playwright, solo sería posible con una compilación web que hoy no existe; se registra como limitación.

## Risks / Trade-offs

- **[Los nombres de objetivos son provisionales]** -> Vienen de la API y se ajustan en el mapa de la semilla; la tarea final los revisa con el usuario en la app y registra el resultado.
- **[Dependencia de las tablas del cambio 1 y del DTO del cambio 2]** -> La tarea 1.1 comprueba `goal`, `goal_subarea`, `plant_goal.pending_review` y el objeto `image` antes de escribir consultas; si difieren, se ajusta este cambio, no los otros.
- **[Ocultar el hipérico y similares reduce la cobertura de «Relajación / Estrés»]** -> Se documenta; con 18 fichas de la EMA el área puede quedar corta. La capa humana lo corrige sin código.
- **[Un objetivo puede quedar con muy pocas plantas o ninguna]** -> El vacío es explícito y no afirma ausencia de utilidad; la QA revisa los conteos reales.
- **[La lista de «Recomendaciones» se lee como consejo]** -> El texto sale del registro, sin verbos de efecto; el aviso, la marca de precaución y la hoja de «Ver más detalles» dejan claro que es información especializada, no una indicación.
- **[Atribución de imágenes en una lista]** -> La tarjeta muestra autor y licencia junto a la miniatura y el pasaporte el detalle; si la revisión de licencias exige el enlace, se añade en la tarjeta.
- **[P06 ahora depende de la red]** -> Error con reintento y mensajes ya existentes; no se cachea.
- **[Orden alfabético por nombre común depende del primer nombre común]** -> Es la misma regla de nombre para mostrar del cliente; el orden de los nombres lo fija la semilla (`displayName` primero).
- **[Conflictos al archivar con los cambios 1 y 2, que también tocan `catalog-api` y `catalog-client`]** -> Los deltas son aditivos salvo el requisito del cliente; se archivan en orden 1, 2, 3 y se revisa el requisito modificado contra la versión vigente.

## Open Questions

- **«Ver más detalles»**: se propone la hoja informativa (D8). Si el usuario prefiere quitar el botón o dirigirlo a otro destino, cambian una tarea y un escenario, no el contrato de la API.
- **Nombres finales de objetivos y subáreas**: se confirman en la tarea de revisión en la app; no cambian la estructura.
- **Áreas de la EMA en español por planta**: si la base del cambio 1 solo guarda el área en inglés de la EMA, la etiqueta en español viene del mapa de objetivos; se confirma en la tarea 1.1 sin cambiar el contrato.
