## MODIFIED Requirements

### Requirement: Usos como registros tradicionales trazables
La pestaña `Usos` SHALL mostrar siempre, al inicio, un aviso fijo («Usos registrados en fuentes etnobotánicas históricas. No son recomendaciones ni están comprobados clínicamente. Algunas citas no se pudieron identificar y se muestran como «sin resolver».», texto provisional que el usuario ajustará en la app), también cuando la planta no tiene usos. Después SHALL mostrar los grupos de uso que entrega la API, cada uno compacto: la actividad como título, una sola línea de datos con el número de registros y, si los hay, los países separados por comas (`5 registros · China, Otros lugares, Trinidad`; sin países, solo `5 registros`), y un control para ver las citas. Las citas de las referencias del grupo SHALL estar plegadas por defecto; el control SHALL decir `Ver N citas` (`Ver 1 cita` si es una) y desplegarlas en el mismo sitio, y entonces decir `Ocultar citas` y plegarlas. Desplegadas, cada cita se muestra completa y una referencia sin obra identificada (`resolved` falso) SHALL mostrarse como «(sin resolver)» en un estilo atenuado y en cursiva. El grupo SHALL NOT repetir la etiqueta `Registro tradicional`, el rótulo `Países` ni la aclaración de que es un registro y no un consejo, porque el aviso fijo ya lo dice para toda la pestaña. Cada grupo SHALL conservar su estado de plegado al cambiar de pestaña y volver, y todos SHALL estar plegados al abrir un pasaporte. Los grupos que entrega la API proceden de la semilla consolidada del catálogo, donde cada actividad está traducida al español y respaldada por la cita de su fuente. Si la planta no tiene usos, SHALL indicar explícitamente que no hay usos tradicionales con referencia verificable disponibles. SHALL NOT completar vacíos desde mockups, desde el cliente ni con contenido que la API no entrega, ni presentar dosis o eficacia, ni reescribir los países (un «Otros lugares» genérico se muestra tal cual), y SHALL NOT añadir lógica propia sobre actividades sensibles: muestra el texto de la actividad tal como llega. Las listas largas SHALL permanecer desplazables y sin truncar.

#### Scenario: Registro tradicional elegible
- **WHEN** la planta tiene un grupo de uso con 12 registros de tres países y dos referencias
- **THEN** el grupo se muestra con su actividad como título, la línea `12 registros` con los tres países separados por comas y el control `Ver 2 citas`

#### Scenario: Aviso fijo de usos tradicionales
- **WHEN** se abre la pestaña `Usos` de cualquier planta, con o sin grupos de uso
- **THEN** el aviso fijo se muestra al inicio, antes del primer grupo o del vacío explícito, y no contiene lenguaje de eficacia

#### Scenario: Citas plegadas por defecto
- **WHEN** se abre la pestaña `Usos` de una planta con grupos de uso
- **THEN** ningún grupo muestra sus citas y cada uno muestra un control `Ver N citas` con el número de sus referencias

#### Scenario: Desplegar y plegar citas
- **WHEN** el usuario pulsa `Ver 5 citas` en un grupo y después `Ocultar citas`
- **THEN** al primer toque las cinco citas se muestran completas en el mismo grupo, sin mover el control, y el control pasa a `Ocultar citas`; al segundo toque las citas se pliegan y el control vuelve a `Ver 5 citas`, sin afectar a los demás grupos

#### Scenario: Estado de plegado al cambiar de pestaña
- **WHEN** el usuario despliega las citas de un grupo, cambia a otra pestaña y vuelve a `Usos`
- **THEN** ese grupo sigue desplegado y los demás siguen plegados; al abrir de nuevo el pasaporte, todos están plegados

#### Scenario: Grupo con una sola cita
- **WHEN** un grupo de uso tiene una sola referencia
- **THEN** el control dice `Ver 1 cita` y, al pulsarlo, se muestra esa cita

#### Scenario: Sin etiqueta ni aclaración por grupo
- **WHEN** se muestra cualquier grupo de uso, plegado o desplegado
- **THEN** no aparece la etiqueta `Registro tradicional`, ni el rótulo `Países`, ni la aclaración `Es un registro, no un consejo de uso.`, y el aviso fijo sigue visible al inicio de la pestaña

#### Scenario: Cita sin resolver visible
- **WHEN** un grupo de uso trae una referencia resuelta y otra con `resolved` falso y la cita «Woi.Syria (sin resolver)», y el usuario despliega las citas
- **THEN** el grupo muestra ambas citas, la segunda como «(sin resolver)» en un estilo atenuado y en cursiva, y no se oculta el grupo

