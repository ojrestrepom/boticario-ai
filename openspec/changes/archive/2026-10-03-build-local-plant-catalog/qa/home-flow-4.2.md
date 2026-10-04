# QA 4.2 — Home → catálogo integrado (host)

Fecha: **2026-10-03**. Code review recibido aprobado. **4.2 pasa en host; no aprobación Android ni del incremento completo.** Sin defectos de producto reproducidos.

## Entorno y alcance

- Leídos completos: `README.md`, `.flutter-version`, `openspec/config.yaml`, specs delta `home-screen`, `explore-screen`, `plant-passport`, `flutter-app-bootstrap`, `design.md` y `tasks.md` del cambio.
- Flutter **3.47.6 stable**, Dart **3.13.5**, macOS. Comandos desde `app/`, PATH temporal. Diagnóstico observado a las **13:00 UTC**: `evidence/home-flow-toolchain.log`.
- Bajo prueba: callback requerido `HomePage.onExplore`, su llamada incondicional después de `_emitHomeAction`, `context.push('/explore')` del router real y tests actualizados Home/app. Harness `flutter/home_flow_qa_test.dart`: **BoticarioApp + ProviderScope + tema + GoRouter reales**; toda navegación normal mediante UI, sin fakeNavigate ni push programático.
- Nuevo scope/router por caso, arranque `/`; viewport 360×640 dp al 100%, fonts Roboto Regular/Medium locales autorizadas. JSON real inyectado en data source; parser/repositorio/providers reales. Sin HTTP, ZIP, nuevas dependencias, configuración de producto ni credenciales.
- No se ejecutó `integration_test/app_test.dart`: contrato Home-only antiguo, actualización reservada a **4.3**. Tampoco se modificaron README/checklists/producto ni QA histórica, incluyendo logs anteriores donde Explorar era inerte.

## Plan y resultados

Precondición común: app real en un widget test host aislado, catálogo local válido, `debugPrint` capturado durante el body y restaurado con `finally` **antes** de invariants Flutter. Todas las cadenas esperadas son literales del delta `home-screen`, no derivadas del helper de implementación.

| ID / riesgo | Requerimiento y capability | Técnica | Pasos | Resultado esperado / obtenido |
|---|---|---|---|---|
| HQ01 / alto | `specs/home-screen`: 11 callbacks/logs, distinción perfiles, Inicio activo, diez acciones sin mutación/overlays, sin log por render | Particiones de diez controles; repetición/límite 1 activación = 1 mensaje | Activar cada control no Explorar dos veces; comparar mensajes, ruta, selección semántica, textos y overlays después de cada tap; reconstruir/reensamblar subtree | **PASA**: 20 activaciones = 20 mensajes literales, distintos perfiles; `/`, una Home, Inicio seleccionado; textos iguales, sin drawer/dialog/SnackBar/bottom sheet. Cero mensajes por render/rebuild/reassembly |
| HQ02 / alto | `specs/home-screen`: Explorar en debug; `specs/explore-screen`: identidad/retorno; `specs/plant-passport`: identidad; `specs/flutter-app-bootstrap`: recorrido acotado | Transición P03→P04→P05→P04→P03; particiones por cinco identidades | Tap tarjeta real; tap cada fila y volver por chevron; chevron P04→Home; rebuild | **PASA**: único `[Home] Explorar plantas y aceites`; fichas IDs **544, 401, 873, 605, 619** con nombres científicos correctos; regreso seguro, sin logs de filas/pop/rebuild |
| HQ03-chevron-P04Home / alto | `specs/explore-screen`: conservar sesión, Inicio; `specs/home-screen`: sin autoreports; diseño limpieza de pila | Transición de sesión; límite scroll > 0 | Home tap Explorar; Plantas/query `a`, drag; fila Menta; chevron P05→P04; Inicio P04→Home; tarjeta Explorar; framework pop | **PASA**: `/explore/619`, query `a`, Plantas, scroll **48→48 dp**; Home sin pila (`canPop=false`), P04/P05 descartados; reentrada Todas/query vacía/scroll 0; 2 taps Explorar = 2 logs, nada más |
| HQ03-frameworkBack-P05Home / alto | Mismos requerimientos/capabilities de HQ03 | Pair de retorno framework / destino Inicio P05 | Mismo flujo; pop por binding a P04; abrir Menta otra vez; Inicio P05→Home; reentrar P04 y pop | **PASA**: sesión **48→48 dp**, Home única sin pila, nueva sesión limpia; exactamente 2 logs de las 2 activaciones Explorar |
| HQ04 / medio | `specs/explore-screen`: pestañas deshabilitadas, vacíos, borrar conserva filtro; `specs/home-screen` / `specs/flutter-app-bootstrap`: sin logs de datos/operaciones de producto | Negativos y transición consulta sin coincidencias→Aceites→borrar | Inspeccionar semántica e intentar activar Favoritos/Historial/Perfil en P04; introducir marcador privado sin coincidencias; Aceites; borrar; Inicio | **PASA**: tres controles anunciados deshabilitados, no navegan; vacíos distintos, borrar conserva Aceites; único mensaje de tap Explorar, cero mensajes de catálogo/query/Inicio del catálogo |
| HPOL / alto | `specs/home-screen`: política debug y navegación independiente; `specs/flutter-app-bootstrap`: verificación reproducible sin exigir binarios | Tabla permitido/no permitido + lectura del control flow | Ejecutar tests existentes de helper (11 true, 11 false + 4 enum); inspeccionar emitter/callback/router | **PASA**: helper false devuelve null en 11/11; emitter solo imprime si no null; `onExplore()` fuera de esa condición y router hace push. **No se falseó kDebugMode ni se ejecutó release/profile** |
| HREG / alto | `specs/flutter-app-bootstrap`: regresión reproducible; capabilities Home/catálogo/Explorar/pasaporte | Regresión automatizada existente, sin duplicar accesibilidad en nuevos casos | Focused Home/app y suite global | **PASA**: focused **64/64**, global **135/135** |

