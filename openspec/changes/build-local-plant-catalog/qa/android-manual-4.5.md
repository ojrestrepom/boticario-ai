# QA manual Android — 4.5 / revisión integral 5.3

**Fecha: 2026-10-03 UTC. Resultado: funcional/visual ejecutado y offline PASS; revisión integral PARCIAL.** No se aprueba accesibilidad integral: TalkBack manual **NO EJECUTADO**. Sin defectos nuevos reproducibles en el alcance ejecutado. No se marcan tareas 4.5/5.3 ni se modifican checklists.

## Entorno, alcance y seguridad

- Exclusivamente `emulator-5566`, AVD `boticario_catalog_api36`, QEMU PID `28376`, Android 16/API 36, arm64, headless/SwiftShader. Identidad comprobada mediante `adb -s emulator-5566 emu avd name` antes de cada operación ADB; helper detiene la ejecución ante identidad incorrecta o tooling concurrente detectado. No operación sobre Samsung/otros seriales.
- Panel 1080×1920 px, 480 dpi: **360×640 dp nominales antes de insets**, no 360×640 de contenido útil. Sin cambiar resolución/densidad ni safe areas del SO.
- Flutter 3.47.6 stable/Dart 3.13.5 existentes. App real `lib/main.dart`, paquete `com.example.boticario_ai`, versión `0.1.0`/code `1`; router/ProviderScope/tema y asset reales. Sin harness, fakes ni rutas debug. Build/instalación normales autorizados con `flutter run --debug --target lib/main.dart --no-resident -d emulator-5566` desde `app/`; exit 0. No clear data/uninstall.
- Ejecuciones registradas: **14:31:37–15:00:36 UTC**, log append-only `evidence/android-manual-commands.log`. Timestamps UTC del host prevalecen sobre el reloj local de las capturas. Inspección de evidencia y resumen posterior a ese intervalo.
- Leídos requerimientos completos del cambio (proposal/design/tasks y cinco specs delta), README/pin/config, mockups, guía USDA e informes/logs QA anteriores. Trazabilidad abajo: `../specs/<capability>/spec.md`.
- Únicos ajustes temporales autorizados: `font_scale=1.0/2.0`, wifi/datos deshabilitados para offline. Originales y finales exactos: **`{"font_scale":"1.0","wifi_on":"1","mobile_data":"1"}`**. Rollback en `finally` y señales SIGINT/SIGTERM; todos los 28 pares before/after coinciden, incluidos intentos abortados del helper. No se cambió TalkBack ni otros ajustes, red host, SDK/licencias, dependencias, código/tests/config producto o documentación existente.
- Herramientas: ADB/UIAutomator/screencap/logcat existentes y helpers Python estándar `android_manual.py`/`android_manual_summary.py`. **Ninguna herramienta/dependencia instalada.** Playwright/axe/Postman no aplican a esta app nativa Android sin interfaz web/API de negocio; no se ejecutaron ni se presentan como cobertura.

## Plan de pruebas y resultados

Precondiciones comunes **P**: revisión aceptada, AVD anterior sin herramienta concurrente, app debug real instalada, datos locales existentes, Home y font 1.0 salvo indicación. Todas las entradas son sintéticas. Evidencia abreviada: **E(x)** significa `qa/evidence/android-manual-x`; capturas `.png` tienen árbol `.xml` con el mismo nombre salvo indicación. PASS acredita solo los pasos descritos, no todos los escenarios de la capability. Riesgo alto primero: navegación/identidad/límites de evidencia; luego controles, legibilidad y seguridad operacional.

