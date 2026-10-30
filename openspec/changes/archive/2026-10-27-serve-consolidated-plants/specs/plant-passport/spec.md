# Spec Delta

## MODIFIED Requirements

### Requirement: Identidad y composición del pasaporte
El pasaporte SHALL resolver la planta por su identificador contra la API del catálogo y mostrar navegación de regreso, la imagen de cabecera según «Imagen de cabecera con atribución», el nombre principal y el nombre científico según la regla de nombre para mostrar de `catalog-client`, y pestañas `General`, `Propiedades` y `Usos` con `General` inicial, seguidas de la sección `Fuentes`. SHALL mostrar los créditos y la atribución solo como dato neutral de la planta, sin indicar de qué fuente proviene cada campo. SHALL adaptar los campos del mockup a plantas y no presentar un tipo de aceite que la API no entrega.

#### Scenario: Cabecera y pestañas iniciales
- **WHEN** se abre el pasaporte de una planta existente, por ejemplo `lavandula-angustifolia`, cuyo `displayName` es «Lavanda»
- **THEN** muestra «Lavanda» como nombre principal y `Lavandula angustifolia` como secundario, navegación de regreso y las tres pestañas con `General` seleccionada

#### Scenario: Campo de aceite no aplicable
- **WHEN** se consulta el campo de tipo de aceite de una planta cuyo `oil` es `null`, o una ficha cuya planta no tiene aceite registrado
- **THEN** se muestra como no disponible en fuente, sin inferir un aceite ni mostrar `Esencial`

#### Scenario: Planta sin nombre común
- **WHEN** se abre el pasaporte de una planta cuyo `displayName` es su nombre científico
- **THEN** el nombre principal es el científico y no se muestra nombre secundario

#### Scenario: Carga del pasaporte
- **WHEN** la planta se está pidiendo a la API
- **THEN** se muestra un estado de carga con regreso seguro, distinto del de error y del de no encontrada

#### Scenario: Atribución sin procedencia por campo
- **WHEN** se recorren las tres pestañas de una planta con datos de varias fuentes
- **THEN** ningún campo de `General`, `Propiedades` ni `Usos` indica el dataset del que viene, y los créditos solo aparecen en `Fuentes` y en el pie de la imagen

### Requirement: General con vacíos explícitos
La pestaña `General` SHALL mostrar solo campos entregados por la API: `Nombre común` (el nombre para mostrar), `Sinónimos`, `Familia`, `Origen`, `Parte utilizada` (las partes registradas como dato de las fuentes, no como recomendación de parte medicinal), `Tipo de aceite`, `Descripción` y los demás nombres comunes con su idioma. Cada campo sin dato SHALL decirlo explícitamente: los de texto con `No disponible en fuente` y las listas con una frase propia, como `No hay partes registradas en fuente`. SHALL NOT completar vacíos con texto ilustrativo ni con contenido que la API no entrega. Si el nivel de seguridad de la planta es `alto`, `General` SHALL mostrar un aviso con ese nivel que remite a `Propiedades`.

#### Scenario: Campos de P05 presentes
- **WHEN** la planta tiene nombre para mostrar «Lavanda», origen «Mediterráneo», partes «Flores», aceite `Esencial` y descripción
- **THEN** `General` muestra `Nombre común: Lavanda`, `Origen: Mediterráneo`, `Parte utilizada: Flores`, `Tipo de aceite: Esencial` y la descripción

#### Scenario: Datos generales ausentes
- **WHEN** la familia, el origen, el aceite o la descripción de la planta son `null`
- **THEN** cada uno muestra `No disponible en fuente` y no se completa con texto ilustrativo

#### Scenario: Parte registrada
- **WHEN** existe un registro de parte para la identidad exacta
- **THEN** se presenta como dato registrado en la fuente, no como recomendación de uso medicinal

#### Scenario: Familia y nombres comunes
- **WHEN** la planta tiene familia, sinónimos científicos y nombres comunes en varios idiomas
- **THEN** `General` muestra la familia, los sinónimos y cada nombre común con su idioma

#### Scenario: Sin partes ni nombres comunes
- **WHEN** la planta no tiene partes, sinónimos o nombres comunes registrados
- **THEN** `General` indica explícitamente que no hay datos registrados en lugar de omitir el campo en silencio

