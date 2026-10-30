# QA del cambio compact-passport-uses: resultados

Entorno: rama `passport-uses-glossary` (commits `f279895` y `6d92468`), API local nativa (binario `catalog-api` compilado con `--target-dir` en una carpeta auxiliar, sobre `data/build/catalog.db`) con un token aleatorio solo en el entorno (`<token-app>`), emulador `boticario_catalog_api36` (1080x1920, 420 dpi, Android 36) y APK debug compilado con `--dart-define=API_TOKEN=<token-app>`. No se usó el teléfono físico.

## Resumen

Sin defectos. Cuatro observaciones, ninguna bloqueante. La tarea 5.1 pasa. La 8.1 queda cumplida, con dos matices: la lista del Romero real tiene 20 grupos (los 46 son del fixture de las pruebas) y la semántica `expanded` no se pudo leer en el emulador (ver «No ejecutado»).

## Casos

| ID | Caso | Escenario o requisito | Resultado | Evidencia |
|---|---|---|---|---|
| S1 | Smoke `flutter test integration_test/app_test.dart -d emulator-5554` contra la API local (tarea 5.1) | Controles `Ver N citas`, sin «Registro tradicional», desplegar y plegar | Pasa: `All tests passed!` (+1) en 56 s | `evidence/smoke-output.txt` |
| M1 | Lavanda, `Usos` plegado: aviso fijo al inicio; dos grupos (Carminativo, Estimulante) con la actividad como título, `2 registros · Otros lugares, Turquía` y `Ver 2 citas`; sin citas visibles | Citas plegadas por defecto; Registro tradicional elegible | Pasa | `evidence/review/lav-usos-plegado.png` |
| M2 | Lavanda, desplegar Carminativo: dos citas completas, el control pasa a `Ocultar citas` y no se mueve (mismo borde superior 1104 px antes y después); el otro grupo sigue plegado; volver a pulsar lo pliega | Desplegar y plegar citas | Pasa | `evidence/review/lav-usos-desplegado.png` |
| M3 | Sin «Registro tradicional», `Países` ni la aclaración por grupo: volcado completo de la interfaz de Lavanda, Quimbombó, Abeto común, Cola de caballo y Romero (el texto de todos los grupos está en un solo nodo) | Sin etiqueta ni aclaración por grupo | Pasa (cero apariciones) | volcados `uiautomator` (no se guardan) |
| M4 | Romero (`salvia-rosmarinus`, 20 grupos): `Ver 4 citas`, línea `4 registros · China, Otros lugares, Europa, Turquía` sin truncar; el último grupo (`Uso tradicional, sin eficacia demostrada: cáncer`, `Ver 1 cita`) es alcanzable | Muchos usos | Pasa | `evidence/review/romero-usos-plegado.png`, `romero-final.png` |
| M5 | Romero, Carminativo desplegado: tres citas resueltas en tinta normal y `Woi.Syria (sin resolver)` en gris y cursiva | Cita sin resolver visible | Pasa | `evidence/review/romero-carminativo-desplegado.png`, `romero-sin-resolver.png` |
| M6 | Romero, grupo en medio de la lista (Dispepsia): al desplegar, el control queda en [48,407][404,551] igual que antes, los grupos de arriba no se mueven y los de abajo bajan 216 px; al plegar vuelve exactamente a las posiciones anteriores | Muchos usos: se conserva la posición de desplazamiento | Pasa | `evidence/review/romero-medio-desplegado.png` |
| M7 | Grupo con una sola cita (Lepechinia chilensis, `Uso tradicional, sin eficacia demostrada: tumor de miembro`; Romero, último grupo): `Ver 1 cita`, al pulsar muestra esa cita y pasa a `Ocultar citas de <actividad>` | Grupo con una sola cita | Pasa | `evidence/exploratory/lepechinia-1cita-plegado.png`, `lepechinia-1cita-desplegado.png` |
| M8 | Grupo sin países (Abeto común, Expectorante y Rubefaciente): la línea dice solo `1 registro`, sin separador ni texto sustituto; «Otros lugares» se muestra tal cual en Lavanda y Romero | Grupo sin países; Países tal como llegan | Pasa | volcado de la interfaz (no se guarda) |
| M9 | Dos grupos con la misma actividad (Cola de caballo, `equisetum-arvense`, Hemostático en las posiciones 6 y 19, con 2 y 1 citas): con el 6 desplegado el 19 está plegado; al desplegar el 19 los dos están abiertos; al plegar el 6 el 19 sigue abierto | La clave del grupo incluye la posición (D3) | Pasa | `evidence/exploratory/equisetum-hemostatico-19.png` |
| M10 | Estado al cambiar de pestaña: Lavanda con Carminativo desplegado, `General` y de nuevo `Usos`: Carminativo sigue desplegado y Estimulante plegado | Estado de plegado al cambiar de pestaña | Pasa | (sin captura; volcado de la interfaz) |
| M11 | Reinicio: salir al listado y reabrir la Lavanda (con Carminativo desplegado antes): los dos grupos están plegados | Todos plegados al abrir un pasaporte | Pasa | (sin captura; volcado de la interfaz) |
| M12 | Planta sin usos (Abeto de Sajalín, `abies-sachalinensis`): aviso fijo y «No hay usos tradicionales con referencia verificable disponibles», sin controles | Sin registro elegible | Pasa | `evidence/exploratory/sin-usos.png` |
| M13 | Texto al 200 % (`font_scale` 2.0, Cola de caballo): actividad larga en dos líneas, línea de datos, `Ver 1 cita` y `Ocultar citas` sin truncar ni desbordes; las citas largas se parten en varias líneas; el control mide 144 px de alto (48 dp a 3 px/dp cumple de sobra) y se pulsó con éxito; el último grupo (`Vejiga`) y su control son alcanzables | Accesibilidad con texto aumentado; Muchos usos | Pasa | `evidence/review/usos-200-plegado.png`, `usos-200-desplegado.png` |
| M14 | Semántica: en el árbol de `uiautomator` el control es `android.widget.Button`, clicable, con etiqueta `Ver 2 citas de Carminativo` plegado y `Ocultar citas de Carminativo` desplegado (el texto visible va primero y sigue la actividad) | Control de citas accesible | Pasa en botón y etiqueta; `expanded` no observable (ver «No ejecutado») | volcados `uiautomator` (no se guardan) |
| M15 | `flutter test test/features/passport/` (incluye la prueba de accesibilidad 4.1 con `SemanticsController`, `expanded` falso y verdadero y las guías de 48 dp a 100 % y 200 %) | Control de citas accesible | Pasa: 197 pruebas | salida en consola |