| ID / riesgo | Requerimiento / capability | Técnica, precondiciones y pasos | Resultado esperado | Resultado y evidencia |
|---|---|---|---|---|
| AM-01 / alto | `flutter-app-bootstrap`: arranque Android, marca y flujo local | Transición inicial; P; force-stop/start app real; observar Home | `Boticario AI`, no saludo alternativo/login/demo; Inicio seleccionado | **PASS**. E(home100-cold.png), E(preflight-info.json), E(build.log) |
| AM-02 / alto | `home-screen`: once acciones, barra inmóvil y recorrido acotado | Tabla de decisión; P; activar dos iconos, tres tarjetas inertes, CTA y cuatro tabs; luego Explorar | Diez inertes permanecen Home sin overlays/permisos; solo Explorar abre P04 | **PASS**. E(home100-inert-after.png), E(explore100-top.png), comandos |
| AM-03 / alto | `home-screen`: contrato debug y no datos de usuario en mensajes | Particiones inicial/activación; P; logs solo PID actual antes y después; buscar marcador sintético tras búsqueda | 0 mensajes Home al cold start; un literal por activación; no consulta en mensajes producto | **PASS** en debug/arranque y activaciones observados. E(cold-pid-4245.log), E(home-actions-pid-4245.log), E(flow100-pid-4245.log), E(synthetic-query-pid-4245.log); no hot reload/release |
| AM-04 / alto | `plant-catalog`: identidad/orden; `explore-screen`: composición | Partición válida y límite nombre largo; P; abrir Todas y desplazar lista a Menta | Exactamente Lavanda/Eucalipto/Romero/Manzanilla/Menta, científicos fuente completos, arte provisional | **PASS**. E(explore100-top.png), E(explore100-bottom.png); científicos enumerados abajo |
| AM-05 / alto | `explore-screen`: búsqueda por ambos nombres normalizada | Equivalencias; P/P04; introducir científico `  LAVANDULA   ANGUSTIFOLIA ` y común `méNTA` (acento por IME nativo); cerrar IME | Solo Lavanda y solo Menta respectivamente, reactividad local y normalización | **PASS**. E(search100-scientific.png), E(search100-accent-common.png), E(keyboard-accent-popup.png); comandos guardan secuencia de teclado |
| AM-06 / alto | `explore-screen`: filtros combinados/borrar/Aceites | Tabla de decisión; P/P04; consulta Menta→Plantas→Aceites; borrar; Todas | Plantas combina consulta; Aceites vacío específico; borrar conserva Aceites; Todas recupera conjunto | **PASS**. E(search100-accent-plants.png), E(search100-oils-query.png), E(search100-oils-clear.png) |
| AM-07 / alto | `explore-screen`: sin coincidencias distinto de Aceites | Partición negativa; P/P04/Todas; `QA_SYNTH_20261003_NO_MATCH` | Vacío de búsqueda, no error ni vacío de Aceites | **PASS**. E(search100-no-match.png), comparación con E(search100-oils-clear.png) |
| AM-08 / alto | `plant-passport`: identidad y General inicial; `explore-screen`: abrir fila correcta | Particiones cinco registros; P/P04; abrir cada fila y volver | Header común/científico correcto, General inicial, tres tabs, arte local | **PASS**. E(lavanda100-top.png), E(eucalipto100-top.png), E(romero100-top.png), E(manzanilla100-top.png), E(menta100-top.png); también cinco árboles offline |
| AM-09 / alto | `plant-passport`: General/vacíos/partes; `plant-catalog`: procedencia/no aceite | Particiones campos presentes/ausentes; P; recorrer General de Menta y Lavanda hasta final de procedencia/cita | Vacíos explícitos, partes registradas no recomendadas, planta no aceite; USDA/CC0/version/dataset/URL/fecha diferenciada/cita disponibles | **PASS** para las dos fichas revisadas a 100%. E(menta100-general-mid.png), E(menta100-source-details.png), E(menta100-source-end.png); E(lavanda-general100-top.png), E(lavanda-general100-mid.png), E(lavanda-general100-source.png), E(lavanda-general100-end.png), E(lavanda-bibliography100-final.png) |
| AM-10 / alto | `plant-passport`: Propiedades sin eficacia y Usos trazables | Particiones con/sin registro elegible; P; Propiedades/Usos Menta; Propiedades/Usos Lavanda, desplazar hasta final | Propiedades sin evaluación; Menta sin usos verificables; Lavanda registro/cita Steinmetz y disclaimer, no dosis/consejo | **PASS** para estas fichas. E(menta100-properties.png), E(menta100-uses.png), E(lavanda100-properties.png), E(lavanda100-uses-top.png), E(lavanda100-uses-1.png)..E(lavanda100-uses-6.png), E(lavanda100-uses-end.png) |
| AM-11 / medio | `plant-passport`: acciones no funcionales; `explore-screen`: footer acotado | Negativos; P; intentar corazón/formulaciones y tabs no disponibles Menta; inspeccionar estados nativos de Menta/P04 | No estado/navegación nuevo; botones etiquetados no disponibles y deshabilitados | **PASS**. E(menta100-disabled-after.png), E(menta100-top.xml), E(explore100-top.xml), comandos. Intentos de activar footer P04 pertenecen al smoke previo, no a esta sesión |
| AM-12 / alto | `explore-screen`: regreso/consulta/filtro/scroll de sesión | Transición de estados; P/P04; query `A`, Plantas, ocultar IME, scroll positivo; abrir Menta y chevron; repetir con `input keyevent 4`; P04→Home por Back/chevron | Ambos retornos P05 conservan query/filtro/posición; ambos retornos P04 llegan Home | **PASS**. E(return100-before.png/xml), E(return100-chevron-after.png/xml), E(return100-android-after.png/xml), E(home100-p04-android-back.png), E(home100-p04-chevron.png); comparación exacta bounds abajo |
| AM-13 / alto | `explore-screen`: Inicio catálogo; `flutter-app-bootstrap`: pila acotada | Transición fin/nueva sesión; P; Inicio desde P04 y P05; reabrir Explorar | Home; nueva sesión Todas/query vacía y lista inicial, sin destino inexistente | **PASS**. E(explore100-home-reset.png), E(explore100-fresh-home.png), E(home200-p05-inicio.png), E(explore200-fresh.png); no inspección interna de pila en manual |
| AM-14 / alto | `explore-screen`/`plant-passport`: texto 100%/200%, safe areas; estructura Home | Valores límite 1.0/2.0; P; recorrer Home completo, P04 cinco filas, búsqueda con/sin IME; Menta tres tabs y General largo; Lavanda Usos primer/final registro y cita | Texto esencial completo y alcanzable mediante scroll; CTA/footer fuera de zonas SO; nombres largos no truncados | **PARCIAL** integral; **PASS en muestras descritas**. E(home200-top/mid/bottom.png), E(explore200-valid-top.png), E(explore200-valid-1/2/3.png), E(explore200-all-bottom.png), E(keyboard200-search-ime.png), E(keyboard200-result-full.png), E(menta200-full-top.png), E(menta200-general-1.png)..E(menta200-general-9.png), E(menta200-source-long-0.png)..E(menta200-source-long-6.png), E(menta200-properties-full.png), E(menta200-uses-full.png), E(lavanda200-uses-disclaimer.png), E(lavanda200-uses-first-cite.png), E(lavanda200-uses-first-cite-end.png), E(lavanda200-uses-end.png). No recorrido completo de otras tres P05/General Lavanda a 200% |
| AM-15 / medio | `explore-screen`/`plant-passport`: etiquetas/estados/targets ≥48 dp | Inspección nativa automatizada, no lector manual; P y 200%; árboles de controles visibles y seleccionados | Botones diferenciados, estado disabled/selected exportado, targets visibles de controles principales ≥144 px a densidad 3 | **PASS en muestra nativa**. E(home100-cold.xml), E(explore100-top.xml), E(menta100-top.xml), E(explore200-valid-top.xml), E(menta200-full-top.xml), E(summary.txt). No afirmar foco/voz TalkBack |
| AM-16 / alto | `explore-screen`/`plant-passport`: recorrido mediante tecnología de asistencia | Exploración asistida; requiere autorización/operador y TalkBack activo; recorrer foco/voz/acciones/scroll a ambas escalas | Lectura y navegación comprensibles y completas | **NO EJECUTADO**: no permiso para activar/cambiar TalkBack ni ejecución humana de voz/foco; semántica no sustituye este caso |
| AM-17 / alto | `plant-catalog`: consulta offline; `flutter-app-bootstrap`: local sin autenticación | Transición online→offline y cold start; P; wifi/data off, esperar no default network/0 agents; Home→búsqueda MENTA/Plantas→Menta Usos→Lavanda Usos; segundo cold y abrir las cinco fichas con Android Back; reconfirmar red antes de restaurar | Todo consultable sin conectividad/login, identidades correctas, referencias locales disponibles | **PASS** offline real. E(offline100-valid-home-cold.png), E(offline100-valid-search.png), E(offline100-valid-menta-uses.png), E(offline100-valid-lavanda-uses.png); E(offline-five-valid-all.png), E(offline-five-valid-{lavanda,eucalipto,romero,manzanilla,menta}.xml), E(offline-five-valid-end-no-network-network.txt) |
| AM-18 / alto | `flutter-app-bootstrap`: no solicitudes remotas de negocio; `home-screen`: no datos usuario | Charter seguridad; P; flujo online/offline, observar permisos/login/overlays y logs app PID; buscar marcador sintético | Sin permisos/autenticación ni consulta sintética en logs; no solicitudes remotas de negocio | **PARCIAL**: síntomas UI/logs ausentes y offline funcional. No captura forense de tráfico/persistencia ni prueba negativa absoluta de red; guard HttpClient anterior se referencia sin atribuirlo a esta ejecución |
| AM-19 / medio | `explore-screen`/`plant-catalog`: error/reintento; `plant-passport`: ID inválido | Particiones negativas error/ID desconocido; requerir inyección/ruta autorizada | Error legible/reintento y no encontrado/regreso seguro | **NO EJECUTADO Android**: no mutar asset/producto ni añadir rutas. Cubierto en suites host previas, no reejecutadas |
| AM-20 / alto | Tarea 4.5: evidencia/entorno/restauración; restricciones del encargo | Comparación antes/después; todas las ejecuciones incluidas abortadas; postflight Home e identidad/settings; hashes | Ajustes exactos restaurados, AVD vivo/Home, fuentes e informes previos intactos, sin comandos QA concurrentes | **PASS**. E(before-manifest.txt), E(after-manifest.txt), E(summary.txt), E(home-final.png), E(postflight-network.txt), E(lavanda-bibliography100-final-settings-after.json), comandos |

