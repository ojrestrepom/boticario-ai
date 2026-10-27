# plant-passport Specification

## Purpose

Define pasaportes locales de plantas que distinguen datos fuente, registros tradicionales y vacíos explícitos sin convertirlos en consejo médico ni promesas de eficacia.

## Requirements

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

### Requirement: General con vacíos explícitos
La pestaña `General` SHALL mostrar solo campos entregados por la API: la familia, o `No disponible en fuente` cuando es `null`; los nombres comunes con su idioma; y las partes registradas como dato de la fuente, no como recomendación de parte medicinal. SHALL mostrar el tipo de aceite como no aplicable. SHALL NOT mostrar origen ni descripción, que el contrato no incluye, ni completar vacíos con texto ilustrativo.

#### Scenario: Datos generales ausentes
- **WHEN** la familia de la planta es `null`
- **THEN** se muestra `No disponible en fuente` y no se completa con texto ilustrativo

#### Scenario: Parte registrada
- **WHEN** existe un registro de parte para la identidad exacta
- **THEN** se presenta como dato registrado en la fuente, no como recomendación de uso medicinal

#### Scenario: Familia y nombres comunes
- **WHEN** la planta tiene familia y nombres comunes
- **THEN** `General` muestra la familia y cada nombre común con su idioma

#### Scenario: Sin partes ni nombres comunes
- **WHEN** la planta no tiene partes o nombres comunes registrados
- **THEN** `General` indica explícitamente que no hay datos registrados en lugar de omitir el campo en silencio

### Requirement: Propiedades sin inferencia de eficacia
La pestaña `Propiedades` SHALL no inferir eficacia ni propiedades medicinales a partir de fitoquímica. Cuando no exista respaldo evaluado para la planta, SHALL mostrar explícitamente `sin propiedades medicinales evaluadas en este catálogo`.

#### Scenario: Plantas sin evaluación respaldada
- **WHEN** se consulta cualquiera de las cinco plantas sin respaldo evaluado en el catálogo
- **THEN** la pestaña comunica explícitamente que no hay propiedades medicinales evaluadas en este catálogo

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

### Requirement: Acciones no funcionales y retorno seguro
El corazón y `Ver formulaciones relacionadas` SHALL permanecer visibles pero deshabilitados con etiqueta de no disponibilidad; SHALL NOT cambiar estado, persistir datos ni abrir destinos. Si la API responde que la planta no existe, el pasaporte SHALL mostrar `Planta no encontrada` con regreso seguro. Si la petición falla por conexión, tiempo agotado o error del servidor, SHALL mostrar un error de red con una acción `Reintentar` y regreso seguro. Regresar SHALL volver a la pantalla anterior y `Inicio` SHALL volver a Home.

#### Scenario: Acciones no disponibles
- **WHEN** se inspecciona o intenta activar favorito o formulaciones relacionadas
- **THEN** ambas acciones se anuncian no disponibles y no mutan estado ni abren destinos

#### Scenario: Identidad inexistente
- **WHEN** se abre un identificador de planta que la API responde con 404
- **THEN** se informa `Planta no encontrada` y se ofrece regreso seguro sin cierre inesperado

#### Scenario: Error de red reintentable
- **WHEN** no puede obtenerse la ficha por falta de conexión, tiempo agotado o error del servidor
- **THEN** se muestra un estado de error distinto de `Planta no encontrada`, con la acción `Reintentar` que repite la petición y regreso seguro

### Requirement: Accesibilidad del pasaporte
El pasaporte SHALL respetar zonas seguras y conservar texto esencial legible, desplazable y sin truncado a 360x640 dp al 100% y 200%. Los controles SHALL disponer de etiquetas distinguibles y áreas de toque de al menos 48 dp; el arte SHALL ser local y provisional.

#### Scenario: Ficha accesible con texto aumentado
- **WHEN** se recorre el pasaporte mediante tecnología de asistencia a 100% o 200% en 360x640 dp
- **THEN** los textos y controles esenciales son legibles, alcanzables, etiquetados y no quedan truncados
