# Resultados de QA: serve-consolidated-plants (cambio 2)

Alcance: tareas 11.1 a 11.4. Plan, casos y trazabilidad en [`test-plan.md`](test-plan.md). Evidencia en `evidence/api/` y `evidence/app/`, scripts en `scripts/` y colección de Postman en `postman/`. Ejecución: 2026-10-27 y 2026-10-28 (UTC), rama `consolidate-catalog-seed` en `c8809f0`, sin cambios en el árbol de trabajo salvo esta carpeta.

## Resumen

- API: 0 fallos. Las 122 comprobaciones del censo de las 2.354 plantas contra la base, las 22 peticiones y 115 aserciones de Postman y las pruebas del producto (Rust 145 y suite de la semilla 559) pasan. Los tiempos del detalle con la base real son de 1,2 ms de mediana y 5,6 ms como máximo.
- App en el emulador: el smoke de `integration_test` **falla** contra el backend local (DEF-01, severidad alta). El resto de los recorridos (Explorar, pasaportes de lavanda, tóxica, eucalipto, planta vacía, sin nombre en español, citas sin resolver, enlaces, imagen sin conexión, backend anterior, texto al 200 %) cumple lo especificado, con la salvedad de DEF-01.
- Muestra de 30 plantas: sin lenguaje de efecto, dosis ni imágenes CC sin autor o sin enlace; 1 defecto de contenido de baja gravedad en textos de seguridad «no tóxica» (DEF-03) y observaciones.
- Defectos: DEF-01 (alta), DEF-02 (baja), DEF-03 (media, contenido de la semilla del cambio 1, no una regresión de este cambio).
- Token: ninguna evidencia lo contiene (barrido al final).

## Resultado por tarea

| Tarea | Estado | Notas |
|---|---|---|
| 11.1 Plan de pruebas | Cumplida | `test-plan.md` con particiones por tipo de planta, casos con ID, pasos y resultados esperados, y tabla de trazabilidad de los 139 escenarios de los seis deltas; verificado con `check-md-lines.py` (0 hallazgos) |
| 11.2 API con Postman | Cumplida | Postman CLI 1.74 ejecuta la colección local sin sesión (la sesión solo hace falta para publicar en la nube), así que no hizo falta `curl`; además un script de Python con un oráculo SQL independiente (censo de 2.354 plantas, 650 alias y 357 nombres anteriores) |
| 11.3 Interfaz en el emulador | **No cumplida**: el smoke falla (DEF-01) | Todo lo demás se ejecutó. Playwright no aplica. Logcat sin el token |
| 11.4 Revisión de 30 plantas y este informe | Cumplida | Muestra revisada en la API (30) y en la app (4 de la muestra más 6 más); cada criterio del plan tiene resultado, evidencia y estado (tabla final) |


## Defectos

### DEF-01 (alta): el smoke falla en el pasaporte con la imagen cargada porque, tras cambiar de pestaña, la ficha vuelve arriba y las pestañas quedan fuera de pantalla

- Requisito afectado: tarea 11.3 («el smoke actualizado en 8.2 debe pasar encontrando la fila `Lavanda`») y `plant-passport`, «Ficha accesible con texto aumentado» (controles esenciales alcanzables) en la práctica a 360x640 dp.
- Pasos para reproducir el smoke: con la API local en marcha y un emulador de 360x640 dp, `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_TOKEN=<token-app>`.
- Obtenido: el smoke llega a la fila `Lavanda` y abre el pasaporte, y falla en `catalog_smoke.dart:348` (`expect(_selectedChip(tester, 'Propiedades'), isTrue)`) con `Bad state: No element`. Se reprodujo dos veces (`evidence/app/APP-01-smoke-output.txt`).
- Pasos para reproducir a mano: Explorar, buscar `lavandula`, abrir `Lavanda`, esperar a que cargue la imagen, pulsar `Propiedades` (hay que desplazarse para llegar al chip).
- Obtenido a mano: con la imagen cargada, la cabecera (nombre, imagen de 600 px, autor, licencia, URL de la página del archivo y enlace) ocupa unos 1.230 de los 1.920 px de la pantalla; las pestañas quedan cortadas en el borde inferior de la primera pantalla y no se ve nada del contenido de la pestaña (`UI-07`). Al pulsar otra pestaña la ficha vuelve al inicio y las pestañas desaparecen de la pantalla (y del árbol de widgets), por lo que hay que volver a desplazarse para ver el contenido nuevo (`UI-08`). Sin imagen (planta sin foto o con la descarga bloqueada) las pestañas se ven completas (`UI-13`).
- Esperado: el smoke pasa y el contenido de la pestaña elegida es alcanzable sin volver a recorrer la cabecera.
- Causa probable (solo lectura del código): `plant_passport_page.dart` usa `key: PageStorageKey('passport-${plant.id}-$_tab')` en el `CustomScrollView`, de modo que cada pestaña es una lista de desplazamiento nueva con posición 0, y la cabecera con atribución es larga a 360x640 dp.
- Por qué no lo detectan las pruebas del producto: las 360 pruebas de `flutter test` pasan porque en ellas la imagen no se descarga (cabecera corta); solo la carga real de Wikimedia lo muestra.
- Evidencia: `evidence/app/APP-01-smoke-output.txt`, `evidence/app/UI-04-aibika-propiedades.png`, `UI-07-lavanda-general-primera-pantalla.png`, `UI-08-lavanda-propiedades-tras-tocar-chip.png`, `UI-13-imagen-sin-conexion-romero-general.png`, `UI-15-imagen-sin-autor-aethusa.png`.

