# Resultados de QA: app conectada al backend (connect-app-to-backend, tareas 7.4 y 7.5)

- Fecha de ejecución: 2026-10-14 (noche) y 2026-10-15, hora local.
- Commit probado: `4ff10be` (`git rev-parse --short HEAD`).
- La re-verificación de DEF-01 (2026-10-15) se hizo sobre el árbol de trabajo posterior a `26a9931`, con la corrección de `plant_passport_page.dart` pendiente de commit (APK debug reconstruido e instalado en `emulator-5554`).
- Emulador: `emulator-5554`, AVD `boticario_catalog_api36`, Android 16 (API 36), 1080x1920 a 480 dpi (360x640 dp).
- Flutter 3.47.6 stable, Dart 3.13.5.
- Backend: imagen `boticario-backend`, 2.376 plantas, en 8080 (topología directa) o en 18080 detrás del proxy de registro en 8080.
- Plan: `test-plan-app-backend.md`. Resultados crudos: `results.jsonl` (una línea por ejecución; el último registro de cada caso es el vigente salvo los FAIL crudos clasificados abajo). Evidencia en `evidence/`. Al cerrar la QA se conservó solo la evidencia referenciada en este informe y en el plan, más el volcado XML gemelo de cada captura; el resto se descartó.
- Herramientas: nada instalado en el proyecto. Solo scripts Python propios en `scripts/` y comandos de adb, Docker y Flutter existentes.

## Resumen

Casos con resultado final: 67 (64 PASS registrados en `results.jsonl`, 2 registrados como OBS crudo que son PASS sin hallazgo (E-04a y E-10a) y TC-02 por `curl`). FAIL finales: 0; ningún caso quedó en FAIL tras clasificar los FAIL crudos como artefactos de medición. Defecto: 1 (DEF-01, severidad baja, preexistente, hallado dentro de A-02), corregido y verificado el 2026-10-15 (sin defectos abiertos). NO EJECUTADO: 6 (sección propia, incluye E-10b como medición de red). Observaciones: 8.

## Resultado por caso

