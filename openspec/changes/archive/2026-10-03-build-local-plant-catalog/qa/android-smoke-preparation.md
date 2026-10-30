# Preparación de smoke Android 4.3

Estado: **NO EJECUTADO aún; pendiente de code review y confirmación Android**.

Preflight automatizado host (2026-10-03):
`flutter test test/app/catalog_smoke_contract_test.dart` pasó (1 prueba). Ejecuta
el mismo flujo UI de app real —P03, P04, P05, retornos, Inicio y catálogo local—,
pero no es evidencia Android, de radios ni de un dispositivo físico.

El flujo compartido está en `app/integration_test/catalog_smoke.dart` y tiene un
preflight host en `app/test/app/catalog_smoke_contract_test.dart`; ese preflight
no acredita Android. No se ha compilado para Android, instalado ni ejecutado en
teléfono/emulador. No registrar este documento como resultado aprobado ni como
evidencia de funcionamiento Android.

Dispositivo observado previamente en QA 4.2 (no reconfirmado en esta pasada):
Samsung SM G998B, serial `R5CR70M9GEE`, Android 15 / API 35. El diagnóstico
previo reportó Android command-line tools ausentes y licencias desconocidas.
No se instalaron herramientas ni se aceptaron licencias.

Comandos planeados, desde `app/`, después de review y confirmación explícita:

```sh
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter devices
PATH=/opt/homebrew/share/flutter/bin:$PATH flutter test integration_test/app_test.dart -d R5CR70M9GEE
```

No se afirma que el segundo comando sea ejecutable todavía: primero resolver los
prerrequisitos Android fuera de esta tarea autorizada. En Android, el harness
instalará temporalmente el guard mediante `HttpOverrides.runZoned`: rechaza cada
creación de `HttpClient`, comprueba exactamente cero intentos y, al salir de la
zona, no modifica el override global previo ni contamina otras pruebas. Esto no
desconecta radios ni demuestra offline del sistema/dispositivo. El preflight host
precarga el asset con el canal del binding fuera de `FakeAsync`, no activa ese
guard y no afirma verificación de red o conectividad.
