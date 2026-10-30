## ADDED Requirements

### Requirement: Lectura tolerante de la explicación del término
La app SHALL leer el campo `glossary` de cada grupo de `useGroups` de forma tolerante, como los demás campos que se añadieron al detalle: un campo ausente o `null` equivale a «sin explicación», y uno presente SHALL ser un objeto con `text` (texto no vacío) y `url` (texto, que la app solo abre si es `https`). Un `glossary` presente con otro tipo, o sin `text`, SHALL producir un error de cliente legible sin mostrar datos parciales. La app SHALL NOT escribir, completar ni reformular el texto, y SHALL NOT pedir la entrada de Wikcionario a la red.

#### Scenario: Grupo con explicación
- **WHEN** un grupo llega con `glossary` igual a `{text: "Que aumenta o facilita la producción y excreción de orina.", url: "https://es.wiktionary.org/…"}`
- **THEN** el modelo del grupo conserva el texto y la URL tal como llegan

#### Scenario: Backend anterior
- **WHEN** los grupos de uso no traen `glossary`
- **THEN** la planta se acepta y los grupos quedan sin explicación

#### Scenario: Explicación nula
- **WHEN** un grupo llega con `glossary` igual a `null`
- **THEN** el grupo se acepta sin explicación

#### Scenario: Campo con tipo erróneo
- **WHEN** `glossary` llega como un texto, o como un objeto sin `text`, o con `text` vacío
- **THEN** se produce un error de cliente legible y no se muestran datos parciales

#### Scenario: Grupos derivados de `uses`
- **WHEN** el backend es anterior y los grupos se derivan de `uses`
- **THEN** esos grupos no tienen explicación y la app no la completa desde el cliente
