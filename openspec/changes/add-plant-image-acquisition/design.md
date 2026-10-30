# Diseño

## Componentes

PlantImageSource define pick y recover; PickerPlantImageSource encapsula image_picker, traduce errores, lee imágenes y verifica su decodificación antes de devolver bytes. PlantImageController gestiona imagen, operación pendiente y mensaje mediante un Notifier de Riverpod con origen sustituible. PlantRecognitionPage recibe los mismos callbacks de navegación y observa el estado. BoticarioApp inicializa el controlador una vez; no espera recuperación ni redirige rutas.

## Semántica de acciones

Cancelar devuelve null, conserva la imagen y no produce error. Descartar limpia imagen y mensaje e invalida resultados previos. Abandonar termina la sesión, limpia estado e invalida resultados; no intenta cerrar por la fuerza una aplicación nativa. La exclusión de selección permanece hasta que termine el diálogo nativo anterior, incluso si se vuelve a entrar. Identificadores de sesión evitan que el dispose de una página antigua limpie una sesión nueva.

## Recuperación Android

retrieveLostData se consulta una vez al arrancar solo en Android; su respuesta se consume una vez según el contrato del plugin. Un contador de revisión capturado al programar la recuperación impide que sobrescriba selección, cancelación, descarte o salida posteriores. Se recupera el resultado pendiente, no una imagen anterior de una sesión destruida; no se persisten rutas ni estado de navegación.

## Archivos y presentación

La app utiliza memoria y la caché temporal del plugin, sin copiar a almacenamiento permanente ni borrar originales de galería. El adaptador solicita imágenes de hasta 2048x2048, calidad 90 y sin metadatos completos; rechaza entradas de más de 32 MiB y verifica la decodificación con tamaño reducido. La vista previa usa Image.memory con BoxFit.contain y decodificación acotada. Descartar y salir liberan las referencias propias; no garantizan borrado físico inmediato de la caché o de las cachés internas del motor. No se realiza HTTP ni se envían imágenes.

## Android y permisos

Flutter 3.47.6 y Dart 3.13.5 resuelven image_picker 1.2.4. El mínimo Android es API 24, ya proporcionado por el SDK Flutter. Se conserva singleTop y no se añaden permisos manuales de cámara o almacenamiento ni permission_handler: el plugin delega en actividades del sistema. Los errores de permisos, cámara inexistente, operación concurrente y archivo ilegible tienen mensajes propios sin detalles nativos.

## Validación

Pruebas con origen falso cubren transiciones, carreras, recuperación y ausencia de HTTP. Un ImagePicker sustituido prueba el adaptador, incluido archivo inválido. Pruebas de widget cubren vista previa, reemplazo, cancelación, error, descarte, navegación y texto aumentado. El smoke compartido conserva controles habilitados sin abrir aplicaciones externas. La prueba Android específica utiliza el plugin real y permite cancelar cámara y galería con Atrás del sistema desde el emulador; no necesita backend.

## Referencias

- [image_picker 1.2.4](https://pub.dev/packages/image_picker/versions/1.2.4).
- [Recuperación de actividad](https://pub.dev/documentation/image_picker/latest/image_picker/ImagePicker/retrieveLostData.html).
