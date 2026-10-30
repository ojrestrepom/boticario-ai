## ADDED Requirements

### Requirement: Tabla del glosario de actividades
La base SHALL guardar el glosario de la semilla en una tabla neutral `activity_glossary`, con la clave normalizada del término como llave, el término, el texto, la URL de la revisión de la entrada, la fecha de la revisión y la fuente (`source_id`, que apunta a la fuente de Wikcionario del manifiesto), y SHALL añadir a los grupos de uso una columna nula que referencia la clave del término que les corresponde. El esquema SHALL llegar por una migración nueva y la versión del esquema registrada en los metadatos SHALL subir. La tabla y la columna SHALL NOT contener nombres propios de un dataset concreto.

#### Scenario: Esquema ampliado con el glosario
- **WHEN** se inspecciona la base construida desde la semilla
- **THEN** contiene la tabla del glosario y la columna de enlace en los grupos de uso, y la versión del esquema refleja la ampliación

#### Scenario: Fuente del glosario como procedencia
- **WHEN** se construye la base con un glosario cuya fuente es `wiktionary_es`
- **THEN** cada fila del glosario apunta a la fuente `wiktionary_es` de la tabla `source`, con su licencia, su URL de licencia y su atribución tomadas del manifiesto

#### Scenario: Fila del glosario sin fuente
- **WHEN** el glosario trae una fila cuya fuente no figura en el manifiesto
- **THEN** la construcción falla y no produce una base utilizable

#### Scenario: Esquema sin términos de una fuente
- **WHEN** se inspecciona el esquema neutral con la tabla nueva
- **THEN** ninguna tabla ni campo lleva el nombre o la estructura de un dataset concreto

### Requirement: Enlace de cada grupo de uso con su término
La construcción SHALL enlazar un grupo de uso con un término del glosario cuando la forma base de su actividad coincide con la clave del término. La forma base SHALL ser el texto de la actividad antes del primer paréntesis, con mayúsculas y minúsculas igualadas en NFC y los espacios colapsados, sin quitar acentos. Un grupo cuya actividad empieza por «Uso tradicional, sin eficacia demostrada: » SHALL NOT enlazarse. El enlace SHALL depender solo de la semilla y SHALL ser determinista.

#### Scenario: Coincidencia exacta
- **WHEN** un grupo tiene la actividad `Diurético` y el glosario tiene la clave `diurético`
- **THEN** el grupo queda enlazado a ese término

#### Scenario: Actividad con calificador
- **WHEN** un grupo tiene la actividad `Antídoto (escorpión)` y el glosario tiene la clave `antídoto`
- **THEN** el grupo queda enlazado al término `antídoto` y conserva su actividad completa

#### Scenario: Sin acento no coincide
- **WHEN** un grupo tiene la actividad `Tonico` y el glosario solo tiene la clave `tónico`
- **THEN** el grupo no se enlaza, porque la coincidencia no quita acentos

#### Scenario: Fórmula de enfermedad grave
- **WHEN** un grupo tiene la actividad «Uso tradicional, sin eficacia demostrada: cáncer»
- **THEN** el grupo no se enlaza a ningún término

#### Scenario: Actividad sin término
- **WHEN** un grupo tiene la actividad `Fiebre`, que no está en el glosario
- **THEN** la columna de enlace queda nula

#### Scenario: Construcción determinista
- **WHEN** se construye la base dos veces con la misma semilla
- **THEN** el hash del contenido de la base es idéntico

### Requirement: Verificación del glosario
Antes de construir, la construcción SHALL verificar el glosario cuando el manifiesto declara `glossaryHash`: que `glossary.json` exista, que el hash de su contenido coincida, que su número de filas coincida con `glossaryCount`, que las claves sean únicas y que la licencia y la URL de la revisión de cada fila sean válidas (la URL, `https`). La construcción SHALL fallar con un error que lo indica y SHALL NOT acceder a la red.

#### Scenario: Glosario íntegro
- **WHEN** el glosario coincide con el manifiesto
- **THEN** la construcción continúa y escribe la tabla del glosario

#### Scenario: Glosario alterado
- **WHEN** una fila de `glossary.json` cambia sin sellar de nuevo la semilla
- **THEN** la construcción falla indicando que el hash del glosario no coincide y no produce una base utilizable

#### Scenario: Glosario ausente con manifiesto que lo declara
- **WHEN** el manifiesto declara `glossaryHash` y falta `glossary.json`
- **THEN** la construcción falla indicando que falta el glosario

#### Scenario: Semilla sin glosario
- **WHEN** el manifiesto no declara glosario
- **THEN** la construcción continúa con la tabla del glosario vacía y todos los grupos sin enlace
