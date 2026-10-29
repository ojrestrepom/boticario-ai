# QA del cambio passport-sources-tab: resultados

La primera ronda (commit `6e90e9b`) está abajo, hasta «Cómo repetir». La sección «Reverificación» al final recoge la segunda ronda sobre el commit `d9102f8`, que corrige el DEF-01; las capturas de `evidence/review/` y `evidence/smoke-output.txt` son las de esa segunda ronda.

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
| M11 | Planta con muy pocos datos (`aeolanthus-myriantha`: un crédito y sin imagen): sin pie ni imagen, `Fuentes` con la intro y una entrada con nombre y licencia enlazados | Sin imagen; Pestaña Fuentes | Pasa | (captura de la primera ronda retirada) |
| M12 | Planta sin créditos ni imagen | Sin créditos | No ejecutado: no existe. En la base, el mínimo es un crédito (219 plantas con un crédito y sin imagen). El estado vacío queda cubierto solo por las pruebas de widget | n/a |
| M13 | Cambio entre pestañas al 100 %: de `Usos` (larga, hasta el final) a `Fuentes`, con las pestañas visibles al volver a subir y el contenido de `Fuentes` alcanzable sin hoja en blanco | DEF-01 del cambio 2 con cuatro pestañas | Pasa | `evidence/review/usos-to-fuentes.png` |
| M14 | Texto al 200 %: lavanda con las cuatro pestañas en un `Wrap` de dos o tres filas, sin truncado ni desbordes, cada pestaña con 165 px (63 dp) de alto, recorridas en ambos sentidos; `Fuentes` y su final alcanzables; de `Usos` a `Fuentes` las pestañas siguen visibles | Accesibilidad con texto aumentado | Pasa | (capturas de la primera ronda reemplazadas por las de la reverificación) |

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

## Reverificación (commit d9102f8)

Mismo entorno que la primera ronda: API local nativa con un token aleatorio nuevo (`<token-app>`), emulador `boticario_catalog_api36`, APK debug recompilado desde `d9102f8`.

| ID | Caso | Resultado | Evidencia |
|---|---|---|---|
| R-S1 | Smoke `flutter test integration_test/app_test.dart` en el emulador | Pasa: `All tests passed!` (+1), 40 s de prueba | `evidence/smoke-output.txt` |
| R-M8 | Pie de la lavanda al 100 %: un solo texto corrido «Foto: [autor] · Public domain» de 2 líneas (el autor, largo, ocupa la primera y parte de la segunda); sin «Foto:» suelto ni «·» huérfano; el autor se abre (`dat=https://commons.wikimedia.org/...`) | Pasa | `evidence/review/lav-general-top.png` |
| R-M9 | Pie de Quimbombó al 100 %: «Foto: [Kristine Paulus from New York, United States]» y en la segunda línea «· [CC BY 2.0]», ambos enlaces se abren (`creativecommons.org` y `commons.wikimedia.org`). Al 200 %: tres líneas de texto corrido, con el « ·» al final de la segunda; sin «Foto:» suelto | Pasa | `evidence/review/footer-two-links-quimbombo.png`, `quimbombo-200-footer-and-tabs.png` |
| R-M10 | Autor desconocido (`actaea-cimicifuga`): «Foto: [Wikimedia Commons] · Public domain» en una línea, el enlace se abre | Pasa | `evidence/review/wikimedia-commons-footer.png` |
| R-M13 | Del final de `Usos` a `Fuentes` al 100 %: las pestañas siguen visibles y el contenido de `Fuentes` empieza bajo ellas | Pasa | `evidence/review/usos-to-fuentes.png` |
| R-M14 | Lavanda al 200 %: pie de tres líneas sin truncar, cuatro pestañas en dos filas, `Fuentes` y su final alcanzables, y de `Usos` a `Fuentes` las pestañas siguen visibles | Pasa | `evidence/review/lav-200-footer-and-tabs.png`, `lav-200-fuentes.png`, `lav-200-fuentes-mid.png`, `lav-200-fuentes-final.png`, `lav-200-usos-to-fuentes.png` |
| R-F1 | `Fuentes` de la lavanda al 100 %: entradas compactas (nombre, «Licencia: …» y atribución consecutivos, sin las bandas vacías de 48 dp de la primera ronda); en `lav-fuentes-2.png` caben cuatro créditos en una pantalla | Pasa | `evidence/review/lav-fuentes-1.png`, `lav-fuentes-2.png`, `lav-fuentes-final.png` |
| R-F2 | Toque en el nombre «Wikipedia en español» y en «CC BY-SA 4.0»: abre Chrome con `https://es.wikipedia.org/...` y `https://creativecommons.org/...` | Pasa | logcat (sin guardar) |
| R-F3 | Pulsación larga sobre «Wikipedia en español»: aviso «Enlace copiado», portapapeles con la URL, no se abre el navegador (0 `START`, foco en la app) | Pasa | `evidence/review/longpress-copied.png` |
| R-F4 | Con Chrome deshabilitado (y luego reactivado): «No se pudo abrir el enlace», pantalla usable | Pasa | `evidence/review/open-failed-snackbar.png` |
| R-T1 | Pestañas al 100 %: recorrí `General`, `Propiedades`, `Usos`, `Fuentes` y de vuelta; los límites de los cuatro chips no cambian ni un píxel entre toques (General 48,904 a 303,1048; Propiedades 327,904 a 674,1048; Usos 698,904 a 901,1048; Fuentes 48,1060 a 308,1204) | Pasa | volcados de `uiautomator` (sin guardar) |
| R-T2 | Pestañas al 200 %: el mismo recorrido; límites fijos (General 48,273 a 406,444; Propiedades 430,273 a 958,444; Usos 48,456 a 312,627; Fuentes 336,456 a 704,627), la altura de cada chip es de 171 px (65 dp) | Pasa | volcados de `uiautomator` (sin guardar), `evidence/review/lav-200-footer-and-tabs.png` |
| R-T3 | Se distingue la pestaña activa: borde verde de 2 dp con relleno verde claro, las demás con borde gris; sin marca de verificación. En `uiautomator`, `selected="true"` solo en la activa en cada selección, tanto al 100 % como al 200 % | Pasa | `evidence/review/lav-general-top.png`, `lav-200-fuentes.png` |
| R-A1 | Árbol de accesibilidad de los enlaces (`uiautomator`): etiqueta «texto. Abre [destino]» sin la frase de pulsación larga, que ya no se anuncia | Pasa | volcados (sin guardar) |
| R-A2 | Ninguna URL como texto: en las capturas de `Fuentes`, del pie y de la lista de la reverificación no se ve ninguna URL ni DOI. No repetí el volcado completo con búsqueda de `http` de la primera ronda | Pasa (visual) | capturas de `evidence/review/` |

