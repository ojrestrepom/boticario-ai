## RENAMED Requirements

- FROM: `### Requirement: Sección Fuentes con licencias y atribución`
- TO: `### Requirement: Pestaña Fuentes con licencias y atribución`

## MODIFIED Requirements

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

## ADDED Requirements

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
