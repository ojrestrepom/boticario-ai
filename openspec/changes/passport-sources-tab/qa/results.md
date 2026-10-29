# QA del cambio passport-sources-tab: resultados

Entorno: API local nativa (binario `catalog-api` compilado con `--target-dir` en una carpeta auxiliar, sobre `data/build/catalog.db`, 2354 plantas), emulador `boticario_catalog_api36` (1080x1920, 420 dpi, Android 36), APK debug compilado con `API_TOKEN` aleatorio solo en la línea de comandos (`<token-app>`). No se usó el teléfono físico.

## Resumen

Sin defectos funcionales. Un defecto bajo de maquetación del pie de la foto y varias observaciones. La tarea 5.1 (smoke) pasa. La 8.1 queda cumplida salvo el caso «planta sin créditos ni imagen», que no existe en la base (toda planta tiene al menos un crédito).

## Casos

| ID | Caso | Escenario o requisito | Resultado | Evidencia |
|---|---|---|---|---|
| S1 | Smoke `flutter test integration_test/app_test.dart` en el emulador contra la API local (tarea 5.1) | Pestañas, `Fuentes` solo en su pestaña, sin URL como texto, pie con enlaces | Pasa: `All tests passed!` (+1) en 53 s | `evidence/smoke-output.txt` |
| M1 | Lavanda: cuatro pestañas `General`, `Propiedades`, `Usos`, `Fuentes`, `General` inicial | Cabecera y pestañas iniciales | Pasa | `evidence/review/lav-general-top.png` |
| M2 | Lavanda: `Fuentes` solo en su pestaña. Recorrido completo (scroll hasta el final) de `General`, `Propiedades` y `Usos` con volcado de la interfaz: sin «Licencia», «Atribución», texto de licencias mixtas ni «Archivo en Wikimedia Commons» | Fuentes no se repite bajo las otras pestañas | Pasa | `evidence/review/usos-end.png` |
| M3 | Ninguna URL como texto: el mismo recorrido de las cuatro pestañas no contiene `http` en ningún texto ni etiqueta; la atribución de EFSA, Duke y otras se ve sin su URL o DOI | Enlaces en línea sin URL visible | Pasa | `evidence/review/lav-fuentes-1.png`, `lav-fuentes-2.png` |
| M4 | `Fuentes` de la lavanda: texto de licencias mixtas, siete créditos con nombre enlazado (subrayado), «Licencia: [nombre]» enlazada cuando hay `licenseUrl`, atribución más pequeña y gris, entrada «Imagen» con autor, licencia (texto, `licenseUrl` nula) y «Archivo en Wikimedia Commons» | Pestaña Fuentes | Pasa | `evidence/review/lav-fuentes-2.png`, `lav-fuentes-final.png` |
| M5 | Abrir el enlace de la licencia «CC BY-SA 4.0» y el nombre «Wikipedia en español»: se abre Chrome (`dat=https://creativecommons.org/...` y `https://es.wikipedia.org/...`) y la app no muestra la página | Abrir un enlace | Pasa | `evidence/review/open-license-link.png` |
| M6 | Pulsación larga sobre «Wikipedia en español»: aviso «Enlace copiado», el portapapeles del sistema muestra `https://es.wikipedia.org/wiki/Lavandula_angustifolia` y no se lanza el navegador (sin `START` en logcat, foco en la app) | Copiar con pulsación larga | Pasa | `evidence/review/longpress-copied.png` |
| M7 | Enlace que no se puede abrir: con Chrome deshabilitado (`pm disable-user`, luego reactivado) el toque en «CC BY-SA 4.0» muestra «No se pudo abrir el enlace» y la pantalla sigue usable | Enlace que no se puede abrir | Pasa | `evidence/review/open-failed-snackbar.png` |
| M8 | Pie de la foto de la lavanda: «Foto: [Franz Eugen Köhler, Köhler's Medizinal-Pflanzen] · Public domain», autor enlazado, licencia como texto (`licenseUrl` nula) | Imagen con atribución; licencia sin URL | Pasa en contenido; ver DEF-01 por la maquetación | `evidence/review/lav-general-top.png` |
| M9 | Pie con dos enlaces (Quimbombó, `abelmoschus-esculentus`): «Foto: [Kristine Paulus from New York, United States] · [CC BY 2.0]», ambos subrayados; en el árbol de accesibilidad son enlaces con destino y aviso de pulsación larga | Imagen con licencia CC; Enlace en línea accesible | Pasa en contenido; ver DEF-01 | `evidence/review/footer-two-links-quimbombo.png` |
| M10 | Autor desconocido (`actaea-cimicifuga`): «Foto: [Wikimedia Commons] · Public domain», enlace a `commons.wikimedia.org` (`dat=https://commons.wikimedia.org/...`); en `Fuentes`, «Autor: No disponible en fuente» y «Archivo en Wikimedia Commons» | Autor desconocido; Imagen sin autor | Pasa | `evidence/review/wikimedia-commons-footer.png`, `commons-fuentes-image-entry.png` |
| M11 | Planta con muy pocos datos (`aeolanthus-myriantha`: un crédito y sin imagen): sin pie ni imagen, `Fuentes` con la intro y una entrada con nombre y licencia enlazados | Sin imagen; Pestaña Fuentes | Pasa | `evidence/review/min-data-aeolanthus-general.png`, `min-data-aeolanthus-fuentes.png` |
| M12 | Planta sin créditos ni imagen | Sin créditos | No ejecutado: no existe. En la base, el mínimo es un crédito (219 plantas con un crédito y sin imagen). El estado vacío queda cubierto solo por las pruebas de widget | n/a |
| M13 | Cambio entre pestañas al 100 %: de `Usos` (larga, hasta el final) a `Fuentes`, con las pestañas visibles al volver a subir y el contenido de `Fuentes` alcanzable sin hoja en blanco | DEF-01 del cambio 2 con cuatro pestañas | Pasa | `evidence/review/usos-to-fuentes.png` |
| M14 | Texto al 200 %: lavanda con las cuatro pestañas en un `Wrap` de dos o tres filas, sin truncado ni desbordes, cada pestaña con 165 px (63 dp) de alto, recorridas en ambos sentidos; `Fuentes` y su final alcanzables; de `Usos` a `Fuentes` las pestañas siguen visibles | Accesibilidad con texto aumentado | Pasa | `evidence/review/lav-200-footer-and-tabs.png`, `lav-200-propiedades.png`, `lav-200-usos.png`, `lav-200-fuentes.png`, `lav-200-fuentes-mid.png`, `lav-200-fuentes-final.png`, `lav-200-usos-end.png`, `lav-200-usos-to-fuentes.png` |

## Defectos

### DEF-01 (baja): el pie de la foto se parte de forma poco legible cuando el autor es largo

- Escenario: «Imagen con licencia CC BY-SA» y «Accesibilidad con texto aumentado» (el contenido es correcto y no se trunca; falla la presentación).
- Reproducir: abrir el pasaporte de la lavanda o de Quimbombó en el emulador a 100 % (o la lavanda a 200 %).
- Obtenido: el `Wrap` deja «Foto:» solo en una línea, el autor en otra y el separador « · » queda al final de la línea del autor (lavanda) o al principio de la siguiente («· CC BY 2.0» en Quimbombó, «· Public domain» a 200 %). Con los 48 dp de cada enlace el pie ocupa de tres a cuatro filas (unos 270 px, 100 dp, a 100 %), cuando el usuario se quejaba de que la sección era intrusiva.
- Esperado: un pie compacto con la forma «Foto: [autor] · [licencia]», sin separador huérfano ni «Foto:» aislado.
- Causa probable: «Foto: », el enlace del autor, « · » y la licencia son cuatro hijos independientes del `Wrap` (véase la nota de implementación de `design.md`).
- Evidencia: `evidence/review/lav-general-top.png`, `footer-two-links-quimbombo.png`, `lav-200-footer-and-tabs.png`.
- No ocurre con autor corto o desconocido (`wikimedia-commons-footer.png`, una sola línea).

## Observaciones

- El smoke comprueba los enlaces del pie solo si la foto cargó (`_expectPhotoFooterLinks` sale sin aserciones cuando no hay «Foto: »). En esta ejecución el emulador tenía red y las fotos cargan, pero la salida del smoke no lo prueba; si no hubiera red, ese punto pasaría sin comprobarse.
- A 100 % en 411 dp la cuarta pestaña `Fuentes` ya baja a una segunda fila; es el `Wrap` previsto en D6 y no oculta ninguna pestaña.
- Al seleccionar una pestaña el `Wrap` se reacomoda (el chip seleccionado lleva una marca y se ensancha): los chips cambian de posición entre toques consecutivos, por ejemplo al 200 %. No afecta la función, pero un toque «a ciegas» en la posición anterior falla.
- A 200 % el botón fijo «Ver formulaciones relacionadas» y la barra inferior en 2x2 ocupan unos 800 px de 1920 y tapan el contenido de las pestañas hasta que se desplaza. Es el diseño existente, no un cambio de esta rama; el contenido sigue alcanzable.
- Los créditos de la EMA y de TPPT traen `url` (https) en la base actual, así que su nombre sí se enlaza; el escenario «Crédito sin enlaces» habla de `url` y `licenseUrl` nulos «como los de la EMA», y solo `licenseUrl` es nula. Los créditos sin ningún enlace no se probaron en el emulador (cubiertos por pruebas de widget). El texto de la spec no coincide del todo con los datos.
- Android 13 o posterior muestra su propia vista previa del portapapeles junto al aviso «Enlace copiado» (esperado, D7).
- Chrome muestra su pantalla de primer arranque al abrir el primer enlace en este emulador; no es un fallo de la app.

## Capturas para el usuario (en `evidence/review/`)

- `lav-general-top.png`: `General` de la lavanda con su pie de foto.
- `lav-fuentes-1.png`: `Fuentes` de la lavanda, primera pantalla (justo tras seleccionar la pestaña); `lav-fuentes-2.png` es la siguiente pantalla.
- `lav-fuentes-final.png`: `Fuentes` de la lavanda, final.
- `wikimedia-commons-footer.png`: pie con «Wikimedia Commons».
- `lav-200-footer-and-tabs.png` (`General` seleccionada) y `lav-200-fuentes.png` (`Fuentes` seleccionada): las cuatro pestañas al 200 %.

## Cobertura y no ejecutado

- No hay plantas sin créditos ni imagen (M12).
- No se probó el modo avión ni la imagen que no carga en el emulador; el fallo de apertura se provocó deshabilitando el navegador.
- URL `http` o sin host: no hay ninguna en la base; solo las pruebas de widget la cubren.
- Lectores de pantalla reales (TalkBack): solo se inspeccionó el árbol de accesibilidad con `uiautomator` (enlaces con destino y aviso de pulsación larga), sin recorrer con TalkBack.
- Solo el emulador de 411 dp de ancho; 360x640 lo cubren las pruebas de widget.

## Cómo repetir

Compilar la API con `cargo build --release --manifest-path backend/Cargo.toml -p catalog-api --target-dir <carpeta-auxiliar>` y arrancarla con `API_TOKENS=<token-app>` sobre `data/build/catalog.db`. Desde `app/`: `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_TOKEN=<token-app>`. Para el recorrido a mano, `flutter build apk --debug --dart-define=API_TOKEN=<token-app>`, instalar con `adb install -r` y navegar con `adb shell input`. Al terminar: `adb shell settings put system font_scale 1.0`.

No se instaló ninguna herramienta ni dependencia. No se delegó en el Junior-Worker.
