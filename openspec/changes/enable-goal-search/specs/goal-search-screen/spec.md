# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Presentación visual de Buscar por objetivo`
- TO: `### Requirement: Presentación de Buscar por objetivo`

## MODIFIED Requirements

### Requirement: Presentación de Buscar por objetivo
P06 SHALL mostrar el título exacto `¿Qué deseas lograr?`, el subtítulo exacto `Selecciona un objetivo principal` y una fila por cada objetivo que entrega la API, en el orden que ella define, con un icono Material local provisional elegido por el identificador del objetivo y un chevron decorativo. Con el catálogo de objetivos vigente, las filas son, en este orden: `Relajación / Estrés`, `Mejorar el sueño`, `Cuidado de la piel`, `Alivio respiratorio`, `Cansancio y fatiga` y `Otros objetivos`.

#### Scenario: Contenido y orden de las seis filas
- **WHEN** se muestra P06 con el catálogo de objetivos vigente
- **THEN** aparecen las filas, en este orden exacto: `Relajación / Estrés`, `Mejorar el sueño`, `Cuidado de la piel`, `Alivio respiratorio`, `Cansancio y fatiga` y `Otros objetivos`, y no aparece `Concentración`

#### Scenario: Nombres y orden de la API
- **WHEN** la API devuelve un objetivo con otro nombre o en otra posición
- **THEN** P06 muestra ese nombre y ese orden sin cambios de código en la app

#### Scenario: Objetivo sin icono conocido
- **WHEN** la API devuelve un objetivo cuyo identificador la app no conoce
- **THEN** su fila se muestra con un icono genérico y es igualmente utilizable

#### Scenario: Presentación local sin collage
- **WHEN** se renderiza P06
- **THEN** título, subtítulo y filas usan texto vivo e iconos/decoración Material locales provisionales, sin rasterizar la pantalla completa ni usar el collage PNG de mockups, fuentes, paquetes, descargas o dependencias nuevas

### Requirement: Adaptación accesible de P06
P06 SHALL mantener el contenido esencial legible en 360x640 dp con texto al 100% y 200%, permitir scroll vertical para alcanzar todo el contenido y respetar las zonas seguras, sin recorte, elipsis esencial ni overflow horizontal; sus controles funcionales, incluidas las filas de objetivos, SHALL ofrecer un área táctil de al menos 48 dp y etiquetas semánticas distinguibles.

#### Scenario: Texto normal y aumentado
- **WHEN** P06 se muestra en 360x640 dp al 100% y al 200% de tamaño de texto
- **THEN** todo el contenido esencial permanece legible y alcanzable mediante scroll vertical, sin recorte, elipsis ni overflow horizontal

#### Scenario: Zonas seguras y controles funcionales accesibles
- **WHEN** P06 se muestra con notch o insets del sistema
- **THEN** la cabecera y barra inferior respetan las zonas seguras; Atrás e Inicio tienen etiquetas semánticas distinguibles y áreas táctiles de al menos 48 dp, y cada fila de objetivo es un control con su nombre como etiqueta y un área táctil de al menos 48 dp

## REMOVED Requirements

### Requirement: Filas de objetivos sin acción ni selección
**Reason**: Las filas de P06 pasan a ser controles que abren los resultados de su objetivo. **Migration**: Véase «Filas de objetivos con acción» y «Navegación a resultados» en esta capacidad.

### Requirement: Sin resultados ni comportamiento de producto
**Reason**: P06 ya lleva a los resultados de P07 (capacidad `goal-results-screen`) y consume la API del catálogo; la prohibición de resultados, backend y API deja de ser cierta. **Migration**: Véanse «Catálogo de objetivos desde la API», «Navegación a resultados» y la capacidad `goal-results-screen`. Siguen prohibidos la búsqueda de texto, las dosis, las promesas de eficacia, la persistencia y el registro de datos de usuario.

## ADDED Requirements

### Requirement: Filas de objetivos con acción
Cada fila de objetivo SHALL ser un control que, al activarse, abre los resultados de ese objetivo, o la lista de subáreas si el objetivo las tiene. SHALL exponerse a la tecnología de asistencia como un botón con el nombre del objetivo, una sola vez, con el icono y el chevron decorativos excluidos de la lectura. SHALL NOT quedar seleccionada ni resaltada de forma persistente.

#### Scenario: Activación de una fila sin subáreas
- **WHEN** se toca la fila `Mejorar el sueño`
- **THEN** se abre P07 con el subtítulo `Para: Mejorar el sueño`

#### Scenario: Activación de una fila con subáreas
- **WHEN** se toca la fila `Otros objetivos`
- **THEN** se abre la pantalla de subáreas y no P07

