# Design

## Context

Hoy `PassportSourcesSection` se añade al final de cada pestaña (`plant_passport_page.dart`) y cada fuente muestra licencia, atribución, la URL como `SelectableText` y un botón «Abrir en el navegador» (`PassportLink`). El pie de la foto (`passport_header.dart`) repite el patrón en tres líneas: autor, licencia y `PassportLink` «Página del archivo». Las tres pestañas son `ChoiceChip` en un `Wrap`, con un solo `CustomScrollView` por planta (`PageStorageKey('passport-<id>')`): la posición del scroll se comparte entre pestañas y `_selectTab` llama a `Scrollable.ensureVisible` sobre el `Wrap` para devolver las pestañas a la vista (arreglo DEF-01 del cambio 2). La spec vigente exige áreas de toque de al menos 48 dp y texto sin truncar a 360x640 dp al 100 % y 200 %. Los datos ya existen (`credits[].url`, `credits[].licenseUrl`, `image.pageUrl`, `image.licenseUrl`) y `url_launcher` ya está en la app (decisiones D8 y D9 de `serve-consolidated-plants`, que siguen vigentes salvo lo que dice este documento sobre mostrar la URL). Motivación y alcance: véase `proposal.md`.

## Goals / Non-Goals

**Goals:**
- `Fuentes` como cuarta pestaña, con el mismo contenido que la sección actual pero con enlaces sobre el nombre y sin URL visible.
- Un único componente de enlace en línea, accesible, usado por la pestaña y por el pie de la foto.
- Conservar el arreglo de scroll del cambio 2 con cuatro pestañas, incluso al 200 %.

**Non-Goals:**
- Cambios de backend, de contrato o de datos; los textos de las licencias (la EMA y TPPT siguen sin URL).
- Enlaces en las tarjetas de P07 (`Foto: <autor> · <licencia>` sigue siendo texto).
- Mostrar o precargar la página destino dentro de la app.
- Verificar los términos legales de la EMA y TPPT (condición abierta anterior).

## Decisions

### D1. `Fuentes` como cuarta pestaña dentro del mismo `CustomScrollView`

Se añade el cuarto `ChoiceChip` `Fuentes` y el cuerpo `PassportSourcesTab` se elige con `_tab == 3`. Se retira `PassportSourcesSection` del final de la lista. Se conserva el `CustomScrollView` único con su `PageStorageKey` y `_selectTab` tal como están. El contenido es: el texto de licencias mixtas (`sourcesIntro`), una entrada por crédito, la entrada de la imagen, y `noSources` si no hay créditos ni imagen. Se quitan el `Divider` y el título «Fuentes» (el chip ya lo nombra). Los widgets internos se renombran a tab; la clase puede conservar el archivo o moverse a `passport_sources_tab.dart` (decisión de implementación).

Alternativas:
- `TabBarView` con un scroll por pestaña: descartada, pierde la posición compartida y reabre DEF-01 del cambio 2.
- Mantener la sección y solo colapsarla («Fuentes ▾»): descartada, el usuario pidió una pestaña.

### D2. Componente `PassportInlineLink` en lugar de `PassportLink`

Un widget de texto enlazado que recibe `text`, `url` (nullable), `destination` (descripción para lectores de pantalla, por ejemplo «la página de la fuente», «el texto de la licencia», «la página del archivo en Wikimedia Commons») y, opcionalmente, un `prefix` («Licencia: ») que va dentro de la zona de toque pero fuera del subrayado.
- Si `canOpen(url)` (se conserva la regla `https` con host): el texto va en verde del pasaporte y **subrayado**, de modo que se distingue por algo más que el color; la zona es un `InkWell` con `ConstrainedBox(minHeight: 48, minWidth: 48)`; `onTap` abre con `launchUrl(..., LaunchMode.externalApplication)`; `onLongPress` hace `Clipboard.setData` y muestra el aviso «Enlace copiado». Si `launchUrl` devuelve falso o lanza, aviso «No se pudo abrir el enlace» (el texto vigente).
- Si `url` es nulo o no es `https`: `Text` plano con el estilo del contexto, sin `InkWell` ni semántica de enlace, sin copia.
- `PassportLink.readable` desaparece (ya no hay URL visible); `canOpen` se conserva como función estática del nuevo componente.
- Se retiran `openLink`, `openLinkTooltip`, `licenseUrlPrefix`, `pageUrlPrefix` e `imageFilePageLabel` de `PassportTexts` y de su lista `all`; el texto `linkNotOpened` se conserva y se añaden los textos nuevos (`linkCopied`, `commonsName`, `imageFileLinkLabel`, `photoPrefix`).