#### Scenario: Planta sin nombre en español
- **WHEN** el `displayName` de la planta coincide con su nombre científico, por ejemplo `abutilon-theophrasti`, que solo tiene nombres comunes en otros idiomas
- **THEN** `Nombre común` muestra `No hay nombre común en español registrado` y no el nombre científico, y los nombres comunes en otros idiomas siguen en los demás nombres comunes, cada uno con su idioma

#### Scenario: Aviso de nivel alto
- **WHEN** el nivel de precauciones de la planta es `alto`
- **THEN** `General` muestra un aviso con el texto del nivel (no solo un color) y la indicación de ver `Propiedades`

#### Scenario: Sin aviso para otros niveles
- **WHEN** el nivel de precauciones es `medio`, `bajo` o `null`, o la planta no tiene datos de precauciones
- **THEN** `General` no muestra el aviso

#### Scenario: Sin lista de referencias en General
- **WHEN** se abre `General` de una planta con usos y referencias
- **THEN** no muestra una lista de referencias bibliográficas; las citas con su texto completo están en `Usos` y las fuentes en `Fuentes`

### Requirement: Propiedades sin inferencia de eficacia
La pestaña `Propiedades` SHALL mostrar dos secciones: `Objetivos registrados por la EMA` y `Precauciones`. Cada objetivo SHALL mostrar su nombre, su subárea si existe, el área y el tipo de documento de la EMA y la cita de su referencia, con una aclaración fija de que es una clasificación de la Agencia Europea de Medicamentos, no una indicación de uso ni una promesa de eficacia. La pestaña SHALL NOT inferir eficacia ni propiedades medicinales a partir de fitoquímica ni añadir textos propios que describan efectos. Sin objetivos, SHALL decir `No hay objetivos registrados por la EMA para esta planta`.

#### Scenario: Planta con objetivos de la EMA
- **WHEN** la planta tiene el objetivo `cuidado-de-la-piel` con un área y una monografía de la EMA
- **THEN** `Propiedades` lo muestra con su nombre, el área, el tipo de documento, la cita y la aclaración de que es una clasificación y no una indicación

#### Scenario: Objetivo de otros objetivos
- **WHEN** el objetivo es `otros-objetivos` con la subárea de digestión
- **THEN** se muestra el nombre del objetivo junto con la subárea

#### Scenario: Plantas sin evaluación respaldada
- **WHEN** la planta no tiene objetivos (por ejemplo una planta tóxica, o una sin monografía de la EMA)
- **THEN** `Propiedades` comunica `No hay objetivos registrados por la EMA para esta planta`, sin inferir propiedades de su composición química

#### Scenario: Sin lenguaje de eficacia
- **WHEN** se revisan los textos fijos de `Propiedades`
- **THEN** ninguno contiene verbos de efecto ni promesas de eficacia como «calma», «cura» o «ayuda a»

### Requirement: Usos como registros tradicionales trazables
La pestaña `Usos` SHALL mostrar siempre, al inicio, un aviso fijo («Usos registrados en fuentes etnobotánicas históricas. No son recomendaciones ni están comprobados clínicamente. Algunas citas no se pudieron identificar y se muestran como «sin resolver».», texto provisional que el usuario ajustará en la app), también cuando la planta no tiene usos. Después SHALL mostrar los grupos de uso que entrega la API, cada uno con su actividad, la etiqueta `Registro tradicional`, el número de registros, los países si los hay, la aclaración de que es un registro y no un consejo, y la cita de cada una de sus referencias; una referencia sin obra identificada (`resolved` falso) SHALL mostrarse como «(sin resolver)» en un estilo atenuado. Los grupos que entrega la API proceden de la semilla consolidada del catálogo, donde cada actividad está traducida al español y respaldada por la cita de su fuente. Si la planta no tiene usos, SHALL indicar explícitamente que no hay usos tradicionales con referencia verificable disponibles. SHALL NOT completar vacíos desde mockups, desde el cliente ni con contenido que la API no entrega, ni presentar dosis o eficacia, y SHALL NOT añadir lógica propia sobre actividades sensibles: muestra el texto de la actividad tal como llega. Las listas largas SHALL permanecer desplazables y sin truncar.

