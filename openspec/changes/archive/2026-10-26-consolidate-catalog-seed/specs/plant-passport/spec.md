# Spec Delta

## MODIFIED Requirements

### Requirement: Identidad y composición del pasaporte
El pasaporte SHALL resolver la planta por su identificador contra la API del catálogo y mostrar navegación de regreso, arte local provisional, el nombre principal y el nombre científico según la regla de nombre para mostrar de `catalog-client`, y pestañas `General`, `Propiedades` y `Usos` con `General` inicial. SHALL NOT mostrar procedencia, fuente ni créditos de los datos. SHALL adaptar los campos del mockup a plantas y no presentar `Tipo de aceite: Esencial` como atributo universal.

#### Scenario: Cabecera y pestañas iniciales
- **WHEN** se abre el pasaporte de una planta existente, por ejemplo `lavandula-angustifolia`, cuyo primer nombre común en la API es el nombre para mostrar de la semilla
- **THEN** muestra ese nombre como principal y el científico (`Lavandula angustifolia`) como secundario, navegación de regreso y las tres pestañas con `General` seleccionada, sin procedencia

#### Scenario: Campo de aceite no aplicable
- **WHEN** se consulta el campo de tipo de aceite en una ficha de planta
- **THEN** se identifica como no aplicable por tratarse de una planta, sin inferir un aceite

#### Scenario: Planta sin nombre común
- **WHEN** se abre el pasaporte de una planta sin nombres comunes
- **THEN** el nombre principal es el científico y no se muestra nombre secundario

#### Scenario: Carga del pasaporte
- **WHEN** la planta se está pidiendo a la API
- **THEN** se muestra un estado de carga con regreso seguro, distinto del de error y del de no encontrada

### Requirement: Usos como registros tradicionales trazables
La pestaña `Usos` SHALL mostrar los usos que entrega la API, cada uno con su actividad, la etiqueta `Registro tradicional`, la aclaración de que es un registro y no un consejo, y la cita de su referencia. Los usos que entrega la API proceden de la semilla consolidada del catálogo, donde cada actividad está traducida al español y respaldada por la cita de su fuente. Si la planta no tiene usos, SHALL indicar explícitamente que no hay usos tradicionales con referencia verificable disponibles. SHALL NOT completar vacíos desde mockups, desde el cliente ni con contenido que la API no entrega, ni presentar dosis o eficacia. Las listas largas SHALL permanecer desplazables y sin truncar.

#### Scenario: Registro tradicional elegible
- **WHEN** la planta tiene usos con referencia en la respuesta de la API
- **THEN** cada uso se muestra con su actividad, su cita y la etiqueta de registro tradicional, no consejo

#### Scenario: Sin registro elegible
- **WHEN** la planta no tiene usos
- **THEN** se muestra el vacío explícito y no se inventa contenido

#### Scenario: Muchos usos
- **WHEN** la planta tiene decenas de usos
- **THEN** todos son alcanzables con desplazamiento, sin truncar ni perder la etiqueta y la cita de cada uno