Alternativas:
- `Text.rich` con `TextSpan` y `TapGestureRecognizer`: da enlaces que fluyen dentro de un párrafo, pero no permite un área de 48 dp ni semántica de enlace por tramo sin código extra; descartada para la pestaña. El pie de la foto usa dos instancias del componente dentro de un `Wrap` (ver D4).
- Paquete de enlaces (`flutter_linkify` y similares): dependencia nueva sin necesidad.
- Mantener `SelectableText` con enlaces: reintroduce la URL visible.

### D3. Entradas de `Fuentes` y atribución secundaria

Crédito, de arriba abajo:
1. Nombre de la fuente en negrita (el estilo de título actual), enlazado a `url` si existe.
2. «Licencia: [nombre]»: la fila entera es la zona de toque (mínimo 48 dp de alto) cuando `licenseUrl` existe, con el nombre subrayado; si no, texto plano.
3. Atribución en `bodySmall`, gris (contraste mínimo 4,5:1 sobre el fondo del pasaporte, comprobado en una prueba), sin enlace y con ajuste de línea.

Entrada de la imagen (título «Imagen»): «Autor: <autor>» en texto plano, o «Autor: No disponible en fuente»; «Licencia: [nombre]» igual que arriba; y una línea con el enlace «Archivo en Wikimedia Commons» a `pageUrl`. Así el enlace al archivo existe siempre, haya o no autor. El autor se enlaza en el pie (D4) pero no aquí, para no repetir el mismo destino dos veces en la misma entrada.

La atribución queda como texto secundario porque ya lo exige la licencia en el pie de la ficha y el nombre/licencia enlazados cumplen la atribución de CC BY y CC BY-SA (nombre, licencia y enlace).

### D4. Pie de la foto: «Foto: [autor] · [licencia]» y autor desconocido

El pie pasa de tres líneas a un `Wrap` con «Foto: », el enlace del autor, « · » y el enlace de la licencia. Cada enlace es una instancia del componente (toque ≥48 dp); si `licenseUrl` es nulo, la licencia es texto plano; si `pageUrl` no es `https`, el autor es texto plano. A 200 % el `Wrap` baja a varias líneas sin truncar. La altura total del pie queda cercana a la de las tres líneas actuales, porque los dos enlaces se alinean en una fila de 48 dp.

**Autor desconocido (51 imágenes, `author` nulo).** El enlace a la página del archivo no puede perderse: las licencias CC piden indicar la fuente. Alternativas:
- **A (propuesta): «Foto: [Wikimedia Commons] · [licencia]».** El enlace del autor se sustituye por el nombre del origen, enlazado a `pageUrl`. Es corto, cabe en 360 dp al 200 %, mantiene la misma estructura que el caso normal y nombra la fuente (lo que pide la atribución). Riesgo: «Wikimedia Commons» podría leerse como el autor; se acepta porque el autor figura en la página del archivo y porque la entrada de `Fuentes` sí dice «Autor: No disponible en fuente».
- B: «Foto: autor no disponible · [licencia]» y un tercer elemento enlazado («Ver archivo»). Es más honesto sobre el dato faltante, pero añade un elemento y una línea más al pie, y deja el autor sin enlace.
- C: «Foto: [Autor no disponible] · [licencia]», con el texto de ausencia enlazado a `pageUrl`. Un enlace con ese texto parece roto y, leído por un lector de pantalla, anuncia un enlace «autor no disponible» confuso.

Se propone A; está en el delta como escenario «Autor desconocido» (pregunta abierta Q1).

### D5. Accesibilidad de los enlaces en línea

Cada enlace expone `Semantics(link: true, label: <texto visible con el prefijo>, hint: <destino y gesto>, onTap, onLongPress, onTapHint/onLongPressHint)`. Por ejemplo: etiqueta «Licencia: CC0», aviso «Enlace al texto de la licencia. Mantén pulsado para copiar el enlace». Se anuncia el destino con una descripción y no la URL, para no volver a leer una dirección larga (el requisito de «ninguna URL visible» se mantiene también en lo que se lee). El texto visible dentro del `InkWell` se excluye del árbol semántico para no leerlo dos veces. Un enlace sin URL no expone semántica de enlace.

