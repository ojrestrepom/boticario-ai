# plant-passport Specification

## Purpose

Define pasaportes locales de plantas que distinguen datos fuente, registros tradicionales y vacíos explícitos sin convertirlos en consejo médico ni promesas de eficacia.

## Requirements

### Requirement: Identidad y composición del pasaporte
El pasaporte SHALL resolver la planta por su identificador contra la API del catálogo y mostrar navegación de regreso, la imagen de cabecera según «Imagen de cabecera con atribución», el nombre principal y el nombre científico según la regla de nombre para mostrar de `catalog-client`, y cuatro pestañas `General`, `Propiedades`, `Usos` y `Fuentes` con `General` inicial. `Fuentes` SHALL ser una pestaña más y SHALL NOT mostrarse bajo el contenido de las otras tres. SHALL mostrar los créditos y la atribución solo como dato neutral de la planta, sin indicar de qué fuente proviene cada campo. SHALL adaptar los campos del mockup a plantas y no presentar un tipo de aceite que la API no entrega.

#### Scenario: Cabecera y pestañas iniciales
- **WHEN** se abre el pasaporte de una planta existente, por ejemplo `lavandula-angustifolia`, cuyo `displayName` es «Lavanda»
- **THEN** muestra «Lavanda» como nombre principal y `Lavandula angustifolia` como secundario, navegación de regreso y las cuatro pestañas `General`, `Propiedades`, `Usos` y `Fuentes` con `General` seleccionada

#### Scenario: Campo de aceite no aplicable
- **WHEN** se consulta el campo de tipo de aceite de una planta cuyo `oil` es `null`, o una ficha cuya planta no tiene aceite registrado
- **THEN** se muestra como no disponible en fuente, sin inferir un aceite ni mostrar `Esencial`

#### Scenario: Planta sin nombre común
- **WHEN** se abre el pasaporte de una planta cuyo `displayName` es su nombre científico
- **THEN** el nombre principal es el científico y no se muestra nombre secundario

#### Scenario: Carga del pasaporte
- **WHEN** la planta se está pidiendo a la API
- **THEN** se muestra un estado de carga con regreso seguro, distinto del de error y del de no encontrada

#### Scenario: Atribución sin procedencia por campo
- **WHEN** se recorren las pestañas `General`, `Propiedades` y `Usos` de una planta con datos de varias fuentes
- **THEN** ningún campo de esas tres pestañas indica el dataset del que viene, y los créditos solo aparecen en la pestaña `Fuentes` y en el pie de la imagen

#### Scenario: Fuentes no se repite bajo las otras pestañas
- **WHEN** el usuario recorre `General`, `Propiedades` y `Usos`
- **THEN** ninguna de las tres muestra créditos, licencias ni entradas de fuentes bajo su contenido

### Requirement: General con vacíos explícitos
La pestaña `General` SHALL mostrar solo campos entregados por la API: `Nombre común` (el nombre para mostrar), `Sinónimos`, `Familia`, `Origen`, `Parte utilizada` (las partes registradas como dato de las fuentes, no como recomendación de parte medicinal), `Tipo de aceite`, `Descripción` y los demás nombres comunes con su idioma. Cada campo sin dato SHALL decirlo explícitamente: los de texto con `No disponible en fuente` y las listas con una frase propia, como `No hay partes registradas en fuente`. SHALL NOT completar vacíos con texto ilustrativo ni con contenido que la API no entrega. Si el nivel de seguridad de la planta es `alto`, `General` SHALL mostrar un aviso con ese nivel que remite a `Propiedades`.

#### Scenario: Campos de P05 presentes
- **WHEN** la planta tiene nombre para mostrar «Lavanda», origen «Mediterráneo», partes «Flores», aceite `Esencial` y descripción
- **THEN** `General` muestra `Nombre común: Lavanda`, `Origen: Mediterráneo`, `Parte utilizada: Flores`, `Tipo de aceite: Esencial` y la descripción

#### Scenario: Datos generales ausentes
- **WHEN** la familia, el origen, el aceite o la descripción de la planta son `null`
- **THEN** cada uno muestra `No disponible en fuente` y no se completa con texto ilustrativo

