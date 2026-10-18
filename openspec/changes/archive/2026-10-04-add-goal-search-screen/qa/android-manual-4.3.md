# QA nativa Android P06 — 4.3

**2026-10-04, 15:15–15:21 UTC. Resultado: 10 casos PASS, 0 FAIL; sin defectos
reproducidos en este alcance.** No implica aprobación de TalkBack, offline
físico, release/profile ni otros dispositivos.

## Contexto y entorno

Requerimiento original: tras recopilar contexto sin implementar, el usuario
confirmó «solo se muestren las diferentes opciones del mockup pero sin
funcionalidad todavía», aprobó el cambio OpenSpec y luego su implementación.
Se verifica la presentación P06, entrada desde Inicio y retornos mínimos; no
P07, búsqueda, selección, recomendaciones ni servicios. Fuente normativa:
`../specs/{goal-search-screen,home-screen,flutter-app-bootstrap}/spec.md`.
Mockup P06 de `docs/mockups.png` leído como referencia estructural provisional,
no pixel-perfect. Proposal/design/tasks/config/README e informes host/4.2 leídos
antes de operar. Code review aprobado por el orquestador; host 144/144 y smoke
Android 1/1 son evidencia previa separada, no resultados manuales inferidos.

Autorización explícita: «Sí, solo ese AVD» para instalar/revisar 100%/200% y
restaurar texto, sin Samsung, otros emuladores ni TalkBack. El AVD ya estaba
arrancado por la autorización adicional del paso 4.2; aquí no se arrancó/paró.

- Único serial: **emulator-5566**, nombre **boticario_catalog_api36**, API **36**,
  state `device`, boot `1`, reconfirmados antes de cada lote ADB.
- Panel real **1080×1920 px, 480 dpi**, densidad 3: **360×640 dp nominales**,
  antes de insets. Área segura observada: y=136…1848 px. No se cambió densidad,
  tamaño de panel, navegación del sistema, SDK, licencias ni imagen del AVD.
- Flutter debug **normal**, target `lib/main.dart`; no entrypoint de integración,
  inyección de router/deep links ni VM interactiva. Aplicación
  `com.example.boticario_ai/.MainActivity`, según manifest existente.
- Sin web, API de negocio, login o credenciales: Playwright/Postman/axe web no
  aplican. Se usaron ADB, UIAutomator, capturas y Python existentes; **ninguna
  herramienta/dependencia instalada**.

## APK normal

Desde `app/`:

```sh
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter build apk --debug --target lib/main.dart
```

Build **exit 0**; instalación `adb -s emulator-5566 install -r …` **Success**;
arranque normal con `am force-stop` y `am start -n` del único paquete autorizado.
APK: `app/build/app/outputs/flutter-apk/app-debug.apk`, **190.060.332 bytes**,
SHA-256 `c2529d18f57837a235bea21c4b850db7e6e90002a1120dda35d80d0775019b15`.
Es distinto del APK de integración 4.2 (`8bddf79…`, 116.878.968 bytes).
Salida completa sanitizada: [`evidence/manual-P06-build-normal.log`](evidence/manual-P06-build-normal.log).
Warnings Gradle de acceso nativo restringido y cuatro paquetes con versiones
nuevas incompatibles conservados; no se alteró entorno para ocultarlos.

## Plan, trazabilidad y resultados

Precondición común: autorización vigente, identidad anterior confirmada, APK
normal instalado, inicio en Home, font_scale `1.0`, sin cambios de radios ni
accesibilidad. Cada nombre de evidencia de la tabla tiene **PNG y XML** dentro
de `evidence/`; son capturas Android reales, no widgets simulados ni traces web.
G=`specs/goal-search-screen`, H=`specs/home-screen`, B=`specs/flutter-app-bootstrap`
del cambio actual.

