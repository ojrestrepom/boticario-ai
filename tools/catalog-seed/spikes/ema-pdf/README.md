# Spike 3.1: extracción de las secciones de seguridad de los PDF de la EMA

Este spike responde la pregunta de D9 (`openspec/changes/consolidate-catalog-seed/design.md`): si se pueden extraer de los PDF de la EMA las contraindicaciones (4.3), las advertencias y precauciones (4.4) y las interacciones (4.5), con su numeración y sin mezclar columnas.

## Conclusión

Criterio de D9 cumplido, con una condición: hay que usar `pdfminer.six` con coordenadas (modo `pdfminer-cols` del script), no el texto plano de ninguna de las dos bibliotecas.

- `pdfminer-cols`: las tres secciones con su numeración y sin mezclar columnas en los 7 PDF de monografías, y la parte equivalente (CONCLUSIONS) en la declaración pública. Éxito en 8 de 8.
- `pypdf` (texto plano): encuentra las tres secciones en las 7 monografías y no entrelaza líneas, pero en las monografías con dos columnas con contenido (hipérico, menta, valeriana) concatena las columnas sin distinguirlas, a veces en la misma línea, y deja pasar notas al pie. Parcial en esas tres, OK en las otras cuatro y en la declaración pública.
- `pdfminer.six` (texto plano): entrelaza líneas de las dos columnas en el hipérico 4.5. Falla en ese caso.
- `pdftotext -layout` (poppler): no se probó. Ver «Sobre pdftotext».

La declaración pública de *Citrus bergamia* no tiene secciones numeradas ni contenido de seguridad: dice que no se puede establecer una monografía por falta de datos. Se extrae la sección CONCLUSIONS, pero su contenido no aporta contraindicaciones, advertencias ni interacciones. Para el paquete de la tarea 3.3 conviene registrar «declaración pública sin datos de seguridad» y no inventar secciones vacías.

## Muestra

Descarga el 20 de octubre de 2026 con el `User-Agent` `BoticarioAI-catalog-seed/0.1 (academic project)`. Los PDF están en `data/.cache/ema-pdf/spike/` (ignorada por Git) con un `SHA256SUMS`. Las páginas de origen salen del campo `herbal_medicine_url` del JSON de la EMA (`medicines-output-herbal_medicines-report-output-json_en.json`).

| Planta | Página de la EMA | Documento usado | Tipo | Págs. | sha256 |
| --- | --- | --- | --- | --- | --- |
| *Hyperici herba* (especie sola) | `/en/medicines/herbal/hyperici-herba-0` | `final-european-union-herbal-monograph-hypericum-perforatum-l-herba-revision-1_en.pdf` (EMA/HMPC/7695/2021) | Monografía final, revisión 1 | 14 | `2225d1b960f790ec8efe81c61c431a54ed96d2d0b827a0a75c0088c24774bfaf` |
| *Symphyti radix* | `/en/medicines/herbal/symphyti-radix` | `final-european-union-herbal-monograph-symphytum-officinale-l-radix_en.pdf` | Monografía final | 7 | `aa23fc2a1f15d76343c43b6a8c764c9e6910a0d8c2208d44fb302452bd6c0896` |
| *Citri bergamiae aetheroleum* | `/en/medicines/herbal/citri-bergamiae-aetheroleum` | `final-public-statement-citrus-bergamia-risso-et-poiteau-aetheroleum_en.pdf` (EMA/HMPC/528177/2011) | Declaración pública final | 2 | `b85c3ca96f9cf5548ef4f1497b6493d6aacd677bcf385987baadad78bafe4d42` |
| *Lavandulae flos* | `/en/medicines/herbal/lavandulae-flos` | `final-community-herbal-monograph-lavandula-angustifolia-p-mill-flos_en.pdf` | Monografía final (comunitaria) | 5 | `24fc44f118f40c4c638040e47f777b0ba4a755ad1faf700cff504f782053b1ad` |
| *Valerianae radix* | `/en/medicines/herbal/valerianae-radix` | `final-european-union-herbal-monograph-valeriana-officinalis-l-radix_en.pdf` (EMA/HMPC/150848/2015) | Monografía final | 9 | `a69cc050171e07c01a2b77afdbecc34990e7dfba161bbfc194405fe1119596cb` |
| *Matricariae flos* | `/en/medicines/herbal/matricariae-flos` | `final-european-union-herbal-monograph-matricaria-recutita-l-flos-first-version_en.pdf` | Monografía final | 13 | `cdc63d61626f49a639c3a5ec2e768a8fa46933b5393e8fa2c9cb0518e10b0ffb` |
| *Menthae piperitae aetheroleum* | `/en/medicines/herbal/menthae-piperitae-aetheroleum` | `european-union-herbal-monograph-mentha-x-piperita-l-aetheroleum-revision-1_en.pdf` (EMA/HMPC/522410/2013) | Monografía final, revisión 1 (sin prefijo `final-` en el nombre) | 12 | `21af051cc4426ebb812a910b7e1a69dfec420e16418f78447ec7eec9af33c399` |
| *Thymi herba* | `/en/medicines/herbal/thymi-herba` | `final-community-herbal-monograph-thymus-vulgaris-l-and-thymus-zygis-l-herba_en.pdf` (EMA/HMPC/342332/2013) | Monografía final (comunitaria) | 8 | `77ee37a0980e71e737d526a1d245e6f256ee0ca41320977f6bb9daa9a59421f9` |