### DEF-02 (baja): los nombres comunes se ordenan en binario (UTF-8), no alfabéticamente

- Requisito afectado: `catalog-api`, «Nombre para mostrar y orden de los nombres comunes», escenario «Nombre para mostrar primero» (resultado esperado «Lavanda», «Árnica», «Espliego»).
- Pasos para reproducir: `GET /v1/plants/acorus-calamus` y `GET /v1/plants/aleurites-moluccanus`.
- Obtenido: tras el `displayName`, las mayúsculas van antes que las minúsculas y las letras acentuadas al final: `Cálamo aromático`, `Calamus`, `Flagroot`, ..., `cálamo acuático`, `Ácoro`; y `Nuez de la India`, `Candleberry`, ..., `Árbol candil`. Con ese orden, el ejemplo de la spec daría «Lavanda», «Espliego», «Árnica». Afecta a 406 de las 1.730 plantas con nombres comunes (el orden binario difiere del alfabético sin distinguir mayúsculas ni acentos).
- Esperado: orden por texto sin distinguir mayúsculas ni acentos (o aclarar en la spec que el orden es binario).
- Impacto: bajo; solo cambia el orden de la lista de «Otros nombres comunes».
- Evidencia: `evidence/api/DEF-02-orden-nombres-comunes.txt`.

### DEF-03 (media, contenido de la semilla del cambio 1): seis textos de precauciones afirman «no tóxica» sin la cláusula «este dato no la hace segura»

- Requisito afectado: `plant-passport`, «Ninguna planta se presenta como segura» (los textos de la API se sirven tal cual, así que el defecto está en la semilla; la app los muestra en `Precauciones`).
- Pasos para reproducir: `GET /v1/plants/reynoutria-japonica` y las cinco `brassica-*` (`evidence/api/DEF-03-textos-no-toxica.txt`); en la app, `Propiedades`, `Precauciones`.
- Obtenido: `reynoutria-japonica` (sin nivel) dice «TPPT la clasifica como no tóxica para los humanos y anota que las especies de Reynoutria suelen ser no tóxicas.» Las cinco coles dicen «TPPT clasifica la toxicidad humana como «no tóxica» y la toxicidad animal como «tóxica»» y mencionan glucosinolatos tóxicos. Los otros textos de la misma familia (`abutilon-theophrasti`, `helianthus-tuberosus`) sí añaden «este dato no la hace segura».
- Esperado: ningún texto afirma que la planta es segura o inocua; los de TPPT con categoría «no tóxica» deberían llevar la misma cláusula.
- Impacto: medio por tratarse de seguridad, aunque cita una clasificación de la fuente. Es un asunto de contenido de la semilla (cambio 1), no de este cambio.

## Observaciones que no son defectos

- OBS-01: en 39 plantas el `displayName` coincide en texto con un nombre común en inglés y otro en español (p. ej. «Sisal»); el de idioma `en` queda antes que el `es` por el orden de idiomas. Un cliente que lea el idioma del primer nombre común vería `en` para un nombre en español.
- OBS-02: `mentha piperita` sin la «x» da 0 resultados, como está documentado. En la app, `matricaria recutita` encuentra Manzanilla de extremo a extremo.
- OBS-03: 17 plantas tienen dos grupos con la misma actividad y distinta fuente (p. ej. «Hidropesía» en `asparagus-officinalis`, de `Dropsy` e `Hydropsy`); la app muestra dos encabezados iguales.
- OBS-04: la semilla limita a 20 los grupos de uso por planta (477 de 1.459 plantas con grupos llegan a 20); el escenario «Muchos usos» con «decenas» solo se puede ejercitar hasta 20.
- OBS-05: autores de imagen con ruido heredados de la semilla: 24 imágenes de atribución obligatoria con «Own work», «Unknown author» o marcas de wiki como «( talk )»; 9 autores con una URL; 51 imágenes de dominio público sin autor (la app muestra «Autor: No disponible en fuente»). Ninguna imagen CC BY o CC BY-SA carece de autor o de enlace a la página.
- OBS-06: la actividad «Asma» (4 apariciones en la muestra) se sirve sin la fórmula «Uso tradicional, sin eficacia demostrada», que la semilla reserva para enfermedades graves. La app lo muestra tal como llega, como pide la spec.
- OBS-07: las citas sin resolver se muestran con la clave opaca de la fuente (p. ej. «M,B,G,&S,1991 (sin resolver)»), en cursiva y atenuadas, según la spec.
- OBS-08: con texto al 200 % en 360x640 dp todo es legible, desplazable y sin truncar, pero el área desplazable queda en poco más de la mitad de la pantalla (el botón fijo y la barra inferior de dos filas ocupan el resto); en horizontal el área es de unos 500 px de alto.
- OBS-09: sin imagen, el «arte local provisional» es el icono pequeño junto al nombre, no un bloque en la cabecera.
- OBS-10: las plantas tóxicas con nivel medio o bajo y advertencias graves en el texto (p. ej. `prunus-amygdalus`, nivel bajo, «registrada como veneno» y «cianogénica») no muestran aviso en `General`, porque el aviso es solo de nivel alto (decisión D4).
- OBS-11: el backend anterior se emuló con un proxy que quita los campos nuevos, pero no reproduce el orden alfabético anterior de los nombres; la prueba de compatibilidad cubre los campos ausentes, no el orden.
- OBS-12: `Tipo de documento` en `Objetivos` muestra la frase completa de `evidence` («La EMA tiene una monografía de la flor y otra del aceite esencial en esta área.»), no un tipo corto.
- OBS-13: textos de la base que tocan el barrido de efecto, todos aceptables: tres de seguridad con «beneficio-riesgo», «beneficios no superan sus riesgos» y «no garantiza su ausencia» (negaciones de la EMA), y «no recomendado» en dos hinojos. No hay dosis ni cantidades (0 coincidencias).
- OBS-14: el APK de depuración que compilé queda en `app/build/app/outputs/flutter-apk/app-debug.apk` (carpeta ignorada por git) con el token de prueba embebido; el token es inválido al bajar la API. No lo borré por estar fuera de `qa/`.
- OBS-15: la colección de Postman se regeneró después de ejecutarla solo para cambiar el valor del token incorrecto de `AUT-04` por un texto corto (sin cambio de lógica); no se volvió a ejecutar porque la API ya estaba detenida.