Charter exploratorio: repetir controles Home, recorrer las cinco identidades desde la tarjeta, abandonar sesión desde P04/P05 y buscar sin coincidencias/Aceites mientras se vigilan logs completos y destinos. Ejecutado como HQ01–HQ04; ningún overlay, ruta extra, log de consulta ni estado obsoleto observado.

## Evidencia y recuentos exactos

| Ejecución | Resultado final | Evidencia |
|---|---|---|
| Focused helper/Home/app | **64 passed** | `evidence/home-flow-focused.log` |
| QA independiente (4 IDs, HQ03 tiene 2 variantes) | **5 passed** | `evidence/home-flow-qa.log` |
| Global `test/` | **135 passed** | `evidence/home-flow-regression.log` |
| Lectura de control flow / búsqueda de servicios y logs / formato harness | Navegación no condicionada al logging; único `debugPrint` de producto en emitter; lockfile sin diff; harness 0 cambios de formato | `evidence/home-flow-controlflow.log` |
| Versiones / devices / doctor | Diagnóstico de solo lectura, detalles abajo | `evidence/home-flow-toolchain.log` |

En QA independiente se capturaron **26 llamadas `debugPrint`**, todas y solo normativas Home: **20** de acciones inertes y **6** de taps Explorar (1 + 2 + 2 + 1). **0 duplicados por activación, 0 logs automáticos, 0 de acciones catálogo ni de consultas**. Los marcadores `HOME-FLOW-QA` son `print` del harness, no producto. La observación no equivale a auditoría de todos los canales del SO, logs de dependencias o persistencia del dispositivo. La lectura de `app/lib` no encontró llamadas a servicios/auth/persistencia; `photo_camera` es solo un icono.

Incidencias del harness corregidas, **no defectos de producto**:

1. Primera ejecución: HQ01 no terminó (timeout externo 120 s, 0 completados) al esperar `binding.reassembleApplication` sin conducir frames en FakeAsync. Sustituido por reassembly síncrono del subtree + pump; no representa Hot Reload VM/IDE real. Evidencia: `evidence/home-flow-harness-initial.log`.
2. Segunda: **4 pasan / 1 falla**; HQ02 tocaba chevron P04 antes de relayout tras `ensureVisible` (centro y=-20). Corregido helper para pump tras scroll y assertion hit-testable antes de tap. Evidencia: `evidence/home-flow-harness-second.log`.
3. Reejecución final completa: **5/5**, sin warnings de hit-test.

## Defectos, límites y riesgos residuales

- **Defectos de producto: ninguno reproducido**; no hay severidad ni repro pendiente para Worker.
- Host confirma callbacks/logs, transición de rutas, semántica y sesión. Global incluye pruebas existentes de accesibilidad/48 dp/legibilidad 100% y 200%; no se recrearon tests extensos de textos en este harness. No representa observación visual Android o TalkBack.
- **No probado:** instalación/build Android en esta pasada, smoke 4.3, Back/gestos predictivos reales, Run/Debug y Hot Reload IDE reales, revisión visual física, escala de fuentes del SO, offline/red física, lifecycle/reinicio de proceso, binarios release/profile o CI remoto. No URL web/API/credenciales: Playwright/Postman **no aplican**.
- No se volvió a ejecutar formato/análisis global ni pub get como aceptación 5.1; la CLI de tests resolvió los paquetes con lock existente. QA 4.1 permanece histórica para errores/carga/IDs desconocidos; no se confunde con ejecución adicional en esta pasada.
- **No aprobar 4.5/5.x** por estos resultados; quedan pendientes validación Android y cierre del incremento. README/smoke antiguos son tareas 4.4/4.3 pendientes, no regresiones 4.2.

## Diagnóstico Android para preparar 4.3 (solo lectura)

- Device **actual observado**, no asumido: **SM G998B**, serial **R5CR70M9GEE**, `android-arm64`, **Android 15 / API 35**. `flutter devices` también lista macOS y Chrome; no lista emulador Android activo. Ninguno sustituye el target Android.
- Disponible: Flutter/Dart pin correctos; SDK Android **36.0.0** en `/Users/jsrc1115/Library/Android/sdk`; componente emulator **37.2.12.0**; teléfono detectado.
- Faltante/bloqueo observado por doctor: **cmdline-tools ausente** y **estado de licencias Android desconocido**. No se concluye que compilar sea imposible sin intentar build; estos hallazgos requieren resolver/validar antes del smoke autorizado.
- Doctor reporta además Xcode incompleto/CocoaPods ausente (fuera del target Android); checks de recursos de red pasan. Eso **no demuestra offline del producto**.
- No se instalaron SDK/herramientas, aceptaron licencias, instalaron apps ni modificaron adb, teléfono, conectividad o font scale. No apareció solicitud interactiva de actualización SDK. Dispositivo disponible **no significa smoke ejecutado**.

## Reejecución

Desde `app/`:

```sh
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test test/features/home/home_action_test.dart test/features/home/home_page_test.dart test/app/app_test.dart --reporter expanded
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test ../openspec/changes/build-local-plant-catalog/qa/flutter/home_flow_qa_test.dart --reporter expanded
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test test/ --reporter expanded
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter devices
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter doctor -v
```

Herramientas/dependencias instaladas: **ninguna**. Único formato aplicado: archivo nuevo QA. Sin cambios a producto/configuración/checklists, sin commits/push; artefactos de esta pasada solo en esta carpeta con `home-flow-*` y `flutter/home_flow_qa_test.dart`. QA previa preservada.
