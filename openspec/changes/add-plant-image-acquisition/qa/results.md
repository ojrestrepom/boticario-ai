# Resultados de QA: adquisición de imágenes

Fecha: 29 de octubre de 2026. Rama: feature/plant-recognition. SDK: Flutter 3.47.6 y Dart 3.13.5. Dependencia resuelta: image_picker 1.2.4, con image_picker_android 0.8.13+25. Se añadieron 15 paquetes directos o transitivos sin actualizar las versiones de paquetes existentes.

## Comportamiento

Cámara y galería están activas en /identify. El adaptador verifica lectura y decodificación antes de sustituir la imagen. Cancelar conserva la anterior; un fallo recuperable también la conserva y muestra un mensaje accesible. Descartar limpia la selección e invalida resultados anteriores. Salir termina la sesión e impide que su resultado se aplique al volver a entrar. La vista previa conserva proporciones mediante BoxFit.contain. No hay inferencia, historial, almacenamiento permanente, copia de originales ni HTTP.

La recuperación se programa una vez por arranque Android desde el proveedor de aplicación, sin bloquear Inicio ni navegar. Una revisión capturada antes de ejecutarla impide sobrescribir acciones posteriores. El bloqueo de diálogo nativo persiste mientras acaba una selección de una sesión abandonada; un identificador de sesión evita que su dispose tardío limpie una sesión nueva.

## Verificaciones automatizadas

| Verificación desde app/ | Resultado | Evidencia |
| --- | --- | --- |
| Resolución de dependencias | Correcta: image_picker 1.2.4 compatible; sin cambios de versiones existentes | pubspec.lock |
| dart format --output=none --set-exit-if-changed lib test integration_test | Correcto: 91 archivos, 0 cambios | [format.log](evidence/format.log) |
| dart analyze sobre los archivos Dart de esta etapa | Correcto: No issues found! | [scoped-analyze.log](evidence/scoped-analyze.log) |
| flutter analyze --no-pub | 70 errores previos del catálogo; ninguna incidencia del incremento | [analyze.log](evidence/analyze.log) |
| flutter test --no-pub test/features/plant_recognition test/app/catalog_smoke_contract_test.dart --concurrency=1 --reporter expanded | 36 pruebas aprobadas | [focused-tests.log](evidence/focused-tests.log) |
| flutter test --no-pub test/ --concurrency=1 --reporter expanded | 612 pruebas aprobadas; 4 archivos de pruebas antiguos de catálogo no compilan | [all-tests.log](evidence/all-tests.log) |
| git diff --check excluyendo .env.cloud-run.example | Correcto | Comando ejecutado en la sesión |
| Concordancia de deltas con specs y escenarios WHEN/THEN | Correcta mediante script local; no sustituye CLI OpenSpec | Comando ejecutado en la sesión |

Las pruebas cubren origen de cámara/galería, cancelación, permisos, cámara inexistente, archivo ausente/ilegible/excesivo, recuperación vacía/con imagen/con error, selección concurrente, descarte pendiente, salida y reentrada, destrucción del proveedor, sesiones antiguas, recuperación tardía ante selección/cancelación/descarte/salida y ausencia de HTTP. Los widgets cubren reemplazo, cancelación, error, descarte, tres retornos desde tarjeta y ruta directa, semántica, texto al 100% y 200% e imágenes verticales y horizontales.

## Android con plugin real

Emulador emulator-5554: sdk gphone16k x86_64, Android 17 API 37. No hizo falta un dispositivo físico. Se compiló e instaló el APK debug sin modificar manifiesto, permisos ni Gradle.

- La prueba integration_test/plant_image_acquisition_test.dart pasó con apertura y cancelación reales de cámara y galería mediante el gesto Atrás; comprobó retorno a Inicio y cero peticiones HTTP. [android-cancel.log](evidence/android-cancel.log).
- La misma prueba con --dart-define=PLANT_NATIVE_ACQUIRE=true pasó al aceptar una foto de la escena virtual y una imagen local del repositorio cargada en la galería. Comprobó imagen no vacía, BoxFit.contain, descarte, retornos y cero HTTP. [android-acquire.log](evidence/android-acquire.log).
- La app normal se volvió a compilar e instalar mediante flutter run --debug --no-pub --no-resident -d emulator-5554, para no dejar el ejecutable de integración en el emulador. [android-app.log](evidence/android-app.log).
- Los selectores nativos se operaron desde el host mediante ADB. La imagen de galería de prueba fue el icono local de la app, no una imagen personal. [Confirmación de galería](evidence/android-gallery-confirmation.png).
- retrieveLostData se ejecutó realmente al arranque sin selección pendiente; los casos con imagen perdida, error y carreras se simularon en las pruebas unitarias. No se forzó destrucción real del proceso ni denegación real de permisos; queda pendiente esa validación en Android. Tampoco se ejecutó el smoke completo del catálogo contra backend; el smoke compartido con fixtures sí pasa.

Para repetir la prueba nativa se necesita interacción con los selectores: cancelar ambos con Atrás para el modo por defecto, o aceptar la foto y confirmar una imagen de galería con PLANT_NATIVE_ACQUIRE=true. La prueba espera el resultado y verifica la vista previa. La interacción de host no forma parte de la automatización de CI.

## Incidencias y límites

Los mismos archivos existentes de catálogo referencian PlantCatalog, PlantPart, traditionalUses y parámetros incompatibles con el modelo actual. Los cuatro archivos de pruebas que fallan al cargar son plant_catalog_asset_data_source_test.dart, plant_catalog_repository_test.dart, plant_search_test.dart y plant_test.dart. No se modificaron para respetar el alcance.

En Windows, dart format . encontró un PathNotFoundException al recorrer rutas generadas largas de Gradle bajo build/. La comprobación se realizó sobre lib, test e integration_test y pasó; no se alteraron archivos generados para sortearlo. Gradle mostró advertencias de acceso nativo de Java, sin impedir las compilaciones Android. Se corrigieron durante el desarrollo errores menores de pruebas (generación asíncrona de PNG y envoltorio ResizeImage); los resultados anteriores son los definitivos.

Las imágenes se mantienen en memoria y caché del plugin. Descartar o salir elimina las referencias propias, no borra originales de galería ni garantiza borrado físico inmediato de cachés. El adaptador limita adquisición a 2048x2048, calidad 90, omite metadatos completos y rechaza archivos de más de 32 MiB. No se garantiza conservar la imagen previa si Android destruye el proceso.

## Alcance conservado

Se mantuvieron intactos .env.cloud-run.example, backend, catálogo, objetivos, pasaportes y todos los cambios archivados. La evidencia de la primera etapa no se reescribió. No se realizaron commits ni push.
