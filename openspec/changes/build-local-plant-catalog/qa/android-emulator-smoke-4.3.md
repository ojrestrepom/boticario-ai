# QA smoke Android en AVD — 4.3 / evidencia 5.2

Fecha: 2026-10-03 UTC. Estado: **PASS — smoke Android AVD 1/1, exit 0**. Corrección del harness revisada y aprobada por el orquestador; build/instalación/test autorizados únicamente en AVD dedicado. Sin cambios de código, README, checklist, commits ni push. Resultado limitado a esta ejecución automatizada; no es aprobación de QA manual 4.5/5.3.

## Precondiciones y entorno

- Serial exclusivo `emulator-5566`, AVD `boticario_catalog_api36`, QEMU PID 28376 con `-port 5566`, headless, SwiftShader y aceleración CPU Hypervisor.Framework preparada previamente.
- Identidad reconfirmada antes de cada operación ADB de estado; no ejecución Flutter test/run/drive ni operación ADB concurrente observada en preflight de 14:19:21 UTC. No se toca Samsung ni otros seriales.
- Android 16/API 36, arm64-v8a, Google APIs revisión 7 sin Play Store. Panel 1080×1920 px/480 dpi = 360×640 dp nominales **antes de insets**. No se cambia resolución, font scale, radios ni TalkBack.
- Flutter 3.47.6 stable/Dart 3.13.5; SDK platform 36, build-tools 36.0.0 y NDK 28.2.13676358 existentes. Doctor Android ✓ en preparación aceptada; no aceptación de licencias, hash preexistente `c43fa37686457c3f18caa3607945f4ec52a9d1beaaad8117e50dc4e863270c85` confirmado.
- Fuentes leídas completas: README/pin/config, cinco specs delta, diseño/tareas, setup del AVD y log completo incluida corrección de aislamiento, investigación del scroll, harness corregido, informe/log Samsung y verificación host 5.1. El incidente ajeno pertenece al setup previo; no se repiten sus operaciones.
- App real `main` con ProviderScope/router/tema y bundle JSON local, sin fakes, URL ni credenciales; datos sintéticos. Android no activa la simulación host de insets.
- Preflight: `evidence/android-emulator-smoke-preflight.log`; manifest SHA-256 antes/después: `evidence/android-emulator-smoke-source-manifest.log`.

## Plan de prueba priorizado

Precondiciones comunes: entorno anterior, revisión aprobada y app de prueba instalable sin licencia/firma/desinstalación requerida. Las capabilities remiten a `../specs/<capability>/spec.md`. AS-01..09 son checkpoints de **un test Android**, no nueve tests independientes.

| ID/riesgo | Capability y requisito | Técnica / pasos | Esperado | Resultado |
|---|---|---|---|---|
| AS-01/alto | flutter-app-bootstrap: arranque y recorrido acotado | Transición inicial: iniciar app; observar `/`, marca/banner, ausencia demo y logs iniciales | Home real, Inicio seleccionado, 0 logs por build; sin autenticación en el flujo | Pasa |
| AS-02/alto | home-screen: 11 acciones/logs y barra inmóvil | Tabla de decisión: diez acciones inertes, Explorar y sus reactivaciones posteriores | Diez no cambian ruta/selección ni overlays; solo Explorar navega; 1 literal exacto por activación, secuencia final 14 logs/11 distintos | Pasa |
| AS-03/alto | explore-screen: composición; plant-catalog: identidad fija | Partición válida: Todas inicial, desplazar para alcanzar cada una de las cinco filas | Lavanda/Eucalipto/Romero/Manzanilla/Menta con científicos fuente exactos | Pasa |
| AS-04/alto | explore-screen: búsqueda, filtros y estados vacíos | Particiones: científico `  LAVÁNDULA   ANGUSTIFOLIA `, común `MENTA`, no-match sintético, Aceites/borrar, Plantas + `A` | Normalización y ambos nombres; no-match distinto de Aceites; borrar conserva filtro; consulta combinada | Pasa |
| AS-05/alto | plant-passport: identidad, General/Propiedades/Usos | Particiones con/sin usos: abrir Menta 619, recorrer tabs; abrir Lavanda 544/Usos | General inicial, campos ausentes/no aceite; propiedades sin evaluar; Menta vacío; Lavanda Carminative con cita Steinmetz y disclaimer | Pasa |
| AS-06/alto | explore-screen: retorno y estado de sesión | Transición: cerrar IME por canal real, exigir inset 0, capturar P04 antes del tap; Menta→chevron y segunda apertura→handlePopRoute; P04 final→handlePopRoute | Consulta `A`/Plantas, controladores idénticos y offset/inset/viewport/maxExtent exactos en ambos retornos; P04 pop vuelve a Home | Pasa; métricas abajo |
| AS-07/alto | explore-screen: Inicio catálogo; flutter-app-bootstrap: navegación acotada | Transición de sesión: Inicio real desde P04/P05; reabrir tras limpieza | Home `/`, no pila poppable; nueva P04 con Todas, query vacía y offset 0 | Pasa |
| AS-08/medio | explore-screen: footer; plant-passport: acciones no disponibles | Negativos/semántica: tocar footer P04 y corazón/formulaciones/footer P05 Menta | Deshabilitados, sin acción semántica tap, sin navegación/mutación/logs nuevos P05 | Pasa |
| AS-09/alto | plant-catalog: local; flutter-app-bootstrap: sin servicios | Flujo con HttpOverrides.runZoned denegando creación de HttpClient; assertion final | **0 intentos app HttpClient**, no prueba offline físico ni tráfico nativo | Pasa, assertion final alcanzada |