#### Scenario: Registro tradicional elegible
- **WHEN** la planta tiene un grupo de uso con 12 registros de tres países y dos referencias
- **THEN** el grupo se muestra con su actividad, `12 registros`, los tres países, sus dos citas y la etiqueta de registro tradicional, no consejo

#### Scenario: Aviso fijo de usos tradicionales
- **WHEN** se abre la pestaña `Usos` de cualquier planta, con o sin grupos de uso
- **THEN** el aviso fijo se muestra al inicio, antes del primer grupo o del vacío explícito, y no contiene lenguaje de eficacia

#### Scenario: Cita sin resolver visible
- **WHEN** un grupo de uso trae una referencia resuelta y otra con `resolved` falso y la cita «Woi.Syria (sin resolver)»
- **THEN** el grupo se muestra con ambas citas, la segunda como «(sin resolver)» en un estilo atenuado, y no se oculta el grupo

#### Scenario: Actividades sensibles tal como llegan
- **WHEN** un grupo trae la actividad «Uso tradicional, sin eficacia demostrada: cáncer» y la planta tiene `safety` con una advertencia de riesgo grave (por ejemplo, toxicidad o uso abortivo) en su texto
- **THEN** `Usos` muestra la actividad con ese texto exacto y `Precauciones` muestra la advertencia tal como llega, sin que la app añada, quite ni reformule ninguno

#### Scenario: Grupo sin países
- **WHEN** un grupo de uso no trae países
- **THEN** se muestra sin la línea de países, sin sustituirla por texto

#### Scenario: Sin registro elegible
- **WHEN** la planta no tiene usos
- **THEN** se muestra el vacío explícito y no se inventa contenido

#### Scenario: Muchos usos
- **WHEN** la planta tiene decenas de grupos de uso
- **THEN** todos son alcanzables con desplazamiento, sin truncar ni perder la etiqueta y las citas de cada uno

### Requirement: Accesibilidad del pasaporte
El pasaporte SHALL respetar zonas seguras y conservar texto esencial legible, desplazable y sin truncado a 360x640 dp al 100% y 200%. Los controles SHALL disponer de etiquetas distinguibles y áreas de toque de al menos 48 dp. La imagen de la planta SHALL tener una descripción accesible, y el arte local provisional SHALL ocupar su lugar cuando la planta no tiene imagen, mientras carga o si falla la descarga. Los niveles de precauciones SHALL expresarse con texto y no solo con color.

#### Scenario: Ficha accesible con texto aumentado
- **WHEN** se recorre el pasaporte mediante tecnología de asistencia a 100% o 200% en 360x640 dp
- **THEN** los textos y controles esenciales, incluidos el pie de la imagen, los enlaces y la sección `Fuentes`, son legibles, alcanzables, etiquetados y no quedan truncados

#### Scenario: Imagen descrita
- **WHEN** la planta tiene imagen
- **THEN** la tecnología de asistencia anuncia una descripción que incluye el nombre de la planta

#### Scenario: Nivel de precauciones sin depender del color
- **WHEN** se muestra el nivel de precauciones `alto`, `medio` o `bajo`
- **THEN** el nivel se presenta como texto, además de cualquier color

## ADDED Requirements

### Requirement: Imagen de cabecera con atribución
Cuando el detalle trae `image`, el pasaporte SHALL mostrar en la cabecera la miniatura de 500 px de ancho que Wikimedia sirve para `image.url`, no el original, y, visible junto a ella, el autor, la licencia y un enlace a la página del archivo, también cuando `attributionRequired` es falso. La URL de la página SHALL poder abrirse en el navegador del sistema y SHALL mostrarse como texto. Mientras la imagen carga, si falla la descarga si no puede construirse la miniatura o si la planta no tiene imagen, el pasaporte SHALL mostrar el arte local provisional, sin recurrir al original, sin atribución de imagen y sin tratarlo como un error de la ficha.

#### Scenario: Imagen con licencia CC BY-SA
- **WHEN** la planta tiene una imagen con autor «J. Pérez», licencia CC BY-SA 4.0 y página en Commons
- **THEN** la cabecera muestra la miniatura de 500 px con «J. Pérez», `CC BY-SA 4.0` y el enlace a la página del archivo

