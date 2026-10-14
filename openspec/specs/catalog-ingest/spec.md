# catalog-ingest Specification

## Purpose
Define cómo se construye la base de datos del catálogo a partir de uno o varios datasets mediante adaptadores de fuente, con un esquema neutral, procedencia de cada dato y construcción determinista, de modo que el dataset sea intercambiable sin afectar a quien consume la base.

## Requirements

### Requirement: Contrato de adaptador de fuente
Cada dataset SHALL integrarse mediante un adaptador de fuente con dos responsabilidades: declarar cómo se importa el dataset crudo (archivos y codificación) y derivar, a partir de las tablas crudas importadas, registros normalizados de plantas, nombres, partes y usos con su referencia bibliográfica. El adaptador SHALL declarar los metadatos de su fuente (identificador, nombre, versión, licencia, cita, URL y checksum del insumo). El proceso de construcción SHALL consumir a los adaptadores solo a través de ese contrato y SHALL NOT requerir conocimiento específico de ninguna fuente fuera de su adaptador.

#### Scenario: Adaptador conforme
- **WHEN** un adaptador declara todos los metadatos de su fuente, su importación cruda y su derivación
- **THEN** el proceso de construcción importa y consolida sus registros sin lógica específica de esa fuente

#### Scenario: Derivación desde tablas crudas
- **WHEN** un adaptador deriva sus registros normalizados
- **THEN** lee únicamente las tablas crudas importadas de su fuente y no accede al insumo original

#### Scenario: Metadatos de fuente incompletos
- **WHEN** un adaptador omite alguno de los metadatos obligatorios de su fuente
- **THEN** la construcción falla con un error que identifica la fuente y el metadato ausente, y no produce una base utilizable

### Requirement: Capa cruda y rederivación
La construcción SHALL conservar cada dataset importado tal como viene, separado de la base neutral. La base neutral SHALL poder reconstruirse desde la capa cruda sin descargar de nuevo el insumo. La base que consume la API SHALL contener solo el esquema neutral.

#### Scenario: Rederivación sin red
- **WHEN** la capa cruda ya contiene los datasets importados y se reconstruye la base neutral sin acceso a la red
- **THEN** la reconstrucción termina correctamente con el mismo contenido lógico que la construcción original

#### Scenario: Dataset conservado sin transformar
- **WHEN** se importa un dataset
- **THEN** la capa cruda conserva todas sus tablas, filas y columnas con los valores originales, sin normalizarlos ni descartarlos

#### Scenario: Base de la API sin tablas de un dataset
- **WHEN** se inspecciona la base que consume la API
- **THEN** no contiene ninguna tabla propia de un dataset, solo las del esquema neutral

#### Scenario: Esquema neutral ampliado
- **WHEN** el esquema neutral incorpora un concepto nuevo y se reconstruye desde la capa cruda
- **THEN** la base neutral lo incluye sin volver a descargar ni cruzar los datos a mano

### Requirement: Esquema neutral independiente de la fuente
La base de datos del catálogo SHALL seguir un esquema neutral que contenga metadatos con la versión del esquema, fuentes, plantas, nombres de planta con su tipo (científico o común) e idioma, partes, referencias bibliográficas y usos con actividad, idioma y referencia. El esquema SHALL NOT contener tablas, campos ni identificadores propios de un dataset concreto; los identificadores propios de cada fuente SHALL guardarse solo como dato de procedencia.

#### Scenario: Esquema sin términos de una fuente
- **WHEN** se inspecciona el esquema neutral
- **THEN** ninguna tabla ni campo lleva el nombre o la estructura de un dataset concreto

#### Scenario: Identificador de fuente como procedencia
- **WHEN** una planta proviene de una fuente que tiene su propio identificador
- **THEN** ese identificador se conserva como dato de procedencia asociado a esa fuente y no como identificador público de la planta

### Requirement: Consolidación multi-fuente con atribución
La construcción SHALL unir los registros de todas las fuentes activas por identidad canónica de planta, definida como el nombre científico normalizado. Los datos multivalor (nombres, partes y usos) SHALL sumarse conservando la fuente de cada uno. Los datos repetidos aportados por varias fuentes SHALL conservar la atribución de cada fuente.

#### Scenario: Dos fuentes aportan a la misma planta
- **WHEN** dos fuentes entregan registros de una planta con el mismo nombre científico normalizado
- **THEN** la base contiene una sola planta con la unión de los nombres, partes y usos de ambas, y cada dato indica de qué fuente proviene