La URL completa de cada PDF es `https://www.ema.europa.eu` más la ruta de la página y del documento tal como aparecen en el HTML de la página (`href` de los `.pdf` en `herbal-monograph/` o `public-statement/`); el script de descarga no se incluye porque fue una prueba manual.

Observaciones de la descarga:

- El JSON de la EMA trae dos filas para el hipérico: la combinación con *Cimicifugae rhizoma* (`hyperici-herba`) y la especie sola (`hyperici-herba-0`). Se usó la segunda. Hay filas duplicadas (por ejemplo *Thymi herba*), así que la herramienta debe deduplicar por URL.
- Una página trae muchos documentos (dictamen, comentarios, borradores, versiones sustituidas «superseded»). La monografía vigente es la de ruta `herbal-monograph/` cuyo nombre empieza por `final-` o no empieza por `draft-` ni `superseded-`. La declaración pública es la de `public-statement/final-`.
- La EMA respondió `429` con `Retry-After: 10` a tres PDF cuando se pidieron con 2 segundos de espera, y entregó una página HTML de error con tipo `200` en el cuerpo del archivo. Hay que verificar que el archivo empiece por `%PDF-` y reintentar respetando `Retry-After`; con 15 segundos entre peticiones funcionó.

## Herramientas probadas

Instaladas en un venv temporal fuera del repo (no se instalaron paquetes en el sistema ni en el repo).

| Herramienta | Versión | Modo |
| --- | --- | --- |
| `pypdf` | 6.21.1 | `extract_text()` por página (texto plano) |
| `pdfminer.six` | 20251107 | `extract_text()` (texto plano) |
| `pdfminer.six` con coordenadas | 20251107 | `extract_pages()`: cada línea con su `x0`, `x1`, `y` y tamaño de fuente (`pdfminer-cols`) |
| `pdftotext -layout` (poppler) | no instalado | no probado |

También se miró el modo `layout` de `pypdf` (`extract_text(extraction_mode="layout")`): conserva las columnas por posición, pero los desplazamientos horizontales no son estables entre líneas y páginas (la columna derecha empieza en columnas de carácter distintas), así que no sirve para cortar por columna sin coordenadas.

## Cómo está hecha la extracción

`extract_sections.py` (en esta carpeta) recibe `--tool pypdf|pdfminer|pdfminer-cols`, una carpeta de salida y rutas de PDF como argumentos. Se ejecuta con `python3 -I` desde esta carpeta (el script no lee nada del directorio de los PDF) y escribe un JSON por PDF y herramienta.

1. Quita cabeceras y pies de página: la línea de título repetida («European Union herbal monograph on ...» o «Community herbal monograph on ...») y la de `EMA/HMPC/n/n Page x/y`. En `pdfminer-cols` también descarta las líneas con fuente menor que el 90 % de la mediana de la página, que son las notas al pie y las cabeceras.
2. Localiza los encabezados con la expresión `^4\.\d{1,2}\.\s+[A-Z]` (número con punto final y título con mayúscula) y exige que el título coincida con el canónico: `Contraindications`, `Special warnings and precautions for use` e `Interactions with other medicinal products and other forms of interaction`. Esto evita las referencias cruzadas que caen al inicio de una línea (por ejemplo `4.4 ’Special warnings...` en la 4.2 de la consuelda).
3. Corta cada sección hasta el siguiente encabezado numerado (`4.4`, `4.5`, `4.6`...).
4. Normaliza espacios y saltos de línea a un solo párrafo.
5. Solo en `pdfminer-cols`: separa cada línea en columna izquierda («Well-established use»), derecha («Traditional use») o «ambas». El límite de columna es el borde izquierdo de la cabecera «Traditional use» de esa página menos 15 puntos; una línea que empieza a la izquierda y llega más allá del límite más 20 puntos se marca «both».

