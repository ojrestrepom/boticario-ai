# Spec Delta

## ADDED Requirements

### Requirement: Construcción del catálogo desde la semilla
La construcción SHALL leer la semilla versionada del repositorio (`data/seed/`) y escribir la base del catálogo sin acceso a la red y sin invocar a ningún LLM. La semilla SHALL ser la única entrada de datos de la construcción. La construcción SHALL conservar el contrato HTTP vigente: cada planta de la semilla se escribe en las tablas que la API ya lee, y los campos adicionales de la semilla se escriben en tablas nuevas que la API actual no consulta.

#### Scenario: Construcción sin red
- **WHEN** se construye la base con la semilla presente y sin acceso a la red
- **THEN** la construcción termina correctamente y escribe la base del catálogo

#### Scenario: Contenido mapeado a las tablas de la API
- **WHEN** se construye la base desde un registro con nombres comunes, sinónimos, partes y grupos de uso con referencias resueltas
- **THEN** los nombres comunes y los sinónimos científicos están en los nombres de la planta, las partes en sus partes y cada grupo de uso con cada referencia resuelta es un uso con actividad en español, idioma `es` y esa referencia

#### Scenario: Nombre para mostrar explícito
- **WHEN** el registro tiene `displayName` y otros nombres comunes
- **THEN** la base guarda `displayName` en el perfil de la planta (`plant_profile.display_name`) y también como nombre común, sin depender del orden en que la API devuelve los nombres

#### Scenario: Catálogo de objetivos cargado
- **WHEN** se construye la base con `data/seed/goals.json`
- **THEN** la base contiene los objetivos con su etiqueta y posición y sus subáreas, y cada objetivo de una planta apunta a uno de ellos

#### Scenario: Objetivo pendiente de revisión
- **WHEN** un registro tiene un objetivo con `pendingReview` verdadero
- **THEN** la base lo guarda con `pending_review` verdadero y el `reviewFlag` asociado con su `code`, `target` y `message`

#### Scenario: Campos adicionales guardados
- **WHEN** el registro tiene descripción, origen, tipo de aceite, objetivos, seguridad, imagen, alias y `reviewFlags`
- **THEN** la base los conserva en tablas nuevas con su atribución, y las respuestas de `/v1` no cambian de forma

#### Scenario: Uso sin cita resuelta
- **WHEN** un grupo de uso tiene `pendingReview` porque alguna de sus citas está marcada «(sin resolver)» por el LLM
- **THEN** el grupo se conserva en las tablas nuevas con `pending_review` verdadero y su `reviewFlag`, y no genera ningún uso de la API hasta que una revisión humana lo apruebe; esa revisión queda fuera de alcance

### Requirement: Verificación de la semilla
Antes de construir, la construcción SHALL verificar la semilla: que el manifiesto exista, que el hash del contenido de los registros coincida con el del manifiesto, que cada archivo se llame como el `id` de su registro y que el número de plantas coincida. La construcción SHALL fallar con un error que lo indica si alguna verificación no se cumple.

#### Scenario: Semilla íntegra
- **WHEN** el manifiesto y los registros coinciden
- **THEN** la construcción continúa

#### Scenario: Registro alterado
- **WHEN** un registro cambia sin actualizar el manifiesto
- **THEN** la construcción falla indicando que el hash del manifiesto no coincide y no produce una base utilizable

#### Scenario: Semilla ausente
- **WHEN** no existe `data/seed/manifest.json`
- **THEN** la construcción falla indicando que falta la semilla y no accede a la red

## MODIFIED Requirements

### Requirement: Esquema neutral independiente de la fuente
La base de datos del catálogo SHALL seguir un esquema neutral que contenga metadatos con la versión del esquema, fuentes, plantas, nombres de planta con su tipo (científico o común) e idioma, partes, referencias bibliográficas y usos con actividad, idioma y referencia, y, en tablas aparte, los datos consolidados de la semilla: perfil de la planta (nombre para mostrar, autores, origen, descripción, tipo de aceite), grupos de uso con actividad original, número de registros y países, el catálogo de objetivos y subáreas con su etiqueta y posición, los objetivos de cada planta con su subárea, área, evidencia y marca de revisión pendiente, seguridad, imagen con su licencia, alias de IDs anteriores y `reviewFlags`. El esquema SHALL NOT contener tablas, campos ni identificadores propios de un dataset concreto; los identificadores propios de cada fuente SHALL guardarse solo como dato de procedencia. La base que consume la API SHALL contener solo el esquema neutral.

#### Scenario: Esquema sin términos de una fuente
- **WHEN** se inspecciona el esquema neutral
- **THEN** ninguna tabla ni campo lleva el nombre o la estructura de un dataset concreto

#### Scenario: Identificador de fuente como procedencia
- **WHEN** una planta proviene de una fuente que tiene su propio identificador
- **THEN** ese identificador se conserva como dato de procedencia asociado a esa fuente y no como identificador público de la planta

