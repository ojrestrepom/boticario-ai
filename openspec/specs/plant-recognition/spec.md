# plant-recognition Specification

## Purpose

Define la adquisición local y temporal de una imagen de planta, sin clasificación ni servicios remotos.

## Requirements

### Requirement: Pantalla inicial de identificación

La ruta /identify SHALL mostrar «Identificar planta», el espacio «Aquí se mostrará la imagen» sin selección y las acciones habilitadas «Tomar fotografía» y «Seleccionar de galería». SHALL usar las aplicaciones nativas mediante un adaptador sustituible y SHALL NOT realizar HTTP, enviar imágenes, clasificar especies, persistir historial ni almacenar imágenes permanentemente.

#### Scenario: Adquirir desde cámara o galería

- **WHEN** el usuario obtiene una imagen válida desde cualquiera de las dos acciones
- **THEN** se muestra en el contenedor existente sin deformación mediante BoxFit.contain y puede reemplazarse o descartarse

### Requirement: Cancelación, descarte y errores

Cancelar una selección SHALL conservar la imagen anterior sin error. Un error recuperable SHALL conservar la imagen y mostrar un mensaje comprensible y accesible; los detalles nativos SHALL NOT mostrarse. «Descartar imagen» SHALL limpiar la selección, el error y cualquier resultado anterior pendiente. La adquisición y validación SHALL completarse antes de reemplazar una imagen válida. SHALL impedir selecciones simultáneas.

#### Scenario: Cancelar o fallar al reemplazar

- **WHEN** se cancela una selección o falla por permisos, cámara, lectura o decodificación
- **THEN** la imagen previa se conserva; solo el fallo muestra un mensaje y permite reintentar

#### Scenario: Descartar

- **WHEN** el usuario pulsa «Descartar imagen»
- **THEN** aparece el espacio reservado y no se aplica ningún resultado anterior pendiente

### Requirement: Recuperación de selección Android

La aplicación SHALL consultar retrieveLostData una sola vez por arranque Android sin bloquear Inicio ni navegar automáticamente. El resultado SHALL quedar disponible para /identify y SHALL NOT sobrescribir una selección, cancelación, descarte o salida posterior. No se garantiza conservar una imagen previa si el proceso es destruido.

#### Scenario: Recuperación tardía

- **WHEN** la recuperación termina después de una nueva acción del usuario
- **THEN** se conserva el estado de la acción reciente y se ignora el resultado antiguo

#### Scenario: Recuperación disponible al entrar

- **WHEN** Android devuelve una selección perdida sin acciones posteriores
- **THEN** se ofrece su imagen al abrir /identify, sin cambiar la ruta durante el arranque

### Requirement: Navegación de regreso

La pantalla SHALL recibir callbacks del router y permitir volver a Inicio mediante Atrás de app, Atrás del sistema y la pestaña Inicio, también al abrir /identify directamente. Inicio SHALL permanecer seleccionado; Favoritos, Historial y Perfil SHALL permanecer inertes. Abandonar SHALL limpiar la selección de la sesión e invalidar sus resultados tardíos; otra sesión SHALL NOT recibirlos.

#### Scenario: Retorno con operación pendiente

- **WHEN** se abandona /identify mientras hay una operación pendiente y se vuelve a entrar
- **THEN** la sesión nueva no recibe la imagen ni el error de la anterior y no permite otro diálogo nativo hasta finalizar el anterior

#### Scenario: Pestañas no disponibles

- **WHEN** se pulsan Favoritos, Historial o Perfil
- **THEN** la ruta sigue siendo /identify y no se abre ninguna pantalla ni overlay

### Requirement: Presentación accesible

La pantalla SHALL conservar Material 3 y la paleta actual, respetar zonas seguras y ofrecer acciones de al menos 48 dp. El contenido SHALL ser alcanzable con scroll en 360x640 a 100% y 200% sin recortes ni overflow horizontal. Los controles de selección SHALL deshabilitarse durante una adquisición, manteniendo disponible la navegación; la imagen SHALL tener etiqueta semántica y los mensajes SHALL anunciarse accesiblemente.

#### Scenario: Texto aumentado y selección pendiente

- **WHEN** se aumenta el texto al 200% o hay una selección pendiente
- **THEN** todo el contenido sigue alcanzable, el estado se comunica y la navegación continúa disponible
