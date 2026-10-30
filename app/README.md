# boticario_ai

App Flutter (Android) de Boticario AI. Consulta el quickstart de la raíz del repositorio: [README.md](../README.md).

## Pasaporte de planta

El Pasaporte se alimenta del detalle consolidado que sirve `GET /v1/plants/{id}`. El cliente lo lee de forma tolerante: un campo ausente equivale a vacío o `null`, un tipo erróneo produce un error legible y un `level` de precauciones nulo es válido.

- Campos nuevos: `displayName`, `synonyms`, `description`, `origin`, `oil`, `useGroups`, `goals`, `safety`, `image` y `credits`.
- Cabecera: la imagen es la miniatura de 500 px de Wikimedia (`PlantImagePolicy`, solo HTTPS y los hosts `commons.wikimedia.org` y `upload.wikimedia.org`, sin `Authorization`) con el pie de atribución «Foto: autor · licencia», con el autor enlazado a la página del archivo y la licencia a su texto. Mientras carga, si falla o si la planta no tiene imagen se ve el arte local de respaldo, sin pie y sin error.
- Pestañas: `General`, `Propiedades`, `Usos` (cada grupo con explicación del término trae bajo el título la etiqueta gris «Significado del término» y `Término: «definición» (Wikcionario)`, `(Wikipedia)` o `(adaptado de Wikipedia)`, con la fuente enlazada en línea) y `Fuentes` (créditos, incluidos Wikcionario y Wikipedia, entrada de la imagen y licencias mixtas).
- Enlaces: van sobre el nombre de la fuente, de la licencia y del autor, sin URL visible ni botón aparte (`PassportLinkedText`). Solo se abren las `https`, en el navegador del sistema con `url_launcher` (versión fijada en `pubspec.lock`); una pulsación larga copia la URL al portapapeles (`Clipboard` de Flutter) con el aviso «Enlace copiado».
- Estados sin datos: cada campo vacío, los objetivos, las precauciones, los usos y las fuentes tienen un texto explícito; ninguna planta se presenta como segura por no tener datos.
- Backend anterior: si faltan los campos nuevos, el Pasaporte usa `uses` para derivar los grupos de uso y el primer nombre común como nombre para mostrar, y muestra los estados sin datos.
- Accesibilidad: las pruebas de `test/features/passport/passport_accessibility_test.dart` comprueban a 360x640 dp, con texto al 100 % y al 200 %, que no hay desbordes, que las pestañas miden al menos 48 dp y los enlaces, que van dentro del texto, se anuncian como enlace con su destino, que el nivel de precauciones se ve como texto y que la imagen tiene descripción.

## Buscar por objetivo y Recomendaciones

P06, la pantalla de subáreas y P07 leen `GET /v1/goals` y `GET /v1/goals/{goalId}/plants` por el mismo repositorio HTTP y el mismo token que el resto del catálogo. Las rutas están en `lib/app/router.dart`: `/goals`, `/goals/:goalId/subareas`, `/goals/:goalId/plants` (con `?subarea=`) y `/goals/:goalId/plants/:plantId`, con los identificadores codificados. Atrás va paso a paso (pasaporte, P07, subáreas, P06, Inicio) y la pestaña Inicio limpia la pila.

- P06 (`goal_search_page.dart`): una fila por objetivo de la API, en su orden y con su nombre; el icono sale de un mapa local por identificador, con un icono genérico por defecto. Sin conteos. Carga y error con «Reintentar» (el 401 no muestra el token).
- «Otros objetivos» (`goal_subareas_page.dart`): una fila por subárea con plantas; un objetivo sin subáreas va directo a P07.
- P07 (`goal_results_page.dart`, con el estado en `goal_results_controller.dart` y los textos fijos en `goal_results_texts.dart`): título, aviso y hoja de `Ver más detalles` son textos de la app; el subtítulo `Para: <nombre>` y las tarjetas salen de la respuesta. Páginas de 20 que se piden al acercarse al final; las respuestas atrasadas se descartan. Cada tarjeta es un solo botón de al menos 48 dp cuyo nombre accesible reúne nombre, línea de la EMA y marca; la miniatura es la de 500 px de `PlantImagePolicy` y la atribución se ve solo con la imagen cargada. El pasaporte se abre apilado sobre P07 con la etiqueta de Atrás «Volver»: las páginas cargadas viven en un `Notifier` y el scroll en el `State` de P07, que siguen vivos mientras el pasaporte está encima.
- Aviso y `Ver más detalles`: al final del scroll, el aviso del mockup con su icono y justo debajo el botón, que abre la hoja `Sobre estas recomendaciones` (texto fijo) con `showModalBottomSheet`; se cierra con «Cerrar», deslizando o con Atrás del sistema y no navega ni hace peticiones.
- Plantas ocultas por revisión: las oculta la API (`plant_goal.pending_review`); la app muestra lo que llega y no vuelve a filtrar.
- Pruebas: `test/features/goal_search/`, `test/app/goal_navigation_test.dart` (pila completa, posición del scroll al volver del pasaporte y hoja sin cambio de ruta) y el smoke de `integration_test/catalog_smoke.dart`.

Las pruebas usan las fixtures reales de [`test/fixtures/api/`](test/fixtures/api/) y un lanzador de URL simulado; no usan red. El quick start y los comandos de calidad están en el [README de la raíz](../README.md).

## Ícono de la app

El logo fuente son las hojas de `assets/branding/boticario-logo.svg`, y `assets/branding/boticario-icon.svg` es su variante de ícono con las hojas dentro de la zona segura de 66 dp. En Android el ícono es adaptativo (`mipmap-anydpi-v26/ic_launcher.xml`, con capa monocromática para los íconos temáticos) y los PNG heredados de `res/mipmap-*` se regeneran rasterizando el SVG con `qlmanage -t -s 1024` (macOS), con las hojas ampliadas 1,3 veces sobre un fondo `#EEF4E8` de esquinas redondeadas, y reduciendo el resultado con `sips -z <px> <px>` a 48, 72, 96, 144 y 192 px.