## Resultado por caso

| Caso | Qué | Resultado | Evidencia |
|---|---|---|---|
| API-01 | Listado, displayName y orden de comunes | PASA | `evidence/api/API-01.txt` |
| API-02 | Detalle de las 2.354 plantas: contrato y campos siempre presentes | PASA | `evidence/api/API-02.txt` |
| API-03 | displayName, names y synonyms | PASA | `evidence/api/API-03.txt, DEF-02-orden-nombres-comunes.txt` |
| API-04 | Perfil: descripción, origen, aceite, familia, partes | PASA | `evidence/api/API-04.txt` |
| API-05 | useGroups y uses | PASA | `evidence/api/API-05.txt` |
| API-06 | goals | PASA | `evidence/api/API-06.txt` |
| API-07 | safety | PASA | `evidence/api/API-07.txt` |
| API-08 | image | PASA | `evidence/api/API-08.txt` |
| API-09 | credits | PASA | `evidence/api/API-09.txt` |
| API-10 | Alias de identificadores (650) | PASA | `evidence/api/API-10.txt` |
| API-11 | Autenticación y OpenAPI | PASA | `evidence/api/API-11.txt` |
| API-12 | Búsqueda (alias, sinónimos, 357 nombres anteriores, oráculo SQL) | PASA | `evidence/api/API-12.txt` |
| API-13 | Casos puntuales | PASA | `evidence/api/API-13.txt` |
| API-14 | Barrido de textos | PASA | `evidence/api/API-14.txt` |
| API-15 | Detalle sin red | PASA | `evidence/api/API-08-sin-red.txt` |
| API-16 | Postman (22 peticiones, 115 aserciones) | PASA | `evidence/api/postman-run.txt` |
| API-17 | Exploratoria de bordes | PASA | `evidence/api/EXP-API-edge-cases.txt` |
| API-18 | Pruebas del producto catalog-api (cargo test) | PASA | `evidence/api/API-18-cargo-test-catalog-api.txt` |
| SED-01 | licenseUrl: sources.json, manifiesto y base | PASA | `evidence/api/seed-ingest-checks.txt` |
| SED-02 | licenseUrl inválida en el validador | PASA | `evidence/api/seed-ingest-checks.txt` |
| SED-03 | Suite unittest de tools/catalog-seed (559 pruebas) | PASA | `evidence/api/SED-03-unittest-summary.txt` |
| ING-01 | Build con licenseUrl | PASA | `evidence/api/ingest-license-url.txt` |
| ING-02 | Manifiesto con licenseUrl inválida | PASA | `evidence/api/ingest-license-url.txt` |
| ING-03 | Pruebas del producto catalog-ingest | PASA | `evidence/api/ING-03-cargo-test-catalog-ingest.txt` |
| IND-01 | Independencia de la fuente (3 pruebas) | PASA | `evidence/api/IND-01-source-independence.txt` |
| APP-01 | Smoke integration_test | FALLA | `evidence/app/APP-01-smoke-output.txt` |
| APP-02 | Explorar | PASA | `evidence/app/APP-02-explorar-filas.txt` |
| APP-03 | Pasaporte de lavanda | PASA | `evidence/app/passport-lavanda.txt` |
| APP-04 | Pasaporte de planta tóxica | PASA | `evidence/app/passport-aconitum-napellus.txt` |
| APP-05 | Pasaporte de eucalipto (sin nivel) | PASA | `evidence/app/passport-eucalipto.txt` |
| APP-06 | Pasaporte de planta sin datos | PASA | `evidence/app/passport-angelica-laxiflora.txt` |
| APP-07 | Planta sin nombre en español | PASA | `evidence/app/passport-abutilon-theophrasti.txt` |
| APP-08 | Citas sin resolver | PASA | `evidence/app/passport-alstonia-scholaris.txt` |
| APP-09 | Hipérico | PASA | `evidence/app/passport-hypericum-perforatum.txt` |
| APP-10 | Apertura de enlaces | PASA | `evidence/app/UI-11-chrome-pagina-archivo-commons.png` |
| APP-11 | Imagen sin conexión | PASA | `evidence/app/UI-13-imagen-sin-conexion-romero-general.png` |
| APP-12 | Backend anterior | PASA | `evidence/app/passport-backend-anterior-lavanda.txt` |
| APP-13 | Texto al 200 % | PASA | `evidence/app/UI-22-aconitum-200pct-general-3.png` |
| APP-14 | Miniatura de 500 px (tráfico) | PASA | `evidence/app/APP-14-trafico.txt` |
| APP-15 | Logcat sin token | PASA | `evidence/app/logcat-app.txt` |
| APP-16 | Pruebas del producto de la app (360) | PASA | `evidence/app/APP-16-flutter-test-summary.txt` |
| REV-01 | Muestra de 30 plantas en la API | PASA | `evidence/api/sample-30-view.txt` |
| REV-02 | Muestra en la app | PASA | `evidence/app/passport-*.txt` |