#### Scenario: Dato idéntico en dos fuentes
- **WHEN** dos fuentes aportan un mismo dato multivalor para una planta
- **THEN** la atribución registra ambas fuentes y el dato no se interpreta como proveniente de una sola

#### Scenario: Planta aportada por una sola fuente
- **WHEN** una planta aparece solo en una de las fuentes
- **THEN** la base la incluye con todos sus datos atribuidos a esa fuente

### Requirement: Una planta por identidad dentro de cada fuente
Un adaptador SHALL entregar como máximo una planta por identidad canónica. Una identidad repetida dentro de la misma fuente SHALL tratarse como error de construcción que identifica ambos registros.

#### Scenario: Identidad repetida en una fuente
- **WHEN** una fuente entrega dos registros de planta con la misma identidad canónica
- **THEN** la construcción falla con un error que identifica ambos registros y no produce una base utilizable

#### Scenario: Misma identidad en fuentes distintas
- **WHEN** dos fuentes distintas entregan una planta con la misma identidad canónica
- **THEN** no es un error y se consolidan como una sola planta

### Requirement: Resolución de campos de valor único
Cuando varias fuentes aporten un valor distinto para un campo de valor único de una planta, como la familia, la consolidación SHALL elegir el valor de la fuente de mayor prioridad según la configuración de fuentes y SHALL registrar cuál fuente fue la elegida. El resultado SHALL NOT depender del orden en que se procesen las fuentes.

#### Scenario: Conflicto resuelto por prioridad
- **WHEN** dos fuentes aportan familias distintas para la misma planta
- **THEN** la base conserva la familia de la fuente de mayor prioridad y registra esa fuente como su origen

#### Scenario: Un solo valor disponible
- **WHEN** solo una fuente aporta valor para un campo de valor único
- **THEN** la base conserva ese valor y lo atribuye a esa fuente, sin importar su prioridad

#### Scenario: Valor ausente
- **WHEN** ninguna fuente aporta valor para un campo de valor único
- **THEN** el campo queda ausente y no se inventa ningún valor

### Requirement: Configuración de fuentes activas
La construcción SHALL tomar de una configuración explícita las fuentes activas y la prioridad de cada una. Añadir, quitar o reordenar fuentes SHALL lograrse editando esa configuración y reconstruyendo la base, sin cambiar el esquema ni la API.

#### Scenario: Fuente intercambiada
- **WHEN** la configuración activa una fuente distinta de la anterior y se reconstruye la base
- **THEN** la base resultante cumple el mismo esquema neutral y contiene solo datos de la fuente activa

#### Scenario: Fuente desconocida en la configuración
- **WHEN** la configuración nombra una fuente para la que no existe adaptador
- **THEN** la construcción falla con un error que identifica esa fuente

### Requirement: Identificador público estable de planta
Cada planta SHALL tener un identificador público en forma de slug derivado de su nombre científico canónico. Ese identificador SHALL NOT ser el de ninguna fuente. Los mismos insumos y la misma configuración SHALL producir los mismos identificadores. Una colisión de identificadores entre plantas distintas SHALL tratarse como error de construcción.

#### Scenario: Slug derivado del nombre científico
- **WHEN** entra una planta con nombre científico `Lavandula angustifolia`
- **THEN** su identificador público es `lavandula-angustifolia`

#### Scenario: Reconstrucción conserva identificadores
- **WHEN** la base se reconstruye con los mismos insumos y la misma configuración
- **THEN** cada planta conserva el mismo identificador público

#### Scenario: Colisión de identificadores
- **WHEN** dos plantas distintas producirían el mismo identificador público
- **THEN** la construcción falla con un error que identifica ambas plantas y no produce una base utilizable

### Requirement: Procedencia de cada dato
Todo dato del catálogo (nombre, parte, uso, referencia y campo de valor único) SHALL llevar la fuente de la que proviene. Las fuentes SHALL registrar su identificador, nombre, versión, licencia, cita, URL y checksum del insumo, de modo que cada dato sea trazable hasta su dataset.

#### Scenario: Trazabilidad de un uso
- **WHEN** se consulta un uso de una planta en la base construida
- **THEN** es posible determinar su fuente, la licencia y la cita de esa fuente y la referencia bibliográfica del uso

#### Scenario: Dato sin fuente
- **WHEN** se intenta construir la base con un dato que no tiene fuente asociada
- **THEN** la construcción falla y no produce una base utilizable

### Requirement: Versión de esquema de la base
La base de datos SHALL registrar la versión de su esquema en sus metadatos, de modo que los consumidores puedan verificar su compatibilidad.