#### Scenario: Parte registrada
- **WHEN** existe un registro de parte para la identidad exacta
- **THEN** se presenta como dato registrado en la fuente, no como recomendación de uso medicinal

#### Scenario: Familia y nombres comunes
- **WHEN** la planta tiene familia, sinónimos científicos y nombres comunes en varios idiomas
- **THEN** `General` muestra la familia, los sinónimos y cada nombre común con su idioma

#### Scenario: Sin partes ni nombres comunes
- **WHEN** la planta no tiene partes, sinónimos o nombres comunes registrados
- **THEN** `General` indica explícitamente que no hay datos registrados en lugar de omitir el campo en silencio

#### Scenario: Planta sin nombre en español
- **WHEN** el `displayName` de la planta coincide con su nombre científico, por ejemplo `abutilon-theophrasti`, que solo tiene nombres comunes en otros idiomas
- **THEN** `Nombre común` muestra `No hay nombre común en español registrado` y no el nombre científico, y los nombres comunes en otros idiomas siguen en los demás nombres comunes, cada uno con su idioma

#### Scenario: Aviso de nivel alto
- **WHEN** el nivel de precauciones de la planta es `alto`
- **THEN** `General` muestra un aviso con el texto del nivel (no solo un color) y la indicación de ver `Propiedades`

#### Scenario: Sin aviso para otros niveles
- **WHEN** el nivel de precauciones es `medio`, `bajo` o `null`, o la planta no tiene datos de precauciones
- **THEN** `General` no muestra el aviso

#### Scenario: Sin lista de referencias en General
- **WHEN** se abre `General` de una planta con usos y referencias
- **THEN** no muestra una lista de referencias bibliográficas; las citas con su texto completo están en `Usos` y las fuentes en `Fuentes`

### Requirement: Propiedades sin inferencia de eficacia
La pestaña `Propiedades` SHALL mostrar dos secciones: `Objetivos registrados por la EMA` y `Precauciones`. Cada objetivo SHALL mostrar su nombre, su subárea si existe, el área y el tipo de documento de la EMA y la cita de su referencia, con una aclaración fija de que es una clasificación de la Agencia Europea de Medicamentos, no una indicación de uso ni una promesa de eficacia. La pestaña SHALL NOT inferir eficacia ni propiedades medicinales a partir de fitoquímica ni añadir textos propios que describan efectos. Sin objetivos, SHALL decir `No hay objetivos registrados por la EMA para esta planta`.

#### Scenario: Planta con objetivos de la EMA
- **WHEN** la planta tiene el objetivo `cuidado-de-la-piel` con un área y una monografía de la EMA
- **THEN** `Propiedades` lo muestra con su nombre, el área, el tipo de documento, la cita y la aclaración de que es una clasificación y no una indicación

#### Scenario: Objetivo de otros objetivos
- **WHEN** el objetivo es `otros-objetivos` con la subárea de digestión
- **THEN** se muestra el nombre del objetivo junto con la subárea

#### Scenario: Plantas sin evaluación respaldada
- **WHEN** la planta no tiene objetivos (por ejemplo una planta tóxica, o una sin monografía de la EMA)
- **THEN** `Propiedades` comunica `No hay objetivos registrados por la EMA para esta planta`, sin inferir propiedades de su composición química

#### Scenario: Sin lenguaje de eficacia
- **WHEN** se revisan los textos fijos de `Propiedades`
- **THEN** ninguno contiene verbos de efecto ni promesas de eficacia como «calma», «cura» o «ayuda a»

