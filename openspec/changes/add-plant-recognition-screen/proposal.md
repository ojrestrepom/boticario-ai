# Pantalla inicial de reconocimiento de plantas

## Why

Inicio expone «Identificar con cámara» pero todavía no permite abrir el módulo. Esta etapa habilita únicamente su pantalla de entrada.

## What Changes

- Añadir el módulo plant_recognition y la ruta /identify con regreso a Inicio.
- Mostrar un espacio reservado para imagen y las acciones de cámara y galería deshabilitadas con explicación visible.
- Ampliar los contratos de navegación de Inicio y arranque, conservando los mensajes de depuración.
- Actualizar las pruebas y el smoke compartido sin incorporar dependencias, permisos, servicios ni inferencia.

## Impact

Afecta a la presentación, router, pruebas y documentación de Flutter; no modifica backend, catálogo, objetivos ni pasaportes. Los cambios archivados permanecen intactos.
