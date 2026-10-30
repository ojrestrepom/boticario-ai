# Resultados de QA

Fecha: 29 de octubre de 2026. Rama: feature/plant-recognition. SDK verificado: Flutter 3.47.6 y Dart 3.13.5, coincidentes con el pin del repositorio.

## Implementación verificada

La tarjeta «Identificar con cámara» abre /identify y conserva un único mensaje de depuración. PlantRecognitionPage muestra el espacio reservado, las dos acciones deshabilitadas y el aviso. Los seis casos de entrada por tarjeta o ruta directa y retorno por Atrás de app, sistema o Inicio pasan sin HTTP; las otras pestañas permanecen inertes. Se verifican semántica deshabilitada, texto íntegro y layout con insets a 100% y 200% en 360x640. El smoke compartido con cliente falso pasa y comprueba que el recorrido no añade peticiones.

## Verificaciones

| Verificación desde app/ | Resultado | Evidencia |
| --- | --- | --- |
| flutter pub get --enforce-lockfile | Correcto; restauración de dependencias existentes sin cambios en pubspec ni lockfile | Estado de Git sin cambios de dependencias |
| dart format --output=none --set-exit-if-changed . | Correcto: 85 archivos, 0 cambios | [format.log](evidence/format.log) |
| flutter analyze --no-pub | Falla: 70 errores en archivos existentes del catálogo, ninguno en los archivos de este incremento | [analyze.log](evidence/analyze.log) |
| dart analyze sobre router, Inicio, plant_recognition, pruebas nuevas y modificadas y smoke | Correcto: No issues found! | Salida del comando en la sesión |
| flutter test --no-pub test/features/home test/features/plant_recognition test/app/app_test.dart test/app/catalog_smoke_contract_test.dart --reporter expanded | Correcto: 78 pruebas aprobadas | [focused-tests.log](evidence/focused-tests.log) |
| flutter test --no-pub test/ --concurrency=1 --reporter expanded | 586 pruebas aprobadas; 4 archivos de pruebas del catálogo fallan al compilar | [all-tests.log](evidence/all-tests.log) |
| git diff --check excluyendo .env.cloud-run.example | Correcto | Salida del comando en la sesión |
| Concordancia de requisitos de deltas con specs vigentes y presencia de escenarios WHEN/THEN | Correcto mediante comprobación local; no equivale a validación con CLI OpenSpec | Salida del script en la sesión |
| Smoke Android | No ejecutado: flutter devices solo lista Windows y Edge, sin Android | Salida del comando en la sesión |

## Incidencias ajenas al incremento

Los archivos plant_catalog_asset_data_source.dart y plant_catalog_repository.dart, junto a pruebas antiguas del catálogo, todavía referencian PlantCatalog, PlantPart, traditionalUses y parámetros de un modelo anterior. Git confirma que estos archivos y los modelos del catálogo no se modificaron en esta funcionalidad. No se corrigen para respetar el alcance autorizado. Los cuatro archivos de pruebas afectados son test/features/catalog/data/plant_catalog_asset_data_source_test.dart, test/features/catalog/data/plant_catalog_repository_test.dart, test/features/catalog/domain/plant_search_test.dart y test/features/catalog/domain/plant_test.dart.

La primera ejecución completa concurrente reportó además un fallo secundario de compilador al cargar app_test.dart. Esa suite pasa en la ejecución focalizada y en la repetición secuencial de toda la suite; el último resultado conserva únicamente los cuatro fallos de catálogo.

El análisis inicial sin restaurar dependencias no resolvía paquetes. Se restauraron exclusivamente las versiones del lockfile. Dos pruebas nuevas liberaban el recurso de semántica demasiado tarde; se corrigieron con finally y pasan. La CLI OpenSpec no está disponible; no se instaló ninguna herramienta nueva. La comprobación global de whitespace detecta una línea vacía final en el cambio previo de .env.cloud-run.example, que se conservó sin tocar.

## Alcance conservado

No se modificaron backend, módulos de catálogo, objetivos o pasaportes, dependencias, especificaciones archivadas ni .env.cloud-run.example. No se incorporaron permisos, cámara, galería, IA ni persistencia. No se realizaron commits ni push. Quedan pendientes corregir el catálogo en un cambio separado y ejecutar el smoke en Android cuando haya dispositivo.

## Validación visual comunicada por el usuario

El usuario confirmó la prueba visual de la pantalla en el emulador Android y el funcionamiento de la flecha Atrás y de la pestaña Inicio, y dio por terminada la primera etapa. Esta validación manual complementa las pruebas automatizadas anteriores; no constituye la ejecución del smoke Android completo. Los errores preexistentes del catálogo permanecen fuera del alcance.