| Caso | Resultado | Evidencia |
|---|---|---|
| TC-01 smoke contra el backend | PASS | `evidence/tc01-smoke-app_test.log` |
| TC-01b smoke con el backend detenido | PASS (falla como se espera, reportado no exitoso) | `evidence/tc01b-smoke-backend-stopped.log` |
| TC-03 `flutter test test/` sin backend (+195) | PASS | `evidence/tc03-flutter-test-no-backend.log`, `evidence/tc03-docker-ps-before.txt` |
| TC-04 manifests (main, debug, profile, fusionados debug y release) | PASS | `evidence/tc04-manifests.txt` |
| D-01 README, enlaces y párrafos de una línea | PASS | `evidence/tc05-docs-checks.txt` |
| TC-02 contexto de la API (`limit=0` 400, `q` de 201 caracteres 400, `no-existe` 404) | PASS | `evidence/tc02-api-context-curl.txt` |
| E-01 primera página y scroll infinito (122 filas en el orden de la API, peticiones `offset=0`, 50, 100) | PASS | `evidence/e01-deep.png`, `evidence/e-paging-ros-rows.json` |
| E-01b posición tras abrir una fila de la segunda página | PASS | `evidence/e01-deep-after-return.png` |
| Paginación completa de `ros` (166 filas, offsets 0, 50, 100, 150, pie «No hay más resultados») | PASS | `evidence/e-paging-ros-bottom.png`, `evidence/e-paging-ros-rows.json` |
| E-02 `lavandula` (7 filas, «English Lavender» / «Lavandula angustifolia») | PASS | `evidence/e-search-lavandula.png`, `evidence/e-search-lavandula-bottom.png` |
| E-03a mayúsculas y espacios exteriores | PASS (ver artefacto 1) | `evidence/e-search-upper-spaces.png` |
| E-03b espacios internos repetidos (`+` en la URL) | PASS (ver artefacto 1) | `evidence/e-search-inner-spaces.png` |
| E-03c acento (`àrnica` encuentra `Arnica montana`, `q=%C3%A0rnica`) | PASS | `evidence/e-search-accent.png` |
| E-04a sin coincidencias | PASS (distinto del vacío de Aceites; registrado como OBS crudo, sin hallazgo) | `evidence/e-search-nomatch.png` |
| E-05a `Aceites` sin petición | PASS | `evidence/e-filter-aceites-nomatch-query.png` |
| E-05b `Plantas` + consulta, borrar conserva filtro | PASS | `evidence/e-filter-plantas-with-query.png`, `evidence/e-filter-plantas-after-clear.png` |
| E-06 consulta de 250 caracteres (máximo enviado 200, respuestas 200, sin 400) | PASS (ver OBS-06) | `evidence/e-longquery-250.png` |
| E-06b reservados `a&b=c#d/e?f+g` codificados | PASS | `evidence/e-reserved-chars.png` |
| E-07 debounce (6 teclas en ~50 ms, una petición) | PASS | `evidence/e-debounce.png`, `evidence/proxy-all.jsonl` |
| E-08 respuesta atrasada descartada | PASS | `evidence/e-late-before-arrival.png`, `evidence/e-late-after-arrival.png` |
| E-09 estado de carga «Cargando catálogo...» | PASS | `evidence/e-loading-first-page.png` |
| E-10a spinner del pie | PASS por captura (ver OBS-04) | `evidence/e-footer-loading.png` |
| E-10b «Reintentar» del pie pide solo esa página | NO EJECUTADO como medición de red (el script que lo medía se interrumpió); S-06b muestra que el reintento del pie carga la siguiente página | `evidence/s06-footer-recovered.png` |
| E-11 tiempo máximo de 10 s (error entre ~7,7 s y 12,1 s con la resolución del sondeo) | PASS (ver artefacto 2) | `evidence/p-loading.png`, `evidence/p-timeout-error.png`, `evidence/e-footer-error-timeout.png` |
| E-12a `abies-spectabilis` solo científico en Explorar | PASS | `evidence/e-abies-rows.png` |
| E-12b nombre `und` mostrado tal cual en Explorar | PASS | `evidence/e-und-name-row.png` |
| P-01 `lavandula-angustifolia` (cabecera, General, Propiedades, 10 usos con cita) | PASS | `evidence/p-lavandula-angustifolia-*.png`, `evidence/p-lavandula-general.png` |
| P-02 `abies-spectabilis` (cabecera solo científico, «No hay nombres comunes registrados», 2 usos) | PASS | `evidence/p-abies-spectabilis-general.png` |
| P-03 `chondrus-crispus` («No disponible en fuente», vacío explícito de usos) | PASS | `evidence/p-chondrus-crispus-general.png`, `evidence/p-chondrus-crispus-usos.png` |
| P-04 `abies-sachalinensis` (sin usos) | PASS (ver artefacto 3) | `evidence/p-abies-sachalinensis-usos.png` |
| P-05 `rosmarinus-officinalis` (59 usos con cita, coinciden con la API) | PASS | `evidence/p-rosmarinus-officinalis-usos.png` |
| P-05b scroll real hasta el último uso de Romero | PASS | `evidence/p-rosmarinus-usos-scrolled-end.png` |
| P-06 `artemisia-annua` (principal con idioma `und`, nombres con idioma) | PASS | `evidence/p-artemisia-general.png` |
| P-07 `/explore/no-existe` y id con reservados (404, «Planta no encontrada», regreso seguro) | PASS | `evidence/p-notfound-direct-route.png`, `evidence/p-notfound-reserved-id.png`, `evidence/p-notfound-after-back.png` |
| N-01a/b consulta, filtro y posición tras abrir y volver con el chevron | PASS | `evidence/n01-before-open.png`, `evidence/n01-after-return.png`, `evidence/n01-top-after-return.png` |
| N-01c Atrás de Android desde el pasaporte | PASS (ver artefacto 4 y OBS-01) | `evidence/n01c-before.png` |
| N-02 volver a Inicio y entrar reinicia Explorar | PASS | `evidence/n02-home.png`, `evidence/n02-reentry.png` |
| N-03 chevron y Atrás desde Explorar llevan a Inicio | PASS | resultado en `results.jsonl` |
| N-04a/b/c barra inferior, corazón y formulaciones deshabilitados; `Inicio` vuelve a Home | PASS | resultado en `results.jsonl` |
| H-01 sockets TCP del UID de la app (solo 10.0.2.2:8080 saliente) | PASS (ver artefacto 5) | `results.jsonl` (H-01), `scripts/s_hosts.py` |
| H-02 Inicio y P06 sin peticiones | PASS | `evidence/h02-p06.png` |
| H-03 120 peticiones de la app: solo GET, `/v1/plants` y `/v1/plants/{id}`, `limit=50`, `Accept: application/json` | PASS (ver artefacto 6) | `evidence/proxy-all.jsonl`, `scripts/s_h03.py` |
| A-01 Explorar al 200 % | PASS | `evidence/a200-explore-top.png`, `evidence/a200-explore-rows.png`, `evidence/a200-explore-footer-end.png`, `evidence/a200-explore-empty.png`, `evidence/a200-explore-aceites-scrolled.png` |
| A-02 Pasaporte al 200 % (contenido) | PASS, con DEF-01 sobre la barra inferior | `evidence/a200-p-lav-general.png`, `evidence/a200-p-lav-general-s2.png`, `evidence/a200-p-lav-usos.png`, `evidence/a200-p-notfound.png` |
| S-01 Explorar con backend detenido: error y Reintentar | PASS | `evidence/s01-explore-error.png`, `evidence/s01-home-backend-down.png` |
| S-02 Reintentar con backend detenido | PASS | `results.jsonl` |
| S-03 Inicio y P06 funcionan con backend detenido | PASS | `evidence/s03-p06-backend-down.png` |
| S-04 `docker compose start` y Reintentar recupera Explorar | PASS | `evidence/s04-explore-recovered.png` |
| S-05 pasaporte: error, Reintentar y recuperación | PASS | `evidence/s05-passport-error.png`, `evidence/s05-passport-recovered.png` |
| S-06a/b error en el pie conservando lo cargado y recuperación | PASS | `evidence/s06-footer-error.png`, `evidence/s06-footer-recovered.png` |
| a200-S-01 a a200-S-06b los mismos al 200 % | PASS (ver artefacto 7) | `evidence/a200-s01-explore-error.png`, `evidence/a200-s01-explore-error-scrolled.png`, `evidence/a200-s05-passport-error.png`, `evidence/a200-s06-footer-error.png` |
| F-01 listado 503 | PASS | `evidence/f-01.png` |
| F-02 listado 400 | PASS | `evidence/f-02.png` |
| F-03 listado 200 con JSON truncado | PASS | `evidence/f-03.png` |
| F-04 listado 200 sin `items` | PASS | `evidence/f-04.png` |
| F-05 detalle 500 | PASS | `evidence/f-05.png` |
| F-06 detalle 200 sin `scientificName` | PASS | `evidence/f-06.png` |
| F-07 campos desconocidos y `family` nula se aceptan | PASS | `evidence/f-07.png`, `evidence/f-run.log` |