### Requirement: Usos como registros tradicionales trazables
La pestaña `Usos` SHALL mostrar siempre, al inicio, un aviso fijo («Usos registrados en fuentes etnobotánicas históricas. No son recomendaciones ni están comprobados clínicamente. Algunas citas no se pudieron identificar y se muestran como «sin resolver».», texto provisional que el usuario ajustará en la app), también cuando la planta no tiene usos. Después SHALL mostrar los grupos de uso que entrega la API, cada uno con su actividad, la etiqueta `Registro tradicional`, el número de registros, los países si los hay, la aclaración de que es un registro y no un consejo, y la cita de cada una de sus referencias; una referencia sin obra identificada (`resolved` falso) SHALL mostrarse como «(sin resolver)» en un estilo atenuado. Los grupos que entrega la API proceden de la semilla consolidada del catálogo, donde cada actividad está traducida al español y respaldada por la cita de su fuente. Si la planta no tiene usos, SHALL indicar explícitamente que no hay usos tradicionales con referencia verificable disponibles. SHALL NOT completar vacíos desde mockups, desde el cliente ni con contenido que la API no entrega, ni presentar dosis o eficacia, y SHALL NOT añadir lógica propia sobre actividades sensibles: muestra el texto de la actividad tal como llega. Las listas largas SHALL permanecer desplazables y sin truncar.

#### Scenario: Registro tradicional elegible
- **WHEN** la planta tiene un grupo de uso con 12 registros de tres países y dos referencias
- **THEN** el grupo se muestra con su actividad, `12 registros`, los tres países, sus dos citas y la etiqueta de registro tradicional, no consejo

#### Scenario: Aviso fijo de usos tradicionales
- **WHEN** se abre la pestaña `Usos` de cualquier planta, con o sin grupos de uso
- **THEN** el aviso fijo se muestra al inicio, antes del primer grupo o del vacío explícito, y no contiene lenguaje de eficacia

#### Scenario: Cita sin resolver visible
- **WHEN** un grupo de uso trae una referencia resuelta y otra con `resolved` falso y la cita «Woi.Syria (sin resolver)»
- **THEN** el grupo se muestra con ambas citas, la segunda como «(sin resolver)» en un estilo atenuado, y no se oculta el grupo

#### Scenario: Actividades sensibles tal como llegan
- **WHEN** un grupo trae la actividad «Uso tradicional, sin eficacia demostrada: cáncer» y la planta tiene `safety` con una advertencia de riesgo grave (por ejemplo, toxicidad o uso abortivo) en su texto
- **THEN** `Usos` muestra la actividad con ese texto exacto y `Precauciones` muestra la advertencia tal como llega, sin que la app añada, quite ni reformule ninguno

#### Scenario: Grupo sin países
- **WHEN** un grupo de uso no trae países
- **THEN** se muestra sin la línea de países, sin sustituirla por texto

#### Scenario: Sin registro elegible
- **WHEN** la planta no tiene usos
- **THEN** se muestra el vacío explícito y no se inventa contenido

#### Scenario: Muchos usos
- **WHEN** la planta tiene decenas de grupos de uso
- **THEN** todos son alcanzables con desplazamiento, sin truncar ni perder la etiqueta y las citas de cada uno

### Requirement: Acciones no funcionales y retorno seguro
El corazón y `Ver formulaciones relacionadas` SHALL permanecer visibles pero deshabilitados con etiqueta de no disponibilidad; SHALL NOT cambiar estado, persistir datos ni abrir destinos. Si la API responde que la planta no existe, el pasaporte SHALL mostrar `Planta no encontrada` con regreso seguro. Si la petición falla por conexión, tiempo agotado o error del servidor, SHALL mostrar un error de red con una acción `Reintentar` y regreso seguro. Regresar SHALL volver a la pantalla anterior y `Inicio` SHALL volver a Home.

#### Scenario: Acciones no disponibles
- **WHEN** se inspecciona o intenta activar favorito o formulaciones relacionadas
- **THEN** ambas acciones se anuncian no disponibles y no mutan estado ni abren destinos

#### Scenario: Identidad inexistente
- **WHEN** se abre un identificador de planta que la API responde con 404
- **THEN** se informa `Planta no encontrada` y se ofrece regreso seguro sin cierre inesperado

#### Scenario: Error de red reintentable
- **WHEN** no puede obtenerse la ficha por falta de conexión, tiempo agotado o error del servidor
- **THEN** se muestra un estado de error distinto de `Planta no encontrada`, con la acción `Reintentar` que repite la petición y regreso seguro