## Revisión de la muestra de 30 plantas (11.4)

- Muestra: la misma del cambio 1, tarea 10.5 (piloto, tóxicas, solo género, separadas y fusionadas por colisión, EMA fuera de USDA, fase 2): `evidence/api/sample-30-view.txt` (texto servido) y `sample-30-checks.tsv` (chequeos por planta). En la app se recorrieron cuatro de ellas (`lavandula-angustifolia`, `aconitum-napellus`, `hypericum-perforatum`, `abutilon-theophrasti`) y seis más (`eucalyptus-globulus`, `angelica-laxiflora`, `alstonia-scholaris`, `actaea-racemosa`, `aethusa-cynapium`, `salvia-rosmarinus`); la app muestra el DTO sin lógica propia, así que el resto se revisó en la API.
- Lenguaje de efecto: ninguno en los textos de las 30 ni en los de las 2.354 (`evidence/api/API-14-text-scan-hits.tsv`, solo las negaciones de la EMA de OBS-13).
- Dosis: ninguna en las 2.354 plantas.
- Ausencias presentadas como seguridad: las plantas sin datos de seguridad (`aloe-spp`, `ephedra-spp`, `crataegus-sp`, la bergamota) dicen «No hay precauciones registradas... Esto no significa que la planta sea segura»; los textos «no tóxica» de DEF-03 son el único caso a corregir.
- Aviso fijo de `Usos`: presente al inicio de la pestaña en todas las plantas recorridas, también en la vacía (`evidence/app/REV-02-comprobacion-aviso-fijo.txt`).
- Citas sin resolver: marcadas «(sin resolver)» y atenuadas (captura `evidence/app/alstonia-scholaris-Usos-2.png`).
- Actividades sensibles: las de cáncer, tumor, malaria y lepra de la muestra llevan «Uso tradicional, sin eficacia demostrada: ...»; las advertencias de riesgo grave (veneno, casos mortales, abortiva) llegan en `Precauciones`, no como usos (hipérico, ricino, estramonio, coralillo).
- Atribuciones: toda imagen CC BY y CC BY-SA de la muestra lleva autor, licencia y página (`sample-30-checks.tsv`, columna `cc_sin_autor_o_pagina` en `False` en las 30); el pie y `Fuentes` de la app muestran autor, licencia, enlace de la licencia y página (`UI-14-aconitum-fuentes-imagen.png`).
- Alias: los 650 alias resuelven a su planta (API-10) y la búsqueda recupera los 357 nombres anteriores.

## Cobertura: lo que no se probó o solo se cubrió con pruebas del producto

- Escenarios que solo cubren las pruebas del producto, porque la base real o el entorno no los ejercitan: «Orden estable en empate» (no hay nombres científicos repetidos), «Planta sin créditos» (todas las plantas tienen créditos), «Base construida con otra fuente» (solo se verificó que el código y OpenAPI no nombran datasets; no se construyó una base con otra fuente), «Carga del pasaporte», «Grupo sin países», «Sin créditos» de `Fuentes` y «Dato sin fuente».
- Las peticiones exactas del cliente (parámetros codificados, recorte a 200 caracteres, cabeceras, hosts permitidos de imágenes) se cubren con las 360 pruebas del producto; en el emulador solo se observó que el flujo real funciona con el token y que la imagen viene de `upload.wikimedia.org`.
- Miniatura de 500 px: se verificó por consumo de red (unos 64 KB en total al abrir un pasaporte cuyo original pesa 4,8 MB), no por la URL exacta, que HTTPS no deja ver.
- No se probó contra Cloud Run ni con un teléfono físico; no se probaron lectores de pantalla (TalkBack) ni otros tamaños de pantalla.
- Wikimedia: la app cargó imágenes de unas doce plantas, repetidas en algunas recargas, y no hubo ningún 429.
- Riesgos residuales: DEF-01 puede ocultar el contenido de las pestañas a usuarios con imagen cargada; los términos de reutilización de la EMA y TPPT siguen sin verificarse contra el texto legal y ahora son visibles en `Fuentes` (riesgo ya anotado en el diseño).

## Criterios del plan: resultado, evidencia y estado

Cada escenario de los deltas tiene casos, resultado, evidencia y estado. Las rutas de evidencia son relativas a `evidence/`.