## Clasificación de los FAIL crudos de `results.jsonl`

Ningún FAIL crudo es un defecto del producto. Todos son artefactos de medición del arnés de QA y todos pasaron al corregir el arnés o la expectativa; el registro corregido es el último de cada caso en `results.jsonl`.

1. E-03a y E-03b: el primer intento tecleó con la lista desplazada hacia abajo, así que el toque a (540, 450) abrió una fila en lugar del campo (peticiones `/v1/plants/lavandula-angustifolia`). Se corrigió el helper para volver arriba y localizar el campo; el reintento da PASS (`q=LAVANDULA` sin espacios exteriores, `q=mentha+++SPICATA`).
2. E-11: el primer registro dio 12,5 s (pie) y 12,1 s (pasaporte) frente a 10 s. Cada volcado de uiautomator tarda 2,35 s, así que el error apareció en una ventana de ~2,4 s anterior a la detección (entre ~7,7 s y 12,1 s); ninguna petición esperó los 16 s inyectados. Artefacto de resolución, no incumplimiento. La exactitud de 10 s la cubren los tests unitarios con `MockClient` (tarea 1.5).
3. P-04: la expectativa del script era «Sakhalin Fir»; la API entrega «Japanese Fir» como primer nombre común. La app muestra lo correcto (`Japanese Fir` / `Abies sachalinensis`, familia `Pinaceae`, sin usos). Corregida la expectativa, PASS.
4. N-01c: el script dejaba el campo de búsqueda con foco; al volver, Flutter restaura el foco y reabre el teclado, que tapaba la lista (y un arrastre sobre el teclado tecleó «by» por gesto). Tras desenfocar antes de abrir la ficha, PASS. El comportamiento de foco queda como OBS-01.
5. H-01: el socket `0.0.0.0:0` en estado `0A` del UID de la app es un socket en escucha (el VM service de Flutter en builds debug), no tráfico saliente. El script ahora excluye los sockets en LISTEN; lo único saliente es `10.0.2.2:8080` (estado establecido).
6. H-03: el análisis incluía mi propio `curl /healthz` y contaba `user-agent` y `accept-encoding` como cabeceras de la app. Esas dos cabeceras las añade `dart:io` (no son identidad de usuario). Se filtraron las peticiones con `User-Agent: Dart/...` y se aceptan `host`, `accept`, `user-agent`, `accept-encoding`; PASS con 120 peticiones, sin `Authorization`, cookies ni otros datos.
7. a200-S-01, a200-S-02 y a200-S-06a: con el texto al 200 % y el error en pantalla, el botón `Reintentar` queda por debajo del pliegue (bajo la barra inferior de 2x2) y no aparece en el volcado hasta desplazar. Sí era alcanzable con un solo arrastre vertical (148x48 dp en Explorar; en el pie, visible bajo las filas ya cargadas). Los dos primeros fallaron por buscar el nodo sin desplazar; el tercero por filtrar filas con la ventana de contenido ocupada por el pie. Corregidos y re-ejecutados (a200-S-01, a200-S-02 y a200-S-06a en PASS, con captura `evidence/a200-s06-footer-error.png`). La alcanzabilidad por scroll se anota como OBS-05.