**Resumen: 20 casos; 16 PASS, 2 PARCIALES, 2 NO EJECUTADOS; 0 fallos de producto reproducidos.** Los casos manuales complementan el smoke: revisión PNG real, IME y Android Back por keyevent, ajustes reales y offline físico del AVD; no se duplicó la suite host 137/137.

## Hallazgos y evidencia clave

### Visual/identidad y límites de fuente

Se inspeccionaron las capturas PNG mediante lectura visual, no solo existencia/hash, incluidas offline y retornos antes/después. P04 muestra científicos completos y orden esperado: `Lavandula angustifolia`, `Eucalyptus globulus`, `Rosmarinus officinalis`, `Matricaria recutita`, `Mentha x piperita subsp. nothosubsp. piperita`. La asociación normativa FNFNUM 544/401/873/605/619 está en asset/spec y QA host aceptada; el flujo manual acredita los nombres/destinos visibles, no inspección interna de IDs del router.

Menta/Lavanda General: `No disponible en fuente` para origen/descripcion, partes como registros, `No aplicable: ficha de planta`, USDA Dr. Duke, CC0, versión 1/dataset 24660351, archivo 43363335 y fecha de inspección `2026-10-01 (no cobertura temporal)`. URL/cita larga y DOI final `1239279` alcanzables por scroll. Lavanda bibliografía completa termina en `Published by the author, Amsterdam.`. Menta Propiedades declara ausencia de evaluación; Usos vacío verificable. Lavanda Usos muestra registros tradicionales (por ejemplo Carminative y final Perfume), cita Steinmetz, disclaimer `No es una recomendación de uso ni evidencia de eficacia clínica`. No se observó recomendación, dosis ni sustitución de contenido vacío en las fichas revisadas.

