# Proposal

## Why

La app solo ofrece hoy Inicio sin navegación funcional, mientras los mockups ya describen Explorar (P04) y Pasaporte digital (P05) pero advierten que sus datos son ilustrativos. Este incremento habilita ese recorrido con un catálogo pequeño, local y trazable, evitando presentar ejemplos o usos tradicionales como evidencia clínica.

## What Changes

- Añadir un catálogo local de cinco plantas basado en el snapshot archivado de USDA Dr Duke (CC0): Lavanda, Eucalipto, Romero, Manzanilla y Menta. Mantener el nombre científico tal como figura en la fuente; conservar los nombres comunes españoles editoriales del mockup sin inferir equivalencias taxonómicas actuales.
- Implementar el flujo acotado Inicio (P03) → Explorar (P04) → Pasaporte (P05), con retorno a la pantalla anterior. Inicio continúa siendo la ruta de arranque `/` y conserva la barra inferior con Inicio seleccionado.
- En Explorar, permitir búsqueda local por nombre común y científico y filtros Todas/Plantas/Aceites. Este incremento solo contiene fichas de plantas: Aceites presenta un estado vacío explícito y no se infieren aceites de las plantas.
- En Pasaporte mostrar únicamente datos respaldados por los registros disponibles, con referencias cuando existan; los campos no sustentados quedan vacíos explícitamente. Etiquetar los usos como registros tradicionales, no recomendaciones. Sin favoritos ni formulaciones funcionales.
- Usar composición del mockup y arte local provisional; no incorporar recursos de internet ni inventar narrativas, origen, dosis o afirmaciones de eficacia.
- Mantener los 11 controles de Inicio y sus mensajes normativos de depuración; el control Explorar además navega. Actualizar las restricciones de navegación y las pruebas que hoy exigen ruta inmóvil.

## Capabilities

### New Capabilities
- `plant-catalog`: catálogo local de plantas y procedencia, datos y referencias trazables.
- `explore-screen`: exploración local, búsqueda, filtros y estado vacío de Aceites.
- `plant-passport`: ficha de planta con datos respaldados, vacíos explícitos y referencias.

### Modified Capabilities
- `home-screen`: el control Explorar abre P04 sin perder su contrato de depuración; delimitar navegación para este único recorrido.
- `flutter-app-bootstrap`: permitir P04/P05 y retorno manteniendo arranque en `/`, sin backend ni solicitudes de negocio; ajustar verificaciones del flujo.

## Impact

- Prerrequisito aprobado: alinear el pin y las instrucciones del toolchain con Flutter 3.47.6 stable/Dart 3.13.5, y validar la compatibilidad baseline antes de implementar el catálogo; no añade funcionalidad de producto.

Impacta `app/` (router, Home, nuevas pantallas y datos locales) y las pruebas unit/widget e integración que actualmente verifican que Home nunca navega. Riverpod y go_router ya están disponibles; no se propone backend, autenticación, acceso de red en runtime, persistencia de usuario ni nuevas dependencias. La fuente de datos es el archivo archivado USDA Dr Duke CC0; no se requiere empaquetar el dataset completo ni añadir imágenes externas. El contenido debe conservar trazabilidad y distinguir limitaciones de referencias incompletas.
