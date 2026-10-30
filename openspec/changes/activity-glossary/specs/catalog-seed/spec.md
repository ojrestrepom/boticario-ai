## MODIFIED Requirements

### Requirement: Fuentes con versión fija, checksum y licencia
Cada fuente que alimenta la semilla SHALL declararse con identificador, versión o snapshot, URL, licencia, URL de la licencia (opcional: una URL https, o `null` si la fuente no tiene una licencia con una URL única, como la licencia por archivo de Commons o los términos propios de la EMA y TPPT), atribución exigida y checksum del insumo. El manifiesto SHALL copiar la URL de la licencia de cada fuente que la declara. Las descargas SHALL ser un paso explícito, SHALL verificarse contra su checksum y SHALL cachearse en `data/.cache/`, ignorada por Git. Una fuente que cambia con el tiempo SHALL fijarse en un snapshot con su fecha. Las fuentes admitidas son USDA Dr. Duke, WCVP, WFO (solo respaldo), EMA (herbal medicines y PDF de seguridad), TPPT de Agroscope, EFSA Compendium of Botanicals, Wikidata, Wikipedia en español (también para el glosario de actividades), Wikcionario en español (solo para el glosario de actividades) y Wikimedia Commons.

#### Scenario: Insumo íntegro
- **WHEN** un insumo cacheado coincide con el checksum declarado
- **THEN** el paso siguiente lo usa sin acceder a la red

#### Scenario: Insumo alterado o ausente
- **WHEN** un insumo cacheado no coincide con su checksum o no ha sido descargado
- **THEN** el paso falla indicando la fuente y el paso de descarga necesario, y no usa datos sin verificar

#### Scenario: Snapshot de una fuente cambiante
- **WHEN** se descarga el JSON de la EMA, que se actualiza dos veces al día
- **THEN** el manifiesto registra el `meta.timestamp` del snapshot y su checksum, y las ejecuciones posteriores usan ese snapshot hasta que se decida actualizarlo

#### Scenario: Retirar una fuente
- **WHEN** una fuente, por ejemplo Wikipedia, se desactiva en la configuración de las herramientas y se calcula el plan de regeneración
- **THEN** solo figuran como pendientes las plantas cuyo paquete usaba esa fuente, ningún registro regenerado contiene refs de ella, `description` queda `null` o se resume de otras fuentes del paquete, el validador no da errores y el manifiesto deja de listar la fuente

#### Scenario: Fuente fuera de la lista
- **WHEN** se intenta añadir una fuente descartada, como DrugBank o iNaturalist
- **THEN** el manifiesto y el validador de fuentes la rechazan por no estar en la lista de fuentes admitidas

#### Scenario: URL de licencia de una fuente
- **WHEN** `sources.json` declara para `wikipedia_es` la licencia CC BY-SA 4.0 y `licenseUrl` igual a `https://creativecommons.org/licenses/by-sa/4.0/`
- **THEN** el manifiesto sellado incluye ese `licenseUrl` en la fuente `wikipedia_es`, y los registros de las plantas y el `seedHash` no cambian

#### Scenario: Fuente sin URL de licencia
- **WHEN** una fuente, como Commons, declara `licenseUrl` igual a `null`, o no lo declara
- **THEN** la fuente se acepta y el manifiesto la lista con `licenseUrl` nulo o sin el campo, respectivamente

#### Scenario: URL de licencia inválida
- **WHEN** `licenseUrl` no es `null` ni una cadena que empiece por `https://`
- **THEN** la validación de fuentes falla indicando la fuente y el campo

#### Scenario: Wikcionario en español como fuente
- **WHEN** `sources.json` declara `wiktionary_es` como servicio en línea con la licencia CC BY-SA 4.0 y `licenseUrl` igual a `https://creativecommons.org/licenses/by-sa/4.0/`
- **THEN** la validación de fuentes la acepta, `download` la omite como a los demás servicios, el manifiesto sellado la lista con su `licenseUrl`, y los registros de las plantas y el `seedHash` no cambian

## ADDED Requirements