Al 200%, Home se desplaza para alcanzar banner/cuatro tarjetas/CTA; chips P04/P05 se redistribuyen, nombres completos y footer P04 en 2×2. Footer Home/P05 conserva cuatro columnas y divide palabras como Favoritos/Historial: **observación estética**, no pérdida de caracteres o clipping reproducible. El nombre largo de Menta y su General completo se recorrieron por tramos hasta final; Lavanda Usos conserva disclaimer/primera cita/final lista y cita. El contenido cortado por el borde de un viewport durante scroll es desplazable; no se confunde con truncado permanente.

### Retorno y limpieza de sesión

AM-12 a font 1.0 estable, query `A`, Plantas e IME cerrado antes de la referencia. Los tres árboles before/chevron-after/android-after coinciden en query/selección y bounds px de **las cinco filas**:

| Fila | Bounds antes y después de ambos retornos |
|---|---|
| Lavanda | `[48,432][1032,636]` |
| Eucalipto | `[48,660][1032,864]` |
| Romero | `[48,888][1032,1092]` |
| Manzanilla | `[48,1116][1032,1320]` |
| Menta | `[48,1344][1032,1608]` |

Las capturas muestran el mismo desplazamiento positivo (cabecera fuera de viewport), no solo retorno en offset cero. Android Back es `adb ... shell input keyevent 4`, **no** framework `handlePopRoute` ni botón físico humano. Si IME está visible, el primer Back lo oculta; el caso formal cerró IME antes del snapshot. No se usaron clamps debidos a cambios de font entre batches para inferir defecto de retorno. Inicio desde P04/P05 retorna Home y al reabrir comienza Todas/query vacía; el smoke previo acredita además pila/controladores internamente.

### Offline real y restauración

- `offline100-valid`: wifi/data `0`, antes de cold launch `Active default network: none`/`Live network agents: 0` (check-4); search MENTA/Plantas, Menta Usos vacío y Lavanda registro/cita, regreso Home.
- `offline-five-valid`: nueva desconexión, check-3 sin default/agents; cold Home y cinco fichas por sus etiquetas nativas; Android Back en cada una. `E(offline-five-valid-end-no-network-network.txt)` reconfirma **none/0** al final. Captura P04 offline revisada visualmente; cinco P05 finales en XML, no afirmar cinco capturas visuales offline inexistentes.
- Settings offline y before/after guardados para ambas pasadas; rollback exacto. Postflight con WIFI/CELLULAR activos/default WIFI, font 1.0/wifi 1/data 1 y captura **Home final**. AVD PID28376 sigue corriendo, ningún flutter run/test/drive o ADB sobre ese serial activo en resumen final. No apagar AVD.

### Logs y semántica nativa

Logcat exclusivamente `--pid=<PID actual> -d -v threadtime`, sin clear/global/otros apps. Cold PID4245: 0 `[Home]`; diez acciones inertes: cada literal esperado una vez; flow100: diez inertes + cinco Explorar = 15 mensajes. PID6298: un CTA al200%; PID6767: tres Explorar; cold offline PIDs9511/11099: 0; flows offline: un Explorar cada uno. Final PID11099 contiene tres Explorar acumulados (offline y dos revisiones Lavanda finales), no duplicaciones por una activación. Los snapshots de log del mismo PID son acumulativos: no sumar archivos como eventos distintos. Marcador `QA_SYNTH_20261003_NO_MATCH` y `[CatalogSmoke]` ausentes de todos los logs app; no errores Flutter de overflow/exception ni fatal/unhandled en las firmas buscadas. Esto no prueba ausencia absoluta de logs perdidos/rotados ni tráfico del SO, persistencia o silencio release/profile.

Árboles nativos: labels distinguibles de regreso/filas/tabs; selected en Todas/Plantas/General/etc.; corazón/formulaciones/footer no disponibles exportan `enabled=false, clickable=false`. Controles principales visibles tienen lados mínimos de 144px/48dp (regreso/corazón/tabs100/CTA100) y footer ≥48dp; no medir como target íntegro las filas parcialmente fuera de viewport. Input exporta hint `Buscar planta o aceite`; UIAutomator puede marcar NAF=true pese al hint. Contenido P05 aparece fusionado en un content-desc grande. Ambas son **observaciones para revisión con TalkBack**, no defectos inferidos de voz/foco. La inspección automatizada de semántica no constituye ejecución manual de TalkBack.

## Defectos y observaciones de ejecución

**Ningún defecto nuevo de producto reproducible encontrado**; por ello no hay severidad/pasos esperado-vs-obtenido de defecto nuevo. El fallo histórico Samsung AS-D01 no se reejecutó: se conserva su informe y estado, sin declararlo corregido ni atribuir causa IME. PASS AVD no lo reemplaza.