#### Scenario: Imagen sin atribución obligatoria
- **WHEN** la imagen es de dominio público y `attributionRequired` es falso
- **THEN** se muestran igualmente el autor, la licencia y el enlace

#### Scenario: Sin imagen
- **WHEN** la planta no tiene imagen
- **THEN** la cabecera muestra el arte local provisional y no muestra pie de atribución

#### Scenario: Falla la descarga de la imagen
- **WHEN** la imagen no puede descargarse por falta de conexión o por un error del host
- **THEN** la cabecera muestra el arte local provisional, el resto de la ficha se muestra completo y no aparece un error

#### Scenario: Abrir la página del archivo
- **WHEN** el usuario activa el enlace de la página del archivo
- **THEN** se abre en el navegador del sistema y la app no descarga ni muestra esa página

### Requirement: Precauciones con nivel opcional y citas
La sección `Precauciones` de `Propiedades` SHALL mostrar, cuando la planta tiene `safety`, el nivel (`Alto`, `Medio` o `Bajo`) como texto si existe, el texto de advertencia de la API y la cita de cada referencia. Cuando `safety.level` es `null`, SHALL mostrar el texto y las citas sin etiqueta de nivel. Cuando `safety` es `null`, SHALL decir que no hay precauciones registradas en las fuentes consultadas y que eso no significa que la planta sea segura. SHALL NOT calificar de segura a una planta ni inferir seguridad de la ausencia de datos.

#### Scenario: Precauciones de nivel alto
- **WHEN** la planta tiene `safety` de nivel `alto` con texto y dos referencias
- **THEN** la sección muestra `Alto` como texto, el texto de advertencia y las dos citas

#### Scenario: Precauciones sin nivel
- **WHEN** la planta tiene `safety` con `level` igual a `null`, un texto con las contraindicaciones de la EMA y sus referencias
- **THEN** la sección muestra el texto y las citas sin etiqueta de nivel, `General` no muestra aviso y la sección no dice que no hay datos

#### Scenario: Precauciones sin datos
- **WHEN** `safety` es `null`
- **THEN** la sección dice que no hay precauciones registradas en las fuentes consultadas y que esto no significa que la planta sea segura

#### Scenario: Ninguna planta se presenta como segura
- **WHEN** se revisan todos los textos de la sección para los niveles `alto`, `medio`, `bajo`, sin nivel y sin datos
- **THEN** ninguno afirma que la planta es segura o inocua

### Requirement: Sección Fuentes con licencias y atribución
El pasaporte SHALL mostrar una sección `Fuentes` después del contenido de la pestaña activa, con una entrada por cada elemento de `credits`: el nombre del dataset, su licencia, la atribución exigida y el enlace cuando existe; y, si la planta tiene imagen, una entrada con el autor, la licencia y la página de la imagen. La sección SHALL indicar que los datos se reúnen de fuentes abiertas y que cada fuente conserva su licencia, y SHALL NOT indicar qué campo proviene de qué fuente. Sin créditos, SHALL decir que no hay fuentes registradas para la planta.

#### Scenario: Fuentes de una planta
- **WHEN** el detalle trae créditos de WCVP (CC BY 3.0), la EMA y Wikipedia (CC BY-SA 4.0)
- **THEN** `Fuentes` lista las tres con su licencia y atribución, y la de Wikipedia con su enlace

#### Scenario: Fuentes visibles en cada pestaña
- **WHEN** el usuario cambia entre `General`, `Propiedades` y `Usos`
- **THEN** la sección `Fuentes` sigue disponible tras el contenido de la pestaña activa

#### Scenario: Entrada de la imagen
- **WHEN** la planta tiene imagen
- **THEN** `Fuentes` incluye una entrada de la imagen con su autor, licencia y página

#### Scenario: Sin créditos
- **WHEN** `credits` está vacío y la planta no tiene imagen
- **THEN** `Fuentes` dice que no hay fuentes registradas para esta planta

#### Scenario: Sin procedencia por campo
- **WHEN** se revisa la sección `Fuentes`
- **THEN** ninguna entrada indica a qué campo de la ficha corresponde
