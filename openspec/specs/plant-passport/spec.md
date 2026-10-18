# plant-passport Specification

## Purpose

Define pasaportes locales de plantas que distinguen datos fuente, registros tradicionales y vacíos explícitos sin convertirlos en consejo médico ni promesas de eficacia.

## Requirements

### Requirement: Identidad y composición del pasaporte
El pasaporte SHALL mostrar navegación de regreso, arte local provisional, nombre común editorial, nombre científico de fuente, pestañas `General`, `Propiedades` y `Usos` con `General` inicial, y procedencia y referencias disponibles. SHALL adaptar los campos del mockup a plantas y no presentar `Tipo de aceite: Esencial` como atributo universal.

#### Scenario: Cabecera y pestañas iniciales
- **WHEN** se abre un pasaporte de una de las cinco plantas
- **THEN** muestra ambos nombres correctos, navegación de regreso, las tres pestañas con `General` seleccionada y la procedencia identificable

#### Scenario: Campo de aceite no aplicable
- **WHEN** se consulta el campo de tipo de aceite en una ficha de planta
- **THEN** se identifica como no aplicable por tratarse de una planta, sin inferir un aceite

### Requirement: General con vacíos explícitos
La pestaña `General` SHALL mostrar solo campos respaldados: origen o descripción sin respaldo se muestran como `No disponible en fuente`; las partes se muestran solo cuando estén registradas explícitamente y no como recomendación de parte medicinal.

#### Scenario: Datos generales ausentes
- **WHEN** un campo de origen o descripción no está respaldado por la fuente disponible
- **THEN** se muestra `No disponible en fuente` y no se completa con texto ilustrativo

#### Scenario: Parte registrada
- **WHEN** existe un registro de parte para la identidad exacta
- **THEN** se presenta como dato registrado en la fuente, no como recomendación de uso medicinal

### Requirement: Propiedades sin inferencia de eficacia
La pestaña `Propiedades` SHALL no inferir eficacia ni propiedades medicinales a partir de fitoquímica. Cuando no exista respaldo evaluado para la planta, SHALL mostrar explícitamente `sin propiedades medicinales evaluadas en este catálogo`.

#### Scenario: Plantas sin evaluación respaldada
- **WHEN** se consulta cualquiera de las cinco plantas sin respaldo evaluado en el catálogo
- **THEN** la pestaña comunica explícitamente que no hay propiedades medicinales evaluadas en este catálogo

### Requirement: Usos como registros tradicionales trazables
La pestaña `Usos` SHALL mostrar solo registros ETHNOBOT vinculados a identidad exacta confirmada y con referencia bibliográfica resoluble; cada uno SHALL identificarse como uso tradicional, no consejo. Si no hay registros elegibles, SHALL indicar explícitamente que no hay usos tradicionales con referencia verificable disponibles. No SHALL completar vacíos desde mockups, modelos generativos ni otras fuentes, ni presentar dosis o eficacia.

#### Scenario: Registro tradicional elegible
- **WHEN** hay un registro ETHNOBOT de identidad exacta con referencia resoluble
- **THEN** se muestra con su cita disponible y etiqueta de registro tradicional, no consejo

#### Scenario: Sin registro elegible
- **WHEN** no hay registros de uso que satisfagan identidad y referencia
- **THEN** se muestra el vacío explícito y no se inventa contenido

### Requirement: Acciones no funcionales y retorno seguro
El corazón y `Ver formulaciones relacionadas` SHALL permanecer visibles pero deshabilitados con etiqueta de no disponibilidad; no SHALL cambiar estado, persistir datos ni abrir destinos. Un identificador de planta inexistente SHALL mostrar estado legible con regreso seguro. Regresar SHALL volver a la pantalla anterior y `Inicio` SHALL volver a Home.

#### Scenario: Acciones no disponibles
- **WHEN** se inspecciona o intenta activar favorito o formulaciones relacionadas
- **THEN** ambas acciones se anuncian no disponibles y no mutan estado ni abren destinos

#### Scenario: Identidad inexistente
- **WHEN** se abre un identificador de planta no existente
- **THEN** se informa el estado no encontrado y se ofrece regreso seguro sin cierre inesperado

### Requirement: Accesibilidad del pasaporte
El pasaporte SHALL respetar zonas seguras y conservar texto esencial legible, desplazable y sin truncado a 360x640 dp al 100% y 200%. Los controles SHALL disponer de etiquetas distinguibles y áreas de toque de al menos 48 dp; el arte SHALL ser local y provisional.

#### Scenario: Ficha accesible con texto aumentado
- **WHEN** se recorre el pasaporte mediante tecnología de asistencia a 100% o 200% en 360x640 dp
- **THEN** los textos y controles esenciales son legibles, alcanzables, etiquetados y no quedan truncados