#### Scenario: Base de la API sin tablas de un dataset
- **WHEN** se inspecciona la base que consume la API
- **THEN** no contiene ninguna tabla propia de un dataset, solo las del esquema neutral

#### Scenario: Esquema ampliado
- **WHEN** se inspecciona la base construida desde la semilla
- **THEN** contiene las tablas de perfil, grupos de uso, objetivos, seguridad, imagen, alias y `reviewFlags` estructurados, y la versión del esquema refleja la ampliación

### Requirement: Identificador público estable de planta
Cada planta SHALL tener un identificador público en forma de slug que viene de la semilla, donde se generó una sola vez a partir del nombre aceptado de la planta (véase `catalog-seed`). Ese identificador SHALL NOT ser el de ninguna fuente y SHALL NOT recalcularse al construir la base. Los mismos insumos SHALL producir los mismos identificadores. Una colisión de identificadores entre plantas distintas, o entre un alias y el identificador de otra planta, SHALL tratarse como error de construcción.

#### Scenario: Slug derivado del nombre científico
- **WHEN** el registro de la semilla tiene `id` `salvia-rosmarinus` y nombre científico `Salvia rosmarinus`
- **THEN** el identificador público de la planta es `salvia-rosmarinus`, el mismo que quedó fijado en la semilla al generarla

#### Scenario: Reconstrucción conserva identificadores
- **WHEN** la base se reconstruye con la misma semilla
- **THEN** cada planta conserva el mismo identificador público

#### Scenario: Nombre cambiado sin cambiar el ID
- **WHEN** el registro cambia su nombre científico mostrado y conserva su `id`
- **THEN** el identificador público no cambia

#### Scenario: Colisión de identificadores
- **WHEN** dos registros de la semilla producirían el mismo identificador público
- **THEN** la construcción falla con un error que identifica ambas plantas y no produce una base utilizable

#### Scenario: Alias que coincide con otra planta
- **WHEN** un alias de una planta es igual al identificador de otra
- **THEN** la construcción falla con un error que identifica ambas plantas

### Requirement: Procedencia de cada dato
Todo dato del catálogo (nombre, parte, uso, referencia, objetivo, seguridad, imagen y campo de valor único) SHALL llevar el dataset del que proviene según los refs de la semilla. Las fuentes SHALL registrar su identificador, nombre, versión, licencia, atribución, cita, URL y checksum del insumo, tomados del manifiesto, de modo que cada dato sea trazable hasta su dataset.

#### Scenario: Trazabilidad de un uso
- **WHEN** se consulta un uso de una planta en la base construida
- **THEN** es posible determinar su fuente, la licencia y la cita de esa fuente y la referencia bibliográfica del uso

#### Scenario: Trazabilidad de un objetivo
- **WHEN** se consulta un objetivo de una planta en la base construida
- **THEN** es posible determinar el dataset de la EMA que lo respalda y su licencia

#### Scenario: Dato sin fuente
- **WHEN** se intenta construir la base con un dato que no tiene fuente asociada
- **THEN** la construcción falla y no produce una base utilizable

### Requirement: Construcción determinista
La construcción SHALL ser determinista a partir de la semilla: la misma semilla SHALL producir el mismo contenido lógico, sin marcas de tiempo de construcción. La igualdad se SHALL verificar mediante un hash del contenido lógico ordenado y no del archivo binario.

#### Scenario: Dos construcciones idénticas
- **WHEN** la base se construye dos veces con la misma semilla
- **THEN** el hash del contenido lógico ordenado es idéntico

#### Scenario: Cambio en el insumo
- **WHEN** cambia algún dato de un registro de la semilla y se actualiza el manifiesto
- **THEN** el hash del contenido lógico ordenado es distinto

### Requirement: Verificación del insumo
Antes de leer la semilla, la construcción SHALL verificarla (véase «Verificación de la semilla») y SHALL fallar si no coincide con su manifiesto. La construcción SHALL NOT descargar ningún insumo, y las verificaciones automáticas SHALL poder ejecutarse sin acceso a la red. Las descargas de fuentes son un paso de las herramientas de generación de la semilla, separado de la construcción.

#### Scenario: Insumo íntegro
- **WHEN** la semilla coincide con su manifiesto
- **THEN** la construcción continúa

#### Scenario: Insumo alterado
- **WHEN** un registro no coincide con el hash del manifiesto
- **THEN** la construcción falla con un error que lo indica y no produce una base utilizable

#### Scenario: Insumo ausente
- **WHEN** la semilla no está presente
- **THEN** la construcción falla indicando que falta la semilla y no accede a la red por su cuenta

#### Scenario: Sin acceso a la red
- **WHEN** la construcción se ejecuta sin acceso a la red
- **THEN** termina correctamente y no intenta ninguna conexión