### Requirement: Accesibilidad del pasaporte
El pasaporte SHALL respetar zonas seguras y conservar texto esencial legible, desplazable y sin truncado a 360x640 dp al 100% y 200%, también con las cuatro pestañas. Los controles, como las pestañas y los botones, SHALL disponer de etiquetas distinguibles y áreas de toque de al menos 48 dp de alto y de ancho, y la selección de una pestaña SHALL expresarse también en la semántica y en el borde, no solo en el relleno. Un enlace en línea, que va dentro de una frase o de una línea de texto, SHALL anunciarse como enlace, con el texto visible y el destino al que lleva (por ejemplo, la página de la fuente o el texto de la licencia), y SHALL distinguirse del texto que lo rodea por algo más que el color. Los enlaces en línea quedan exentos del mínimo de 48 dp, según la excepción de WCAG 2.5.8 para enlaces dentro de una frase. La imagen de la planta SHALL tener una descripción accesible, y el arte local provisional SHALL ocupar su lugar cuando la planta no tiene imagen, mientras carga o si falla la descarga. Los niveles de precauciones SHALL expresarse con texto y no solo con color.

#### Scenario: Ficha accesible con texto aumentado
- **WHEN** se recorre el pasaporte mediante tecnología de asistencia a 100% o 200% en 360x640 dp
- **THEN** los textos y controles esenciales, incluidos las cuatro pestañas, el pie de la imagen, los enlaces y la pestaña `Fuentes`, son legibles, alcanzables, etiquetados y no quedan truncados

#### Scenario: Imagen descrita
- **WHEN** la planta tiene imagen
- **THEN** la tecnología de asistencia anuncia una descripción que incluye el nombre de la planta

#### Scenario: Nivel de precauciones sin depender del color
- **WHEN** se muestra el nivel de precauciones `alto`, `medio` o `bajo`
- **THEN** el nivel se presenta como texto, además de cualquier color

#### Scenario: Pestañas estables al seleccionar
- **WHEN** el usuario elige una pestaña distinta
- **THEN** las cuatro pestañas conservan su posición y su tamaño, y la pestaña elegida se distingue por su relleno, su borde y su semántica de seleccionada

#### Scenario: Enlace en línea accesible
- **WHEN** se inspecciona con tecnología de asistencia un enlace de `Fuentes` o del pie de la imagen
- **THEN** se anuncia como enlace con su texto visible y su destino, sin leer la URL, y no depende solo del color para distinguirse del texto que lo rodea; al ir dentro del texto, no se le exige un área de toque de 48 dp

### Requirement: Imagen de cabecera con atribución
Cuando el detalle trae `image`, el pasaporte SHALL mostrar en la cabecera la miniatura de 500 px de ancho que Wikimedia sirve para `image.url`, no el original, y, visible junto a ella, un pie con la forma «Foto: [autor] · [licencia]», escrito como texto corrido que ocupa a lo sumo dos líneas a 360 dp con texto al 100 %, también cuando `attributionRequired` es falso. El autor SHALL enlazar a la página del archivo (`image.pageUrl`) y la licencia a su texto (`image.licenseUrl`) cuando existe, según «Enlaces en línea sin URL visible». Cuando el autor no está disponible, el pie SHALL conservar un enlace a la página del archivo, nombrando su origen (`Wikimedia Commons`) en lugar del autor. El pie SHALL NOT mostrar la URL como texto. Mientras la imagen carga, si falla la descarga, si no puede construirse la miniatura o si la planta no tiene imagen, el pasaporte SHALL mostrar el arte local provisional, sin recurrir al original, sin atribución de imagen y sin tratarlo como un error de la ficha.

#### Scenario: Imagen con licencia CC BY-SA
- **WHEN** la planta tiene una imagen con autor «J. Pérez», licencia CC BY-SA 4.0 con `licenseUrl` y página en Commons
- **THEN** la cabecera muestra la miniatura de 500 px y el pie «Foto: J. Pérez · CC BY-SA 4.0», con «J. Pérez» enlazado a la página del archivo y «CC BY-SA 4.0» enlazado al texto de la licencia, sin ninguna URL visible