### Requirement: Lista versionada de términos del glosario
Las herramientas SHALL leer una lista versionada de términos (`tools/catalog-seed/glossary-terms.json`) que decide qué actividades llevan explicación. Cada término de la lista SHALL declarar el texto de la actividad tal como aparece en los grupos de uso, el título de su entrada en Wikcionario y la fuente elegida: Wikcionario con el número de la acepción, o Wikipedia con el título del artículo, el modo (literal o adaptado), el texto adaptado y su evidencia; los términos que no entran SHALL quedar en una sección aparte con su motivo (sin entrada, sin artículo, sin acepción adecuada, circular, sensible o pendiente de aprobación). La lista SHALL contener solo términos de acción (por ejemplo, Diurético o Astringente) y SHALL NOT contener enfermedades, síntomas ni partes del cuerpo, ni ningún término de la lista de actividades sensibles.

#### Scenario: Término de acción
- **WHEN** la lista declara `Diurético` con el título `diurético` y la acepción 1
- **THEN** el glosario se arma con esa acepción de la entrada y el término queda enlazable por la forma base de la actividad

#### Scenario: Término sin entrada en Wikcionario
- **WHEN** Wikcionario no tiene entrada para `Vermífugo`, cuyo único resultado es la forma femenina `vermífuga`
- **THEN** el término pasa a Wikipedia y, si su artículo no lo define, figura en la sección de excluidos con el motivo «sin artículo» o «el artículo no define» y la fecha de la consulta, y el glosario no lo incluye

#### Scenario: Término explicado con Wikipedia
- **WHEN** Wikcionario no tiene entrada para `Hemostático` y el artículo de Wikipedia `Hemostático` lo define
- **THEN** la lista declara la fuente `wikipedia_es`, el título del artículo y el modo del texto

#### Scenario: Término sensible
- **WHEN** la lista incluye una actividad de la categoría de enfermedades graves o de señales de riesgo de `sensitive-activities.json`
- **THEN** la validación de la lista falla nombrando el término

#### Scenario: Crecimiento de la lista
- **WHEN** se añade un término a la lista
- **THEN** la regeneración descarga solo la entrada nueva, el glosario cambia solo en esa fila y ningún registro de planta figura como pendiente de regenerar

### Requirement: Descarga de Wikcionario y de Wikipedia con revisión fija
La descarga SHALL ser un paso explícito y reanudable que consulte la API de MediaWiki de `es.wiktionary.org` (`action=parse` con `prop=text|revid`) y de `es.wikipedia.org` (`action=query` con el extracto de la introducción, la revisión y la marca de desambiguación) una entrada o un artículo por petición, de forma serial y con pausa entre peticiones, con un `User-Agent` genérico con el nombre del proyecto y sin correo ni datos personales, respetando `Retry-After` y guardando cada respuesta en `data/.cache/wiktionary_es/` o `data/.cache/wikipedia_es/glossary/` con su revisión y su fecha de consulta. Wikipedia SHALL descargarse solo para los términos que declaran un artículo. Las ejecuciones posteriores SHALL usar la caché sin acceder a la red hasta que se decida actualizar una entrada. El contenido descargado SHALL NOT entrar en Git.

#### Scenario: Descarga de una entrada
- **WHEN** se descarga la entrada `diurético`
- **THEN** la caché guarda el HTML renderizado de la entrada, el identificador y la hora de su revisión y la fecha, y una segunda ejecución no vuelve a pedirla

#### Scenario: Descarga de un artículo de Wikipedia
- **WHEN** se descarga el artículo `Estimulante`
- **THEN** la caché guarda el extracto de la introducción, el identificador y la hora de la revisión, si es una página de desambiguación y la fecha, y una segunda ejecución no vuelve a pedirlo

#### Scenario: Límite de peticiones
- **WHEN** Wikcionario o Wikipedia responde 429 con `Retry-After`
- **THEN** el paso no reintenta antes del plazo, conserva lo descargado y termina con el estado de reanudación

#### Scenario: Entrada o artículo inexistente
- **WHEN** la API responde que la página no existe
- **THEN** la caché guarda la ausencia con su fecha y el término se reporta como «sin entrada» o «sin artículo» sin repetir la consulta

