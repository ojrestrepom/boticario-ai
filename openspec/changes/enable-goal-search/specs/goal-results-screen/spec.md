# Spec Delta

## Purpose

Define P07 («Recomendaciones»): la lista de plantas que el catálogo asocia a un objetivo o subárea, con tarjetas cuyo texto sale del registro y no de afirmaciones de eficacia, marca de precaución, estados de carga, error y vacío, y navegación al pasaporte.

## ADDED Requirements

### Requirement: Composición de P07
P07 SHALL mostrar navegación de regreso, el título exacto `Recomendaciones`, el subtítulo `Para: <nombre>` con el nombre del objetivo o de la subárea elegida, la lista de tarjetas, el aviso `Estas recomendaciones se basan en información especializada. Consulta detalles y precauciones.` con un icono informativo, el botón `Ver más detalles` y la barra inferior compartida con Inicio seleccionado. El subtítulo SHALL salir de la respuesta de la API, no del texto que viajó por la navegación.

#### Scenario: Contenido
- **WHEN** se abre P07 para `Relajación / Estrés` con resultados
- **THEN** se ven el título `Recomendaciones`, el subtítulo `Para: Relajación / Estrés`, las tarjetas, el aviso, el botón `Ver más detalles` y la barra inferior

#### Scenario: Subárea
- **WHEN** se abre P07 para la subárea `Digestión`
- **THEN** el subtítulo es `Para: Digestión` y solo hay plantas de esa subárea

#### Scenario: Barra inferior
- **WHEN** P07 está visible
- **THEN** la barra muestra Inicio, Favoritos, Historial y Perfil con Inicio seleccionado, Inicio vuelve a la raíz con la pila limpia y las otras tres no tienen acción

### Requirement: Tarjetas derivadas del registro
Cada tarjeta SHALL mostrar una miniatura, el `displayName` de la planta como nombre principal, el nombre científico como secundario si `displayName` es distinto de él, y la línea `La EMA la registra en: <áreas>` con los nombres en español de las áreas que la API entrega para la planta en ese objetivo o subárea. Si hay más de dos áreas SHALL mostrar dos seguidas de `y N más`. El texto de la tarjeta SHALL NOT incluir verbos ni frases de efecto o eficacia, dosis ni indicaciones, ni textos de ejemplo del mockup, y SHALL NOT completarse con contenido que la API no entregó.

#### Scenario: Tarjeta con un área
- **WHEN** la API devuelve una planta con `areas` igual a `["Estrés mental y trastornos del ánimo"]`
- **THEN** la tarjeta muestra su nombre, su nombre científico y `La EMA la registra en: Estrés mental y trastornos del ánimo`

#### Scenario: Más de dos áreas
- **WHEN** una planta trae cuatro áreas
- **THEN** la línea muestra las dos primeras y `y 2 más`

#### Scenario: Sin lenguaje de eficacia
- **WHEN** se muestra cualquier tarjeta
- **THEN** su texto no contiene `Efecto calmante`, `Ayuda a reducir`, `Promueve` ni ninguna afirmación de efecto, y la única descripción es la línea de la EMA

#### Scenario: Planta sin nombre común
- **WHEN** el `displayName` de la planta es su nombre científico
- **THEN** el nombre principal es el científico y no hay nombre secundario

#### Scenario: Miniatura ausente o fallida
- **WHEN** la planta no tiene `image`, su URL no es HTTPS de un host permitido o la imagen no carga
- **THEN** la tarjeta muestra el arte local provisional, sin atribución de imagen, y la lista sigue siendo utilizable

### Requirement: Miniatura con atribución en la tarjeta
Cuando la planta trae `image` y esta se carga, la tarjeta SHALL mostrarla como miniatura con, visibles junto a ella, el autor y la licencia como texto corto (por ejemplo `Foto: J. Pérez · CC BY-SA 4.0`), también cuando `attributionRequired` es falso. La imagen SHALL cargarse directamente desde el host de Wikimedia permitido por `catalog-client`, sin `Authorization`. El enlace a la página del archivo y el detalle de la licencia SHALL permanecer en el pasaporte (imagen de cabecera y sección `Fuentes`). Mientras carga o si falla, la tarjeta SHALL mostrar el arte local sin atribución.

