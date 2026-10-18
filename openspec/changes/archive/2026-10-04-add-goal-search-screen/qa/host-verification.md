# Verificación host P06 / global 4.1

Ejecución: 2026-10-04, entorno local macOS; desde `app/`, con
`PATH=/opt/homebrew/share/flutter/bin:$PATH`.

| Comando | Resultado |
|---|---|
| `flutter --version` | exit 0; Flutter 3.47.6 stable, Dart 3.13.5 |
| `flutter pub get --enforce-lockfile` | exit 0; dependencias resueltas con lock exigido |
| `dart format --output=none --set-exit-if-changed .` | exit 0; 28 archivos revisados, 0 por formatear |
| `flutter analyze` | exit 0; `No issues found!` |
| `flutter test test/` | exit 0; 144/144 pruebas pasaron |
| `git diff --exit-code -- app/pubspec.lock` | exit 0; lockfile sin cambios |

El contrato host compartido se ejecutó aparte con
`flutter test test/app/catalog_smoke_contract_test.dart`: exit 0, 2/2 casos
pasaron, incluidos flujo compartido P06/catálogo y simulación de viewport IME.
En cada recorrido P06 verificó seis filas inertes, tabs inertes, ruta y retorno
por Atrás de app, pop framework/sistema y Inicio; el smoke comprobó la secuencia
literal de logs sin logs por render y preservó los casos P04/P05 de búsqueda,
filtros, insets, consulta, scroll, pasaporte y estado de retorno.

**Solo evidencia host. Android smoke: NOT RUN.** No se interactuó con ADB ni con
el AVD `emulator-5566`; por tanto esto no afirma ejecución Android, radios,
accesibilidad manual/TalkBack ni prueba de binarios release/profile. El guard
HTTP de la app se activa en el smoke Android; el preflight host no lo activó ni
prueba conectividad física.