#### Scenario: Actividades sensibles tal como llegan
- **WHEN** un grupo trae la actividad «Uso tradicional, sin eficacia demostrada: cáncer» y la planta tiene `safety` con una advertencia de riesgo grave (por ejemplo, toxicidad o uso abortivo) en su texto
- **THEN** `Usos` muestra la actividad con ese texto exacto y `Precauciones` muestra la advertencia tal como llega, sin que la app añada, quite ni reformule ninguno

#### Scenario: Grupo sin países
- **WHEN** un grupo de uso no trae países
- **THEN** la línea de datos muestra solo el número de registros, sin separador ni texto sustituto

#### Scenario: Países tal como llegan
- **WHEN** un grupo trae los países `China`, `Otros lugares` y `Trinidad`
- **THEN** la línea de datos los muestra en ese orden y con ese texto, sin reescribir `Otros lugares`

#### Scenario: Sin registro elegible
- **WHEN** la planta no tiene usos
- **THEN** se muestra el vacío explícito y no se inventa contenido

#### Scenario: Muchos usos
- **WHEN** la planta tiene decenas de grupos de uso
- **THEN** todos son alcanzables con desplazamiento, sin truncar la actividad, la línea de datos ni el control de cada uno, y al desplegar o plegar un grupo se conserva la posición de desplazamiento

### Requirement: Accesibilidad del pasaporte
El pasaporte SHALL respetar zonas seguras y conservar texto esencial legible, desplazable y sin truncado a 360x640 dp al 100% y 200%, también con las cuatro pestañas. Los controles, como las pestañas y los botones, SHALL disponer de etiquetas distinguibles y áreas de toque de al menos 48 dp de alto y de ancho, y la selección de una pestaña SHALL expresarse también en la semántica y en el borde, no solo en el relleno. El control que pliega y despliega las citas de un grupo de `Usos` SHALL ser un botón con esa área de toque, SHALL expresar en su semántica si está expandido o plegado, y su etiqueta SHALL incluir el texto visible (`Ver N citas` u `Ocultar citas`) y la actividad del grupo, de modo que la tecnología de asistencia anuncie el número de citas y distinga los grupos entre sí; el estado SHALL expresarse también con el texto del control, no solo con un icono. Un enlace en línea, que va dentro de una frase o de una línea de texto, SHALL anunciarse como enlace, con el texto visible y el destino al que lleva (por ejemplo, la página de la fuente o el texto de la licencia), y SHALL distinguirse del texto que lo rodea por algo más que el color. Los enlaces en línea quedan exentos del mínimo de 48 dp, según la excepción de WCAG 2.5.8 para enlaces dentro de una frase. La imagen de la planta SHALL tener una descripción accesible, y el arte local provisional SHALL ocupar su lugar cuando la planta no tiene imagen, mientras carga o si falla la descarga. Los niveles de precauciones SHALL expresarse con texto y no solo con color.

#### Scenario: Ficha accesible con texto aumentado
- **WHEN** se recorre el pasaporte mediante tecnología de asistencia a 100% o 200% en 360x640 dp
- **THEN** los textos y controles esenciales, incluidos las cuatro pestañas, el pie de la imagen, los enlaces, la pestaña `Fuentes` y los controles de citas de `Usos`, son legibles, alcanzables, etiquetados y no quedan truncados

#### Scenario: Imagen descrita
- **WHEN** la planta tiene imagen
- **THEN** la tecnología de asistencia anuncia una descripción que incluye el nombre de la planta

#### Scenario: Nivel de precauciones sin depender del color
- **WHEN** se muestra el nivel de precauciones `alto`, `medio` o `bajo`
- **THEN** el nivel se presenta como texto, además de cualquier color

#### Scenario: Pestañas estables al seleccionar
- **WHEN** el usuario elige una pestaña distinta
- **THEN** las cuatro pestañas conservan su posición y su tamaño, y la pestaña elegida se distingue por su relleno, su borde y su semántica de seleccionada

#### Scenario: Enlace en línea accesible
- **WHEN** se inspecciona con tecnología de asistencia un enlace de `Fuentes` o del pie de la imagen
- **THEN** se anuncia como enlace con su texto visible y su destino, sin leer la URL, y no depende solo del color para distinguirse del texto que lo rodea; al ir dentro del texto, no se le exige un área de toque de 48 dp

#### Scenario: Control de citas accesible
- **WHEN** se inspecciona con tecnología de asistencia el control de citas de un grupo de `Usos`, plegado y desplegado
- **THEN** se anuncia como botón con su estado de plegado o expandido, su etiqueta contiene el texto visible (`Ver 5 citas`, `Ocultar citas`) y la actividad del grupo, y su área de toque es de al menos 48 dp de alto y de ancho, también a 200 % de texto en 360x640 dp
