# Proposal

## Why

El repositorio no tiene aún código de aplicación; la Fase 1 del plan de trabajo
exige un incremento verificable. Este cambio crea el andamiaje mínimo
Flutter/Android que valida el toolchain, una ruta inicial y estado demo antes de
construir features del producto.

## What Changes

- Crear la app Android en `app/` con Flutter; package Dart `boticario_ai`;
  organización demo `com.example` (`--org`) y applicationId provisional
  `com.example.boticario_ai`, no identidad de publicación.
- Pantalla inicial en la ruta `/` con `go_router` y Material 3; saludo EXACTO
  `Hola, Boticario AI`.
- Estado contador demo con Riverpod moderno (`Notifier`/`NotifierProvider`, sin
  código generado): inicia en 0 en una nueva instancia/arranque en frío, botón
  Incrementar suma 1, estado en memoria por instancia; no persistente. No es
  feature de producto.
- Dependencias: `flutter_riverpod` y `go_router`.
- Pruebas unit y widget, más un smoke test Android; análisis y lints.
- Fijar un SDK Flutter stable concreto (versión y Dart detallados en design), la
  misma versión en local y CI, y versionar el lockfile de la app.
- CI básico: format, analyze, unit y widget.
- Actualizar el quickstart de docs para reflejar la app real (se hará en apply).
- Android Studio abre `app/` como proyecto (su raíz tiene `pubspec.yaml`), con
  configuración manual de SDK/plugins y un dispositivo Android.

No incluye en este hito: iOS, backend, IA, cámara, persistencia, login, pagos ni
publicación en Play. Estas exclusiones son alcance técnico, no roadmap cancelado.

## Capabilities

### New Capabilities

- `flutter-app-bootstrap`: andamiaje Android con shell mínimo, saludo exacto,
  navegación inicial con `go_router` y estado contador demo con Riverpod.

### Modified Capabilities

Ninguna: no existen capabilities previas en el inventario.

## Impact

- Código nuevo en `app/`.
- Documentación: quickstart del README actualizado en apply.
- Metadatos de SDK/CI e ignores mínimos según lo que genere el scaffold.
- Dependencias: `flutter_riverpod`, `go_router`.
- Toolchain/SDK: prerequisito futuro de apply; su ausencia no autoriza
  instalaciones ni aceptación automática de licencias.