#### Scenario: Imagen con licencia
- **WHEN** una planta trae `image` con autor «J. Pérez» y licencia `CC BY-SA 4.0` y la imagen carga
- **THEN** la tarjeta muestra la miniatura y `Foto: J. Pérez · CC BY-SA 4.0`

#### Scenario: Imagen de dominio público
- **WHEN** `attributionRequired` es falso
- **THEN** la tarjeta igualmente muestra autor y licencia

#### Scenario: Descarga fallida
- **WHEN** la imagen no puede descargarse
- **THEN** la tarjeta muestra el arte local y no muestra autor ni licencia

#### Scenario: Atribución accesible
- **WHEN** una tecnología de asistencia recorre una tarjeta con imagen
- **THEN** la atribución se lee una vez como parte de la tarjeta y la imagen no duplica la lectura del nombre

### Requirement: Marca de precaución en la tarjeta
La tarjeta SHALL mostrar una marca con texto según el `safetyLevel` y el `hasSafety` de la API: `Precaución` solo si `safetyLevel` es `alto` o `medio`; `Sin datos de precauciones (esto no significa que sea segura)` si `hasSafety` es falso; y ninguna marca si `safetyLevel` es `bajo`, o si es `null` con `hasSafety` verdadero (precauciones sin nivel). La marca SHALL ser texto, no solo color, y formar parte del nombre accesible de la tarjeta. La tarjeta SHALL NOT mostrar el texto de precauciones ni declarar segura a ninguna planta; el detalle y las citas SHALL permanecer en el pasaporte.

#### Scenario: Nivel alto o medio
- **WHEN** una planta trae `safetyLevel` `alto` o `medio`
- **THEN** su tarjeta muestra `Precaución`

#### Scenario: Sin datos
- **WHEN** una planta trae `safetyLevel` `null` y `hasSafety` falso
- **THEN** su tarjeta muestra `Sin datos de precauciones (esto no significa que sea segura)` y ningún texto que la presente como segura

#### Scenario: Nivel bajo
- **WHEN** una planta trae `safetyLevel` `bajo`
- **THEN** su tarjeta no muestra marca de precaución

#### Scenario: Precauciones sin nivel
- **WHEN** una planta trae `safetyLevel` `null` y `hasSafety` verdadero (por ejemplo el eucalipto con contraindicaciones de la EMA sin nivel)
- **THEN** su tarjeta no muestra `Precaución` ni `Sin datos de precauciones`, y su pasaporte muestra el texto en `Precauciones` sin etiqueta de nivel

#### Scenario: Lectura accesible
- **WHEN** una tecnología de asistencia recorre una tarjeta con marca
- **THEN** el nombre accesible incluye nombre, línea de la EMA y la marca

### Requirement: Orden y paginación de los resultados
P07 SHALL listar las plantas en el orden que entrega la API (`displayName`, nombre científico e identificador, sin ranking) y SHALL cargarlas en páginas de 20, pidiendo la siguiente al acercarse al final del scroll, con un pie de carga mientras responde, un error reintentable en el pie que conserve lo ya cargado y un indicador de fin de lista. SHALL descartar las respuestas atrasadas y SHALL NOT repetir ni omitir plantas entre páginas.

#### Scenario: Primera página
- **WHEN** un objetivo tiene más de 20 plantas
- **THEN** P07 muestra las primeras 20 en el orden de la API y carga más al llegar al final

#### Scenario: Fin de lista
- **WHEN** ya se cargaron todas las plantas del `total`
- **THEN** no se piden más páginas y se muestra el fin de lista

#### Scenario: Error al cargar más
- **WHEN** falla la petición de una página siguiente
- **THEN** se conservan las tarjetas cargadas y el pie ofrece `Reintentar`

#### Scenario: Sin sugerir relevancia
- **WHEN** se muestran los resultados
- **THEN** la pantalla no muestra puntuaciones, posiciones ni textos como `Más recomendada`

### Requirement: Estados de P07
P07 SHALL mostrar un estado de carga con etiqueta accesible mientras llega la primera página, un error legible con `Reintentar` si falla (incluido el de no autorizado, sin el token) y, si el objetivo no tiene plantas visibles, el texto `Aún no hay plantas con información registrada para este objetivo`, sin afirmar que ninguna planta sirva para él ni sugerir otras plantas. Si la API responde que el objetivo no existe, SHALL mostrar `Objetivo no encontrado`. El aviso y la barra inferior SHALL permanecer visibles en todos los estados.