Comprobación contra el requisito vigente («Controles con etiquetas distinguibles y áreas de toque de al menos 48 dp»): se cumple si los enlaces cuentan como controles, pero la spec no lo dice ni menciona el destino ni el subrayado. El delta lo ajusta («Accesibilidad del pasaporte»): enlaces anunciados como enlace con destino, 48 dp de alto y de ancho, y distinguibles por algo más que el color. Las pruebas usan el `SemanticsController` de Flutter y `meetsGuideline(androidTapTargetGuideline)` y `labeledTapTargetGuideline`.

Alternativas para el área de toque: (a) solo el nombre con relleno vertical: más fiel al diseño visual, pero un nombre corto como «CC0» queda por debajo de 48 dp de ancho si no se fuerza `minWidth`; (b) la fila completa «Licencia: CC0» como zona de toque: elegida para las filas de la pestaña, porque es una zona grande y estable y el prefijo da contexto al lector de pantalla; en el pie, donde dos enlaces comparten línea, cada uno lleva su `minWidth`/`minHeight` de 48 dp.

### D6. Cuatro pestañas al 200 % en 360 dp

Con 200 % de texto, los cuatro chips (`General`, `Propiedades`, `Usos`, `Fuentes`) no caben en una fila de 360 dp (344 dp útiles); el `Wrap` actual los reparte en dos o tres filas de 48 dp, sin truncar, y es la solución que se conserva. Se descartan: una fila horizontal desplazable (oculta pestañas fuera de la vista y compite con el scroll vertical) y acortar las etiquetas (no resuelve `Propiedades`). El orden es `General`, `Propiedades`, `Usos`, `Fuentes`.

El arreglo de DEF-01 sigue valiendo sin cambios de diseño: el scroll es uno por planta (`PageStorageKey`), y `_selectTab` vuelve a poner el `Wrap` a la vista con `ensureVisible(keepVisibleAtStart)`. Lo que cambia es que `Fuentes`, antes bajo cada pestaña, puede ser la pestaña más corta o la más larga según la planta, y que al 200 % el `Wrap` es más alto (hasta unos 150 dp). Hay que comprobar que (a) `ensureVisible` deja el inicio del contenido bajo los chips también cuando el `Wrap` ocupa tres filas, (b) pasar de `Usos` (larga) a `Fuentes` (corta) no deja la hoja en blanco por debajo del final y (c) las cuatro pestañas se recorren en ambos sentidos. Las pruebas existentes de DEF-01 (`plant_passport_page_test.dart`, `passport_tall_header_test.dart`) se extienden a la cuarta pestaña.

### D7. Aviso de copia y de fallo

Ambos avisos son `SnackBar` del `ScaffoldMessenger` más cercano, como el de fallo actual. «Enlace copiado» es el texto de confirmación. La copia usa `Clipboard.setData` con la URL original recortada, no la decodificada. Android 13 o posterior muestra además su propio aviso del portapapeles; es normal y no se intenta suprimir.

### D8. Enlaces dentro del texto, sin mínimo de 48 dp (corrige D2, D3, D4 y D5)

La primera implementación hizo de cada enlace una caja de 48 dp (`InkWell` con `minHeight` y `minWidth`). En el emulador (DEF-01 de la QA) el pie de la foto ocupaba de tres a cuatro filas, con «Foto:» aislado y el separador colgando, y en `Fuentes` quedaba una banda vacía entre el nombre y la licencia. Era justo lo que el usuario quería evitar: que las fuentes ocupen más que el contenido. Se decide:
- Los enlaces son tramos de un `Text.rich` (`PassportLinkedText` con partes `PassportLinkPart`): el pie se lee como texto corrido, «Foto: autor · licencia», y cada entrada de `Fuentes` son líneas consecutivas.
- Los enlaces en línea quedan exentos del mínimo de 48 dp por la excepción de WCAG 2.5.8 para enlaces dentro de una frase. Los chips y los botones conservan los 48 dp. Siguen anunciándose como enlace (Flutter lo deriva del reconocedor de toque del tramo), con el destino en la etiqueta («texto. Abre [destino]») y subrayados.
- El toque abre y la pulsación larga copia con un reconocedor propio, `_LinkRecognizer`, que extiende `TapGestureRecognizer` (para conservar la semántica de enlace) y añade un temporizador de pulsación larga; una pulsación larga suprime el toque que la sigue. Límite: Flutter solo traslada a la semántica el toque del tramo, así que la pulsación larga no se ofrece como acción de accesibilidad y el aviso de la etiqueta ya no la menciona. Los usuarios de lector de pantalla abren el enlace; copiarlo es un atajo táctil.
- Los chips ya no llevan marca de verificación (`showCheckmark: false`), porque ensanchaba el chip elegido y movía los demás. El borde mide siempre 2 dp para no alterar el tamaño; el elegido lo tiene verde y relleno verde claro, y conserva la semántica de seleccionado. Las pruebas comprueban que las posiciones no cambian a 100 % y 200 %.

