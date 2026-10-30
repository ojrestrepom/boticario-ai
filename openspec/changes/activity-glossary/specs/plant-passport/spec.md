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
- **THEN** el aviso fijo del inicio incluye la oración «Las explicaciones de términos son definiciones generales de diccionario o enciclopedia, no afirmaciones sobre esta planta.» y cada explicación lleva la etiqueta «Significado general del término»

#### Scenario: Sin lenguaje de eficacia en los textos fijos
- **WHEN** se revisan los textos fijos de la explicación («Significado general del término», las comillas y «adaptado de»)
- **THEN** ninguno contiene verbos de efecto ni promesas de eficacia

## MODIFIED Requirements

### Requirement: Usos como registros tradicionales trazables
La pestaña `Usos` SHALL mostrar siempre, al inicio, un aviso fijo («Usos registrados en fuentes etnobotánicas históricas. No son recomendaciones ni están comprobados clínicamente. Algunas citas no se pudieron identificar y se muestran como «sin resolver». Las explicaciones de términos son definiciones generales de diccionario o enciclopedia, no afirmaciones sobre esta planta.», texto provisional que el usuario ajustará en la app), también cuando la planta no tiene usos. Después SHALL mostrar los grupos de uso que entrega la API, cada uno compacto: la actividad como título, una sola línea de datos con el número de registros y, si los hay, los países separados por comas (`5 registros · China, Otros lugares, Trinidad`; sin países, solo `5 registros`), y un control para ver las citas. Las citas de las referencias del grupo SHALL estar plegadas por defecto; el control SHALL decir `Ver N citas` (`Ver 1 cita` si es una) y desplegarlas en el mismo sitio, y entonces decir `Ocultar citas` y plegarlas. Desplegadas, cada cita se muestra completa y una referencia sin obra identificada (`resolved` falso) SHALL mostrarse como «(sin resolver)» en un estilo atenuado y en cursiva. El grupo SHALL NOT repetir la etiqueta `Registro tradicional`, el rótulo `Países` ni la aclaración de que es un registro y no un consejo, porque el aviso fijo ya lo dice para toda la pestaña. Cada grupo SHALL conservar su estado de plegado al cambiar de pestaña y volver, y todos SHALL estar plegados al abrir un pasaporte. Los grupos que entrega la API proceden de la semilla consolidada del catálogo, donde cada actividad está traducida al español y respaldada por la cita de su fuente. Si la planta no tiene usos, SHALL indicar explícitamente que no hay usos tradicionales con referencia verificable disponibles. SHALL NOT completar vacíos desde mockups, desde el cliente ni con contenido que la API no entrega, ni presentar dosis o eficacia, ni reescribir los países (un «Otros lugares» genérico se muestra tal cual), y SHALL NOT añadir lógica propia sobre actividades sensibles: muestra el texto de la actividad tal como llega. Las listas largas SHALL permanecer desplazables y sin truncar.

#### Scenario: Registro tradicional elegible
- **WHEN** la planta tiene un grupo de uso con 12 registros de tres países y dos referencias
- **THEN** el grupo se muestra con su actividad como título, la línea `12 registros` con los tres países separados por comas y el control `Ver 2 citas`

#### Scenario: Aviso fijo de usos tradicionales
- **WHEN** se abre la pestaña `Usos` de cualquier planta, con o sin grupos de uso
- **THEN** el aviso fijo, con su oración final sobre las explicaciones de términos, se muestra al inicio, antes del primer grupo o del vacío explícito, y no contiene lenguaje de eficacia

#### Scenario: Citas plegadas por defecto
- **WHEN** se abre la pestaña `Usos` de una planta con grupos de uso
- **THEN** ningún grupo muestra sus citas y cada uno muestra un control `Ver N citas` con el número de sus referencias

#### Scenario: Desplegar y plegar citas
- **WHEN** el usuario pulsa `Ver 5 citas` en un grupo y después `Ocultar citas`
- **THEN** al primer toque las cinco citas se muestran completas en el mismo grupo, sin mover el control, y el control pasa a `Ocultar citas`; al segundo toque las citas se pliegan y el control vuelve a `Ver 5 citas`, sin afectar a los demás grupos

#### Scenario: Estado de plegado al cambiar de pestaña
- **WHEN** el usuario despliega las citas de un grupo, cambia a otra pestaña y vuelve a `Usos`
- **THEN** ese grupo sigue desplegado y los demás siguen plegados; al abrir de nuevo el pasaporte, todos están plegados

#### Scenario: Grupo con una sola cita
- **WHEN** un grupo de uso tiene una sola referencia
- **THEN** el control dice `Ver 1 cita` y, al pulsarlo, se muestra esa cita

#### Scenario: Sin etiqueta ni aclaración por grupo
- **WHEN** se muestra cualquier grupo de uso, plegado o desplegado
- **THEN** no aparece la etiqueta `Registro tradicional`, ni el rótulo `Países`, ni la aclaración `Es un registro, no un consejo de uso.`, y el aviso fijo sigue visible al inicio de la pestaña

#### Scenario: Cita sin resolver visible
- **WHEN** un grupo de uso trae una referencia resuelta y otra con `resolved` falso y la cita «Woi.Syria (sin resolver)», y el usuario despliega las citas
- **THEN** el grupo muestra ambas citas, la segunda como «(sin resolver)» en un estilo atenuado y en cursiva, y no se oculta el grupo

#### Scenario: Actividades sensibles tal como llegan
- **WHEN** un grupo trae la actividad «Uso tradicional, sin eficacia demostrada: cáncer» y la planta tiene `safety` con una advertencia de riesgo grave (por ejemplo, toxicidad o uso abortivo) en su texto
- **THEN** `Usos` muestra la actividad con ese texto exacto y `Precauciones` muestra la advertencia tal como llega, sin que la app añada, quite ni reformule ninguno

#### Scenario: Grupo sin países
- **WHEN** un grupo de uso no trae países
- **THEN** la línea de datos muestra solo el número de registros, sin separador ni texto sustituto

#### Scenario: Países tal como llegan
- **WHEN** un grupo trae los países `China`, `Otros lugares` y `Trinidad`
- **THEN** la línea de datos los muestra en ese orden y con ese texto, sin reescribir `Otros lugares`

#### Scenario: Sin registro elegible
- **WHEN** la planta no tiene usos
- **THEN** se muestra el vacío explícito y no se inventa contenido

#### Scenario: Muchos usos
- **WHEN** la planta tiene decenas de grupos de uso
- **THEN** todos son alcanzables con desplazamiento, sin truncar la actividad, la línea de datos ni el control de cada uno, y al desplegar o plegar un grupo se conserva la posición de desplazamiento