#### Scenario: Imagen sin atribución obligatoria
- **WHEN** la imagen es de dominio público y `attributionRequired` es falso
- **THEN** se muestra igualmente el pie con el autor, la licencia y sus enlaces

#### Scenario: Licencia sin URL
- **WHEN** la imagen tiene licencia pero `licenseUrl` es `null`
- **THEN** el pie muestra la licencia como texto sin enlace y el autor sigue enlazado a la página del archivo

#### Scenario: Autor desconocido
- **WHEN** la imagen no tiene autor
- **THEN** el pie dice «Foto: Wikimedia Commons · [licencia]» con «Wikimedia Commons» enlazado a la página del archivo, de modo que el enlace al archivo no se pierde

#### Scenario: Sin imagen
- **WHEN** la planta no tiene imagen
- **THEN** la cabecera muestra el arte local provisional y no muestra pie de atribución

#### Scenario: Falla la descarga de la imagen
- **WHEN** la imagen no puede descargarse por falta de conexión o por un error del host
- **THEN** la cabecera muestra el arte local provisional, el resto de la ficha se muestra completo y no aparece un error

#### Scenario: Abrir la página del archivo
- **WHEN** el usuario activa el autor del pie
- **THEN** la página del archivo se abre en el navegador del sistema y la app no descarga ni muestra esa página

### Requirement: Precauciones con nivel opcional y citas
La sección `Precauciones` de `Propiedades` SHALL mostrar, cuando la planta tiene `safety`, el nivel (`Alto`, `Medio` o `Bajo`) como texto si existe, el texto de advertencia de la API y la cita de cada referencia. Cuando `safety.level` es `null`, SHALL mostrar el texto y las citas sin etiqueta de nivel. Cuando `safety` es `null`, SHALL decir que no hay precauciones registradas en las fuentes consultadas y que eso no significa que la planta sea segura. SHALL NOT calificar de segura a una planta ni inferir seguridad de la ausencia de datos.

#### Scenario: Precauciones de nivel alto
- **WHEN** la planta tiene `safety` de nivel `alto` con texto y dos referencias
- **THEN** la sección muestra `Alto` como texto, el texto de advertencia y las dos citas

#### Scenario: Precauciones sin nivel
- **WHEN** la planta tiene `safety` con `level` igual a `null`, un texto con las contraindicaciones de la EMA y sus referencias
- **THEN** la sección muestra el texto y las citas sin etiqueta de nivel, `General` no muestra aviso y la sección no dice que no hay datos

#### Scenario: Precauciones sin datos
- **WHEN** `safety` es `null`
- **THEN** la sección dice que no hay precauciones registradas en las fuentes consultadas y que esto no significa que la planta sea segura

#### Scenario: Ninguna planta se presenta como segura
- **WHEN** se revisan todos los textos de la sección para los niveles `alto`, `medio`, `bajo`, sin nivel y sin datos
- **THEN** ninguno afirma que la planta es segura o inocua

### Requirement: Pestaña Fuentes con licencias y atribución
El pasaporte SHALL mostrar una pestaña `Fuentes` que indique que los datos se reúnen de fuentes abiertas y que cada fuente conserva su licencia, con una entrada por cada elemento de `credits` y, si la planta tiene imagen, una entrada de la imagen. Cada entrada de crédito SHALL mostrar el nombre de la fuente, que enlaza a su página (`url`) cuando existe; la licencia como «Licencia: [nombre]», cuyo nombre enlaza al texto de la licencia (`licenseUrl`) cuando existe; y la atribución exigida como texto secundario, más pequeño y gris, sin enlace. La entrada de la imagen SHALL mostrar el autor (o que no está disponible), la licencia con su enlace cuando existe y un enlace a la página del archivo en Commons. La pestaña SHALL NOT mostrar ninguna URL como texto ni indicar qué campo proviene de qué fuente. Sin créditos ni imagen, SHALL decir que no hay fuentes registradas para la planta.