Intentos auxiliares fallidos se conservaron y **no** se cuentan como PASS ni como defectos:

- UIAutomator `/dev/tty` inicial no produjo XML en Android16; helper cambió a archivo temporal de QA en `/data/local/tmp/android_manual_tree.xml`, leído y eliminado en cada dump.
- Algunas capturas preliminares `explore200-*` muestran Home y `menta200-top` muestra Eucalipto por coordinación/coordenadas incorrectas. No se usan para acreditar P04/Menta: evidencia válida es `explore200-valid-*`, `explore200-all-bottom`, `menta200-full-top` y secuencias posteriores.
- Primer batch `offline100` detectó red todavía en transición y abortó, restaurando ajustes. Helper espera condición verificable hasta 20s; no PASS offline basado únicamente en toggles. `offline100-valid` completó.
- `offline-all-five` no alcanzó Menta por swipe antes de navegación asentada; restauró. `offline-five-valid` añade árbol de readiness tras abrir P04 y recorrió cinco identidades.
- Sin borrar evidencias ni reintentar para ocultar defectos: cada comando/salida/excepción/restauración y la repetición corregida quedan registrados. Ningún ajuste adicional usado para arreglar comportamiento de producto.

## Integridad y concordancia con QA previa

`E(before-manifest.txt)` y `E(after-manifest.txt)` idénticos: código lib, tests/harness, assets, pin/config/lock/Android, docs e informes/evidencia QA anteriores incluidos en manifiesto no cambiaron. Manifiestos excluyen build/.gradle y nuevos `android-manual`/`android_manual`; no prueban identidad de todo archivo generado o no incluido. Git ya tenía implementación sin commit antes del QA; su estado dirty no es modificación atribuible al agente. Nuevos artefactos únicamente este informe y prefijos autorizados en QA. Sin commits/push.

APK debug real SHA-256: `8f422de770ce334607787ee11464ccc481f3789fc91a78fa0b5fd0b052cfdacb`. Info runtime y build registrados; este hash identifica APK local generado, no una extracción/hash del APK instalado.

Concordancia: `android-emulator-smoke-4.3.md`/log previo **1/1 PASS** ya verificó arranque/acciones/búsqueda/retorno/controladores/pila y guard **0 intentos app HttpClient** dentro de zona Dart. Esta sesión amplía a revisión PNG, cinco P05, Android keyevent, IME200, font/radios reales y offline sin red por cold start. No reejecutó smoke ni host. `global-5.1.md` conserva resultado host **137/137**, format/analyze/pub-lock strict previos y sus advertencias/limitaciones. No reinterpretar estos como resultados nuevos ni hacer verde retrospectivamente Samsung.

## Cobertura residual / decisión

**4.5 tiene evidencia ejecutada; 5.3 queda PARCIAL para decisión del Orchestrator.** No aprobación integral mientras falte TalkBack y se mantengan límites siguientes:

- TalkBack manual voz/foco/gestos/lectura/orden/scroll a100%/200% no ejecutado; semántica puede ocultar problemas de lectura por contenido fusionado o búsqueda. Requiere autorización/operador.
- 200% completo en Home/P04/Menta, muestra Usos Lavanda; no recorrido completo General/Propiedades Lavanda ni las tres fichas restantes a200%. Al100%, cinco headers/destinos y revisión profunda Menta/Lavanda; no contenido completo tres restantes.
- Error asset/reintento/loading transitorio/ID inválido no inducidos Android para no mutar producto ni añadir rutas; suites host previas cubren esos contratos.
- Ausencia de red de negocio/persistencia se sostiene por requisitos/revisión aceptada, síntomas ausentes, offline real y guard previo limitado, no forense de paquetes/sockets nativos/OS ni datos en almacenamiento. No datos sensibles usados.
- Sin binarios release/profile, IDE/hot reload, otros tamaños/densidades/Samsung/dispositivo físico. AVD headless operado por ADB no sustituye interacción humana ni hardware; exactitud del scroll manual usa bounds/capturas, no offset interno.
- No videos/traces Playwright/axe/API; evidencia es PNG/XML/logcat PID/logs de comandos/settings/metadatos de conectividad/manifiestos.

## Reejecución

Sin ejecutar en producción ni otros seriales. Confirmar AVD esperado, detenerse si otra herramienta lo usa; mantener autorización de build/font/radios vigente. No activar TalkBack con estos scripts. Desde raíz del repo, helper verifica identidad antes de cada ADB y rollback; usar nombre nuevo para no sobrescribir evidencia de esta sesión:

```sh
python3 openspec/changes/build-local-plant-catalog/qa/android_manual.py \
  --name rerun100 --actions '[["cold"],["shot","rerun100-home"],["activate","Explorar plantas y aceites"],["shot","rerun100-p04"],["activate","Lavanda, Lavandula angustifolia"],["shot","rerun100-p05"],["back"],["shot","rerun100-return"],["activate","Inicio"]]'

python3 openspec/changes/build-local-plant-catalog/qa/android_manual.py \
  --name rerun200 --font 2.0 --actions '[["cold"],["shot","rerun200-home"],["activate","Explorar plantas y aceites"],["shot","rerun200-p04"],["activate","Inicio"]]'

python3 openspec/changes/build-local-plant-catalog/qa/android_manual.py \
  --name rerun-offline --offline --actions '[["cold"],["shot","rerun-offline-home"],["activate","Explorar plantas y aceites"],["shot","rerun-offline-p04"],["activate","Lavanda, Lavandula angustifolia"],["shot","rerun-offline-p05"],["activate","Usos"],["shot","rerun-offline-uses"],["network","rerun-offline-end"],["activate","Inicio"]]'
```