### DEF-01: cerrado

El pie ya no se parte en filas independientes: la lavanda ocupa 2 líneas al 100 % y Quimbombó 2 líneas, con el « · » unido a la licencia. No quedan «Foto:» aislados ni separadores huérfanos. La observación de las pestañas que se movían al seleccionarlas también queda cerrada (R-T1 a R-T3).

### Defectos nuevos

Ninguno.

### Observaciones de la reverificación

- Con textos largos, el « · » puede quedar al principio de una línea (Quimbombó al 100 %: «· CC BY 2.0») o al final de otra (Quimbombó al 200 %), siempre pegado a la licencia o al autor. Es el comportamiento normal de un texto corrido y no se considera defecto.
- Las áreas de toque de los enlaces en línea son ahora de la altura del texto (unos 30 dp en las filas de `Fuentes`, sobre 78 px), por la excepción de WCAG 2.5.8 que documentan el delta y D8. En el emulador los toques en el texto abrieron el enlace sin fallos; no se midió con un dedo real.
- El botón fijo «Ver formulaciones relacionadas» y la barra 2x2 a 200 % siguen tapando el inicio de `Fuentes` hasta desplazar (diseño previo).
- Retiré de `evidence/review/` las capturas de la primera ronda que mostraban la interfaz anterior (pestañas con marca, pie de tres filas, entradas con bandas) y que ya no representan el producto: `lav-200-general-top`, `lav-200-propiedades`, `lav-200-usos`, `lav-200-usos-end`, `min-data-aeolanthus-general`, `min-data-aeolanthus-fuentes` y `commons-fuentes-image-entry`. Los casos M10 y M11 de la primera ronda se revalidaron con el producto anterior; M11 (planta con pocos datos) no se repitió con la corrección.

### Cobertura de la reverificación

No se repitió M11 (planta con un crédito y sin imagen), ni la copia por pulsación larga al 200 %, ni TalkBack real. Limpieza: API detenida, emulador apagado, app desinstalada, `font_scale` en 1.0, `app-debug.apk` y `app-debug.apk.sha1` borrados.