#### Scenario: Fuentes de una planta
- **WHEN** el detalle trae créditos de WCVP (CC BY 3.0), la EMA y Wikipedia (CC BY-SA 4.0) y el usuario abre la pestaña `Fuentes`
- **THEN** lista las tres con su licencia y su atribución, con el nombre de Wikipedia enlazado a su página y «CC BY-SA 4.0» enlazado a su texto, y el texto de licencias mixtas al inicio

#### Scenario: Crédito sin enlaces
- **WHEN** un crédito tiene `url` y `licenseUrl` nulos, como los de la EMA
- **THEN** su nombre y su licencia se muestran como texto sin enlace y su atribución como texto secundario

#### Scenario: Entradas compactas
- **WHEN** se muestra un crédito
- **THEN** el nombre, la licencia y la atribución van en líneas consecutivas, con una separación de a lo sumo 8 dp entre ellas, sin bandas vacías dentro de la entrada

#### Scenario: Atribución como texto secundario
- **WHEN** se muestra un crédito con atribución
- **THEN** la atribución aparece en un texto más pequeño y gris que el nombre y la licencia, sin cortarse a 200% de texto

#### Scenario: Fuentes visibles en cada pestaña
- **WHEN** el usuario cambia entre `General`, `Propiedades`, `Usos` y `Fuentes`
- **THEN** el contenido de `Fuentes` solo se ve con esa pestaña seleccionada y no aparece bajo las otras tres

#### Scenario: Entrada de la imagen
- **WHEN** la planta tiene imagen
- **THEN** `Fuentes` incluye una entrada de la imagen con su autor, su licencia (con enlace si hay `licenseUrl`) y un enlace a la página del archivo, sin URL visible

#### Scenario: Imagen sin autor
- **WHEN** la imagen no tiene autor
- **THEN** la entrada de la imagen dice que el autor no está disponible en fuente y conserva el enlace a la página del archivo

#### Scenario: Sin créditos
- **WHEN** `credits` está vacío y la planta no tiene imagen
- **THEN** `Fuentes` dice que no hay fuentes registradas para esta planta

#### Scenario: Sin procedencia por campo
- **WHEN** se revisa la pestaña `Fuentes`
- **THEN** ninguna entrada indica a qué campo de la ficha corresponde

### Requirement: Enlaces en línea sin URL visible
Los enlaces del pasaporte (nombre de la fuente, nombre de la licencia, autor del pie y página del archivo) SHALL mostrarse como texto enlazado, sin la URL como texto y sin un botón aparte. Activar un enlace SHALL abrir su URL en el navegador del sistema; la app SHALL NOT descargar ni mostrar la página destino. Solo se SHALL abrir una URL `https` con host; una URL que no lo sea SHALL mostrarse como texto sin enlace. Si el navegador no puede abrir el enlace, SHALL mostrarse el aviso «No se pudo abrir el enlace» sin cierre inesperado. Una pulsación larga sobre un enlace SHALL copiar su URL al portapapeles y mostrar un aviso de que se copió.

#### Scenario: Abrir un enlace
- **WHEN** el usuario activa el nombre de una fuente que tiene `url` `https`
- **THEN** la URL se abre en el navegador del sistema y la pantalla no muestra la URL como texto

#### Scenario: Enlace que no se puede abrir
- **WHEN** el sistema no puede abrir la URL de un enlace
- **THEN** se muestra el aviso «No se pudo abrir el enlace» y el pasaporte sigue utilizable

#### Scenario: Copiar con pulsación larga
- **WHEN** el usuario mantiene pulsado un enlace
- **THEN** su URL queda copiada en el portapapeles y se muestra un aviso de confirmación, sin abrir el navegador

#### Scenario: URL que no es https
- **WHEN** un enlace tiene una URL `http` u otro esquema, o sin host
- **THEN** su texto se muestra sin enlace, no se abre y no se puede copiar

#### Scenario: Sin URL
- **WHEN** una fuente o una licencia no tiene URL
- **THEN** su nombre se muestra como texto plano, sin apariencia de enlace
