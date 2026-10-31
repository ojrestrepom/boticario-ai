## ADDED Requirements

### Requirement: Explicación del término bajo el título del grupo
Cuando un grupo de `Usos` trae `glossary`, la pestaña SHALL mostrar bajo el título del grupo (la actividad), antes de la línea de datos, una etiqueta en gris «Significado general del término» y debajo, como texto secundario (más pequeño y gris que el título), la línea `<Término>: «<definición>» (<fuente>)`, con el `term` y el `text` tal como llegan, las comillas angulares y el nombre de la fuente (`sourceName`, «Wikcionario» o «Wikipedia») enlazado a la `url` en línea, como en `Fuentes`. Si `adapted` es verdadero, el paréntesis SHALL decir «adaptado de» seguido de la fuente enlazada. Un grupo sin `glossary` SHALL mostrarse sin esa etiqueta ni línea y sin sustituto. La etiqueta, las comillas y «adaptado de» SHALL ser los únicos textos propios de la app en la explicación, y SHALL no contener lenguaje de eficacia. La explicación SHALL NOT truncarse a 360x640 dp al 200 % de texto, SHALL NOT mostrar la URL como texto, SHALL abrir la `url` solo si es `https` y SHALL formar parte del título del grupo para la tecnología de asistencia, con el enlace como elemento accionable de nombre accesible y área táctil suficiente. La atribución completa SHALL estar en `Fuentes`, que ya muestra un crédito por cada elemento de `credits`.

#### Scenario: Grupo con explicación de Wikcionario
- **WHEN** el grupo `Diurético` trae `glossary` con `term` `Diurético`, `text` «Que aumenta o facilita la producción y excreción de orina.», `sourceName` `Wikcionario` y `adapted` falso
- **THEN** bajo el título `Diurético` se lee la etiqueta gris «Significado general del término» y debajo «Diurético: «Que aumenta o facilita la producción y excreción de orina.» (Wikcionario)», con «Wikcionario» enlazado a la entrada, antes de la línea de datos

#### Scenario: Grupo con explicación de Wikipedia
- **WHEN** un grupo trae `glossary` con `sourceName` `Wikipedia` y `adapted` falso
- **THEN** la línea termina en «(Wikipedia)», con «Wikipedia» enlazado al artículo

#### Scenario: Explicación adaptada
- **WHEN** un grupo trae `glossary` con `sourceName` `Wikipedia` y `adapted` verdadero
- **THEN** la línea termina en «(adaptado de Wikipedia)», con «Wikipedia» enlazado a la revisión del artículo

#### Scenario: Actividad con calificador
- **WHEN** el grupo tiene la actividad `Antídoto (escorpión)` y su `glossary` trae `term` `Antídoto`
- **THEN** el título conserva el calificador y la línea de la explicación empieza con «Antídoto:»

#### Scenario: Grupo sin explicación
- **WHEN** el grupo `Fiebre` no trae `glossary`
- **THEN** el grupo muestra el título y la línea de datos, sin etiqueta ni línea de explicación ni espacio vacío

#### Scenario: Actividad sensible
- **WHEN** el grupo trae la actividad «Uso tradicional, sin eficacia demostrada: cáncer»
- **THEN** el grupo no muestra explicación y su actividad se muestra tal como llega

#### Scenario: Texto aumentado
- **WHEN** se abre `Usos` a 360x640 dp con 200 % de texto y un grupo con una explicación larga
- **THEN** la etiqueta y la explicación se leen completas, sin truncar y sin desbordar, y el título, la explicación y la línea de datos se anuncian en orden

#### Scenario: Enlace de la fuente
- **WHEN** el usuario activa el nombre de la fuente de una explicación
- **THEN** la app abre la `url` si es `https`, y no la muestra como texto en la línea

#### Scenario: Atribución en Fuentes
- **WHEN** la planta tiene grupos con explicación y el usuario abre `Fuentes`
- **THEN** la pestaña lista Wikcionario en español, Wikipedia en español o ambas, según corresponda, con su licencia CC BY-SA 4.0 enlazada y su atribución, como el resto de los créditos