Salida de ejemplo en `samples/` (los PDF no se incluyen):

- `hyperici.pdfminer-cols.json`: el caso más difícil (dos columnas con contenido distinto por sección y nota al pie en la 4.5).
- `hyperici.pdfminer-flat.json`: la misma sección con `pdfminer` plano, que muestra el entrelazado de columnas («...increased agents metabolised by CYP3A4...»).
- `valerianae.pdfminer-cols.json` y `valerianae.pypdf.json`: la misma sección con cada modo (en `pypdf`, «Hypersensitivity to the active substance. Hypersensitivity to the active substance.» sale seguido, sin saber cuál es cada columna).
- `bergamiae.pdfminer-cols.json`: la declaración pública.

## Resultados por PDF y sección

Evaluación manual: cada sección se comparó con el texto de `pypdf` en modo `layout` (que muestra las columnas tal como están en la página) y con las cajas de texto con coordenadas de `pdfminer`, página por página. Además, para las tres herramientas se comprobó que el conjunto de palabras de `pdfminer-cols` coincide con el de `pypdf` en cada sección (las únicas diferencias son la nota al pie del hipérico, presente solo en `pypdf`).

No se renderizó el PDF a imagen (no hay `pdftoppm` ni se instaló nada), así que la comparación «contra el original» es contra el texto con posiciones del propio PDF, no contra una captura.

Leyenda: OK = sección encontrada con su número, texto completo y columnas separadas; parcial = sección y texto completos pero columnas sin separar o con residuos; falla = líneas entrelazadas.

| PDF | Sección | `pdfminer-cols` | `pypdf` plano | `pdfminer` plano |
| --- | --- | --- | --- | --- |
| Hipérico | 4.3 | OK (izquierda: uso bien establecido; derecha: uso tradicional) | Parcial: columnas una tras otra sin etiqueta | No revisado línea a línea |
| Hipérico | 4.4 | OK (abarca págs. 8-9) | Parcial: igual | No revisado línea a línea |
| Hipérico | 4.5 | OK (págs. 9-10; la nota al pie 6 se descarta por tamaño de fuente) | Parcial: columnas sin etiqueta y la nota al pie queda dentro de la sección | Falla: entrelaza líneas de las dos columnas y trae la nota al pie |
| Consuelda | 4.3, 4.4, 4.5 | OK (solo columna derecha) | OK | OK |
| Bergamota (declaración pública) | CONCLUSIONS | OK, sin datos de seguridad en el documento | OK | OK |
| Lavanda | 4.3, 4.4, 4.5 | OK (solo columna derecha; 4.4 abarca págs. 3-4) | OK | OK |
| Valeriana | 4.3 | OK (izquierda y derecha; págs. 6-7, con la cabecera de columna repetida en la página 7) | Parcial: «Hypersensitivity... Hypersensitivity...» en la misma línea | No revisado línea a línea |
| Valeriana | 4.4 | OK | Parcial | No revisado línea a línea |
| Valeriana | 4.5 | OK («None reported» en cada columna) | Parcial: «None reported None reported» | No revisado línea a línea |
| Manzanilla | 4.3, 4.4, 4.5 | OK (solo columna derecha; 4.4 abarca págs. 11-12) | OK | OK |
| Menta | 4.3, 4.4, 4.5 | OK (ambas columnas con texto; las indicaciones 1, 2 y 3 quedan separadas por columna) | Parcial: sin etiqueta de columna | No revisado línea a línea |
| Tomillo | 4.3, 4.4, 4.5 | OK (solo columna derecha) | OK | OK |

Resumen: `pdfminer-cols` 8/8 PDF con OK en todas las secciones. `pypdf` plano: 5/8 OK (consuelda, bergamota, lavanda, manzanilla, tomillo) y 3/8 parcial (hipérico, valeriana, menta). `pdfminer` plano: falla en el hipérico 4.5 por entrelazado; en el resto solo se revisó que el texto coincidiera en palabras con `pypdf`, y como también carece de etiquetas de columna no mejora a `pypdf`.

