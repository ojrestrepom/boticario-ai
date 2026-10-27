# boticario_ai

App Flutter (Android) de Boticario AI. Consulta el quickstart de la raíz del repositorio: [README.md](../README.md).

## Pasaporte de planta

El Pasaporte se alimenta del detalle consolidado que sirve `GET /v1/plants/{id}`. El cliente lo lee de forma tolerante: un campo ausente equivale a vacío o `null`, un tipo erróneo produce un error legible y un `level` de precauciones nulo es válido.

- Campos nuevos: `displayName`, `synonyms`, `description`, `origin`, `oil`, `useGroups`, `goals`, `safety`, `image` y `credits`.
- Cabecera: la imagen es la miniatura de 500 px de Wikimedia (`PlantImagePolicy`, solo HTTPS y los hosts `commons.wikimedia.org` y `upload.wikimedia.org`, sin `Authorization`) con el pie de atribución (autor, licencia y página del archivo). Mientras carga, si falla o si la planta no tiene imagen se ve el arte local de respaldo, sin pie y sin error.
- Pestañas: `General`, `Propiedades` y `Usos`, y bajo la activa la sección `Fuentes` (créditos, entrada de la imagen y licencias mixtas).
- Enlaces: las URL se muestran como texto y las `https` se abren en el navegador del sistema con `url_launcher` (versión fijada en `pubspec.lock`) desde el botón «Abrir en el navegador».
- Estados sin datos: cada campo vacío, los objetivos, las precauciones, los usos y las fuentes tienen un texto explícito; ninguna planta se presenta como segura por no tener datos.
- Backend anterior: si faltan los campos nuevos, el Pasaporte usa `uses` para derivar los grupos de uso y el primer nombre común como nombre para mostrar, y muestra los estados sin datos.
- Accesibilidad: las pruebas de `test/features/passport/passport_accessibility_test.dart` comprueban a 360x640 dp, con texto al 100 % y al 200 %, que no hay desbordes, que los botones miden al menos 48 dp, que el nivel de precauciones se ve como texto y que la imagen tiene descripción.

Las pruebas usan las fixtures reales de [`test/fixtures/api/`](test/fixtures/api/) y un lanzador de URL simulado; no usan red. El quick start y los comandos de calidad están en el [README de la raíz](../README.md).