#### Scenario: Aclaración de que la explicación es general
- **WHEN** se abre `Usos` de una planta cuyos grupos traen explicación
- **THEN** el aviso fijo, que se lee en el diálogo de la línea «Aviso sobre usos» del inicio, incluye la oración «Las explicaciones de términos son definiciones generales de diccionario o enciclopedia, no afirmaciones sobre esta planta.» y cada explicación lleva la etiqueta «Significado general del término»

#### Scenario: Sin lenguaje de eficacia en los textos fijos
- **WHEN** se revisan los textos fijos de la explicación («Significado general del término», las comillas y «adaptado de»)
- **THEN** ninguno contiene verbos de efecto ni promesas de eficacia

## MODIFIED Requirements

### Requirement: Usos como registros tradicionales trazables
La pestaña `Usos` SHALL mostrar siempre, al inicio, una línea compacta con el icono de advertencia y el rótulo «Aviso sobre usos», también cuando la planta no tiene usos. La línea SHALL ser un solo botón de al menos 48 dp que abre un diálogo titulado «Aviso sobre usos» con el aviso fijo completo («Usos registrados en fuentes etnobotánicas históricas. No son recomendaciones ni están comprobados clínicamente. Algunas citas no se pudieron identificar y se muestran como «sin resolver». Las explicaciones de términos son definiciones generales de diccionario o enciclopedia, no afirmaciones sobre esta planta.», texto provisional que el usuario ajustará en la app) y un botón «Entendido»; el diálogo SHALL cerrarse con ese botón, con Atrás del sistema y tocando fuera, y el texto del aviso SHALL NOT mostrarse en la pestaña fuera del diálogo. Después SHALL mostrar los grupos de uso que entrega la API, cada uno compacto: la actividad como título y, a la derecha del título y en su misma fila, un icono de libro que es el control para ver las citas (`Icons.menu_book_outlined` plegado y `Icons.menu_book` desplegado). El grupo SHALL NOT mostrar línea de datos, ni los países que entrega la API (ni el prefijo `Lugares: ` ni otro texto con ellos), ni el número de registros aunque la API lo envíe; los países siguen en la API y en el modelo, pero la app no los muestra. El número de citas del grupo (`references.length`) SHALL aparecer solo en el texto del control (tooltip), como `Ver N citas` (`Ver 1 cita` si es una). Las citas de las referencias del grupo SHALL estar plegadas por defecto; al tocar el icono se despliegan en el mismo sitio, el tooltip pasa a `Ocultar citas` y el icono a libro abierto, y al volver a tocarlo se pliegan. El icono SHALL medir 20 dp, ser de color verde del pasaporte y tener un área táctil de al menos 48 dp. Desplegadas, cada cita se muestra completa y una referencia sin obra identificada (`resolved` falso) SHALL mostrarse como «(sin resolver)» en un estilo atenuado y en cursiva. El grupo SHALL NOT repetir la etiqueta `Registro tradicional`, el rótulo `Países` ni la aclaración de que es un registro y no un consejo, porque el aviso fijo del diálogo ya lo dice para toda la pestaña. Cada grupo SHALL conservar su estado de plegado al cambiar de pestaña y volver, y todos SHALL estar plegados al abrir un pasaporte. Los grupos que entrega la API proceden de la semilla consolidada del catálogo, donde cada actividad está traducida al español y respaldada por la cita de su fuente. Si la planta no tiene usos, SHALL indicar explícitamente que no hay usos tradicionales con referencia verificable disponibles. SHALL NOT completar vacíos desde mockups, desde el cliente ni con contenido que la API no entrega, ni presentar dosis o eficacia, y SHALL NOT añadir lógica propia sobre actividades sensibles: muestra el texto de la actividad tal como llega. Las listas largas SHALL permanecer desplazables y sin truncar.

