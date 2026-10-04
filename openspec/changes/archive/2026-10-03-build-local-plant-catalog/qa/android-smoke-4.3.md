# QA Android smoke 4.3 / evidencia para 5.2

Fecha: 2026-10-03 UTC. Estado: **FALLÓ — Android no aprobado**. Code review aceptado y build/instalación/prueba autorizados por el usuario. No se marcan tareas ni se modifica producto/harness.

## Entorno y precondiciones

- Samsung SM-G998B, serial `R5CR70M9GEE`, Android 15 / API 35, conectado y autorizado por ADB; reconfirmado en esta pasada.
- Flutter 3.47.6 stable, Dart 3.13.5; doctor Android ✓. SDK platform 36, build-tools 36.0.0 y NDK 28.2.13676358 preexistentes. Doctor enumera también platform 37.0; no cambia el compile/target API 36 fijado por Flutter.
- Licencias ya aceptadas según doctor; no se ejecuta ningún comando de aceptación. SHA-256 del archivo de licencia coincide con preparación: `c43fa37686457c3f18caa3607945f4ec52a9d1beaaad8117e50dc4e863270c85`.
- App real `main`, ProviderScope/router/tema y JSON local de cinco plantas; sin URL, credenciales ni sustituciones de repositorio. Se usa únicamente dato sintético.
- Fuentes leídas: README, pin, config OpenSpec, diseño/tareas, las cinco specs delta y ambos documentos de preparación con log de toolchain.
- Preflight íntegro: `evidence/android-smoke-preflight.log`, 13:32:17–13:32:19 UTC. Advertencias iOS fuera de alcance.

## Plan priorizado y trazabilidad

Todos los casos comparten esas precondiciones. Son comprobaciones del único test Android `real app: Home, local catalog, passport and session returns`; no se cuentan como tests Android separados. Las capabilities siguientes remiten a `../specs/<capability>/spec.md`.

| ID / riesgo | Capability / requisito | Técnica y pasos | Resultado esperado | Resultado |
|---|---|---|---|---|
| AS-01 / alto | flutter-app-bootstrap: arranque Android | Transición inicial: iniciar app real; comprobar `/`, marca/banner y ausencia demo | Home visible, Inicio seleccionado, 0 logs por build | Pasa hasta el punto de fallo |
| AS-02 / alto | home-screen: 11 acciones y barra inmóvil | Tabla de decisión: activar diez controles inertes y Explorar; oráculo literal por activación | Diez mantienen `/`, selección y no overlays; Explorar abre P04; exactamente un log normativo por acción | Pasa por activación: 11 mensajes distintos; secuencia global final bloqueada |
| AS-03 / alto | explore-screen: composición; plant-catalog: cinco identidades | Partición válida: abrir P04, desplazar para alcanzar cada fila | Todas inicial, cinco pares común/científico exactos y accesibles | Pasa |
| AS-04 / alto | explore-screen: búsqueda/filtros/vacíos | Particiones: `  LAVÁNDULA   ANGUSTIFOLIA `, `MENTA`, consulta sintética sin match; Aceites; borrar; Plantas con `A` | Normalización/ambos nombres, vacío no-match distinto de Aceites; borrar conserva Aceites; filtro combina con consulta | Pasa |
| AS-05 / alto | plant-passport: identidad, General/Propiedades/Usos | Particiones de contenido: abrir Menta 619; recorrer tabs; luego Lavanda 544/Usos | Identidades correctas; General inicial/ausencias/no aceite; propiedades sin evaluar; Menta usos vacíos; Lavanda tradicional con cita y disclaimer | Parcial: Menta pasa; Lavanda bloqueada |
| AS-06 / alto | explore-screen: retorno/estado | Transición de estados: capturar consulta `A`, Plantas y offset; Menta→chevron; reabrir→framework handlePopRoute | P04 recupera consulta/filtro/offset exacto en ambos retornos; offset >0 si hay extensión | FALLA chevron: offset 108.79999999999995→0.0; query/filtro pasan; framework Back bloqueado |
| AS-07 / alto | explore-screen: Inicio desde catálogo; flutter-app-bootstrap: recorrido acotado | Transición de sesiones: Inicio real desde P04 y P05; reabrir Explorar tras cada limpieza | Home `/`, sin pila poppable; nueva sesión Todas/consulta vacía/offset 0 | Parcial: primer Inicio P04/nueva sesión pasan; Inicio P05 y resto bloqueados |
| AS-08 / medio | explore-screen: footer; plant-passport: acciones no funcionales | Negativos/semántica: inspeccionar y tocar footer no disponible, corazón/formulaciones | Deshabilitados, sin acción semántica de tap, sin navegación/mutación ni logs Home nuevos en P05 | Pasa para P04 y Menta P05 |
| AS-09 / alto | plant-catalog: disponibilidad local; flutter-app-bootstrap: sin servicios | Flujo bajo HttpOverrides.runZoned, fábrica HttpClient denegada; assertion final | Cero intentos de crear HttpClient de app; NO equivale a radios desconectados | Bloqueado: guard activo, assertion final de cero no alcanzada; no se acredita 0 intentos |