| ID / prioridad | Requisito y técnica | Pasos / esperado | Resultado real / evidencia |
|---|---|---|---|
| M00 / alta | B: arranque; precondiciones e integridad | Confirmar identidad/boot/ajustes, compilar/instalar entrypoint normal y arrancar en frío. Esperado Home sin login; fuentes y ajustes finales idénticos. | **PASS**. Home normal, build/install exitosos, 58/58 archivos sin cambios; `manual-P06-100-home`, `manual-P06-settings-integrity.json`, build log. |
| M01 / alta | G: presentación y ausencia de producto; H: entrada; equivalencia/charter visual | Home→Buscar por objetivo. Comparar título/subtítulo, seis filas en orden con mockup, iconos/chevrons locales y ausencia de buscador/selección/resultados/P07/dosis/recomendaciones. Esperado contenido exacto, sin extras de producto. | **PASS**. `manual-P06-100-top`: ¿Qué deseas lograr? / Selecciona un objetivo principal / Relajación / Estrés / Mejorar el sueño / Cuidado de la piel / Alivio respiratorio / Concentración / Otros objetivos. |
| M02 / alta | G: filas sin acción; partición exhaustiva de seis objetivos, negativo | Tocar por coordenadas de cada etiqueta nativa las **seis** filas; tras cada tap volcar árbol. Esperado misma UI, ninguna selección/nav/overlay/log de datos. | **PASS**, 6/6 árboles byte-idénticos al inicial; **0 líneas nuevas** en logcat limitado al PID durante esos taps y M03. `manual-P06-100-after-inert-taps`, JSON de integridad. No demuestra auditoría de persistencia/red interna. |
| M03 / alta | G: barra inferior; tabla de decisión activo/inactivos | Tocar Favoritos, Historial y Perfil en P06. Esperado nada cambia, Inicio sigue seleccionado. | **PASS**, 3/3 árboles idénticos; etiquetas nativas «… no disponible», enabled=false/clickable=false; Inicio selected=true. `manual-P06-100-after-inert-taps`. |
| M04 / alta | G/B: Atrás app; transición de estados | P06→flecha «Volver a Inicio». Esperado Home sin pantalla adicional. | **PASS**, marca/card Home visibles. `manual-P06-back-app-home`. |
| M05 / alta | G/B: Atrás sistema; transición real Android | Nueva visita P06→`input keyevent KEYCODE_BACK`. Esperado Home. | **PASS**. `manual-P06-back-android-home`. Es pulsación Android, no `handlePopRoute` del smoke. |
| M06 / alta | G/B: Inicio y limpieza de pila; transición/negativo | Nueva visita P06→Inicio footer→Back Android. Esperado Home primero; después salir al launcher, **no volver a P06**. Reabrir MainActivity. | **PASS**, Home→launcher→Home normal. `manual-P06-footer-home`, `manual-P06-cleared-stack-launcher`. |
| M07 / alta | G: 360×640, escalas y scroll; valores límite 1.0/2.0 y charter de lectura | Leer top/bottom al 100%; poner font_scale 2.0, leer top/intermedio/bottom con swipes reales; restaurar en finally. Esperado cada título/subtítulo/fila/footer completo y alcanzable sin elipsis/corte horizontal. | **PASS**. `manual-P06-100-{top,bottom}` y `manual-P06-200-{top,middle,bottom}`. Al 200% título/subtítulo/primera fila envuelven; footer cambia a 2 columnas, cuatro etiquetas completas. Todos los seis objetivos leídos completos entre capturas. |
| M08 / alta | G: zonas seguras, targets y semántica nativa; límites geométricos/negativo | Medir bounds UIAutomator de Atrás/Inicio con controles completos al top en ambas escalas; inspeccionar filas y decoración. Esperado ≥48×48 dp, etiquetas distinguibles, contenido sin botón/selected/tap, sin duplicados decorativos. | **PASS en inspección nativa limitada**, medidas abajo. Filas una vez en árbol 100%, clickable=false/selected=false (enabled=true como contenido); iconos/chevrons sin etiquetas extra. **No PASS TalkBack**. PNG/XML top y JSON. |
| M09 / media | B: recorrido existente; charter de regresión ligera | Tras P06, Home→Explorar→Lavanda→Back Android→Explorar→Inicio. Esperado recorrido existente y retorno seguro. | **PASS**. `manual-P06-regression-{explore,passport}`, `manual-P06-final-home`. No repite búsqueda/filtros/121 usos cubiertos previamente. |

Son casos manuales agrupados, no diez tests automatizados independientes.
Los checks de taps/árboles son asistencia CLI a la exploración de UI nativa.
Los cuatro ingresos a P06 produjeron **4 mensajes exactos**, uno por ingreso,
`[Home] Buscar por objetivo`; hubo un mensaje `[Home] Explorar plantas y aceites`
en M09. Sin mensajes de producto por filas ni por render observados.

### Medidas reales y comportamiento del scroll

Se midieron controles funcionales **completamente visibles al top**, con densidad
3, no se dedujeron áreas táctiles del dibujo del icono:

| Escala | Control | Bounds px | Área dp |
|---|---|---|---|
| 100% | Volver a Inicio | `[12,148][156,292]` | **48×48** |
| 100% | Inicio | `[0,1680][270,1848]` | **90×56** |
| 200% | Volver a Inicio | `[12,208][156,352]` | **48×48** |
| 200% | Inicio | `[0,1440][540,1644]` | **180×68** |

Footer permanece fuera de la barra Android, que comienza tras y=1848; Atrás
completo queda bajo el inset superior y=136. La cabecera pertenece al cuerpo
desplazable, **no es sticky**: al bajar se desplaza/recorta en el borde del
viewport (visible en `100-bottom` y ausente en `200-middle/bottom`). No se
afirma que el target Atrás parcialmente desplazado mida 48 dp visibles ni que
todo texto esté simultáneamente en pantalla. El contenido completo está
disponible al top o por scroll; las capturas verifican esa alcanzabilidad, sin
elipsis ni recorte horizontal permanente. Inicio queda accesible al fondo.