#### Scenario: Registro tradicional elegible
- **WHEN** la planta tiene un grupo de uso con 12 registros de tres países y dos referencias
- **THEN** el grupo se muestra con su actividad como título, sin línea de datos ni países y sin ninguna cifra de registros, y el icono de libro a la derecha del título con el texto `Ver 2 citas`

#### Scenario: Aviso fijo de usos tradicionales
- **WHEN** se abre la pestaña `Usos` de cualquier planta, con o sin grupos de uso
- **THEN** la línea «Aviso sobre usos» se muestra al inicio, antes del primer grupo o del vacío explícito, y el texto del aviso no se ve en la pestaña; al tocarla se abre el diálogo «Aviso sobre usos» con el texto completo del aviso fijo, con su oración final sobre las explicaciones de términos y sin lenguaje de eficacia, y se cierra con «Entendido», con Atrás o tocando fuera, sin cambiar la pestaña

#### Scenario: Citas plegadas por defecto
- **WHEN** se abre la pestaña `Usos` de una planta con grupos de uso
- **THEN** ningún grupo muestra sus citas y cada uno muestra un icono de libro cerrado a la derecha del título, con el texto `Ver N citas` y el número de sus referencias

#### Scenario: Desplegar y plegar citas
- **WHEN** el usuario pulsa el icono de libro de un grupo con `Ver 5 citas` y después el mismo icono con `Ocultar citas`
- **THEN** al primer toque las cinco citas se muestran completas en el mismo grupo, sin mover el icono, y el icono pasa a libro abierto con el texto `Ocultar citas`; al segundo toque las citas se pliegan y el icono vuelve a libro cerrado con `Ver 5 citas`, sin afectar a los demás grupos

#### Scenario: Estado de plegado al cambiar de pestaña
- **WHEN** el usuario despliega las citas de un grupo, cambia a otra pestaña y vuelve a `Usos`
- **THEN** ese grupo sigue desplegado y los demás siguen plegados; al abrir de nuevo el pasaporte, todos están plegados

#### Scenario: Grupo con una sola cita
- **WHEN** un grupo de uso tiene una sola referencia
- **THEN** el icono tiene el texto `Ver 1 cita` y, al tocarlo, se muestra esa cita

#### Scenario: Registros y citas distintos
- **WHEN** un grupo de uso llega con `count` 2 y una sola referencia
- **THEN** el grupo muestra solo el icono de citas, con el texto `Ver 1 cita`, y ninguna cifra de registros

#### Scenario: Sin etiqueta ni aclaración por grupo
- **WHEN** se muestra cualquier grupo de uso, plegado o desplegado
- **THEN** no aparece la etiqueta `Registro tradicional`, ni el rótulo `Países`, ni la aclaración `Es un registro, no un consejo de uso.`, y la línea «Aviso sobre usos» sigue al inicio de la pestaña

#### Scenario: Cita sin resolver visible
- **WHEN** un grupo de uso trae una referencia resuelta y otra con `resolved` falso y la cita «Woi.Syria (sin resolver)», y el usuario despliega las citas
- **THEN** el grupo muestra ambas citas, la segunda como «(sin resolver)» en un estilo atenuado y en cursiva, y no se oculta el grupo

#### Scenario: Actividades sensibles tal como llegan
- **WHEN** un grupo trae la actividad «Uso tradicional, sin eficacia demostrada: cáncer» y la planta tiene `safety` con una advertencia de riesgo grave (por ejemplo, toxicidad o uso abortivo) en su texto
- **THEN** `Usos` muestra la actividad con ese texto exacto y `Precauciones` muestra la advertencia tal como llega, sin que la app añada, quite ni reformule ninguno

#### Scenario: Grupo sin países
- **WHEN** un grupo de uso no trae países
- **THEN** el grupo no muestra línea de datos, ni el prefijo `Lugares: ` ni texto sustituto, y conserva su título y el icono de citas

#### Scenario: Países tal como llegan
- **WHEN** un grupo trae los países `China`, `Otros lugares` y `Trinidad`
- **THEN** el grupo no muestra ninguno de ellos ni el prefijo `Lugares: `, y sigue mostrando su título y el icono de citas

