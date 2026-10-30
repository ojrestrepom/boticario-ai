## ADDED Requirements

### Requirement: Explicación del término en los grupos de uso
Cada elemento de `useGroups` SHALL incluir siempre el campo `glossary`, que SHALL ser `null` cuando la actividad del grupo no tiene término en el glosario y, si lo tiene, un objeto con `text` (la definición literal que guarda la semilla) y `url` (la URL permanente de la revisión de la entrada de la que sale). El campo SHALL ser aditivo: los demás campos del grupo, su orden y `uses` no cambian. La API SHALL servir el texto tal como está en la base, sin reescribirlo, y SHALL NOT consultar la red.

#### Scenario: Grupo con término
- **WHEN** se pide el detalle de una planta con un grupo de actividad `Diurético`
- **THEN** el grupo lleva `glossary` con `text` igual a «Que aumenta o facilita la producción y excreción de orina.» y `url` igual al enlace permanente de la entrada

#### Scenario: Grupo sin término
- **WHEN** el grupo tiene la actividad `Fiebre` o la fórmula «Uso tradicional, sin eficacia demostrada: cáncer»
- **THEN** `glossary` es `null`

#### Scenario: Actividad con calificador
- **WHEN** el grupo tiene la actividad `Antídoto (escorpión)`
- **THEN** `glossary` trae la definición de `Antídoto` y `activity` conserva el calificador

#### Scenario: Campo aditivo
- **WHEN** un cliente que ignora los campos desconocidos lee `useGroups`
- **THEN** sigue leyendo `activity`, `activitySource`, `count`, `countries` y `references` sin cambios

#### Scenario: Grupo pendiente de revisión
- **WHEN** un grupo tiene `pendingReview` verdadero
- **THEN** el grupo no se sirve y tampoco su explicación

#### Scenario: Documento OpenAPI
- **WHEN** se consulta `/openapi.json`
- **THEN** el esquema del grupo de uso describe `glossary` como un objeto con `text` y `url`, o nulo, y siempre presente

### Requirement: Crédito de Wikcionario
El detalle SHALL incluir en `credits` el crédito de Wikcionario en español, con su licencia CC BY-SA 4.0, su URL de licencia, su atribución y la URL del sitio, si y solo si algún grupo de uso servido de la planta tiene `glossary` no nulo. Las reglas de los créditos (nivel de planta, sin repeticiones, orden por nombre, sin indicar campos) SHALL aplicarse igual.

#### Scenario: Planta con explicaciones
- **WHEN** se pide el detalle de una planta con al menos un grupo con `glossary` no nulo
- **THEN** `credits` incluye Wikcionario en español con la licencia CC BY-SA 4.0 y su `licenseUrl` igual a `https://creativecommons.org/licenses/by-sa/4.0/`, una sola vez

#### Scenario: Planta sin explicaciones
- **WHEN** ningún grupo servido de la planta tiene `glossary`
- **THEN** `credits` no incluye Wikcionario

#### Scenario: Solo grupos pendientes
- **WHEN** los únicos grupos enlazados a un término están pendientes de revisión
- **THEN** `credits` no incluye Wikcionario, porque no se sirve ninguna explicación

#### Scenario: Atribución con los cambios
- **WHEN** se lee el crédito de Wikcionario
- **THEN** su atribución dice que las definiciones se tomaron de Wikcionario, que se les retiró el marcado y las notas y se recortaron a la primera oración, y que el historial de cada entrada lista a sus autores
