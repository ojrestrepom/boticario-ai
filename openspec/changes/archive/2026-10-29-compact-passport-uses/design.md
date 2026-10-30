# Design

## Context

`PassportUsesTab` es un `StatelessWidget`. `PlantPassportPage` mantiene la pestaña elegida en su estado (`_tab`) y construye solo el contenido de la pestaña activa dentro de un único `ListView` con `PageStorageKey('passport-<id>')`, de modo que la posición de scroll es una sola para las cuatro pestañas. Al cambiar de pestaña, el contenido de `Usos` se destruye y se reconstruye al volver, así que cualquier estado local de un grupo se pierde. Cada `UseGroup` trae `activity`, `count`, `countries` y `references`, y una `CitedReference` trae `citation` y `resolved`.

## Goals / Non-Goals

**Goals:**

- Que el uso (la actividad, cuántos registros y de dónde) sea lo primero que se lea, y las citas queden a un toque.
- Que el plegado sea accesible y no cambie el contenido que ve quien lo despliega.

**Non-Goals:**

- Cambiar el orden de los grupos, el aviso fijo, el vacío explícito, el respaldo de `uses` o el tratamiento de las actividades sensibles.
- Tocar el backend, la API o el modelo del catálogo.
- Reescribir o normalizar los países («Otros lugares» se muestra tal como llega).

## Decisions

### D1. Grupo compacto

Cada grupo es una columna con tres elementos: la actividad (`titleSmall`, negrita, como hoy), una línea de datos y el control de citas, seguidos del `Divider` actual. La línea de datos es un solo `Text` con `recordCount(count)` y, si hay países, ` · ` y `countries.join(', ')`; sin países es solo el número. El texto sale de una función de `PassportTexts` (por ejemplo `useGroupSummary(count, countries)`) para que las pruebas y el escaneo de lenguaje de eficacia lo cubran. Se retiran `traditionalRecord`, `useGroupClarification` y `countriesLabel` de `PassportTexts` y de `all`. `PassportField` se conserva, porque `General` y otras pestañas lo usan.

### D2. Control de citas

Un `TextButton`-like (`InkWell` o `TextButton` con `minimumSize` 48x48) alineado a la izquierda, con el texto «Ver N citas» / «Ver 1 cita» plegado y «Ocultar citas» desplegado, y un icono de Material (`expand_more` plegado, `expand_less` desplegado) que no es lo único que indica el estado (decisión del usuario, antes Q2). El texto de «Ver N citas» sale de `PassportTexts.showCitations(count)` y el de plegar de `PassportTexts.hideCitations`. N es `references.length`, que es lo que se despliega (puede diferir de `count` si hay registros sin referencia propia; el control cuenta citas, la línea de datos cuenta registros). Las citas desplegadas usan el widget `_Citation` actual sin cambios, dentro del mismo grupo y antes del `Divider`.

### D3. Estado del plegado

El estado vive en `_PlantPassportPageState` como un `Set<String>` de claves de grupo desplegadas, que se pasa a `PassportUsesTab` junto con un callback para alternar. La clave del grupo NO puede ser solo la actividad: en la base real, 17 plantas tienen dos grupos con la misma actividad y distinta actividad original (por ejemplo, «Hidropesía» viene de dos términos de USDA), y desplegar uno desplegaría el otro. La clave es `<posición>|<actividad>|<actividad original>` (función `useGroupKey`): la posición en la lista es estable dentro de una planta porque el orden de los grupos no cambia, y los otros dos componentes la hacen legible. Una prueba con dos grupos de igual actividad comprueba que se pliegan y despliegan por separado.

