# plant-recognition Specification

## Purpose

Define la pantalla inicial del módulo de reconocimiento, sin adquisición de imágenes ni inferencia.

## Requirements

### Requirement: Pantalla inicial de identificación

La ruta /identify SHALL mostrar «Identificar planta», un espacio reservado «Aquí se mostrará la imagen», las acciones «Tomar fotografía» y «Seleccionar de galería» deshabilitadas y el aviso «Cámara y galería no disponibles por ahora.». SHALL NOT solicitar permisos, adquirir imágenes, realizar peticiones, persistir datos ni mostrar predicciones.

#### Scenario: Pantalla local sin reconocimiento

- **WHEN** el usuario abre /identify
- **THEN** ve el espacio reservado, ambas acciones deshabilitadas y su aviso sin operaciones externas ni resultados simulados

### Requirement: Navegación de regreso

La pantalla SHALL recibir callbacks del router y permitir volver a Inicio mediante Atrás de app, Atrás del sistema y la pestaña Inicio, también al abrir /identify directamente. Inicio SHALL permanecer seleccionado; Favoritos, Historial y Perfil SHALL permanecer inertes.

#### Scenario: Retorno seguro

- **WHEN** se usa cualquiera de los tres mecanismos de regreso desde una entrada por tarjeta o ruta directa
- **THEN** se muestra / sin rutas pendientes de regreso

#### Scenario: Pestañas no disponibles

- **WHEN** se pulsan Favoritos, Historial o Perfil
- **THEN** la ruta sigue siendo /identify y no se abre ninguna pantalla ni overlay

### Requirement: Presentación accesible

La pantalla SHALL conservar Material 3 y la paleta de la app, respetar zonas seguras y exponer los botones como deshabilitados. El contenido SHALL ser alcanzable con scroll en 360x640 dp a 100% y 200% de texto sin recorte ni overflow horizontal, con controles de navegación de al menos 48 dp.

#### Scenario: Texto aumentado

- **WHEN** se renderiza la pantalla al 100% o 200% con insets de sistema
- **THEN** los textos esenciales permanecen íntegros y alcanzables y la barra inferior queda dentro de la zona segura
