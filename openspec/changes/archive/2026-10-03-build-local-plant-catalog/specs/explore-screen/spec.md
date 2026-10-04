# Spec Delta

## Purpose

Especifica la exploración local de plantas y aceites con búsqueda y filtros, enlazada únicamente a las fichas de plantas incluidas en este incremento.

## ADDED Requirements

### Requirement: Composición y contenido de Explorar
Explorar SHALL presentar navegación de regreso, el título `Explorar`, búsqueda con sugerencia `Buscar planta o aceite...`, filtros `Todas`, `Plantas` y `Aceites`, y las cinco plantas del catálogo con nombre común editorial y nombre científico de fuente. SHALL usar solo ilustraciones o decoraciones locales provisionales, no fotografías externas.

#### Scenario: Vista inicial
- **WHEN** se abre Explorar por primera vez
- **THEN** se muestran las cinco plantas, `Todas` está seleccionada y cada fila presenta nombre común y científico

#### Scenario: Arte local
- **WHEN** se muestra una fila de planta
- **THEN** su decoración proviene de recursos locales provisionales y no requiere imágenes externas

### Requirement: Búsqueda local y filtros
La búsqueda SHALL actualizar resultados localmente mediante coincidencia de subcadena en nombre común o científico, sin distinguir mayúsculas ni acentos y normalizando espacios exteriores y repetidos. El filtro seleccionado SHALL combinarse con la consulta; `Todas` y `Plantas` incluyen el conjunto fijo y `Aceites` no deriva aceites de plantas.

#### Scenario: Búsqueda por cualquiera de los nombres
- **WHEN** se escribe una subcadena del nombre común o científico con diferencias de mayúsculas, acentos o espacios
- **THEN** se muestran las coincidencias correspondientes de forma reactiva

#### Scenario: Filtro de aceites sin catálogo
- **WHEN** se selecciona `Aceites`
- **THEN** no se muestran plantas como aceites y aparece el estado vacío específico de aceites sin datos

#### Scenario: Filtro y consulta combinados
- **WHEN** hay una consulta activa y se selecciona un filtro
- **THEN** cada resultado satisface simultáneamente la consulta y el filtro

#### Scenario: Borrar conserva filtro
- **WHEN** se borra una consulta mientras un filtro está seleccionado
- **THEN** la consulta queda vacía, se muestran los elementos del filtro y el filtro permanece seleccionado

### Requirement: Estados y navegación de resultados
Explorar SHALL distinguir resultados vacíos de estados de carga y error; el error SHALL permitir reintentar la consulta local. Al seleccionar una fila SHALL abrir el pasaporte de la identidad correcta. Regresar desde una ficha SHALL conservar durante la sesión la consulta, filtro y posición de lista; volver desde Explorar SHALL regresar a Inicio.

#### Scenario: Resultado sin coincidencias
- **WHEN** la consulta no coincide con plantas
- **THEN** se presenta un estado vacío distinto del estado de Aceites sin datos

#### Scenario: Carga del catálogo
- **WHEN** el catálogo local está cargándose
- **THEN** Explorar presenta un estado de carga distinto de resultados vacíos y de error

#### Scenario: Error local reintentable
- **WHEN** no puede cargarse el catálogo
- **THEN** se presenta un estado de error y una acción para reintentar localmente

#### Scenario: Abrir y volver de una ficha
- **WHEN** se abre una planta y se regresa desde su pasaporte
- **THEN** se muestra la ficha correspondiente y se restaura consulta, filtro y posición de lista de esa sesión

#### Scenario: Volver desde Explorar a Inicio
- **WHEN** se activa el chevron de regreso o el botón Atrás de Android desde Explorar
- **THEN** se regresa a Inicio sin quedar en una ruta inexistente

#### Scenario: Volver desde Pasaporte a Explorar
- **WHEN** se activa el chevron de regreso o el botón Atrás de Android desde Pasaporte
- **THEN** se regresa a Explorar con la consulta, filtro y posición de lista conservados en la sesión, sin quedar en una ruta inexistente

### Requirement: Barra inferior en pantallas del catálogo
Explorar y Pasaporte SHALL mostrar la barra con `Inicio` seleccionado; `Inicio` SHALL regresar a Home y `Favoritos`, `Historial` y `Perfil` SHALL estar accesiblemente deshabilitados y no navegar. Esta habilitación acotada no SHALL añadir otras pantallas ni overlays.

#### Scenario: Navegación inferior acotada
- **WHEN** se activa `Inicio` en Explorar o Pasaporte
- **THEN** se regresa a Home; las otras tres pestañas se anuncian deshabilitadas y no cambian la pantalla

#### Scenario: Inicio desde pantallas del catálogo
- **WHEN** se activa `Inicio` desde Explorar o Pasaporte
- **THEN** se llega a Home en la ruta inicial `/` sin dejar la aplicación en una ruta inexistente

### Requirement: Accesibilidad de Explorar
Explorar SHALL respetar zonas seguras, permitir desplazamiento cuando sea necesario y conservar texto esencial legible sin truncado a 360x640 dp con tamaño de texto al 100% y 200%. Cada control SHALL tener etiqueta distinguible y área de toque de al menos 48 dp.

#### Scenario: Texto aumentado y controles accesibles
- **WHEN** se recorre Explorar con tecnología de asistencia a 100% o 200% en 360x640 dp
- **THEN** los textos esenciales son legibles y alcanzables, sin truncado, y los controles tienen etiquetas y áreas de toque de al menos 48 dp