Para todos los casos, reproducir pasos de la tabla con `--actions` del helper; verbos documentados en `android_manual.py` y secuencia exacta de la ejecución en `E(commands.log)` (`ACTION`/`CMD`). Después de navegación y antes de swipe usar `tree`/`shot` para readiness; coordenadas dependen de viewport/IME/font. Para acento usar IME nativo, no `adb input text` que no admite directamente ese carácter. Revisar cada PNG, no automatizar un PASS por creación del archivo. Finalizar con Inicio y comprobar settings-after/identidad; no dejar comandos propios activos. `android_manual_summary.py` permite repetir comparación/logs/árboles usando evidencia existente, sin operar sobre el AVD; puede sobrescribir únicamente su resumen autorizado.

---

## Addendum 2026-10-03 — cierre visual AM-14 a 200%

**Estado actualizado: AM-14 PASS en el alcance visual acordado; 5.3 sigue PARCIAL por TalkBack manual NO EJECUTADO.** La tabla y conclusiones anteriores conservan la muestra/historia inicial; este addendum sustituye únicamente la limitación visual pendiente de AM-14 y precisa el alcance contractual de AM-18. No se marcan tareas ni se aprueba accesibilidad integral.

### Autorización, método y evidencia

- Continuación solicitada después de revisión de evidencia inicial: solo Lavanda General/Propiedades y Eucalipto/Romero/Manzanilla a200%, con muestreo de Usos por plantilla y contenido largo. No auditoría textual nueva de los 121 registros; cobertura de datos completa permanece en QA host previa.
- Operaciones **15:14:07–15:33:02 UTC**, cinco batches visuales y un postflight. Exclusivamente `emulator-5566`/`boticario_catalog_api36`, identidad antes de cada operación, mismo APK instalado y SDK existente. No rebuild/smoke/host, instalación/dependencia nueva, TalkBack/servicios ni modificación de producto/tests/config/README/checklists.
- Solo `font_scale=2.0` temporal en cada batch visual; rollback exacto a1.0. **No comandos de cambio de radios/global settings** en esta etapa. Los seis pares before/after, incluido postflight, conservan exactamente `font_scale=1.0`, `wifi_on=1`, `mobile_data=1`. Offline previo no repetido.
- Adaptación mínima de `android_manual.py`: `walk` acotado con PNG/XML y parada por dos coincidencias consecutivas de imagen; restauración de radios/settings globales solo cuando se solicita `--offline`. General usa desplazamientos lentos de800px con solapes; Usos usa desplazamiento rápido para localizar el final, seguido de tramos lentos alrededor de citas largas/último registro. Nunca se declara un registro visible por encontrar su texto en el content-desc fusionado de toda la ficha.
- Capturas **reales inspeccionadas visualmente**, completas de pantalla y por tramos con solape. Los duplicados de fondo estable solo acreditan fin de scroll, no un PASS visual automático. Un párrafo mayor que el viewport se valida en varios tramos, sin exigirlo entero en una imagen.
- Prefijo nuevo **E(am14add-...)**, sin sobrescribir PNG/XML/settings/manifiestos/resumen anteriores; comandos añadidos al log append-only. Resumen nuevo: **E(am14add-summary.txt)**; hashes nuevos: **E(am14add-evidence-sha256.txt)**. El hash histórico de informe/helper/log corresponde a su versión anterior, preservado; no implica que sus posteriores adiciones deban tener el mismo hash.

**Nota de publicación:** los logs de depuración locales referenciados en esta QA
se sanearon posteriormente para retirar segmentos de autenticación Dart VM
Service. Los eventos y resultados se conservaron; sus hashes históricos
corresponden a las versiones anteriores al saneamiento. Véase
[`publication-sanitization.md`](publication-sanitization.md) para el inventario
y los hashes actuales.

### Plan adicional y resultados

Precondiciones **P200**: P anterior, Home, font original1.0, app real instalada, sin tooling concurrente; helper activa2.0 y restaura al salir. Los siete subcasos siguientes amplían **AM-14**, no son siete repeticiones de la suite host. Todos trazan `../specs/plant-passport/spec.md` (legibilidad, General/Propiedades/Usos, acciones) y `../specs/plant-catalog/spec.md` (contenido/procedencia); controles/safe areas complementan AM-15.