## Defectos

### DEF-01 (baja, preexistente): la barra inferior del pasaporte parte «Favoritos» y «Historial» a mitad de palabra al 200 %

- Spec contradicha: `openspec/specs/plant-passport/spec.md`, «Accesibilidad del pasaporte», escenario «Ficha accesible con texto aumentado» (texto esencial legible y sin truncado a 360x640 dp al 200 %).
- Reproducción: emulador a 360x640 dp, `adb shell settings put system font_scale 2.0`, abrir cualquier pasaporte (por ejemplo `adb shell am start -n com.example.boticario_ai/.MainActivity --es route /explore/lavandula-angustifolia`) y mirar la barra inferior.
- Esperado: etiquetas legibles completas (como en la barra de Explorar, que pasa a 2x2).
- Obtenido: «Favorit / os» y «Histori / al» en dos líneas cortando la palabra; «Inicio» y «Perfil» enteras.
- Evidencia: `evidence/a200-p-lav-usos.png`, `evidence/a200-p-lav-general-s2.png`.
- Nota de alcance: `_PassportBottomBar` y `_navItem` no cambian en `182e2ca..HEAD` (misma `Row` con `Expanded` anterior al cambio), por lo que no es regresión de este cambio; se reporta porque la spec vigente aplica y el orquestador decide si se corrige aquí o en un cambio propio. Los controles son alcanzables y las etiquetas semánticas son correctas.

- Estado: corregido y verificado el 2026-10-15 sobre el árbol de trabajo con la corrección pendiente de commit. Con `font_scale` 2.0 la barra del pasaporte se dispone en 2x2 (Inicio y Favoritos en la fila superior, Historial y Perfil en la inferior; cada elemento ocupa la mitad del ancho), «Favoritos» e «Historial» se leen enteras en una línea, cada control mide 180x65 dp (>= 48 dp) y conserva su etiqueta semántica («Inicio», «Favoritos no disponible», «Historial no disponible», «Perfil no disponible», los tres últimos deshabilitados), e «Inicio» vuelve a Home. Al 100 % la barra sigue en una sola fila (cuatro elementos de 90x56 dp en y=1680). Evidencia: `evidence/def01-fix-200-passport.png`, `evidence/def01-fix-200-passport.xml`, `evidence/def01-fix-200-passport-b.png`, `evidence/def01-fix-200-home.png`, `evidence/def01-fix-100-passport.png`, `evidence/def01-fix-100-passport.xml`; registros `DEF01-fix-100`, `DEF01-fix-200` y `DEF01-fix-200-home` en `results.jsonl`.

No se encontraron defectos de severidad crítica, alta ni media.

## Observaciones