#### Scenario: Versión registrada
- **WHEN** se construye la base
- **THEN** sus metadatos contienen la versión del esquema con el que se construyó

### Requirement: Construcción determinista
La construcción SHALL ser determinista: los mismos insumos y la misma configuración SHALL producir el mismo contenido lógico, sin marcas de tiempo de construcción. La igualdad se SHALL verificar mediante un hash del contenido lógico ordenado y no del archivo binario.

#### Scenario: Dos construcciones idénticas
- **WHEN** la base se construye dos veces con los mismos insumos y la misma configuración
- **THEN** el hash del contenido lógico ordenado es idéntico

#### Scenario: Cambio en el insumo
- **WHEN** cambia algún dato del insumo
- **THEN** el hash del contenido lógico ordenado es distinto

### Requirement: Verificación del insumo
Antes de leer un insumo descargado, la construcción SHALL verificar su tamaño y checksum contra los valores declarados por el adaptador y SHALL fallar si no coinciden. La descarga del insumo SHALL ser un paso explícito y separado de la construcción, y las verificaciones automáticas SHALL poder ejecutarse sin acceso a la red.

#### Scenario: Insumo íntegro
- **WHEN** el insumo coincide con el tamaño y el checksum declarados
- **THEN** la construcción continúa

#### Scenario: Insumo alterado
- **WHEN** el insumo no coincide con el checksum o el tamaño declarados
- **THEN** la construcción falla con un error que lo indica y no produce una base utilizable

#### Scenario: Insumo ausente
- **WHEN** el insumo no ha sido descargado
- **THEN** la construcción falla indicando el paso de descarga necesario y no accede a la red por su cuenta

### Requirement: Fallo ante datos inconsistentes
Ante datos inconsistentes, la construcción SHALL fallar con un error claro y SHALL NOT dejar una base parcial utilizable. Son inconsistencias, como mínimo, un uso cuya referencia no resuelve, una parte o un uso que apunta a una planta inexistente y una referencia duplicada con contenido distinto.

#### Scenario: Referencia que no resuelve
- **WHEN** un registro normalizado entrega un uso con una referencia bibliográfica inexistente
- **THEN** la construcción falla con un error que identifica el registro y no deja una base utilizable

#### Scenario: Fallo no deja base parcial
- **WHEN** la construcción falla
- **THEN** no queda en la ubicación de salida una base que parezca válida

### Requirement: Adaptador de USDA Dr. Duke
El adaptador de USDA Dr. Duke SHALL declarar los metadatos del dataset archivado (versión, licencia CC0, cita, URL, tamaño y checksum del archivo) tomados de la guía de procedencia del repositorio. SHALL entregar todas las plantas del dataset con su nombre científico literal y los nombres comunes que trae el dataset marcados con su idioma, las etiquetas de parte y de actividad tal como aparecen, sin traducirlas, y SHALL aplicar los criterios de curación documentados: identidad exacta por género, especie y taxón, y referencia bibliográfica resoluble de forma inequívoca. SHALL NOT incluir traducciones ni nombres editoriales.

#### Scenario: Planta con usos elegibles
- **WHEN** una planta del dataset tiene registros de uso con identidad exacta y referencia resoluble
- **THEN** la base contiene esos usos con la actividad literal en inglés y la cita completa de su referencia

#### Scenario: Uso excluido
- **WHEN** un registro de uso del dataset no coincide exactamente con la identidad de la planta o su referencia falta o no resuelve de forma inequívoca
- **THEN** ese uso no se incluye en la base

#### Scenario: Planta sin usos elegibles
- **WHEN** una planta del dataset no tiene usos elegibles
- **THEN** la base la incluye con una lista de usos vacía y sin inventar contenido

### Requirement: Datos sin interpretación clínica
El catálogo SHALL entregar los usos y las etiquetas de actividad tal como los registra la fuente, como registros atribuidos y no como recomendaciones, dosis, consejo o afirmaciones de eficacia. SHALL NOT convertir registros de partes o sustancias en fichas de aceites esenciales.

#### Scenario: Etiquetas sensibles sin alterar
- **WHEN** la fuente registra una etiqueta de actividad sensible
- **THEN** la base la conserva literalmente, sin omitirla, reinterpretarla ni reetiquetarla

#### Scenario: Sin recomendaciones inventadas
- **WHEN** se construye la base
- **THEN** no se generan dosis, recomendaciones ni propiedades que la fuente no registre