## Ejecución y evidencia

Desde `app/`:

```sh
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test integration_test/app_test.dart -d R5CR70M9GEE
```

Stdout/stderr completos UTF-8, fechas y exit code: `evidence/android-smoke-run.log` (evidencia para todos los casos anteriores; pasos previos inferidos por orden secuencial y primer fallo). Se ejecutó una sola vez; no se repitió ni se hicieron capturas o logcat.

- Inicio 13:33:49.377221 UTC; fin 13:34:30.901353 UTC; **exit 1**, wall **41.524 s**.
- Gradle `assembleDebug`: **15.3 s**, APK debug construido en `app/build/app/outputs/flutter-apk/app-debug.apk`. Instalación en Samsung: **3.7 s**, exit de esas etapas exitoso; la app real arrancó y ejecutó el test.
- Runner Android: **0 pruebas pasadas, 1 fallida**, duración informada **00:18**; setUpAll/tearDownAll no son tests adicionales. No se usa el resultado host para volver verde Android.
- Últimas acciones: Plantas + consulta `A` → desplazar a Menta → abrir `/explore/619` → General/Propiedades/Usos vacío → comprobar/tocar cinco controles deshabilitados → chevron `Volver a Explorar` → `/explore`, consulta/filtro conservados, offset falla.
- Se observaron 12 mensajes Home hasta el fallo (diez inertes + dos Explorar), cada activación alcanzada validada con su literal. La assertion de la secuencia completa de 14 y la de cero HttpClient no se alcanzaron.
- No hubo solicitudes de nuevas licencias/componentes SDK, conflictos de firma, uninstall ni clear data ejecutados por QA. No hubo comandos de aceptación de licencias ni instalación nueva de herramientas. La resolución normal de paquetes no actualizó el lockfile/pin; hashes antes/después coinciden en manifest.

### Regresión host diagnóstica tras fallo Android

`evidence/android-smoke-host-regression.log` conserva ambas salidas completas:

| Comando desde app/ (mismo PATH) | UTC inicio–fin | Resultado | Wall |
|---|---|---|---|
| `flutter test test/app/catalog_smoke_contract_test.dart` | 13:34:56.819691–13:34:59.522700 | 1/1 pasa, exit 0 | 2.703 s |
| `flutter test test/` | 13:34:59.522778–13:35:05.670673 | 136/136 pasan, exit 0 | 6.148 s |

No se repitieron analyze/formato: los resultados previos no se atribuyen a esta pasada. El host usa el mismo flujo, **sin guard HTTP** y sin dispositivo Android. Su éxito no confirma el offset del Samsung ni desconexión física.

## Defecto / fallo de aceptación observado

