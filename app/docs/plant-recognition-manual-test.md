# Prueba manual del reconocimiento en Android

## Ejecución desde VS Code

Abre la carpeta `app/` como proyecto en VS Code. Con la extensión Flutter disponible, selecciona `emulator-5554` mediante `Flutter: Select Device`, abre `lib/main.dart` y pulsa F5. No se necesitan backend, credenciales ni archivos `.env` para reconocer plantas. El catálogo conserva sus requisitos independientes.

La alternativa equivalente en la terminal PowerShell de VS Code, situada en `app/`, es:

```powershell
flutter devices
flutter pub get
flutter run -d emulator-5554
```

Espera a que `flutter devices` muestre el emulador conectado. No ejecutes compilaciones debug, pruebas Flutter y compilaciones release simultáneamente: comparten artefactos generados de plugins. Detén la depuración con Shift+F5 o usa `q` en la terminal antes de iniciar otra compilación.

## Fotografías locales de referencia

Los assets de prueba no aparecen automáticamente en la galería Android. Desde `app/`, copia las cuatro fotografías al emulador y registra sus archivos locales:

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
1..4 | ForEach-Object {
    $photo = "Boticario-reference-$_.jpg"
    & $adb -s emulator-5554 push "assets/images/test/$_.jpg" "/sdcard/Download/$photo"
    & $adb -s emulator-5554 shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file:///sdcard/Download/$photo"
}
```

En el selector del emulador API 37, las referencias están en `Collections → From this device → Downloads`. Selecciona una y confirma con `Done` si aparece. Evita escoger capturas de pantalla en la pestaña general de fotos. La interfaz del selector puede variar según la versión Android.

| Fotografía | Clase Top-1 de referencia | Especie |
| --- | ---: | --- |
| 1.jpg | 4 | Cirsium vulgare |
| 2.jpg | 144 | Chaerophyllum temulum |
| 3.jpg | 187 | Sedum rupestre |
| 4.jpg | 529 | Adenostyles alpina |

El selector existente puede reducir o recomprimir la fotografía; por ello sus porcentajes pueden diferir de la prueba de integración que lee directamente los assets. No se modificaron ni la adquisición ni los parámetros del preprocesamiento.

## Recorrido manual

1. Comprueba que aparece Inicio y pulsa «Identificar con cámara». Debe abrirse `/identify` con «Identificar planta» deshabilitado mientras no haya imagen.
2. Pulsa «Seleccionar de galería», elige una referencia y confirma. Comprueba la vista previa y que «Identificar planta» quede habilitado.
3. Pulsa «Identificar planta». Durante el reconocimiento debe aparecer progreso y el botón debe estar deshabilitado. Al terminar, desplaza la pantalla hasta ver las cinco candidatas ordenadas, sus nombres científicos y puntuaciones relativas con dos decimales.
4. Repite la identificación de la misma fotografía. No deben acumularse tarjetas ni solicitudes por pulsaciones repetidas.
5. Cancela una nueva selección en la galería. Deben conservarse la fotografía y los resultados anteriores. Después selecciona otra referencia: los resultados anteriores deben desaparecer hasta una nueva identificación.
6. Pulsa «Descartar imagen». Deben desaparecer la imagen y los resultados, y deshabilitarse «Identificar planta».
7. Pulsa «Tomar fotografía», captura con la cámara nativa, acepta y comprueba la vista previa. Identifica la captura. La cámara virtual del emulador no constituye una referencia botánica; esta prueba comprueba adquisición e inferencia, no exactitud científica.
8. Cancela una nueva captura y comprueba que se conserva el resultado anterior. Sal mediante Atrás o Inicio; al volver a `/identify` no deben reaparecer la imagen ni resultados de esa sesión. También puedes salir durante el progreso: una respuesta tardía no debe modificar la siguiente visita.
9. Desactiva Wi-Fi y datos móviles desde Android, cierra y vuelve a abrir Boticario AI y repite galería e identificación. El reconocimiento debe funcionar sin conexión. Restaura después el estado previo de las radios.
10. Un fallo de reconocimiento debe mostrar un mensaje comprensible y permitir reintentar. No alteres el modelo ni sus metadatos para provocar fallos: la inyección controlada de errores se verifica con las pruebas automáticas.

## Diagnóstico de ventanas negras o splash persistente

En la validación se reprodujo el problema también al abrir Ajustes de Android: el contenido existía en accesibilidad, pero la ventana permanecía oculta y la captura mostraba el splash. Reiniciar Android recuperó el arranque de ambas aplicaciones sin cambios de código, modelo o renderizador. Esto identifica un estado defectuoso del emulador; no identifica la causa interna exacta de Android.

Si vuelve a ocurrir, comprueba primero si afecta también a una app del sistema. Guarda el trabajo de otras apps del emulador y reinicia Android sin borrar sus datos:

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb -s emulator-5554 reboot
& $adb -s emulator-5554 wait-for-device
& $adb -s emulator-5554 shell getprop sys.boot_completed
```