## Reejecución y evidencia

Antes de cualquier operación sobre el AVD, confirmar identidad y ausencia de QA concurrente:

```sh
"$HOME/Library/Android/sdk/platform-tools/adb" -s emulator-5566 emu avd name
# Debe devolver boticario_catalog_api36. No seleccionar otro serial.
```

Desde `app/`:

```sh
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test integration_test/app_test.dart -d emulator-5566
```

Salida stdout/stderr UTF-8 completa con fechas, comando y exit code: `evidence/android-emulator-smoke-run.log`. Sin reintentos arbitrarios; al terminar se deja AVD corriendo para la futura QA manual.

Referencias del harness revisado: entrada Android `app_test.dart:13–16`; cierre IME real y límite de 60 frames `catalog_smoke.dart:569–586`; captura P04 antes de chevron/framework Back `:197–204` y `:264–269`; comparación de identidad/inset/viewport/extensión/offset `:396–424`; secuencia Home literal y assertion 0 HttpClient `:339–361`. En Android se exige igualdad exacta, no clamp/tolerancia ni insets sintéticos.

## Resultado ejecutado y evidencia

- Inicio **14:21:26.310107 UTC**; fin **14:21:58.624594 UTC**. Wall **32.314 s**; runner **00:21**, **1 pasada / 0 fallidas**, `All tests passed!`, exit **0**. setUpAll/tearDownAll no cuentan como pruebas adicionales.
- Gradle `assembleDebug` **8.0 s**; APK debug generado en `app/build/app/outputs/flutter-apk/app-debug.apk`; instalación AVD **290 ms**. App real arrancó y completó el flujo, no solo terminó el proceso.
- Una ejecución, sin reintentos ni regresión host nueva. Último punto: framework pop desde P04 final a Home `/` sin pila; secuencia literal de **14 logs Home** (diez acciones inertes y cuatro Explorar, 11 mensajes distintos) y **0 intentos de crear HttpClient** bajo guard app comprobados al final.
- AS-01..09 pasan según las assertions secuenciales del único test, sustentadas por `evidence/android-emulator-smoke-run.log` íntegro. Sin screenshots, videos ni logcat global; no se atribuye observación visual manual.
- **7 snapshots** registrados por el harness: todos con query sintética `A`, inset `0.0`, viewport `514.6666666666666`, maxExtent/offset `117.33333333333337`, scrollController `406561890`, queryController `87496682`. Las métricas corresponden al scroll de P04, incluso en snapshots con stage P05; no describen el viewport de su pasaporte.

### AS-06: comparación exacta de retornos (dp)

