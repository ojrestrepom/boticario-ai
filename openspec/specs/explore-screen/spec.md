# explore-screen Specification

## Purpose

Especifica la exploración local de plantas y aceites con búsqueda y filtros, enlazada únicamente a las fichas de plantas incluidas en este incremento.

## Requirements

### Requirement: Composición y contenido de Explorar
Explorar SHALL presentar navegación de regreso, el título `Explorar`, búsqueda con sugerencia `Buscar planta o aceite...`, filtros `Todas`, `Plantas` y `Aceites`, y la lista de plantas del catálogo que entrega la API, paginada. Cada fila SHALL mostrar el nombre principal y el secundario según la regla de nombre para mostrar de `catalog-client`: el primer nombre común como principal y el científico como secundario, o solo el científico si la planta no tiene nombre común. SHALL usar solo ilustraciones o decoraciones locales provisionales, no fotografías externas.

#### Scenario: Vista inicial
- **WHEN** se abre Explorar por primera vez con el backend disponible
- **THEN** se muestra la primera página de 50 plantas, `Todas` está seleccionada y cada fila presenta su nombre principal y, si lo hay, el secundario

#### Scenario: Arte local
- **WHEN** se muestra una fila de planta
- **THEN** su decoración proviene de recursos locales provisionales y no requiere imágenes externas

#### Scenario: Planta sin nombre común
- **WHEN** se muestra una planta que no tiene nombres comunes
- **THEN** su fila presenta el nombre científico como principal y no presenta nombre secundario

### Requirement: Búsqueda local y filtros
La búsqueda SHALL delegarse a la API mediante el parámetro `q`: la app solo recorta los espacios exteriores de la consulta y la limita a 200 caracteres, y la API normaliza mayúsculas, acentos y espacios. SHALL esperar unos 300 ms desde la última pulsación antes de pedir resultados y SHALL descartar las respuestas de consultas anteriores, de modo que una respuesta atrasada nunca sustituya a la vigente. Una consulta vacía SHALL listar todo el catálogo. Los filtros `Todas`, `Plantas` y `Aceites` SHALL seguir siendo locales y combinarse con la consulta; `Todas` y `Plantas` muestran las plantas devueltas y `Aceites` no deriva aceites de plantas ni muestra plantas.

#### Scenario: Búsqueda por cualquiera de los nombres
- **WHEN** se escribe una subcadena del nombre común o científico con diferencias de mayúsculas, acentos o espacios
- **THEN** tras el debounce se muestran las coincidencias que devuelve la API para esa consulta

#### Scenario: Filtro de aceites sin catálogo
- **WHEN** se selecciona `Aceites`
- **THEN** no se muestran plantas como aceites y aparece el estado vacío específico de aceites sin datos

#### Scenario: Filtro y consulta combinados
- **WHEN** hay una consulta activa y se selecciona un filtro
- **THEN** cada resultado satisface simultáneamente la consulta y el filtro

#### Scenario: Borrar conserva filtro
- **WHEN** se borra una consulta mientras un filtro está seleccionado
- **THEN** la consulta queda vacía, se muestran los elementos del filtro y el filtro permanece seleccionado

#### Scenario: Debounce de la consulta
- **WHEN** se escriben varios caracteres seguidos con pausas menores a 300 ms
- **THEN** se envía una sola petición con la consulta final

#### Scenario: Respuesta atrasada descartada
- **WHEN** la respuesta de una consulta anterior llega después de haberse escrito una consulta nueva
- **THEN** se descarta y la lista corresponde a la consulta vigente

#### Scenario: Consulta recortada
- **WHEN** la consulta tiene espacios exteriores o más de 200 caracteres
- **THEN** se envía recortada y limitada a 200 caracteres

### Requirement: Estados y navegación de resultados
Explorar SHALL distinguir resultados vacíos de estados de carga y error; el error de red SHALL permitir reintentar la petición. La lista SHALL cargar la página siguiente de forma automática al acercarse al final, con un pie de lista con indicador de carga, y SHALL marcar el fin de la lista cuando se hayan cargado todas las coincidencias. Si falla la carga de más resultados, el pie SHALL mostrar un error reintentable y conservar los elementos ya cargados. Al seleccionar una fila SHALL abrir el pasaporte de la identidad correcta. Regresar desde una ficha SHALL conservar durante la sesión la consulta, filtro y posición de lista; volver desde Explorar SHALL regresar a Inicio.

#### Scenario: Resultado sin coincidencias
- **WHEN** la consulta no coincide con plantas
- **THEN** se presenta un estado vacío distinto del estado de Aceites sin datos

#### Scenario: Carga del catálogo
- **WHEN** la primera página se está pidiendo a la API
- **THEN** Explorar presenta un estado de carga distinto de resultados vacíos y de error

#### Scenario: Error local reintentable
- **WHEN** no puede obtenerse la primera página por falta de conexión, tiempo agotado o error del servidor
- **THEN** se presenta un estado de error de red y una acción `Reintentar` que repite la petición

#### Scenario: Abrir y volver de una ficha
- **WHEN** se abre una planta y se regresa desde su pasaporte
- **THEN** se muestra la ficha correspondiente y se restaura consulta, filtro y posición de lista de esa sesión

#### Scenario: Volver desde Explorar a Inicio
- **WHEN** se activa el chevron de regreso o el botón Atrás de Android desde Explorar
- **THEN** se regresa a Inicio sin quedar en una ruta inexistente

#### Scenario: Volver desde Pasaporte a Explorar
- **WHEN** se activa el chevron de regreso o el botón Atrás de Android desde Pasaporte
- **THEN** se regresa a Explorar con la consulta, filtro y posición de lista conservados en la sesión, sin quedar en una ruta inexistente

#### Scenario: Scroll infinito
- **WHEN** hay más coincidencias que las cargadas y el usuario se acerca al final de la lista
- **THEN** se pide automáticamente la siguiente página de 50, se muestra un indicador de carga en el pie y los nuevos elementos se añaden sin reiniciar la posición

#### Scenario: Fin de la lista
- **WHEN** ya se cargaron todas las coincidencias
- **THEN** no se piden más páginas y el pie indica que no hay más resultados

#### Scenario: Error al cargar más
- **WHEN** falla la petición de una página siguiente
- **THEN** el pie muestra un error con una acción `Reintentar`, los elementos ya cargados permanecen y reintentar pide solo esa página

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