#### Scenario: Carga
- **WHEN** la primera página aún no ha llegado
- **THEN** se muestra un indicador con etiqueta accesible y ninguna tarjeta

#### Scenario: Error con reintento
- **WHEN** la primera petición falla
- **THEN** se muestra un error legible con `Reintentar` y al activarlo con el backend disponible aparecen las tarjetas

#### Scenario: Vacío
- **WHEN** la API devuelve cero plantas y total cero
- **THEN** se muestra `Aún no hay plantas con información registrada para este objetivo`

#### Scenario: Objetivo desconocido
- **WHEN** la API responde 404
- **THEN** se muestra `Objetivo no encontrado`, no un error reintentable

#### Scenario: Sin autorización
- **WHEN** la API responde 401
- **THEN** se muestra el error de no autorizado, que no contiene el token

### Requirement: Destino de las tarjetas
Activar una tarjeta SHALL abrir el pasaporte de esa planta por su identificador, apilado sobre P07, y Atrás SHALL volver a P07 con las páginas cargadas y la posición de scroll conservadas. Cada tarjeta SHALL ser un control con área táctil de al menos 48 dp. P07 SHALL NOT registrar qué plantas se abrieron.

#### Scenario: Abrir el pasaporte
- **WHEN** se toca la tarjeta de `lavandula-angustifolia`
- **THEN** se abre el pasaporte de esa planta

#### Scenario: Volver conservando la posición
- **WHEN** el usuario baja por la lista, abre una planta y vuelve con Atrás
- **THEN** P07 muestra las mismas tarjetas en la misma posición, sin recargar la primera página

#### Scenario: Atrás desde el pasaporte hasta Inicio
- **WHEN** el usuario pulsa Atrás sucesivamente desde el pasaporte
- **THEN** vuelve a P07, luego a P06 (o a subáreas y luego a P06) y luego a Inicio

### Requirement: Ver más detalles
El botón `Ver más detalles` SHALL abrir una hoja inferior con el título `Sobre estas recomendaciones` y un texto fijo que explique que las plantas listadas son las que la Agencia Europea de Medicamentos (EMA) registra en el área indicada, que no es un consejo médico ni una dosis, que la marca de precaución señala advertencias de seguridad del registro, que el detalle y las citas están en el pasaporte de cada planta y que se debe consultar a un profesional de la salud. SHALL poder cerrarse y SHALL NOT navegar a otra pantalla, registrar datos ni hacer peticiones.

#### Scenario: Abrir la hoja
- **WHEN** se activa `Ver más detalles`
- **THEN** se abre la hoja `Sobre estas recomendaciones` con el texto de la base y los límites de la información, sin cambiar de ruta

#### Scenario: Cerrar la hoja
- **WHEN** se cierra la hoja con su control, deslizándola o con Atrás del sistema
- **THEN** se vuelve a P07 con su estado intacto

#### Scenario: Sin peticiones ni registro
- **WHEN** se abre y se cierra la hoja
- **THEN** no se hace ninguna petición ni se registra ningún dato de usuario

### Requirement: Adaptación accesible de P07
P07 SHALL mantener el contenido esencial legible en 360x640 dp con texto al 100% y 200%, con scroll vertical, zonas seguras respetadas y sin recorte, elipsis esencial ni overflow horizontal. Atrás, Inicio, las tarjetas, `Ver más detalles` y `Reintentar` SHALL tener áreas táctiles de al menos 48 dp y etiquetas semánticas distinguibles. Las miniaturas y los iconos decorativos SHALL no duplicar la lectura del nombre de la planta.

#### Scenario: Texto aumentado
- **WHEN** P07 se muestra en 360x640 dp al 200% de tamaño de texto con tarjetas, marca y aviso
- **THEN** todo el contenido esencial es legible y alcanzable por scroll, sin recorte ni overflow horizontal

#### Scenario: Controles accesibles
- **WHEN** se inspeccionan los controles de P07
- **THEN** Atrás, Inicio, cada tarjeta, `Ver más detalles` y `Reintentar` miden al menos 48 dp y tienen etiquetas distinguibles