#### Scenario: Semántica de botón
- **WHEN** una tecnología de asistencia recorre P06
- **THEN** cada fila se anuncia como botón con el nombre del objetivo, una sola vez, y los iconos y chevrons no duplican la lectura

#### Scenario: Sin selección persistente
- **WHEN** el usuario vuelve a P06 desde P07
- **THEN** ninguna fila aparece seleccionada o resaltada

### Requirement: Catálogo de objetivos desde la API
P06 SHALL pedir el catálogo de objetivos a la API al abrirse y mostrar un estado de carga con etiqueta accesible mientras responde. Si la petición falla, SHALL mostrar un error legible con la acción `Reintentar` (y, ante un 401, el error de no autorizado del cliente) sin cerrarse inesperadamente. SHALL descartar respuestas atrasadas y SHALL NOT mostrar filas inventadas ni la lista anterior fija en el código. SHALL NOT mostrar conteos de plantas en las filas.

#### Scenario: Carga
- **WHEN** se abre P06 y la API aún no ha respondido
- **THEN** se muestra un indicador de carga con etiqueta accesible, el título y la cabecera, sin filas

#### Scenario: Error con reintento
- **WHEN** la petición del catálogo falla por conexión, tiempo agotado o 5xx
- **THEN** se muestra un error legible con `Reintentar`, y al activarlo con el backend disponible aparecen las filas

#### Scenario: Sin autorización
- **WHEN** la API responde 401
- **THEN** se muestra el error de no autorizado del cliente, que no contiene el token

#### Scenario: Sin conteos
- **WHEN** la API devuelve `plantCount` en los objetivos
- **THEN** las filas no muestran ese número

### Requirement: Pantalla de Otros objetivos
Cuando un objetivo trae subáreas, activar su fila SHALL abrir una pantalla con navegación de regreso, el nombre del objetivo como título y una fila por cada subárea que devuelve la API, con la misma presentación y accesibilidad que las filas de P06. Cada fila SHALL abrir P07 filtrada por esa subárea con el subtítulo `Para: <nombre de la subárea>`. Con el catálogo vigente, las subáreas son `Digestión`, `Vías urinarias y genitales`, `Dolor e inflamación`, `Boca y garganta`, `Circulación` y `Molestias oculares`. Una subárea sin plantas visibles SHALL NOT listarse.

#### Scenario: Lista de subáreas
- **WHEN** se abre la pantalla de `Otros objetivos` con el catálogo vigente
- **THEN** aparecen las subáreas que la API entrega con plantas, en el orden de la API, y cada una es un botón con su nombre

#### Scenario: Abrir una subárea
- **WHEN** se toca la fila `Digestión`
- **THEN** se abre P07 con el subtítulo `Para: Digestión` y las plantas de esa subárea

#### Scenario: Subárea vacía
- **WHEN** la API devuelve una subárea con cero plantas
- **THEN** no aparece en la lista

#### Scenario: Retorno
- **WHEN** se activa Atrás en la app o en el sistema desde la pantalla de subáreas
- **THEN** se vuelve a P06; la pestaña Inicio vuelve a la raíz y deja la pila limpia

#### Scenario: Estados de carga y error
- **WHEN** el catálogo aún carga o falla al abrir la pantalla directamente
- **THEN** se muestran los mismos estados de carga y de error con `Reintentar` que en P06

### Requirement: Navegación a resultados
La navegación SHALL ser Inicio -> P06 -> (subáreas ->) P07 -> pasaporte, apilada, de modo que Atrás vuelva a la pantalla anterior conservando su estado. SHALL NOT registrar ni persistir datos de usuario, ni siquiera el objetivo elegido, y SHALL NOT ofrecer búsqueda de texto en P06. La barra inferior compartida SHALL conservar Inicio seleccionado y las otras tres pestañas sin acción.

#### Scenario: Pila completa
- **WHEN** el usuario recorre Inicio, P06, `Otros objetivos`, `Digestión`, una planta y vuelve con Atrás en cada paso
- **THEN** pasa por el pasaporte, P07, subáreas, P06 e Inicio, en ese orden

#### Scenario: Pestaña Inicio
- **WHEN** se activa Inicio en la barra inferior desde cualquier pantalla del flujo
- **THEN** se vuelve a la raíz Inicio y la pila queda limpia

#### Scenario: Sin datos de usuario
- **WHEN** el usuario elige objetivos y abre plantas
- **THEN** la app no persiste ni registra qué objetivos eligió, y las únicas peticiones son las del catálogo con el token de API

#### Scenario: Otras pestañas sin acción
- **WHEN** se activa Favoritos, Historial o Perfil en P06
- **THEN** no cambia ruta, selección ni interfaz