**AS-D01 — severidad media: pérdida del offset P04 al volver de Menta por chevron en Android.** Afecta `specs/explore-screen` → Estados y navegación de resultados / Abrir y volver de una ficha y Volver desde Pasaporte a Explorar; también el contrato de sesión del diseño y aceptación 4.3/5.2.

Reproducir con el comando Android anterior y este mismo working tree/Samsung. Recorrido preciso: Home→Explorar; búsqueda/filtros del harness; Inicio P04; nueva P04 (Todas/consulta vacía/offset 0); seleccionar Plantas, escribir `A`, desplazar hasta Menta, capturar offset; tocar Menta; recorrer General→Propiedades→Usos; tocar controles deshabilitados; tocar chevron Volver a Explorar.

- Esperado por contrato/harness: ruta `/explore`, query `A`, filtro Plantas y offset **108.79999999999995** preservados.
- Obtenido: ruta/query/filtro pasan sus assertions; offset **0.0**. `TestFailure` en `app/integration_test/catalog_smoke.dart:350`, invocado por primer retorno `:215`; entrada Android `app_test.dart:16`.
- Reproducción disponible mediante secuencia automatizada completa, observada en una sola ejecución autorizada; no se hizo segunda pasada ni verificación manual. No es fallo de build, instalación, permisos ni licencias.
- **Producto vs harness:** el síntoma de scroll en el estado real de P04 está comprobado; la causa y la atribución definitiva quedan pendientes del Worker/Orchestrator. No se observó locator fallido, tap perdido ni timeout: el chevron se activó y el retorno a `/explore`/query/filtro fue validado antes del offset. El host pasa. El log no instrumenta viewport/insets/maxScrollExtent al regresar: un cambio del viewport/teclado con clamp legal del offset es hipótesis a investigar, no defecto adicional confirmado ni justificación para ignorar el fallo. No afirmar pérdida de estado por recreación del router sin evidencia. No se modificó harness para diagnosticar ni arreglar.

**Decisión QA:** smoke Android no exitoso; devolver AS-D01 con log y líneas al Orchestrator. No acreditar aceptación completa de 4.3/5.2. Si se confirma un problema del test, requerirá corrección/review y nueva ejecución, no un cambio por QA.

Manifest de fuentes SHA-256 y configuración Android leída: `evidence/android-smoke-source-manifest.log`. El working tree revisado contiene cambios aún no committeados; HEAD base `a97472b77cfc63cbba3f93d1bfde9cd6e16e447d` no se presenta como SHA de la implementación probada. El contrato está en `app_test.dart:13–16`; las comprobaciones secuenciales están en `catalog_smoke.dart:79–306` (oráculo final de 14 logs: diez acciones inertes y cuatro activaciones Explorar; cubre los 11 mensajes distintos). AGP 9.1.0 y Gradle wrapper 9.3.1.

## Límites y cobertura residual

- No se autoriza ni prueba Back físico, TalkBack, cambio de font scale/200% o desconexión física de radios. `handlePopRoute` no es evidencia de pulsación física.
- Semántica del harness no sustituye recorrido manual con tecnología de asistencia, accesibilidad visual/48dp, safe areas ni revisión integral 5.3.
- Guard HTTP cubre creación de clientes `dart:io` dentro de la zona app, no tráfico nativo, sockets alternativos ni conectividad del dispositivo. Precarga del asset ocurre antes del guard. Host no activa ese guard.
- No se inyectan errores de asset/IDs inexistentes ni se alteran fixtures; cubiertos por suites host previas, no por este smoke. No se prueba release/profile, hot reload/IDE ni CI.
- P05 se abre para Menta/Lavanda; las otras tres identidades se verifican como filas P04, no como pasaportes Android.
- No se usa Playwright/Chrome/Postman: app Android local sin API. No se instalan herramientas nuevas en esta pasada; toolchain fue preparado previamente.
- Exploración manual adicional fuera del harness queda sin ejecutar en esta autorización. No se afirma ni marca 4.5/5.3.