| ID | Técnica / pasos (P200) | Resultado esperado | Resultado / evidencia visual PNG y XML homónimo |
|---|---|---|---|
| AM14-LV | Límite de fuente y campo largo: abrir Lavanda; General completo hasta fin; reabrir y Propiedades, desplazar | Cabecera/científico/chips completos; todos los campos General, 4 partes y ausencias explícitas, procedencia/URL/cita archivada; bibliografía final alcanzable; Propiedades sin evaluación | **PASS**. E(am14add-lavanda-general-00.png)..E(am14add-lavanda-general-09.png); E(am14add-lavanda-props-top.png), E(am14add-lavanda-props-end.png). Bibliografía termina `Published by the author, Amsterdam.` |
| AM14-EU | Límite de fuente y lista extensa: buscar EUCALIPTO, cerrar IME, abrir fila; recorrer General; reabrir Propiedades | Científico completo; 15 partes como registros, no recomendación/aceite; todos los campos, URL/cita y 8 referencias General alcanzables; Propiedades vacío explícito | **PASS**. E(am14add-eucalipto-general-00.png)..E(am14add-eucalipto-general-16.png); E(am14add-eucalipto-props-top.png), E(am14add-eucalipto-props-end.png). Última bibliografía FontQuer: `Barcelona. 5th Ed.` |
| AM14-RO | Límite de fuente y bibliografía extensa: buscar ROMERO, cerrar IME, abrir; General completo; reabrir Propiedades | Científico completo; 9 partes, ausencias, procedencia/URL/cita y 10 referencias General legibles; último renglón alcanzable; Propiedades sin eficacia | **PASS**. E(am14add-romero-general-00.png)..E(am14add-romero-general-19.png); E(am14add-romero-props-top.png), E(am14add-romero-props-end.png). Bibliografía final Brutus: `Port-Au-Prince, Haiti.` |
| AM14-MA | Equivalencia sin referencias/límite de fuente: buscar MANZANILLA, cerrar IME, abrir; General completo; reabrir Propiedades | Científico completo; 3 partes, ausencias explícitas, procedencia/URL/cita; no bibliografía inventada; Propiedades vacío legible | **PASS**. E(am14add-manzanilla-general-00.png)..E(am14add-manzanilla-general-08.png); E(am14add-manzanilla-props-top.png), E(am14add-manzanilla-props-end.png). Final General DOI `1239279` |
| AM14-UE | Partición con usos / muestreo por longitud: Eucalipto Usos; aviso/primera cita; cita máxima representativa; localizar fin y retroceder por tramos | Aviso no clínico; Antimalaria/Uphof completo; Krochmal completo sin ellipses; último Wound/Leung íntegro y alcanzable | **PASS**. E(am14add-eucalipto-uses-00.png)..E(am14add-eucalipto-uses-03.png); E(am14add-euc-long-06.png), E(am14add-euc-long-07.png) (Boil/Krochmal); E(am14add-euc-endseek-12.png), E(am14add-euc-last-back-01.png), E(am14add-euc-last-back-02.png) |
| AM14-UR | Partición con usos / referencia más larga: Romero Usos; aviso/primera cita; fin y retorno lento hasta Stomachic/Takeda | Ache(Head)/Leung completo; cita máxima Takeda desde `ANON. 1978` hasta `Kyoto, Japan.`; último Vulnerary/Brutus y cita final legibles | **PASS**. E(am14add-romero-uses-00.png)..E(am14add-romero-uses-03.png); E(am14add-romero-last-back-06.png), E(am14add-romero-last-back-05.png), E(am14add-romero-last-back-04.png); E(am14add-romero-endseek-16.png), E(am14add-romero-last-back-01.png), E(am14add-romero-last-back-02.png) |
| AM14-UM | Partición negativa sin usos elegibles: Manzanilla Usos; desplazar hasta texto final | Vacío `No hay usos tradicionales con referencia verificable disponibles`, sin registro/cita ficticios; CTA/footer visibles | **PASS**. E(am14add-manzanilla-uses-top.png), E(am14add-manzanilla-uses-end.png) |

**Resultado adicional: 7/7 subcasos visuales PASS; ningún defecto nuevo reproducible.** General de las cuatro fichas se recorrió completo a200%, no solo cabecera y final. Se leyeron por tramos origen/descripción ausentes, partes registradas, extracción no aplicable, fuente/licencia/versión/dataset, URL de fuente, archivo/ID, fecha de inspección no cobertura temporal y cita recomendada archivada. Bibliografías existentes se recorrieron hasta última línea; Manzanilla no tiene referencias elegibles. P05 continúa siendo ficha de planta aunque algunos nombres de partes fuente contengan `Essential Oil`.

### Cobertura acumulada y controles

| Área a200% | Evidencia acumulada / estado actual |
|---|---|
| Cinco cabeceras y científicos completos | Nuevos `am14add-{lavanda,eucalipto,romero,manzanilla}-general-00` + anterior `menta200-full-top`: **PASS visual** |
| Cinco General y Propiedades | Cuatro secuencias nuevas + Menta anterior `menta200-general-*`/`menta200-source-long-*`, `menta200-properties-full`: **PASS visual**, final de contenidos alcanzable |
| Cinco paths Usos | Vacíos Menta anterior y Manzanilla nuevo; Lavanda anterior aviso/Carminative/Perfume con Steinmetz (primera=máxima=última referencia); Eucalipto/Romero nuevos: **PASS para plantillas/muestras** |
| Primera/máxima/última referencia en tres plantas con usos | Lavanda76 caracteres/Steinmetz; Eucalipto123/Krochmal; Romero169/Takeda, seleccionados desde asset read-only. Primeros/últimos registros de cada una y cita íntegra revisados mediante tramos. **No lectura visual exhaustiva de los 121 registros** |
| Home/P04/fuentes/IME/retornos anteriores | Resultados anteriores conservados; no reejecutados innecesariamente |
| Chips/CTA/footer/targets/safe areas P05 | Nuevos XML y Menta anterior: estados General/Propiedades/Usos seleccionados; corazón/formulaciones/footer inertes disabled. Regreso/corazón144×144px, chips lado mínimo165px, CTA984×222px, footer mínimo270×195px: **≥48dp a densidad3**. Bounds dentro de área y sin invadir insets136/1848px; no modificar safe areas. Detalle en E(am14add-summary.txt) |