#### Scenario: Sin registro elegible
- **WHEN** la planta no tiene usos
- **THEN** se muestra el vacío explícito y no se inventa contenido

#### Scenario: Muchos usos
- **WHEN** la planta tiene decenas de grupos de uso
- **THEN** todos son alcanzables con desplazamiento, sin truncar la actividad ni el icono de citas de cada uno, y al desplegar o plegar un grupo se conserva la posición de desplazamiento

### Requirement: Accesibilidad del pasaporte
El pasaporte SHALL respetar zonas seguras y conservar texto esencial legible, desplazable y sin truncado a 360x640 dp al 100% y 200%, también con las cuatro pestañas. Los controles, como las pestañas y los botones, SHALL disponer de etiquetas distinguibles y áreas de toque de al menos 48 dp de alto y de ancho, y la selección de una pestaña SHALL expresarse también en la semántica y en el borde, no solo en el relleno. La línea «Aviso sobre usos» de `Usos` SHALL ser un solo botón con esa área de toque, con la etiqueta «Aviso sobre usos» y semántica de botón, y el diálogo que abre SHALL tener ese título, mostrar el texto completo sin truncar (desplazable si no cabe) y cerrarse con «Entendido», con Atrás y tocando fuera, también a 200 % de texto en 360x640 dp. El control que pliega y despliega las citas de un grupo de `Usos` SHALL ser un botón de icono de libro con esa área de toque, SHALL expresar en su semántica si está expandido o plegado, y su etiqueta SHALL incluir el texto del control (`Ver N citas` u `Ocultar citas`) y la actividad del grupo, de modo que la tecnología de asistencia anuncie el número de citas y distinga los grupos entre sí; el texto SHALL verse como tooltip al mantener pulsado o al pasar el puntero, y el estado SHALL expresarse también en el icono (libro cerrado o abierto), no solo en el color. Un enlace en línea, que va dentro de una frase o de una línea de texto, SHALL anunciarse como enlace, con el texto visible y el destino al que lleva (por ejemplo, la página de la fuente o el texto de la licencia), y SHALL distinguirse del texto que lo rodea por algo más que el color. Los enlaces en línea quedan exentos del mínimo de 48 dp, según la excepción de WCAG 2.5.8 para enlaces dentro de una frase. La imagen de la planta SHALL tener una descripción accesible, y el arte local provisional SHALL ocupar su lugar cuando la planta no tiene imagen, mientras carga o si falla la descarga. Los niveles de precauciones SHALL expresarse con texto y no solo con color.

#### Scenario: Ficha accesible con texto aumentado
- **WHEN** se recorre el pasaporte mediante tecnología de asistencia a 100% o 200% en 360x640 dp
- **THEN** los textos y controles esenciales, incluidos las cuatro pestañas, el pie de la imagen, los enlaces, la pestaña `Fuentes` y los controles de citas de `Usos`, son legibles, alcanzables, etiquetados y no quedan truncados

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

#### Scenario: Control de citas accesible
- **WHEN** se inspecciona con tecnología de asistencia el control de citas de un grupo de `Usos`, plegado y desplegado
- **THEN** se anuncia como botón con su estado de plegado o expandido, su etiqueta contiene el texto del control (`Ver 5 citas`, `Ocultar citas`) y la actividad del grupo, el icono queda a la derecha del título, y su área de toque es de al menos 48 dp de alto y de ancho, también a 200 % de texto en 360x640 dp

#### Scenario: Línea de aviso de usos accesible
- **WHEN** se inspecciona con tecnología de asistencia la línea «Aviso sobre usos» y se abre su diálogo, a 100 % y 200 % de texto en 360x640 dp
- **THEN** la línea se anuncia como un solo botón con la etiqueta «Aviso sobre usos» y un área de toque de al menos 48 dp de alto y de ancho, y el diálogo muestra su título y el texto completo sin truncar, con el botón «Entendido» alcanzable