| Capability | Escenario | Casos | Resultado | Evidencia | Estado |
|---|---|---|---|---|---|
| `catalog-api` | Listado sin búsqueda | API-01 API-16 APP-02 | API-01: PASA, API-16: PASA, APP-02: PASA | `api/API-01.txt`, `api/postman-run.txt`, `app/APP-02-explorar-filas.txt` | PASA |
| `catalog-api` | Contenido de cada elemento | API-01 API-16 | API-01: PASA, API-16: PASA | `api/API-01.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Nombre para mostrar en el listado | API-01 API-03 API-16 | API-01: PASA, API-03: PASA, API-16: PASA | `api/API-01.txt`, `api/API-03.txt, DEF-02-orden-nombres-comunes.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Planta sin nombre común | API-01 API-03 API-13 | API-01: PASA, API-03: PASA, API-13: PASA | `api/API-01.txt`, `api/API-03.txt, DEF-02-orden-nombres-comunes.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Orden estable en empate | API-01 (la base no tiene nombres cientificos repetidos: el empate solo se cubre con la prueba del producto, API-18) | API-01: PASA, API-18: PASA | `api/API-01.txt`, `api/API-18-cargo-test-catalog-api.txt` | PASA |
| `catalog-api` | Consulta vacía | API-12 | API-12: PASA | `api/API-12.txt` | PASA |
| `catalog-api` | Caracteres de patrón literales | API-12 API-16 API-17 | API-12: PASA, API-16: PASA, API-17: PASA | `api/API-12.txt`, `api/EXP-API-edge-cases.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Búsqueda por nombre científico | API-12 API-16 | API-12: PASA, API-16: PASA | `api/API-12.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Búsqueda por nombre común | API-01 API-12 API-13 API-16 | API-01: PASA, API-12: PASA, API-13: PASA, API-16: PASA | `api/API-01.txt`, `api/API-12.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Búsqueda por sinónimo | API-01 API-12 API-13 API-16 | API-01: PASA, API-12: PASA, API-13: PASA, API-16: PASA | `api/API-01.txt`, `api/API-12.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Búsqueda por identificador anterior | API-12 API-16 | API-12: PASA, API-16: PASA | `api/API-12.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Alias con puntuación en la consulta | API-12 API-16 | API-12: PASA, API-16: PASA | `api/API-12.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Alias sin duplicar resultados | API-01 API-12 API-13 API-16 | API-01: PASA, API-12: PASA, API-13: PASA, API-16: PASA | `api/API-01.txt`, `api/API-12.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Consulta sin letras ni dígitos | API-12 | API-12: PASA | `api/API-12.txt` | PASA |
| `catalog-api` | Búsqueda insensible a mayúsculas, acentos y espacios | API-01 API-12 API-13 API-16 | API-01: PASA, API-12: PASA, API-13: PASA, API-16: PASA | `api/API-01.txt`, `api/API-12.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Sin coincidencias | API-12 API-17 | API-12: PASA, API-17: PASA | `api/API-12.txt`, `api/EXP-API-edge-cases.txt` | PASA |
| `catalog-api` | Planta existente | API-02 API-13 API-16 | API-02: PASA, API-13: PASA, API-16: PASA | `api/API-02.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Sin información de procedencia | API-02 API-11 | API-02: PASA, API-11: PASA | `api/API-02.txt`, `api/API-11.txt` | PASA |
| `catalog-api` | Cita de `uses` sin cambios | API-05 API-13 API-16 | API-05: PASA, API-13: PASA, API-16: PASA | `api/API-05.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Planta sin usos | API-02 API-13 API-16 | API-02: PASA, API-13: PASA, API-16: PASA | `api/API-02.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Familia presente | API-02 API-04 | API-02: PASA, API-04: PASA | `api/API-02.txt`, `api/API-04.txt` | PASA |
| `catalog-api` | Familia ausente | API-02 API-04 API-13 | API-02: PASA, API-04: PASA, API-13: PASA | `api/API-02.txt`, `api/API-04.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Identificador inexistente | API-10 API-16 API-17 | API-10: PASA, API-16: PASA, API-17: PASA | `api/API-10.txt`, `api/EXP-API-edge-cases.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Base construida con otra fuente | IND-01 API-18 (solo pruebas del producto) | IND-01: PASA, API-18: PASA | `api/API-18-cargo-test-catalog-api.txt`, `api/IND-01-source-independence.txt` | PASA |
| `catalog-api` | Atribución en las respuestas | API-09 API-13 | API-09: PASA, API-13: PASA | `api/API-09.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Contrato sin nombres de dataset | API-11 IND-01 | API-11: PASA, IND-01: PASA | `api/API-11.txt`, `api/IND-01-source-independence.txt` | PASA |
| `catalog-api` | Nombre para mostrar primero | API-03 API-13 | API-03: PASA, API-13: PASA | `api/API-03.txt, DEF-02-orden-nombres-comunes.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Sin nombre común | API-01 API-03 API-13 | API-01: PASA, API-03: PASA, API-13: PASA | `api/API-01.txt`, `api/API-03.txt, DEF-02-orden-nombres-comunes.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Solo nombres en otros idiomas | API-03 API-13 | API-03: PASA, API-13: PASA | `api/API-03.txt, DEF-02-orden-nombres-comunes.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Varios nombres en otros idiomas | API-03 API-13 | API-03: PASA, API-13: PASA | `api/API-03.txt, DEF-02-orden-nombres-comunes.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Planta con todos los campos | API-13 API-16 | API-13: PASA, API-16: PASA | `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Planta con campos vacíos | API-13 API-16 | API-13: PASA, API-16: PASA | `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Grupos de uso | API-05 API-13 | API-05: PASA, API-13: PASA | `api/API-05.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Seguridad sin datos | API-07 API-13 | API-07: PASA, API-13: PASA | `api/API-07.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Seguridad sin nivel | API-07 API-13 API-16 APP-05 | API-07: PASA, API-13: PASA, API-16: PASA, APP-05: PASA | `api/API-07.txt`, `api/API-13.txt`, `api/postman-run.txt`, `app/passport-eucalipto.txt` | PASA |
| `catalog-api` | Cita completa en los grupos de uso | API-05 API-13 API-16 | API-05: PASA, API-13: PASA, API-16: PASA | `api/API-05.txt`, `api/API-13.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Grupo de uso con una cita sin resolver | API-05 APP-08 | API-05: PASA, APP-08: PASA | `api/API-05.txt`, `app/passport-alstonia-scholaris.txt` | PASA |
| `catalog-api` | Objetivo de la EMA | API-06 API-13 APP-03 | API-06: PASA, API-13: PASA, APP-03: PASA | `api/API-06.txt`, `api/API-13.txt`, `app/passport-lavanda.txt` | PASA |
| `catalog-api` | Subárea de otros objetivos | API-06 APP-05 | API-06: PASA, APP-05: PASA | `api/API-06.txt`, `app/passport-eucalipto.txt` | PASA |
| `catalog-api` | Imagen con licencia | API-08 API-13 | API-08: PASA, API-13: PASA | `api/API-08.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Sin imagen | API-08 API-13 | API-08: PASA, API-13: PASA | `api/API-08.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Sin acceso a la red | API-15 | API-15: PASA | `api/API-08-sin-red.txt` | PASA |
| `catalog-api` | Créditos de una planta con varias fuentes | API-09 API-13 | API-09: PASA, API-13: PASA | `api/API-09.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | URL de licencia por fuente | API-09 API-13 | API-09: PASA, API-13: PASA | `api/API-09.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Sin repeticiones | API-09 API-13 | API-09: PASA, API-13: PASA | `api/API-09.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Descripción derivada de Wikipedia | API-09 API-13 | API-09: PASA, API-13: PASA | `api/API-09.txt`, `api/API-13.txt` | PASA |
| `catalog-api` | Planta sin créditos | API-09 (0 plantas sin creditos en la base real: solo la prueba del producto, API-18) | API-09: PASA, API-18: PASA | `api/API-09.txt`, `api/API-18-cargo-test-catalog-api.txt` | PASA |
| `catalog-api` | Alias de un renombre | API-10 API-16 | API-10: PASA, API-16: PASA | `api/API-10.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Identificador canónico | API-10 API-16 | API-10: PASA, API-16: PASA | `api/API-10.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Identificador desconocido | API-10 API-16 | API-10: PASA, API-16: PASA | `api/API-10.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Alias sin autorización | API-10 API-11 API-16 | API-10: PASA, API-11: PASA, API-16: PASA | `api/API-10.txt`, `api/API-11.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Alias fuera del listado | API-10 API-16 | API-10: PASA, API-16: PASA | `api/API-10.txt`, `api/postman-run.txt` | PASA |
| `catalog-api` | Objetivo condicionado | API-06 API-13 API-16 APP-09 | API-06: PASA, API-13: PASA, API-16: PASA, APP-09: PASA | `api/API-06.txt`, `api/API-13.txt`, `api/postman-run.txt`, `app/passport-hypericum-perforatum.txt` | PASA |
| `catalog-api` | Grupo sin ninguna cita resuelta | API-05 | API-05: PASA | `api/API-05.txt` | PASA |
| `catalog-api` | Grupo con una cita resuelta y otra sin resolver | API-05 APP-08 | API-05: PASA, APP-08: PASA | `api/API-05.txt`, `app/passport-alstonia-scholaris.txt` | PASA |
| `catalog-api` | Planta con otros flags | API-02 API-13 REV-01 | API-02: PASA, API-13: PASA, REV-01: PASA | `api/API-02.txt`, `api/API-13.txt`, `api/sample-30-view.txt` | PASA |
| `catalog-api` | Sin flags en las respuestas | API-02 API-11 | API-02: PASA, API-11: PASA | `api/API-02.txt`, `api/API-11.txt` | PASA |
| `catalog-client` | Listado con parámetros | APP-02 APP-16 | APP-02: PASA, APP-16: PASA | `app/APP-02-explorar-filas.txt`, `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Consulta con caracteres especiales | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Consulta vacía | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Consulta larga | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Detalle por identificador | APP-03 APP-16 | APP-03: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-lavanda.txt` | PASA |
| `catalog-client` | Token en cada petición | APP-02 APP-03 APP-16 | APP-02: PASA, APP-03: PASA, APP-16: PASA | `app/APP-02-explorar-filas.txt`, `app/APP-16-flutter-test-summary.txt`, `app/passport-lavanda.txt` | PASA |
| `catalog-client` | Sin otros endpoints, hosts ni datos de usuario | APP-16 APP-14 | APP-16: PASA, APP-14: PASA | `app/APP-14-trafico.txt`, `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Imagen de un host permitido | APP-14 APP-16 | APP-14: PASA, APP-16: PASA | `app/APP-14-trafico.txt`, `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Imagen de un host no permitido | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Listado válido | APP-02 APP-16 | APP-02: PASA, APP-16: PASA | `app/APP-02-explorar-filas.txt`, `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Detalle válido | APP-03 APP-16 | APP-03: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-lavanda.txt` | PASA |
| `catalog-client` | Precauciones sin nivel | APP-05 APP-16 | APP-05: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-eucalipto.txt` | PASA |
| `catalog-client` | Cita sin resolver | APP-08 APP-16 | APP-08: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-alstonia-scholaris.txt` | PASA |
| `catalog-client` | Familia nula | APP-06 APP-16 | APP-06: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-angelica-laxiflora.txt` | PASA |
| `catalog-client` | Campos desconocidos | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Campo requerido ausente o de tipo erróneo | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Backend anterior sin los campos nuevos | APP-12 APP-16 | APP-12: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-backend-anterior-lavanda.txt` | PASA |
| `catalog-client` | Campo nuevo con tipo erróneo | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | JSON inválido | APP-16 | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `catalog-client` | Planta con nombre común | APP-02 APP-03 | APP-02: PASA, APP-03: PASA | `app/APP-02-explorar-filas.txt`, `app/passport-lavanda.txt` | PASA |
| `catalog-client` | Planta sin nombre común | APP-02 APP-06 APP-07 | APP-02: PASA, APP-06: PASA, APP-07: PASA | `app/APP-02-explorar-filas.txt`, `app/passport-abutilon-theophrasti.txt`, `app/passport-angelica-laxiflora.txt` | PASA |
| `catalog-client` | Backend sin nombre para mostrar | APP-12 APP-16 | APP-12: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-backend-anterior-lavanda.txt` | PASA |
| `catalog-client` | Idioma del nombre común | APP-16 APP-07 | APP-16: PASA, APP-07: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-abutilon-theophrasti.txt` | PASA |
| `explore-screen` | Vista inicial | APP-02 | APP-02: PASA | `app/APP-02-explorar-filas.txt` | PASA |
| `explore-screen` | Arte local | APP-02 | APP-02: PASA | `app/APP-02-explorar-filas.txt` | PASA |
| `explore-screen` | Planta sin nombre común | APP-02 | APP-02: PASA | `app/APP-02-explorar-filas.txt` | PASA |
| `explore-screen` | Nombre en español | APP-02 API-12 | APP-02: PASA, API-12: PASA | `api/API-12.txt`, `app/APP-02-explorar-filas.txt` | PASA |
| `plant-passport` | Cabecera y pestañas iniciales | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Campo de aceite no aplicable | APP-06 APP-16 | APP-06: PASA, APP-16: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Planta sin nombre común | APP-06 APP-07 | APP-06: PASA, APP-07: PASA | `app/passport-abutilon-theophrasti.txt`, `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Carga del pasaporte | APP-16 (solo pruebas del producto) | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `plant-passport` | Atribución sin procedencia por campo | APP-03 APP-04 REV-02 | APP-03: PASA, APP-04: PASA, REV-02: PASA | `app/passport-*.txt`, `app/passport-aconitum-napellus.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Campos de P05 presentes | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Datos generales ausentes | APP-06 | APP-06: PASA | `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Parte registrada | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Familia y nombres comunes | APP-03 APP-05 | APP-03: PASA, APP-05: PASA | `app/passport-eucalipto.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Sin partes ni nombres comunes | APP-06 | APP-06: PASA | `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Planta sin nombre en español | APP-07 | APP-07: PASA | `app/passport-abutilon-theophrasti.txt` | PASA |
| `plant-passport` | Aviso de nivel alto | APP-04 | APP-04: PASA | `app/passport-aconitum-napellus.txt` | PASA |
| `plant-passport` | Sin aviso para otros niveles | APP-03 APP-05 | APP-03: PASA, APP-05: PASA | `app/passport-eucalipto.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Sin lista de referencias en General | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Planta con objetivos de la EMA | APP-03 APP-05 | APP-03: PASA, APP-05: PASA | `app/passport-eucalipto.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Objetivo de otros objetivos | APP-05 | APP-05: PASA | `app/passport-eucalipto.txt` | PASA |
| `plant-passport` | Plantas sin evaluación respaldada | APP-04 APP-06 | APP-04: PASA, APP-06: PASA | `app/passport-aconitum-napellus.txt`, `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Sin lenguaje de eficacia | APP-03 APP-16 REV-02 | APP-03: PASA, APP-16: PASA, REV-02: PASA | `app/APP-16-flutter-test-summary.txt`, `app/passport-*.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Registro tradicional elegible | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Aviso fijo de usos tradicionales | APP-03 APP-06 | APP-03: PASA, APP-06: PASA | `app/passport-angelica-laxiflora.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Cita sin resolver visible | APP-08 | APP-08: PASA | `app/passport-alstonia-scholaris.txt` | PASA |
| `plant-passport` | Actividades sensibles tal como llegan | APP-04 REV-01 REV-02 | APP-04: PASA, REV-01: PASA, REV-02: PASA | `api/sample-30-view.txt`, `app/passport-*.txt`, `app/passport-aconitum-napellus.txt` | PASA |
| `plant-passport` | Grupo sin países | APP-16 (solo pruebas del producto) | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `plant-passport` | Sin registro elegible | APP-06 | APP-06: PASA | `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Muchos usos | APP-03 APP-13 | APP-03: PASA, APP-13: PASA | `app/UI-22-aconitum-200pct-general-3.png`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Ficha accesible con texto aumentado | APP-13 | APP-13: PASA | `app/UI-22-aconitum-200pct-general-3.png` | PASA |
| `plant-passport` | Imagen descrita | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Nivel de precauciones sin depender del color | APP-04 APP-05 | APP-04: PASA, APP-05: PASA | `app/passport-aconitum-napellus.txt`, `app/passport-eucalipto.txt` | PASA |
| `plant-passport` | Imagen con licencia CC BY-SA | APP-03 APP-14 | APP-03: PASA, APP-14: PASA | `app/APP-14-trafico.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Imagen sin atribución obligatoria | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Sin imagen | APP-06 | APP-06: PASA | `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Falla la descarga de la imagen | APP-11 | APP-11: PASA | `app/UI-13-imagen-sin-conexion-romero-general.png` | PASA |
| `plant-passport` | Abrir la página del archivo | APP-10 | APP-10: PASA | `app/UI-11-chrome-pagina-archivo-commons.png` | PASA |
| `plant-passport` | Precauciones de nivel alto | APP-04 | APP-04: PASA | `app/passport-aconitum-napellus.txt` | PASA |
| `plant-passport` | Precauciones sin nivel | APP-05 | APP-05: PASA | `app/passport-eucalipto.txt` | PASA |
| `plant-passport` | Precauciones sin datos | APP-06 | APP-06: PASA | `app/passport-angelica-laxiflora.txt` | PASA |
| `plant-passport` | Ninguna planta se presenta como segura | APP-04 APP-05 APP-06 REV-01 REV-02 | APP-04: PASA, APP-05: PASA, APP-06: PASA, REV-01: PASA, REV-02: PASA | `api/sample-30-view.txt`, `app/passport-*.txt`, `app/passport-aconitum-napellus.txt`, `app/passport-angelica-laxiflora.txt`, `app/passport-eucalipto.txt` | PASA |
| `plant-passport` | Fuentes de una planta | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Fuentes visibles en cada pestaña | APP-03 APP-04 | APP-03: PASA, APP-04: PASA | `app/passport-aconitum-napellus.txt`, `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Entrada de la imagen | APP-03 | APP-03: PASA | `app/passport-lavanda.txt` | PASA |
| `plant-passport` | Sin créditos | APP-16 (solo pruebas del producto) | APP-16: PASA | `app/APP-16-flutter-test-summary.txt` | PASA |
| `plant-passport` | Sin procedencia por campo | APP-03 REV-02 | APP-03: PASA, REV-02: PASA | `app/passport-*.txt`, `app/passport-lavanda.txt` | PASA |
| `catalog-seed` | Insumo íntegro | SED-03 | SED-03: PASA | `api/SED-03-unittest-summary.txt` | PASA |
| `catalog-seed` | Insumo alterado o ausente | SED-03 | SED-03: PASA | `api/SED-03-unittest-summary.txt` | PASA |
| `catalog-seed` | Snapshot de una fuente cambiante | SED-03 | SED-03: PASA | `api/SED-03-unittest-summary.txt` | PASA |
| `catalog-seed` | Retirar una fuente | SED-03 | SED-03: PASA | `api/SED-03-unittest-summary.txt` | PASA |
| `catalog-seed` | Fuente fuera de la lista | SED-03 | SED-03: PASA | `api/SED-03-unittest-summary.txt` | PASA |
| `catalog-seed` | URL de licencia de una fuente | SED-01 ING-01 | SED-01: PASA, ING-01: PASA | `api/ingest-license-url.txt`, `api/seed-ingest-checks.txt` | PASA |
| `catalog-seed` | Fuente sin URL de licencia | SED-01 SED-02 | SED-01: PASA, SED-02: PASA | `api/seed-ingest-checks.txt` | PASA |
| `catalog-seed` | URL de licencia inválida | SED-02 | SED-02: PASA | `api/seed-ingest-checks.txt` | PASA |
| `catalog-ingest` | Trazabilidad de un uso | API-05 ING-03 | API-05: PASA, ING-03: PASA | `api/API-05.txt`, `api/ING-03-cargo-test-catalog-ingest.txt` | PASA |
| `catalog-ingest` | Trazabilidad de un objetivo | API-06 API-09 ING-03 | API-06: PASA, API-09: PASA, ING-03: PASA | `api/API-06.txt`, `api/API-09.txt`, `api/ING-03-cargo-test-catalog-ingest.txt` | PASA |
| `catalog-ingest` | Dato sin fuente | ING-03 (solo pruebas del producto) | ING-03: PASA | `api/ING-03-cargo-test-catalog-ingest.txt` | PASA |
| `catalog-ingest` | URL de licencia de una fuente | SED-01 ING-01 | SED-01: PASA, ING-01: PASA | `api/ingest-license-url.txt`, `api/seed-ingest-checks.txt` | PASA |
| `catalog-ingest` | URL de licencia inválida en el manifiesto | ING-02 | ING-02: PASA | `api/ingest-license-url.txt` | PASA |

## Herramientas, delegación y limpieza

- Herramientas: no se instaló nada. Se usaron `postman` CLI 1.74 (ya instalado), `docker compose`, `sqlite3`, `adb` y `uiautomator` del SDK de Android, `flutter`, `cargo` (vía `mise`) y `python3` con la librería estándar.
- Delegación: no se delegó nada en el Junior-Worker; todo se hizo directamente.
- Lo que se creó y se retiró: el contenedor del compose, la red `qa-sin-red` y el contenedor `qa-api-sin-red` (eliminados), la imagen `boticario-backend:latest` construida hoy (eliminada), el proxy de backend anterior (detenido) y el emulador `boticario_catalog_api36` (apagado, con la app desinstalada y las reglas de `iptables` retiradas).
- Barrido de tokens: `grep -rEn '[0-9a-f]{32,}' openspec/changes/serve-consolidated-plants/qa/` no devuelve coincidencias, ni la búsqueda del valor exacto del token, ni de cabeceras `Bearer` con valor. El logcat completo del emulador (116.429 líneas) no contiene el token; en `evidence/app/logcat-app.txt` solo quedan las líneas de la app.