Footer a200% conserva todas las letras aunque Favoritos/Historial se dividan en dos líneas; observación estética previa, **no defecto**. Texto temporalmente fuera del viewport reaparece completo al scroll; no se observaron ellipses/pérdida permanente ni solapamiento que impida alcanzar información en los tramos revisados. El content-desc fusionado no acredita voz/foco/gestos.

**AM-18: PASS acotado al contrato de producto**, por revisión de arquitectura aceptada + guard HttpClient previo0 + cold offline real PASS previo + logs PID sin consulta/marcador y ausencia de permisos/login en flujos observados. Esta precisión no cambia los hechos originales ni introduce pruebas de red nuevas: la ausencia de errores/logs por sí sola **no demuestra ausencia de negocio remoto online general**, ni se afirma negativa absoluta sobre SO/sockets/persistencia/logs rotados. Forense absoluta no es criterio añadido ni bloqueo de producto de este encargo. Tabla base actualizada por referencia a este addendum: **18 PASS acotados, AM-16/AM-19 NO EJECUTADOS Android; aprobación integral5.3 aún pendiente**.

### Restauración e integridad

- Postflight **15:33:02 UTC**: E(am14add-home-final.png/xml) muestra Home/Inicio y font original; seis before/after exactos. E(am14add-postflight-network.txt) solo lectura: default WIFI109, 2 agentes WIFI/CELLULAR; radios sin cambios en toda esta etapa.
- E(am14add-before-manifest.txt) = E(am14add-after-manifest.txt): **150 entradas idénticas** de producto/config/assets/docs/QA anterior del alcance del helper; mismo límite de exclusión build/.gradle/artefactos manuales. Informes/evidencia anteriores preservados; informe actual solo recibe addendum y log solo append. Sin commits/push.
- Log final solo PID11099, E(am14add-final-pid-11099.log): sin las firmas buscadas overflow/Flutter exception/fatal/unhandled/marcador sintético/CatalogSmoke. Acumulativo; no sumar como eventos nuevos a snapshots anteriores ni inferir forense absoluta.
- Comprobación read-only posterior de procesos: QEMU **PID28376**, mismo AVD/puerto5566 activo; sin ADB propio/Flutter run/test/drive activos. Ver E(am14add-summary.txt). No apagar AVD ni nueva operación Android necesaria.

### Residuales para decisión del Orchestrator

| Pendiente / límite | Estado y tratamiento |
|---|---|
| AM-16 TalkBack manual100%/200%: voz/foco/orden/gestos/lectura/scroll | **NO EJECUTADO**, usuario ausente/sin permiso para activar servicio. Requiere autorización y operador; sigue impidiendo presentar5.3 como aprobación de accesibilidad integral |
| AM-19 errores asset/reintento/ID inválido Android | **NO EJECUTADO Android**, cobertura host previa conservada; no se muta producto para inducirlos. No defecto/blocker de producto inferido |
| Usos121 registros | Muestreo visual por plantilla/largos/extremos acordado, no nueva auditoría textual exhaustiva; datos completos cubiertos en QA host previa |
| Persistencia/forense absoluta, release/profile, otros dispositivos/densidades | No ejecutados; no son criterios añadidos. Límites históricos se mantienen; Samsung histórico no se vuelve verde |

### Reejecución de esta ampliación (sin radios)

Sin herramientas instaladas. Usar nombres **nuevos** para todos los artefactos; ejemplo desde raíz, misma autorización/identidad y Home como precondición:

```sh
python3 openspec/changes/build-local-plant-catalog/qa/android_manual.py \
  --name rerun-am14-lavanda200-UNIQUE --font 2.0 \
  --actions '[["activate","Explorar plantas y aceites"],["tree","rerun-am14-list-UNIQUE"],["activate","Lavanda, Lavandula angustifolia"],["walk","rerun-am14-general-UNIQUE",25],["activate","Inicio"]]'
```

`walk` con duración850ms sirve a General/tramos con solape; duración100ms opcional solo para localizar el final de listas largas, no acredita lectura de registros omitidos. Reproducir demás subcasos con `ACTION` de batches `am14add-*` del log (búsqueda y cierre IME, Propiedades/Usos, capturas y retornos lentos); no seleccionar texto del content-desc General como prueba de registro visible. Revisar PNG reales, finalizar Inicio, comprobar settings-before/after y no dejar procesos propios. No usar `--offline`/`--build` ni activar TalkBack para repetir este addendum.
