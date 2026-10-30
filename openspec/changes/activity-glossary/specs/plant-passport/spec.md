## ADDED Requirements

### Requirement: Explicación del término bajo el título del grupo
Cuando un grupo de `Usos` trae `glossary`, la pestaña SHALL mostrar su `text` bajo el título del grupo (la actividad), antes de la línea de datos, como texto secundario (más pequeño y gris que el título), con el encabezado fijo «Según Wikcionario:» y el texto entre comillas angulares tal como llega. Un grupo sin `glossary` SHALL mostrarse sin esa línea y sin sustituto. El encabezado y las comillas SHALL ser los únicos textos propios de la app en la línea, y los textos fijos de la línea SHALL no contener lenguaje de eficacia. La explicación SHALL NOT truncarse a 360x640 dp al 200 % de texto, SHALL NOT mostrar la URL como texto y SHALL formar parte del título del grupo para la tecnología de asistencia. La atribución completa de Wikcionario SHALL estar en `Fuentes`, que ya muestra un crédito por cada elemento de `credits`.

#### Scenario: Grupo con explicación
- **WHEN** el grupo `Diurético` trae `glossary` con el texto «Que aumenta o facilita la producción y excreción de orina.»
- **THEN** bajo el título `Diurético` se lee, en texto secundario, «Según Wikcionario: «Que aumenta o facilita la producción y excreción de orina.»» antes de la línea de datos

#### Scenario: Grupo sin explicación
- **WHEN** el grupo `Fiebre` no trae `glossary`
- **THEN** el grupo muestra el título y la línea de datos, sin línea de explicación ni espacio vacío

#### Scenario: Actividad sensible
- **WHEN** el grupo trae la actividad «Uso tradicional, sin eficacia demostrada: cáncer»
- **THEN** el grupo no muestra explicación y su actividad se muestra tal como llega

#### Scenario: Texto aumentado
- **WHEN** se abre `Usos` a 360x640 dp con 200 % de texto y un grupo con una explicación de dos líneas
- **THEN** la explicación se lee completa, sin truncar y sin desbordar, y el título, la explicación y la línea de datos se anuncian en orden

#### Scenario: Sin URL visible
- **WHEN** se revisa la línea de explicación
- **THEN** no muestra ninguna URL como texto ni oculta el aviso fijo de la pestaña

#### Scenario: Atribución en Fuentes
- **WHEN** la planta tiene grupos con explicación y el usuario abre `Fuentes`
- **THEN** la pestaña lista Wikcionario en español con su licencia CC BY-SA 4.0 enlazada y su atribución, como el resto de los créditos

#### Scenario: Sin lenguaje de eficacia en los textos fijos
- **WHEN** se revisan los textos fijos de la línea de explicación
- **THEN** ninguno contiene verbos de efecto ni promesas de eficacia
