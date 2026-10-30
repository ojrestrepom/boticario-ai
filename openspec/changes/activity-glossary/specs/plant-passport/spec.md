## ADDED Requirements

### Requirement: Explicación del término bajo el título del grupo
Cuando un grupo de `Usos` trae `glossary`, la pestaña SHALL mostrar bajo el título del grupo (la actividad), antes de la línea de datos, una etiqueta en gris «Significado del término» y debajo, como texto secundario (más pequeño y gris que el título), la línea `<Término>: «<definición>» (<fuente>)`, con el `term` y el `text` tal como llegan, las comillas angulares y el nombre de la fuente (`sourceName`, «Wikcionario» o «Wikipedia») enlazado a la `url` en línea, como en `Fuentes`. Si `adapted` es verdadero, el paréntesis SHALL decir «adaptado de» seguido de la fuente enlazada. Un grupo sin `glossary` SHALL mostrarse sin esa etiqueta ni línea y sin sustituto. La etiqueta, las comillas y «adaptado de» SHALL ser los únicos textos propios de la app en la explicación, y SHALL no contener lenguaje de eficacia. La explicación SHALL NOT truncarse a 360x640 dp al 200 % de texto, SHALL NOT mostrar la URL como texto, SHALL abrir la `url` solo si es `https` y SHALL formar parte del título del grupo para la tecnología de asistencia, con el enlace como elemento accionable de nombre accesible y área táctil suficiente. La atribución completa SHALL estar en `Fuentes`, que ya muestra un crédito por cada elemento de `credits`.

#### Scenario: Grupo con explicación de Wikcionario
- **WHEN** el grupo `Diurético` trae `glossary` con `term` `Diurético`, `text` «Que aumenta o facilita la producción y excreción de orina.», `sourceName` `Wikcionario` y `adapted` falso
- **THEN** bajo el título `Diurético` se lee la etiqueta gris «Significado del término» y debajo «Diurético: «Que aumenta o facilita la producción y excreción de orina.» (Wikcionario)», con «Wikcionario» enlazado a la entrada, antes de la línea de datos

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

#### Scenario: Sin lenguaje de eficacia en los textos fijos
- **WHEN** se revisan los textos fijos de la explicación («Significado del término», las comillas y «adaptado de»)
- **THEN** ninguno contiene verbos de efecto ni promesas de eficacia