## Evidencia, logs y estado final

- **14 PNG y 14 XML** `evidence/manual-P06-*.{png,xml}`; sin video/trace.
- [`manual-P06-app.log`](evidence/manual-P06-app.log): logcat limitado al PID
  de la app, máximo 180 líneas (87 obtenidas), no dump general del sistema.
  **1 URL con token Dart VM-service reemplazada** antes de guardar. Raw solo
  temporal privado autorizado, no versionado.
- Cero `E/flutter`, `Unhandled Exception`, `EXCEPTION CAUGHT`, `RenderFlex` o
  `FATAL EXCEPTION` en el log acotado. Sí hay warnings nativos de EGL/ashmem,
  parser de fuentes y 57 frames omitidos en arranque debug del emulador; sin
  fallo funcional reproducido. No se presenta benchmark de rendimiento.
- [`manual-P06-settings-integrity.json`](evidence/manual-P06-settings-integrity.json):
  manifests completos antes/después y bounds, APK, ajustes, taps sin cambios.
- Capturas privadas/logs raw primero en
  `/private/var/folders/1x/gxw5xrxs1x12swr4t_4wwmf00000gn/T/opencode/goal-search-4.3/`.
  Ningún secreto/credencial de prueba en artefactos.

Font `1.0`→`2.0`→**`1.0`**, restaurado mediante **try/finally** y releído.
Baseline/final idénticos: wifi **1**, mobile data **1**, airplane **0**,
accessibility **0**, touch exploration **0**. No se modificó ninguno de esos
cinco ajustes. Código de restauración contempla baseline ausente (`null`)
con `settings delete`, aunque aquí era `1.0`.

AVD **PID 2863** sigue activo; app normal **PID 4624**, Home abierta con tamaño
original, comprobado a **15:21:19 UTC**. **58 archivos de app tracked/untracked
no ignorados: idénticos**, incluido `pubspec.yaml` y `pubspec.lock`. Diff binario
de app idéntico SHA-256
`573b465dfdd1e7d98519575e029c637a39c98f333614491437636cc9b080e680`.
No se editaron producto/tests, README/tasks, evidencia histórica, setup log,
configuración del proyecto/SDK/AVD ni se hizo stage/commit/push.

## Defectos y cobertura residual

**Ningún defecto reproducible en el alcance ejecutado.** No se corrigió producto
ni se modificaron assertions. El scroll normal descrito arriba no se oculta ni
se confunde con una cabecera fija.

| Cobertura no realizada | Estado / motivo / riesgo residual |
|---|---|
| TalkBack: voz, foco, orden anunciado, gestos | **NOT RUN**, prohibido por autorización. XML no verifica experiencia de lector; unit/widget de semántica previos no sustituyen voz Android. |
| Offline físico y observación de red/persistencia interna | **NOT RUN**, sin autorización para cambiar radios. El smoke previo tiene guard HttpClient, no prueba de desconexión física; aquí solo se verificaron UI/logs observables. |
| Binarios profile/release | **NOT RUN**, solo debug autorizado. Navegación/silencio de esos binarios siguen sin prueba real. |
| Otros dispositivos/insets/notches, Samsung y otros AVD | **NOT RUN**, alcance exclusivo. Insets reales de este panel sí revisados; no notch adicional sintético. |
| Catálogo exhaustivo y lectura clínica/121 usos | **NOT RUN** en esta tarea; regresión ligera M09 y automatizadas previas separadas. No se hacen afirmaciones médicas. |

## Reejecución

Requiere nueva confirmación de autorización y AVD existente/encendido; si está
ausente/offline, **STOP sin fallback**. Desde repo, helper reutilizable
[`native_manual_4_3.py`](native_manual_4_3.py) con `QA_PRIVATE_TEMP` apuntando a
un temporal privado aprobado y `PYTHONDONTWRITEBYTECODE=1`. `guard()` valida
serial/nombre/API/boot; `settings()` registra baseline; guardar baseline.json
antes de cualquier cambio (incluido font original exacto) y `manifest()`.
Compilar target normal con el comando anterior, instalar/arrancar solo el
paquete autorizado; ejecutar los pasos M00–M09, `capture()` a **nuevos nombres**
sin sobrescribir esta evidencia. `tap()` usa etiquetas exactas del árbol,
`scroll_up()` swipe real y `adb('shell','input','keyevent','KEYCODE_BACK')`
retorno Android. Para M07, envolver cambio 2.0/lectura en
`try: … finally: restore_font()`; volver a Home, comparar ajustes y hashes.
Sanitizar log mediante `redact()` antes de guardarlo. El helper no ejecuta toda
la revisión visual automáticamente: leer las PNG y registrar resultados es
necesario. No instalar herramientas, cambiar radios/TalkBack, SDK, licencias
ni modificar fuentes para reejecutar.