`wait-for-device` solo confirma la conexión ADB. Repite la última consulta hasta obtener `1`, desbloquea el emulador y ejecuta de nuevo `flutter run -d emulator-5554`. No cambies ONNX, sus parámetros o la arquitectura para corregir un fallo de visibilidad del sistema.

## Regresión y compilación de evaluación

Ejecuta estos comandos secuencialmente desde `app/`:

```powershell
dart analyze lib/features/plant_recognition test/features/plant_recognition test/support/fake_plant_recognition_service.dart integration_test/plant_recognition_ui_test.dart
flutter test test/features/plant_recognition
flutter test integration_test/plant_recognition_ui_test.dart -d emulator-5554
flutter build apk --release
```

La integración sustituye solo la adquisición por fotografías conocidas; usa la app, la ruta, el controlador y ONNX reales, y comprueba que no haya HTTP. No sustituye la prueba manual del selector nativo.

El APK de evaluación se genera en `build/app/outputs/flutter-apk/app-release.apk`. La configuración actual usa la clave de depuración también en release: no es una versión firmada definitivamente ni publicada. La regla `android/app/proguard-rules.pro`, conectada desde Gradle, conserva las clases `ai.onnxruntime` que JNI necesita por nombre; sin ella, la inferencia release produjo un aborto nativo tras la ofuscación R8. No basta con que el APK compile: comprueba también su inferencia instalada.

Si una compilación release después de pruebas falla porque `GeneratedPluginRegistrant.java` referencia `integration_test`, no edites ese archivo generado. Con las demás herramientas Flutter detenidas, vuelve a ejecutar `flutter build apk --release` para regenerar los artefactos adecuados al modo de distribución.

## Registro de validación de la Etapa 3.4

Validación realizada el 31 de octubre de 2026 en `emulator-5554`, Android API 37, x86_64 y páginas de 16 KB, con Flutter 3.47.6. No se cambiaron dependencias, modelo, metadatos, parámetros del preprocesamiento ni arquitectura. El reinicio del emulador resolvió el bloqueo de visibilidad; la única corrección de ejecución en el repositorio fue conservar mediante R8 las clases usadas por JNI de ONNX Runtime.

| Comprobación | Resultado y alcance |
| --- | --- |
| Arranque normal e Inicio → `/identify` | Verificados por toques reales en debug y release, fuera del runner de integración. |
| Galería nativa e identificación | Verificadas las referencias 1 y 2: Top-1 `Cirsium vulgare` con 65.57 % y `Chaerophyllum temulum` con 81.09 %, respectivamente; cinco candidatas visibles en ambos casos. |
| Repetición, cambio y descarte | Verificados desde la interfaz; el cambio elimina resultados y el descarte deshabilita la identificación. |
| Cámara nativa | Captura aceptada, vista previa e inferencia verificadas con la cámara virtual; cancelar una nueva captura conserva el resultado anterior. No equivale a evaluar una cámara física ni exactitud botánica. |
| Sin Internet | Wi-Fi y datos móviles desactivados; Android informó `Active default network: none`. Galería, cámara e inferencia funcionaron; también se comprobó el arranque en frío e inferencia release en ese estado. Ambas radios se restauraron a su estado previo habilitado. |
| Errores controlados y salida durante inferencia | Verificados automáticamente con servicios sustituidos, sin alterar los assets de producción. No se provocó deliberadamente una excepción de ONNX desde la interfaz normal. |
| Regresión | 49 pruebas unitarias y de widgets aprobadas; análisis de la funcionalidad y sus pruebas sin incidencias; integración Android de la app y ONNX reales aprobada con cero HTTP. |
| Release | APK compilado, instalado y probado interactivamente tras añadir la regla R8. JNI conservó `TensorInfo` y `OnnxJavaType`; la referencia 2 produjo las cinco candidatas sin cierre del proceso. Firma de depuración existente; no publicado. |

La [captura del APK release sin conexión](plant-recognition-release.png) muestra los cinco resultados de la referencia 2. Persiste el aviso del paquete sobre Kotlin Gradle Plugin y futuras versiones de Flutter; no impidió las compilaciones verificadas. El usuario confirmó satisfactoriamente las seis verificaciones manuales de la interfaz, aprobó las etapas 3.3 y 3.4 y autorizó crear el commit y realizar push a `feature/plant-recognition`.
