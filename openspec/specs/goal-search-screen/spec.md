# goal-search-screen Specification

## Purpose

Define P06 como una presentación exclusivamente visual de seis objetivos, sin selección ni resultados de recomendación o comportamiento de producto.

## Requirements

### Requirement: Presentación visual de Buscar por objetivo
P06 SHALL mostrar el título exacto `¿Qué deseas lograr?`, el subtítulo exacto `Selecciona un objetivo principal` y seis filas con iconos Material locales provisionales y chevrons decorativos, en el orden especificado.

#### Scenario: Contenido y orden de las seis filas
- **WHEN** se muestra P06
- **THEN** aparecen las filas, en este orden exacto: `Relajación / Estrés`, `Mejorar el sueño`, `Cuidado de la piel`, `Alivio respiratorio`, `Concentración` y `Otros objetivos`

#### Scenario: Presentación local sin collage
- **WHEN** se renderiza P06
- **THEN** título, subtítulo y filas usan texto vivo e iconos/decoración Material locales provisionales, sin rasterizar la pantalla completa ni usar el collage PNG de mockups, fuentes, paquetes, descargas o dependencias nuevas

### Requirement: Filas de objetivos sin acción ni selección
Las seis filas SHALL ser contenido visual no interactivo: SHALL NOT seleccionar ni resaltar objetivos, declarar semántica de botón/seleccionado/activación, ni producir efectos observables al tocarlas.

#### Scenario: Activación inerte de cada fila
- **WHEN** se toca cualquiera de las seis filas
- **THEN** no cambia la interfaz ni se abre navegación, overlay, diálogo o SnackBar, ni se emiten logs o se registran datos de usuario

#### Scenario: Semántica de contenido no interactivo
- **WHEN** una tecnología de asistencia recorre P06
- **THEN** el texto de cada objetivo se expone como contenido accesible una sola vez, los iconos y chevrons decorativos no duplican la lectura y ninguna fila se expone como botón, seleccionada o con acción de activación

### Requirement: Adaptación accesible de P06
P06 SHALL mantener el contenido esencial legible en 360x640 dp con texto al 100% y 200%, permitir scroll vertical para alcanzar todo el contenido y respetar las zonas seguras, sin recorte, elipsis esencial ni overflow horizontal; sus controles funcionales SHALL ofrecer un área táctil de al menos 48 dp y etiquetas semánticas distinguibles.

#### Scenario: Texto normal y aumentado
- **WHEN** P06 se muestra en 360x640 dp al 100% y al 200% de tamaño de texto
- **THEN** todo el contenido esencial permanece legible y alcanzable mediante scroll vertical, sin recorte, elipsis ni overflow horizontal

#### Scenario: Zonas seguras y controles funcionales accesibles
- **WHEN** P06 se muestra con notch o insets del sistema
- **THEN** la cabecera y barra inferior respetan las zonas seguras; Atrás e Inicio tienen etiquetas semánticas distinguibles y áreas táctiles de al menos 48 dp, sin convertir las filas visuales en controles

### Requirement: Retorno de P06 a Inicio
P06 SHALL ofrecer retorno a Inicio mediante el control Atrás de la app, Atrás del sistema y la pestaña Inicio; SHALL conservar la barra inferior compartida con Inicio seleccionado y las otras tres pestañas sin acción.

#### Scenario: Atrás de app o sistema
- **WHEN** se activa Atrás en la app o el sistema estando en P06
- **THEN** se retorna a Inicio sin abrir otra pantalla

#### Scenario: Pestaña Inicio
- **WHEN** se activa Inicio en la barra inferior de P06
- **THEN** se vuelve a la raíz Inicio y la pila de navegación queda limpia

#### Scenario: Barra inferior compartida
- **WHEN** P06 está visible
- **THEN** la barra muestra Inicio, Favoritos, Historial y Perfil con Inicio seleccionado, y activar Favoritos, Historial o Perfil no cambia ruta, selección ni interfaz

### Requirement: Sin resultados ni comportamiento de producto
La presentación de P06 SHALL NOT ofrecer búsqueda de texto, selección de objetivos, resultados P07, recomendaciones, dosis, eficacia, plantas por objetivo, backend, API, persistencia ni registro de datos de usuario.

#### Scenario: Sin búsqueda ni resultados
- **WHEN** se muestra P06 o se toca una fila
- **THEN** no aparece campo de búsqueda ni resultado, recomendación, P07, dosis, eficacia o planta asociada a un objetivo

#### Scenario: Sin servicios ni persistencia
- **WHEN** el usuario visita P06 o toca sus filas
- **THEN** no se invocan servicios, backend o API ni se registra o persiste información de usuario