- OBS-01: si el campo de búsqueda tenía foco antes de abrir una ficha, al volver (chevron o Atrás) Flutter restaura el foco y reaparece el teclado, que oculta la lista (`evidence/probe-nav-C.png`). Si el campo no tiene foco no ocurre. No contradice las specs.
- OBS-02: con un nombre principal de dos líneas (por ejemplo `Annual Mugwort (GRIN)`), el árbol de accesibilidad lista el nombre científico antes del nombre principal (`evidence/p-artemisia-general.xml`); con un nombre corto el orden es principal y luego científico. El orden de lectura de TalkBack no se verificó.
- OBS-03: la API no registra peticiones (`docker compose logs api` solo muestra la línea «escuchando»), así que las peticiones de la app se observaron con un proxy de registro propio (`scripts/logproxy.py`). Las cabeceras vistas son `host`, `accept: application/json`, `user-agent` (Dart) y `accept-encoding`.
- OBS-04: el indicador de carga del pie tiene `Semantics(label: 'Cargando más resultados')` en el código, pero no aparece en el volcado de uiautomator mientras gira (sí se ve en la captura `evidence/e-footer-loading.png`). Pendiente de TalkBack.
- OBS-05: al 200 % con un error en pantalla (Explorar o pie), `Reintentar` queda bajo el pliegue y hay que desplazar una vez; es alcanzable (148x48 dp) y la página sigue siendo desplazable. No contradice la spec.
- OBS-06: el campo de búsqueda conservó solo 200 caracteres al teclear 250, de modo que el recorte del repositorio no se alcanzó en la prueba de caja negra (cubierto por tests unitarios); la API nunca recibió más de 200 caracteres ni devolvió 400.
- OBS-07: abrir una ruta directa `/explore/:id` (extra `route` del intent) construye también Explorar debajo y dispara una petición de lista `offset=0`; es inofensivo y permite que «Volver a Explorar» tenga destino.
- OBS-08: en Usos el volcado de uiautomator expone todos los registros en un solo nodo semántico aunque estén fuera de pantalla; la alcanzabilidad se verificó con scroll real y capturas. Además, `flutter test integration_test/...` sobrescribe `app/build/app/outputs/flutter-apk/app-debug.apk` con el APK del arnés y desinstala la app del emulador; para pruebas manuales hay que volver a ejecutar `flutter build apk --debug` e instalar.

## NO EJECUTADO

- Dispositivo físico con `--dart-define=API_BASE_URL=http://<IP-del-Mac>:8080`: no hay dispositivo físico; solo el valor por defecto del emulador y la lectura de `README.md`.
- Ejecución de un build `release` en dispositivo: solo se verificó el manifest fusionado de release (INTERNET sin HTTP en claro); la imposibilidad real de HTTP en claro en release no se ejecutó.
- TalkBack y lectores de pantalla: solo se inspeccionó el árbol semántico con uiautomator (ver OBS-02 y OBS-04).
- Caja negra del guard HTTP del smoke que deniega hosts distintos del de la URL base: se leyó el código (`_AllowOnlyApiHostGuard`) y el smoke pasa, pero no se provocó una petición a otro host; el muestreo de sockets (H-01) y el proxy (H-03) confirman que la app solo contacta a `10.0.2.2:8080`.
- E-10b como medición de red (el reintento del pie pide solo esa página): el script se interrumpió; queda cubierto por los tests de `explore_controller_test.dart` y por S-06b a nivel de comportamiento.
- Consultas con caracteres de control y el carácter `%` literal en `q`: no se pueden teclear con adb ni el teclado; cubierto por el recorte del repositorio y por la API (que responde 400 a esos casos).

## Riesgos residuales

- Los nombres vienen en inglés o `und` (decisión de producto); las filas de plantas con `und` muestran sufijos como «(GRIN)».
- La precisión exacta de 10 s del timeout se verifica solo con tests unitarios; en el emulador se acotó a una ventana de ~2,4 s.
- No se probó build release ni dispositivo físico, donde la red y el HTTP en claro se comportan distinto.

## Estado al terminar

- Backend: parado (`docker compose down`).
- Emulador `emulator-5554`: encendido, con la app debug instalada y `font_scale` restaurado a 1.0.
- El proxy `logproxy.py` está detenido.
- No se hicieron commits ni se modificó código, docs, specs ni `tasks.md`; solo se escribió en `openspec/changes/connect-app-to-backend/qa/`.