- **Cambio de pestaña y vuelta:** cada grupo recuerda su estado, porque el conjunto vive en la página y no en el widget de la pestaña, que se destruye.
- **Cambio de planta** (`didUpdateWidget` con otro `plant.id`, donde ya se reinicia `_tab`): el conjunto se vacía.
- **Salir del pasaporte:** el estado se descarta con la página; al volver a abrir una planta, todo está plegado. No se persiste en disco ni entre sesiones.
- **Alternativa descartada:** `PageStorage` por grupo. Funciona, pero con decenas de claves por planta añade más maquinaria que un conjunto en el estado de la página.
- **Alternativa descartada:** `ExpansionTile`. Trae su propio control de 56 dp, su propia animación y su semántica; el diseño pide un control en línea con el texto del diseño elegido.

### D4. Scroll al desplegar y plegar

El contenido sigue en el `ListView` único; el grupo se despliega en el mismo sitio y solo crece hacia abajo, así que el control pulsado no se mueve y no se pierde la posición. Al plegar, el grupo se acorta; si el usuario estaba al final de una lista larga, Flutter ajusta el offset al nuevo máximo sin saltos hacia arriba por encima de lo necesario. No hay `ensureVisible` ni animación de scroll. Con decenas de grupos todos plegados, la pestaña es mucho más corta que hoy, y el escenario «Muchos usos» sigue exigiendo que todos sean alcanzables con desplazamiento.

### D5. Accesibilidad

- El control es un botón (`button: true`) de al menos 48 dp de alto y de ancho (`androidTapTargetGuideline` y `labeledTapTargetGuideline` en la prueba) con `expanded: true|false` en su semántica.
- La etiqueta semántica empieza por el texto visible y añade la actividad, por ejemplo «Ver 5 citas de Demulcente» (la etiqueta contiene el texto visible, según WCAG 2.5.3, y distingue los controles repetidos al navegar por controles). Ocultar: «Ocultar citas de Demulcente». El número de citas se anuncia así en el estado plegado; desplegado, el lector lee las citas mismas.
- El control no depende del icono ni del color: el texto cambia entre «Ver» y «Ocultar».
- A 360x640 dp al 200 % el texto del control y de la línea de datos pueden ocupar varias líneas; no se trunca (sin `maxLines` ni `ellipsis`), y el control crece en alto conservando los 48 dp mínimos.
- Las citas «(sin resolver)» conservan el texto, la cursiva y el gris actuales, de modo que el estado no depende solo del color.

### D6. Qué pasa con el aviso de «registro, no consejo»

La etiqueta y la aclaración por grupo repiten lo que dice el aviso fijo («No son recomendaciones ni están comprobados clínicamente»), que se muestra siempre al inicio de la pestaña, también sin usos, y no cambia. Por eso se retiran de cada grupo sin perder la salvaguarda: el aviso cubre toda la pestaña. El único escenario que las exigía por grupo es «Registro tradicional elegible» de `plant-passport`; se reescribe en el delta y se añade «Sin etiqueta ni aclaración por grupo». El escaneo de lenguaje de eficacia sigue cubriendo los textos nuevos.

### D7. Respaldo, orden y sensibles

No cambia nada: `plant.useGroups` ya deriva los grupos desde `uses` con un backend anterior, el orden es el que llega y la actividad se muestra tal como llega, sin lógica propia sobre actividades sensibles.

## Risks / Trade-offs

- [Un lector que no despliega nunca ve las citas] → el control está siempre visible, con su número, y el aviso fijo explica que algunas citas son «sin resolver»; la trazabilidad sigue a un toque.
- [Las citas sin resolver quedan ocultas por defecto] → el aviso fijo ya las menciona; el desplegado las muestra igual que hoy.
- [Estado perdido al salir del pasaporte] → es deliberado; evita persistencia y estado obsoleto.
- [Los tests actuales cuentan «Registro tradicional» y buscan citas visibles] → hay que ajustarlos (tareas 4 y 5): las citas solo existen en el árbol desplegado.

## Open Questions

- Q1 (resuelta). La etiqueta semántica incluye la actividad («Ver 5 citas de Demulcente»), según la decisión del usuario.
- Q2 (resuelta). Se usan los iconos de Material `expand_more` y `expand_less`, de modo que el estado no depende solo del texto.
