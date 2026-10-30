# Adquisición local de imágenes

## Why

La pantalla /identify ya permite entrar y volver a Inicio, pero sus acciones de cámara y galería están deshabilitadas. Esta etapa permite obtener una imagen local sin reconocer especies ni consultar servicios.

## What Changes

- Incorporar image_picker 1.2.4 y sus dependencias transitivas fijadas en el lockfile.
- Separar adaptador de adquisición, controlador Riverpod y presentación; activar cámara, galería y descarte.
- Conservar la imagen previa ante cancelación o error y mostrar la nueva sin deformación.
- Recuperar una vez por arranque en Android los resultados perdidos, sin navegación automática ni sobrescritura de acciones recientes.
- Actualizar pruebas de adaptador, controlador, vista, smoke, especificaciones y documentación.

## Impact

Solo Flutter, pruebas y documentación del módulo. Sin backend, inferencia, clasificación, historial ni almacenamiento permanente. Se conservan los módulos de catálogo, objetivos y pasaportes, los archivos archivados y .env.cloud-run.example.