### Requirement: Fallo ante datos inconsistentes
Ante datos inconsistentes, la construcción SHALL fallar con un error claro y SHALL NOT dejar una base parcial utilizable. Son inconsistencias, como mínimo, un ref que no existe en el diccionario del registro, un registro con dos plantas del mismo identificador, un objetivo o subárea fuera del catálogo de objetivos de la semilla, un objetivo o grupo de uso con revisión pendiente sin `reviewFlag` asociado, un nivel de seguridad fuera de alto, medio y bajo, una imagen con una licencia no admitida, un dato sin dataset o licencia y un campo desconocido en el registro.

#### Scenario: Referencia que no resuelve
- **WHEN** un registro cita un ref que no existe en su diccionario
- **THEN** la construcción falla con un error que identifica el registro y el ref y no deja una base utilizable

#### Scenario: Objetivo desconocido
- **WHEN** un registro tiene un objetivo que no está en la lista de objetivos
- **THEN** la construcción falla identificando el registro y el objetivo

#### Scenario: Fallo no deja base parcial
- **WHEN** la construcción falla
- **THEN** no queda en la ubicación de salida una base que parezca válida

### Requirement: Datos sin interpretación clínica
El catálogo SHALL entregar el contenido consolidado de la semilla (descripciones breves, nombres, usos tradicionales con su actividad traducida y su actividad original, objetivos y seguridad) siempre con las citas que lo respaldan, como registros atribuidos y no como recomendaciones. SHALL NOT contener dosis, posologías, indicaciones de tratamiento, consejo ni afirmaciones de eficacia, ni generar propiedades que sus fuentes no registren. El tipo de aceite SHALL poder ser `Esencial` cuando una fuente registra aceite esencial para la planta, y SHALL NOT inferirse de otros registros de partes o sustancias.

#### Scenario: Etiquetas sensibles sin alterar
- **WHEN** la fuente registra una etiqueta de actividad sensible
- **THEN** el catálogo conserva la etiqueta original en el grupo de uso junto con su traducción, sin omitirla ni reinterpretarla

#### Scenario: Sin recomendaciones inventadas
- **WHEN** se construye la base
- **THEN** no hay dosis, recomendaciones ni propiedades que las fuentes del paquete no registren

#### Scenario: Aceite esencial registrado
- **WHEN** el registro tiene `oil` con tipo `Esencial` respaldado por una fuente
- **THEN** la base lo guarda en el perfil de la planta con su referencia

#### Scenario: Aceite no inferido
- **WHEN** una planta tiene una parte llamada «Essential Oil» pero ninguna fuente registra aceite esencial para ella
- **THEN** el perfil no tiene tipo de aceite

## REMOVED Requirements

### Requirement: Contrato de adaptador de fuente
**Reason**: Las fuentes se procesan offline en las herramientas de generación de la semilla; la construcción solo lee la semilla y no necesita adaptadores por dataset.
**Migration**: Las reglas de lectura de cada fuente pasan a `tools/catalog-seed/` y se describen en `catalog-seed`. La construcción consume el formato de la semilla.

### Requirement: Capa cruda y rederivación
**Reason**: La semilla versionada sustituye al ZIP y a `raw.db`; reconstruir la base no necesita volcar datasets crudos. La separación entre la base de la API y los datasets se conserva en «Esquema neutral independiente de la fuente».
**Migration**: Reconstruir con la construcción desde la semilla, sin red. `data/build/raw.db` deja de generarse.

### Requirement: Consolidación multi-fuente con atribución
**Reason**: La unión de fuentes por identidad ocurre ahora en la resolución taxonómica y en la consolidación offline (`catalog-seed`), y su atribución se guarda en los refs de cada registro.
**Migration**: Véanse «Resolución al nombre aceptado», «Regla de colisiones y separación de plantas» y «Licencias y atribución en la semilla» en `catalog-seed`.

### Requirement: Una planta por identidad dentro de cada fuente
**Reason**: Ya no hay adaptadores por fuente. La unicidad de la identidad se garantiza con la unicidad del identificador público en la semilla.
**Migration**: Véase «Identificador público estable de planta» y «Verificación de la semilla».

### Requirement: Resolución de campos de valor único
**Reason**: Los campos de valor único, como la familia, llegan resueltos en el registro de la semilla, con su origen en los refs. La prioridad por fuente configurada deja de existir.
**Migration**: La familia del registro se escribe tal cual, atribuida al dataset de los refs del nombre científico.

### Requirement: Configuración de fuentes activas
**Reason**: `data/sources.toml` y los adaptadores desaparecen; las fuentes y sus versiones se declaran en el manifiesto de la semilla.
**Migration**: Editar las fuentes del manifiesto y regenerar la semilla, según `catalog-seed`.

### Requirement: Adaptador de USDA Dr. Duke
**Reason**: USDA es ahora una de las fuentes de la semilla; su lectura (nombres comunes con idioma, partes, etiquetas de actividad y cruce de ETHNOBOT por sinónimos resueltos) pasa a las herramientas de generación y el cruce exacto por nombre deja de aplicar.
**Migration**: Véanse «Fuentes con versión fija, checksum y licencia», «Resolución al nombre aceptado» y «Paquete por planta determinista» en `catalog-seed`.
