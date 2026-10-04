# plant-catalog Specification

## Purpose

Define un catálogo offline pequeño y trazable de plantas, separando la identidad de fuente de los nombres editoriales y evitando presentar datos incompletos como afirmaciones respaldadas.

## Requirements

### Requirement: Catálogo fijo con identidad de fuente
El catálogo SHALL contener exactamente cinco plantas, en el orden Lavanda, Eucalipto, Romero, Manzanilla y Menta, con los identificadores FNFNUM 544, 401, 873, 605 y 619 respectivamente. SHALL conservar los nombres científicos de fuente y tratar los nombres comunes españoles como editoriales, sin atribuirlos al USDA.

#### Scenario: Identidades y orden iniciales
- **WHEN** se consulta la colección del catálogo
- **THEN** aparecen esas cinco plantas en ese orden, con nombres científicos `Lavandula angustifolia`, `Eucalyptus globulus`, `Rosmarinus officinalis`, `Matricaria recutita` y `Mentha x piperita subsp. nothosubsp. piperita` y sus respectivos FNFNUM indicados

#### Scenario: Identidad desconocida
- **WHEN** se solicita una identidad que no pertenece al catálogo
- **THEN** el sistema produce un resultado de identidad no encontrada legible y no falla

### Requirement: Procedencia verificable y límites del snapshot
El catálogo SHALL identificar el origen como un snapshot archivado de USDA Dr Duke, CC0, cuya procedencia y versión sean identificables. SHALL NOT inferir sinonimia taxonómica actual ni inferir aceites esenciales a partir de plantas.

#### Scenario: Identificación de fuente
- **WHEN** se consulta la procedencia del catálogo
- **THEN** se informa USDA Dr Duke, la licencia CC0 y una identificación de versión del snapshot

#### Scenario: Planta no equivale a aceite
- **WHEN** una planta tiene registros de partes o sustancias en la fuente
- **THEN** esos registros no se presentan como identidad de un aceite esencial ni crean fichas de aceite

### Requirement: Solo datos sustentados y ausencias explícitas
El catálogo SHALL exponer únicamente datos respaldados por registros archivados y referencias bibliográficas resolubles cuando sean necesarias. No SHALL generar dosis, recomendaciones ni afirmaciones de eficacia, ni trasladar propiedades de compuestos a la planta. La disponibilidad del snapshot no SHALL implicar evidencia clínica; los datos ausentes o referencias no resueltas SHALL quedar explícitos y no habilitar afirmaciones de uso.

#### Scenario: Referencia no resuelta
- **WHEN** un registro de uso carece de referencia bibliográfica resoluble o no puede vincularse con identidad exacta
- **THEN** no habilita una afirmación de uso y se representa como no disponible o ausente

#### Scenario: Sin inferencias clínicas
- **WHEN** se presentan registros de la fuente o sustancias asociadas
- **THEN** no se convierten en dosis, consejo, recomendación, eficacia clínica ni propiedades medicinales de la planta

### Requirement: Disponibilidad local y errores de datos
El catálogo SHALL estar disponible sin conectividad. Ante datos inválidos o inaccesibles, SHALL mostrar un estado de error legible y no fallar ni sustituirlos por contenido inventado.

#### Scenario: Consulta offline
- **WHEN** la aplicación se usa sin conectividad
- **THEN** puede consultar las cinco identidades y los datos archivados disponibles

#### Scenario: Error de datos
- **WHEN** los datos locales no pueden leerse o validarse
- **THEN** se informa un error legible, sin cierre inesperado ni contenido de reemplazo inventado