#### Scenario: Armado sin red
- **WHEN** se arma el glosario con la caché completa y sin acceso a la red
- **THEN** el armado termina correctamente y produce el mismo archivo en cada ejecución

### Requirement: Acepción y texto literal o adaptado del glosario
La explicación de un término SHALL salir de una de dos fuentes. De Wikcionario, el texto de una acepción de la entrada en español, elegida entre las acepciones reales de la entrada, guardado literal: solo se SHALL retirar el marcado, las notas al pie y las listas de sinónimos, antónimos, usos y ejemplos, normalizar los espacios y recortar a la primera oración; no se SHALL parafrasear, traducir ni completar con conocimiento del modelo. De Wikipedia, solo para un término sin entrada o sin acepción adecuada en Wikcionario, la primera oración del artículo si define bien el término (literal, con los mismos cambios permitidos) o, si no basta, una paráfrasis de una o dos oraciones hecha solo con el texto del extracto del artículo guardado, sin conocimiento propio, marcada como adaptada y con la evidencia literal del extracto en que se apoya. La explicación SHALL describir una acción o propiedad atribuida a un remedio o sustancia; si ninguna fuente lo hace, o el texto solo remite a otra palabra o repite el término, el término SHALL quedar sin explicación.

#### Scenario: Primera oración de una acepción larga
- **WHEN** la acepción elegida de `astringente` tiene dos oraciones
- **THEN** el glosario guarda solo la primera, sin alterar sus palabras

#### Scenario: Acepción farmacológica que no es la primera
- **WHEN** la entrada `anodino` tiene cuatro acepciones y solo la cuarta (`Dicho de un medicamento: Que mitiga el dolor.`) se refiere a un medicamento
- **THEN** el glosario guarda esa acepción y no las tres anteriores, que son figuradas

#### Scenario: Acepción que solo remite o repite
- **WHEN** la única acepción de `sedante` es un sinónimo («Calmante, hablando de remedios») o la de `purgante` es «Que purga»
- **THEN** el término queda sin definición con el motivo «sin acepción adecuada»

#### Scenario: Primera oración de Wikipedia que define el término
- **WHEN** el artículo `Diurético` de Wikipedia empieza con una oración que define el término
- **THEN** el glosario puede guardar esa oración como texto literal de Wikipedia, con el enlace a la revisión del artículo

#### Scenario: Paráfrasis de Wikipedia
- **WHEN** la primera oración del artículo `Estimulante` no basta como definición
- **THEN** el glosario puede guardar una paráfrasis de una o dos oraciones hecha solo con el extracto, marcada como adaptada y con la evidencia literal del extracto

#### Scenario: Texto no literal
- **WHEN** el texto literal de una fila del glosario difiere de la acepción o de la primera oración de la caché tras retirar el marcado y recortar
- **THEN** la validación falla nombrando el término

### Requirement: Validación del glosario
El validador SHALL comprobar que cada fila del glosario tiene esquema válido, que su texto literal coincide con la caché (y, en un texto adaptado, que su evidencia es literal respecto del extracto), que su término no pertenece a la lista de actividades sensibles y que su texto, además de estar en español y terminar en punto, no contiene dosis ni posologías, ni los patrones de dosis y eficacia del validador de los registros, ni nombres de las enfermedades graves de la lista de actividades sensibles. Un patrón de eficacia SHALL poder aprobarse por término, y solo así, con su motivo en la lista versionada; una dosis SHALL NOT poder aprobarse. Un error SHALL impedir que el glosario entre en la semilla.

#### Scenario: Dosis en una definición
- **WHEN** el texto de un término contiene una cantidad con unidad, «dosis», «posología» o «gotas»
- **THEN** el validador devuelve un error con el término y la expresión

#### Scenario: Patrón de eficacia sin aprobar
- **WHEN** el texto de `bactericida` («Que elimina las bacterias o los microbios.») contiene un patrón de eficacia y la lista no lo aprueba
- **THEN** el validador devuelve un error y el término no entra en el glosario