## Defectos

Ninguno.

## Observaciones

- En la base real, el máximo de grupos por planta es 20 (el Romero tiene 20 grupos y 33 usos); los 46 grupos y 59 usos de las tareas son datos de las pruebas. El caso «muchos grupos» se probó con los 20 reales.
- La línea de datos dice `1 registro` en singular. La spec solo ejemplifica `N registros` con N mayor que uno; es el comportamiento natural y no contradice nada.
- Hay actividades sin traducir en los datos (por ejemplo `Gravel`, `Internulcer` y `Tubercle` en el Abeto común), que la app muestra tal como llegan. Es de datos, no de este cambio, y coincide con la carpeta `activity-glossary` que está en curso.
- El grupo muestra `2 registros` pero `Ver 1 cita` en varios casos (por ejemplo el último del Romero): los registros y las referencias son cosas distintas. El usuario podría confundirse, pero es el diseño elegido.
- A 200 % el icono del control no escala con el texto (queda pequeño junto a «Ver 1 cita»); la función no se ve afectada porque el texto cambia entre «Ver» y «Ocultar».
- El botón fijo «Ver formulaciones relacionadas» y la barra inferior (2x2 a 200 %) ocupan buena parte de la pantalla y tapan contenido hasta que se desplaza; es el diseño existente, ya anotado en el QA de `passport-sources-tab`.
- El smoke comprueba que la actividad, la línea y el control aparecen al desplegar con una cuenta de al menos cuatro `Text` en el grupo, una comprobación débil pero suficiente con las otras pruebas.

## No ejecutado

- La semántica `expanded` en el dispositivo: `uiautomator` no expone ese estado y TalkBack no registra el texto que pronuncia (se activó y se desactivó, `enabled_accessibility_services` y `accessibility_enabled` quedaron como al inicio). Está cubierta por la prueba de accesibilidad de widget (M15).
- El reinicio al cambiar de planta dentro de la misma página (`didUpdateWidget` con otro `plant.id`): no hay camino en la interfaz que cambie de planta sin salir del pasaporte. Se probó salir y reabrir (M11); lo demás lo cubren las pruebas de widget de la tarea 3.2.
- Citas «sin resolver» en la Lavanda: la Lavanda real no tiene ninguna, así que el caso se probó con el Romero (M5).

## Capturas para el usuario (en `evidence/review/`)

- `lav-usos-plegado.png`: `Usos` de la lavanda plegado.
- `lav-usos-desplegado.png`: `Usos` de la lavanda con Carminativo desplegado.
- `romero-usos-plegado.png` y `romero-final.png`: el Romero, primeros y últimos grupos.
- `romero-sin-resolver.png`: cita «(sin resolver)» en gris y cursiva.
- `usos-200-plegado.png` y `usos-200-desplegado.png`: `Usos` al 200 %.

## Cómo repetir

Con `API_TOKENS=$(openssl rand -hex 32)` en el entorno, compilar la API con `cargo build --release --manifest-path backend/Cargo.toml -p catalog-api --target-dir <carpeta-auxiliar>` y arrancarla sobre `data/build/catalog.db`; con el emulador en marcha, `flutter test integration_test/app_test.dart -d emulator-5554 --dart-define=API_TOKEN=<token-app>` desde `app/` (para el recorrido a mano, `flutter build apk --debug --dart-define=API_TOKEN=<token-app>` e instalar con `adb`). No se instaló ninguna herramienta ni se añadieron dependencias. Las plantas con la misma actividad en dos grupos salen de `select plant_id, activity, count(*) from plant_use_group where pending_review=0 group by plant_id, activity having count(*)>1` (17 plantas).

## Limpieza

API detenida, app desinstalada, `font_scale` en 1.0, emulador apagado, daemon de Gradle detenido (`./gradlew --stop`) y `app-debug.apk` con su `.sha1` borrados de `app/build/app/outputs/flutter-apk/`. El build y el smoke funcionaron dentro del sandbox, sin el fallo de «starting process» de Gradle. No se guardaron logcat.