## Recomendación para la tarea 3.3

- **Herramienta:** `pdfminer.six` con `extract_pages()` y coordenadas (modo `pdfminer-cols`). Es Python puro, instalable con pip y solo la usa el desarrollador (D1). `pypdf` no basta si se quiere distinguir uso bien establecido de uso tradicional.
- **Encabezados:** `^4\.(3|4|5)\.\s+<título canónico>` (ver arriba), con el título de 4.5 posiblemente partido en dos líneas y un dígito de nota al pie pegado («interaction6»). Terminar en el siguiente `^4\.\d+\.\s+[A-Z]`. No aceptar `4.4` seguido de una comilla ni sin punto final, porque son referencias cruzadas.
- **Columnas:** los PDF traen una tabla con «Well-established use» (izquierda) y «Traditional use» (derecha). Las monografías de solo uso tradicional tienen la izquierda vacía. Guardar la salida por columna (`left`, `right`, `both`) y que el paquete cite la sección con su columna. El límite de columna se calcula por página con la cabecera «Traditional use», que se repite en cada página; si falta, reutilizar el de la página anterior.
- **Casos especiales:**
  - Declaraciones públicas: sin numeración; la parte equivalente es `CONCLUSIONS` y puede no contener datos de seguridad. Registrar eso en el paquete.
  - Secciones que cruzan páginas (hipérico, valeriana, lavanda, manzanilla): la cabecera de columna se repite arriba de la página siguiente y se descarta.
  - Notas al pie dentro de una sección (hipérico 4.5): descartarlas por tamaño de fuente (< 90 % de la mediana de la página) y, si hace falta conservarlas, tratarlas aparte.
  - Subtítulos internos como «Indication 1)», «Indications 1), 3) and 4)», «Herbal preparations a, b, d...» o «Use as bath additive»: se conservan como texto dentro de la sección; el LLM los usa para atribuir el contenido.
  - Monografías de combinaciones: tienen la misma estructura, pero la sección mezcla las dos plantas; filtrar por la fila de especie sola o marcar la combinación.
  - Documentos sin PDF de monografía final (solo borrador o «superseded»): usar el borrador y anotarlo en la procedencia.
- **Descarga:** esperar al menos 15 segundos tras un `429`, verificar que el archivo empiece por `%PDF-` antes de cachearlo y guardar su sha256. Los PDF de la EMA responden con `Retry-After: 10`.
- **Residuos conocidos:** guiones de fin de línea que dejan «P- glycoprotein» o «CYP- enzymes» (no se unen para no estropear términos con guion legítimo); erratas del original («cutenous», «insufficency») se conservan.

## Sobre pdftotext

No hizo falta para decidir: `pdfminer-cols` cumple el criterio en toda la muestra. Probar `pdftotext -layout` (`brew install poppler`) no cambiaría la conclusión, porque ya hay una herramienta instalable con pip que lo cumple; solo serviría como comparación o para renderizar páginas a imagen (`pdftoppm`) y confirmar a ojo una muestra. Su salida `-layout` conserva columnas por posición de carácter, igual que el modo `layout` de `pypdf`, que se descartó para cortar columnas, así que habría que cortar por posición también. Recomendación: no instalarlo salvo que el usuario quiera la verificación visual.

## Limitaciones

- Muestra de 8 PDF: 7 monografías (6 especies más el hipérico) y 1 declaración pública. Solo en inglés. No cubre monografías con tres o más columnas, tablas anidadas ni PDF escaneados.
- La evaluación «contra el original» es contra el texto con coordenadas del PDF, no contra una imagen de la página. Una verificación visual de al menos el hipérico y la menta sigue pendiente.
- La detección de columnas depende de la cabecera «Traditional use» y de un margen de 15 puntos; una monografía con otra maquetación puede asignar mal una línea. Una línea que cruza el límite se marca «both» (en la muestra final no apareció ninguna).
- Los términos de reutilización de la EMA siguen sin verificar (D12). Los PDF se descargaron solo para el spike y quedan en la caché local.
- Las notas al pie se descartan por tamaño de fuente en `pdfminer-cols`; en el texto plano de las dos bibliotecas no se pueden filtrar.
- El script no está probado con pruebas automáticas; la implementación de la tarea 3.3 debe llevar fixtures con trozos de estos PDF (la salida de `samples/` sirve de referencia) y pruebas de las expresiones de encabezado.
