# Verificación global host 5.1

Fecha: 2026-10-03 UTC. Alcance: verificación host de Flutter, sin ejecutar
build/test de app Android. Ningún test se omitió ni actualizó.

## Toolchain y resultados

- Pin `.flutter-version`: **3.47.6**.
- Flutter efectivo: **3.47.6 stable**, revision `5fc346839b`.
- Dart efectivo: **3.13.5 stable**, macOS arm64.
- Directorio de todos los comandos: `app/`; `PATH=/opt/homebrew/share/flutter/bin:$PATH`.

| Comando | UTC | Resultado |
|---|---|---|
| `flutter pub get --enforce-lockfile` | 13:47:46 | exit 0; deps resueltas con lockfile requerido |
| `dart format --output=none --set-exit-if-changed .` | 13:48:13 | exit 0; 26 archivos revisados, 0 cambiados |
| `flutter analyze` | 13:48:17–13:48:19 | exit 0; No issues found |
| `flutter test test/` | 13:48:23–13:48:29 | exit 0; **137/137 pasaron** |

Flutter informó que cuatro paquetes tienen versiones más nuevas incompatibles
con las restricciones actuales (`material_color_utilities`, `meta`, `test_api`,
`vector_math`); no se actualizaron dependencias.

Salidas stdout/stderr completas, con comando, directorio, timestamps y exit code:

- [pub get](evidence/global-5.1-pub-get.log)
- [format](evidence/global-5.1-format.log)
- [analyze](evidence/global-5.1-analyze.log)
- [tests](evidence/global-5.1-tests.log)

## Integridad y límites

El SHA-256 de `app/pubspec.lock` antes y después es el mismo:
`af69c6b69b339d74946004a863954adfa14f9c30d44692e762fbade82bd02626`.
El formatter reportó cero archivos cambiados. No se modificaron el pin SDK ni
los archivos de configuración Android; el incremento comprobado aquí es host,
no acredita compilación, instalación ni smoke Android.

El smoke Android Samsung del 2026-10-03 ejecutó build e instalación y **falló**
al verificar el retorno de scroll; Android no está aprobado. La repetición en
AVD continúa pendiente. Se conserva sin sobrescribir el
[informe Android 4.3](android-smoke-4.3.md) y la
[investigación del retorno](scroll-return-investigation.md). El host pasa no
elimina ni reinterpreta ese fallo. Esta verificación tampoco completa las tareas
4.3, 4.5, 5.2 o 5.3.