#### Scenario: Patrón de eficacia aprobado
- **WHEN** la lista aprueba el patrón «elimina» para `bactericida` con su motivo (aprobación explícita del usuario)
- **THEN** el validador no devuelve error por ese patrón y sí lo devolvería por cualquier otro patrón del mismo texto

#### Scenario: Evidencia ausente en un texto adaptado
- **WHEN** una fila adaptada de Wikipedia no trae evidencia, o su evidencia no figura en el extracto de la caché
- **THEN** el validador devuelve un error con el término

#### Scenario: Enfermedad grave en la definición
- **WHEN** el texto elegido para `emoliente` menciona «tumores»
- **THEN** el validador devuelve un error y el término no entra en el glosario sin cambiar de acepción

### Requirement: Glosario sellado en la semilla
La semilla SHALL incluir `data/seed/glossary.json`, con la versión de formato, la licencia con su URL y las filas ordenadas por clave; cada fila con la clave normalizada, el término, el texto, la fuente (`sourceId` y `sourceName`), si el texto es adaptado, el número de acepción (nulo en Wikipedia), la URL permanente de la revisión de la entrada o del artículo, el identificador y la fecha de la revisión y la fecha de descarga. El manifiesto SHALL registrar `glossaryHash` (sha256 del JSON canónico del archivo) y `glossaryCount`, y SHALL NOT incluir el glosario en el `seedHash`. La verificación de la semilla SHALL fallar si el glosario falta o no coincide con el manifiesto, salvo que el manifiesto no declare glosario.

#### Scenario: Glosario sellado
- **WHEN** se ejecuta el sellado con un glosario válido
- **THEN** `glossary.json` queda con claves ordenadas, el manifiesto trae `glossaryHash` y `glossaryCount`, y el `seedHash` es el mismo de antes

#### Scenario: Glosario alterado
- **WHEN** se modifica una fila de `glossary.json` sin volver a sellar
- **THEN** la verificación de la semilla falla indicando que el hash del glosario no coincide

#### Scenario: Semilla sin glosario
- **WHEN** el manifiesto no declara `glossaryHash`
- **THEN** la verificación continúa y el glosario se considera vacío

#### Scenario: Regeneración de plantas independiente
- **WHEN** se agrega la fuente de Wikcionario o se cambia el glosario y se calcula el plan de regeneración
- **THEN** ninguna planta figura como pendiente, porque la fuente no entra en los paquetes y la versión del prompt no cambia

### Requirement: Licencia y atribución del glosario
Cada fila del glosario SHALL registrar la licencia CC BY-SA 4.0 y la URL de la revisión de la entrada o del artículo de la que sale, de modo que se cumpla la atribución mediante un enlace a la entrada, cuyo historial lista a sus autores. El glosario es una obra derivada de Wikcionario y de Wikipedia: SHALL licenciarse como CC BY-SA 4.0 y SHALL indicar los cambios hechos al texto (marcado y notas retirados, recorte a la primera oración y, en Wikipedia, la paráfrasis marcada como adaptada). La atribución de cada fuente SHALL decir que las definiciones se tomaron de ella con esos cambios.

#### Scenario: Atribución de una fila
- **WHEN** se consulta la fila de `diurético`
- **THEN** trae la licencia CC BY-SA 4.0, su URL y el enlace permanente a la revisión de la entrada

#### Scenario: Fila adaptada de Wikipedia
- **WHEN** se consulta una fila de Wikipedia con texto adaptado
- **THEN** trae `adapted` verdadero, la licencia CC BY-SA 4.0 y el enlace permanente a la revisión del artículo (`oldid`)

#### Scenario: Cambios indicados
- **WHEN** se lee la atribución de la fuente `wiktionary_es` en `sources.json` y en el manifiesto
- **THEN** menciona que las definiciones son de Wikcionario, que se les retiró el marcado y las notas y que se recortaron a la primera oración, y que el historial de cada entrada lista a sus autores

#### Scenario: Atribución de Wikipedia para el glosario
- **WHEN** se lee la atribución de la fuente `wikipedia_es` en `sources.json` y en el manifiesto
- **THEN** menciona además que, en el glosario de actividades, el texto es la primera oración de un artículo o una paráfrasis marcada como adaptada, hecha solo con el texto del artículo