| Retorno / snapshots P04 antes→después | Offset | Inset inferior | Viewport | Max extent | Identidad scroll/query |
|---|---|---|---|---|---|
| Chevron: `P04.before-tap.stable-viewport` → primer `P04.after-return.stable-viewport` | 117.33333333333337 → 117.33333333333337 | 0.0 → 0.0 | 514.6666666666666 → 514.6666666666666 | 117.33333333333337 → 117.33333333333337 | 406561890/87496682 → mismos; `identical` true |
| Framework Back: `P04.before-framework-tap.stable-viewport` → segundo `P04.after-return.stable-viewport` | 117.33333333333337 → 117.33333333333337 | 0.0 → 0.0 | 514.6666666666666 → 514.6666666666666 | 117.33333333333337 → 117.33333333333337 | 406561890/87496682 → mismos; `identical` true |

Ambos restauran query `A`, filtro Plantas y ruta `/explore`. Extensión positiva y offset positivo: se ejercitó restauración no trivial, no únicamente `0→0`. No es pulsación física de Android Back.

### Integridad y estado de entrega

- `evidence/android-emulator-smoke-source-manifest.log` confirma hashes sin cambios de pin, pubspec/lock, harness, código lib, bundle y config Android. Base HEAD `a97472b77cfc63cbba3f93d1bfde9cd6e16e447d` no representa el SHA de implementación aún no committeada; harness probado SHA-256 `475fdabfe771845458dff1e2e115c4078c64bd673c869cd3a2074257796a3360`.
- Informe y log Samsung originales también conservan hashes **UNCHANGED**. AS-D01 no se reproduce en este AVD/viewport estable; no confirma retrospectivamente IME como causa en Samsung, ni reemplaza su FALLÓ.
- Licencia conserva hash original. No instalaciones nuevas de SDK/herramientas, aceptación de licencias, clear data, uninstall ni cambios de ajustes por QA. Descargas/resolución normal de dependencias no modificaron lockfile.
- Postflight **14:22:31 UTC**, `evidence/android-emulator-smoke-postflight.log`: nombre AVD correcto, serial en estado device, boot_completed=1 y PID 28376 todavía corriendo en puerto 5566. Se deja AVD activo para otro agente; no nuevas operaciones tras entrega.

## Defectos y observaciones

**Sin defectos nuevos encontrados en esta pasada automatizada.** El fallo histórico Samsung AS-D01 se conserva con su severidad/media y causa no confirmada; no se declara resuelto en aquel dispositivo.

Observaciones no bloqueantes de toolchain (salida conservada, no fallos de producto): warning Java de acceso nativo restringido; warning SDK XML lector versión 3 frente a archivo versión 4; cuatro paquetes tienen versiones más nuevas fuera de restricciones. Build y test terminaron correctamente; no se actualizaron herramientas ni dependencias para silenciarlos.

**Decisión QA:** evidencia PASS Android AVD para revisión del Orchestrator de 4.3/5.2. No se marcan esas tareas ni se avanza a QA manual 4.5/5.3; permanecen límites/residuos siguientes.

## Cobertura residual / límites

- No se prueba Back físico/keyevent, TalkBack, font scale/200%, radios desconectados, QA visual integral, IDE/hot reload ni binarios release/profile. Semántica no sustituye tecnología de asistencia manual. No afirmar ni marcar 4.5/5.3.
- P05 se abre para Menta/Lavanda; las otras tres identidades son filas P04. Errores de asset/reintento/IDs inválidos quedan en suites host existentes, sin inyección ni mutación en Android.
- Guard cubre creación de clientes `dart:io` de app dentro de su zona, no sockets alternativos/tráfico nativo/radios. Precarga del asset anterior al guard. Host no usa guard.
- Métricas `[CatalogSmoke metrics]` y query sintética `A` son instrumentación exclusiva del harness, no logging de datos de usuario por producto.
- La prueba host de clamp IME no demuestra causa Samsung. El informe Samsung `android-smoke-4.3.md` y su log quedan intactos/FALLÓ; un PASS AVD no los vuelve verdes ni confirma retrospectivamente su causa.
- Host reciente 5.1: 137/137, formato/análisis/pub-lock strict pasaron en otra pasada (`global-5.1.md`); no se atribuyen como nuevos resultados de este smoke. No duplicar host salvo necesidad diagnóstica.
- Sin herramientas nuevas ni instalaciones de QA/SDK. No Playwright/Chrome/Postman: aplicación Android-only local sin API.