## Risks / Trade-offs

- [Pie de la foto más alto que hoy con 48 dp de toque por enlace] → medir en el emulador a 100 % y 200 %; el pie reemplaza tres líneas, así que el impacto esperado es pequeño.
- [La fila de licencia como zona de toque deja a un lector de pantalla con una etiqueta larga] → etiqueta corta («Licencia: CC0») y destino en el aviso, comprobado con el `SemanticsController`.
- [La pulsación larga no se descubre] → el aviso de accesibilidad la menciona; para el resto de usuarios, la copia es un atajo y no la única vía (el enlace abre).
- [«Wikimedia Commons» como texto del autor desconocido puede leerse como autor] → mitigado en la entrada de `Fuentes` (autor «No disponible en fuente»); alternativas B y C en D4.
- [Las plantas sin `url` en un crédito (EMA, TPPT) no tienen ningún enlace] → es el dato de la semilla; el nombre y la licencia se ven como texto.
- [Quitar la URL visible impide copiarla si el navegador falla] → la pulsación larga la copia.
- [Contraste del gris de la atribución] → una prueba comprueba 4,5:1 contra el fondo del pasaporte.

## Migration Plan

Solo cambia la app. No hay migración de datos ni de despliegue: se recompila el APK y se instala en el emulador. Para revertir basta volver al commit anterior. La documentación se actualiza en el mismo cambio.

## Open Questions

Resueltas por el usuario antes de implementar (2026-10-28):

- Q1: con autor desconocido el pie dice «Foto: [Wikimedia Commons] · [licencia]», con «Wikimedia Commons» enlazado a `pageUrl` (opción A de D4). Las opciones B y C quedan descartadas.
- Q2: la pulsación larga solo muestra el aviso «Enlace copiado», sin otra señal visual del gesto.

## Implementation Notes

Diferencias y decisiones de implementación respecto del plan:

- `passport_sources_section.dart` pasó a `passport_sources_tab.dart` y la clase a `PassportSourcesTab` (D1 dejaba la decisión abierta). `PassportInlineLink` vive en `passport_link.dart`, que reemplaza a `PassportLink`.
- El pie de la foto es un solo `Text.rich` («Foto: », el enlace del autor o de «Wikimedia Commons», « · » y el enlace de la licencia); el texto «Foto: » y el separador no son parte de ningún enlace. La versión inicial con un `Wrap` de cuatro hijos de 48 dp se sustituyó por D8.
- Los textos de destino para lectores de pantalla son «la página de la fuente», «el texto de la licencia» y «la página del archivo en Wikimedia Commons»; la etiqueta del tramo enlazado queda como «[texto]. Abre [destino]» (véase D8).
- La atribución conserva el prefijo «Atribución: » y usa `bodySmall` en `passportMuted` (`0xFF58635B`), con contraste superior a 4,5:1 sobre el fondo del pasaporte, comprobado en una prueba.
- Las atribuciones de la semilla citan a veces una URL o un DOI dentro de su propio texto (por ejemplo, la de EFSA o la de Wikipedia). Por decisión del usuario, `Fuentes` muestra la atribución sin URL, porque la fuente ya queda enlazada sobre su nombre: la función pura `attributionWithoutUrls` (en `passport_sources_tab.dart`) quita `http://` y `https://` hasta el siguiente espacio, sin la puntuación final, y limpia paréntesis vacíos, dobles espacios, espacios antes de la puntuación y puntos duplicados. El dato de la API y de la semilla no cambia.
- `_selectTab` no cambió: con cuatro pestañas, `ensureVisible` mantuvo las cuatro a la vista en 360x640 al 100 % y al 200 % (incluido el `Wrap` en varias filas y el paso de `Usos` a `Fuentes`), comprobado en `passport_tall_header_test.dart`.
