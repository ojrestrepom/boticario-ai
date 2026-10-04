# Catálogo local: procedencia y reproducción

Esta guía documenta el asset curado `app/assets/data/plant_catalog.json` (schema 1). No es una importación completa de la base USDA ni una afirmación sobre la vigencia taxonómica o clínica de sus datos.

## Fuente, archivo y fechas

- Dataset archivado: [USDA Dr. Duke's Phytochemical and Ethnobotanical Databases, Ag Data Commons, artículo 24660351, versión 1](https://agdatacommons.nal.usda.gov/articles/dataset/Dr_Duke_s_Phytochemical_and_Ethnobotanical_Databases/24660351).
- Archivo original: [`Duke-Source-CSV.zip`, file ID 43363335](https://ndownloader.figshare.com/files/43363335) (6,033,990 bytes; MD5 `45ae44a0544586b8ac22a232beaac344`). La ficha de API del artículo es [v2](https://api.figshare.com/v2/articles/24660351).
- Diccionario de datos del artículo: [file ID 43363338](https://ndownloader.figshare.com/files/43363338) (archivo complementario; no se empaqueta en el asset).
- Licencia declarada por USDA: [CC0](https://phytochem.nal.usda.gov/about).
- Inspección del ZIP y del asset: 2026-10-01. `inspectedOn` es la fecha de esa inspección, no una fecha de publicación, captura ni periodo cubierto.
- Cita del artículo registrada por la API de Figshare y reflejada en el asset: Duke, James A. (2016). *Dr. Duke's Phytochemical and Ethnobotanical Databases*. Ag Data Commons. Dataset. <https://doi.org/10.15482/USDA.ADC/1239279>.
- La página [About de USDA](https://phytochem.nal.usda.gov/about) recomienda citar el recurso como 1992–2016. Ese rango pertenece a la recomendación de cita de USDA, no al texto de cita de la API del artículo; tampoco establece la cobertura temporal efectiva de este ZIP, que no fue determinada.

El tamaño medido del asset es **80,391 bytes**. No es el tamaño del archivo empaquetado por Flutter/SDK, ni del ZIP de origen. El ID de planta `usdaPlantId` refleja el valor fuente `FNFNUM` del catálogo; no se expande el acrónimo FNF, cuyo significado no se verificó, ni se presenta como identificador universal. Los nombres comunes en español (`Lavanda`, `Eucalipto`, `Romero`, `Manzanilla`, `Menta`) son etiquetas editoriales tomadas del mockup, no nombres traducidos/verificados por USDA. El texto científico mantiene literalmente la forma archivada; no se valida sinonimia vigente.

## Qué conserva el asset

El JSON tiene `schemaVersion`, `provenance`, `references` y `plants`. Cada planta contiene identidad (`usdaPlantId`, `editorialCommonName`, `sourceScientificName`, `kind`), `origin` y `description` (actualmente `null`), `identitySource`, `parts` con selectores de fila fuente, `traditionalUses` con selector de origen y `referenceIds`, y `propertiesNotEvaluated: true`. Las referencias llevan `id`, cita literal y selector `REFERENCES`.

Resumen de las filas curadas (usos son filas, no actividades únicas):

| FNFNUM | Nombre editorial | Nombre científico literal | Partes | Usos elegibles | Referencias usadas |
|---:|---|---|---:|---:|---|
| 544 | Lavanda | `Lavandula angustifolia` | 4 | 10 | Steinmetz |
| 401 | Eucalipto | `Eucalyptus globulus` | 15 | 51 | FontQuer, Hartwell, Krochmal, Leung, Martinez, Pittier, Steinmetz, Uphof |
| 873 | Romero | `Rosmarinus officinalis` | 9 | 60 | Altschul, Brutus, FontQuer, Gupta, Hartwell, Leung, Martinez, Pittier, Steinmetz, Takeda, Uphof |
| 605 | Manzanilla | `Matricaria recutita` | 3 | 0 | — |
| 619 | Menta | `Mentha x piperita subsp. nothosubsp. piperita` | 5 | 0 | — |

En conjunto son 36 entradas de parte, 121 usos elegibles y 12 referencias bibliográficas distintas.

Cada fila de parte traza a `FARMACY_NEW(FNFNUM,PPCO)` y al nombre de código `PARTS(PPCO,PPNA)`. `FARMACY_NEW` es registro fitoquímico/componente; no respalda por sí mismo eficacia o propiedad medicinal. Sus nombres como `Essential Oil` tampoco crean una ficha de aceite: el catálogo de aceites queda vacío y `kind` es `plant`, incluso cuando una etiqueta de parte menciona aceite esencial.

Cada uso conserva `ETHNOBOT` con `GENUS`, `SPECIES`, `TAXON`, `ACTIVITY`, `REFERENCE` y `ETHNO`, junto a su clave bibliográfica resoluble. Las cadenas `ACTIVITY` y `LONGREF` se conservan como aparecen en el archivo (incluidos errores tipográficos presentes en la fuente; no se corrigen ni traducen). La fecha de inspección y trazabilidad no hacen que esas entradas sean evidencia médica. Son, como máximo, registros tradicionales atribuidos por esa base; no son consejo, dosis, recomendación ni afirmaciones clínicas sustentadas por la cita genérica de USDA.

## Selector y criterio de curación

1. Leer `FNFTAX.csv` y localizar por `FNFNUM` las cinco identidades. `TAXON`, `GENUS`, `SPECIES` y, cuando exista, `SUBSPECIES` se comparan como campos de identidad. El `TAXON` fuente da el nombre científico literal. No se sustituyen formas por nomenclatura actual.
2. Para cada FNFNUM, tomar los códigos `PPCO` asociados a ese número en `FARMACY_NEW.csv`; resolver cada código por `PPCO` en `PARTS.csv` y guardar el `PPNA` archivado. Se conserva la etiqueta fuente, sin traducirla. Esto solo documenta asociaciones fitoquímicas/partes del dataset.
3. `ETHNOBOT.csv` no tiene FNFNUM. Cruzar los cinco registros de identidad con `GENUS`, `SPECIES` **y `TAXON` exactos**; no usar coincidencia parcial, alias o solo nombre común. Guardar la fila individual seleccionada, en particular su `ACTIVITY`, `REFERENCE` y `ETHNO`.
4. Resolver `REFERENCE` en `REFERENCES.csv` mediante una única coincidencia de clave no vacía y `LONGREF` no vacío. Se requiere una resolución inequívoca. Excluir usos cuyo taxón no coincide exactamente, cuya fila es ambigua, o cuyo `REFERENCE` falta/no resuelve. No se descarta ni altera la cita fuente una vez resuelta.

El criterio anterior produce para estos cinco taxones, en el ZIP verificado: Lavandula 13 coincidencias taxonómicas exactas, 10 elegibles y 3 referencias no resolubles excluidas; Eucalyptus 57, 51 y 6; Rosmarinus 92, 60 y 32; Matricaria 0, 0 y 0; Mentha 0, 0 y 0. Las filas excluidas no se incorporan al asset. En particular, Manzanilla y Menta sin usos elegibles solo significa que no se encontraron filas ETHNOBOT que satisfagan este cruce y criterio; no significa que esas plantas carezcan de usos.

La normalización usada al preparar selectores textuales es limitarse a quitar espacios exteriores (`strip`/`trim`) al leer y comparar celdas; no se cambia mayúsculas, puntuación, acentos, taxón, actividad ni texto bibliográfico. La salida JSON registra los valores exactos de selección tras ese recorte, por lo que la documentación distingue la forma almacenada de posibles espacios externos del CSV original. No se completa `origin` ni `description`; ambas ausencias son `null`. No se incorporan dosis. `propertiesNotEvaluated: true` indica que este catálogo no evaluó propiedades medicinales.

### Ejemplo de traza en el JSON

```json
{"usdaPlantId":544,"identitySource":{"table":"FNFTAX","selectors":{"FNFNUM":544,"TAXON":"Lavandula angustifolia","GENUS":"Lavandula","SPECIES":"angustifolia"}},"parts":[{"name":"Flower","sourceCode":"FL","sources":[{"table":"FARMACY_NEW","selectors":{"FNFNUM":544,"PPCO":"FL"}},{"table":"PARTS","selectors":{"PPCO":"FL","PPNA":"Flower"}}]}],"traditionalUses":[{"activity":"Carminative","source":{"table":"ETHNOBOT","selectors":{"GENUS":"Lavandula","SPECIES":"angustifolia","TAXON":"Lavandula angustifolia","ACTIVITY":"Carminative","REFERENCE":"Steinmetz","ETHNO":"10546"}},"referenceIds":["Steinmetz"]}]}
```

El mismo patrón de selectores permite reproducir las relaciones de cada fila del asset sin duplicar aquí las 121 filas de uso. El ejemplo no atribuye eficacia a la actividad.

## Correspondencia con P04 (Explorar)

La lista de P04 presenta el catálogo local; cada fila se corresponde con un registro `plants` del JSON y sus valores se muestran así:

| Elemento de P04 | Campo/origen | Alcance y límite |
|---|---|---|
| Nombre principal (por ejemplo, «Lavanda») | `editorialCommonName` | Etiqueta editorial del mockup en español; no es traducción ni nombre común validado por USDA. |
| Nombre secundario | `sourceScientificName`, copiado de `identitySource.selectors.TAXON` | Forma taxonómica literal del archivo inspeccionado; no se actualiza ni valida sinonimia vigente. |
| Identidad usada al seleccionar una fila | `usdaPlantId`, correspondiente al `FNFNUM` archivado | Identificador interno del catálogo/app, no identificador universal; el toque llama al callback con este valor. La ruta destino aún no forma parte de esta correspondencia. |
| Icono de flor | Decoración local `Icons.local_florist` | Icono Material genérico; no es una fotografía ni una ilustración identificativa de la especie. |
| Búsqueda | Normalización de consulta y comparación contra `editorialCommonName` y `sourceScientificName` | Coincidencia por texto normalizado (mayúsculas/minúsculas, acentos y espacios repetidos/exteriores), no alias ni búsqueda en USDA/red. No se inventa un nombre común en español a partir de la fuente. |
| Filtros «Todas», «Plantas», «Aceites» | Filtro `kind` de los registros | El catálogo actual contiene cinco registros `plant` y ningún registro `oil`: «Aceites» muestra su estado vacío. Una parte llamada `Essential Oil` en `parts` no convierte la planta en aceite ni crea un producto/ficha de aceite. |

P04 inicia en «Todas» con consulta vacía. Carga, error local con «Reintentar», catálogo sin resultados y filtro de aceites vacío son estados distintos; ninguno rellena contenido ausente ni afirma ausencia real de plantas/aceites fuera de este conjunto curado. La fila solo expone identidad editorial/científica y selección: no muestra partes, usos ni propiedades. Los límites de los datos de partes/usos y su trazabilidad descritos arriba no cambian por aparecer la planta en la lista.

## Correspondencia con P05 (Pasaporte)

P05 resuelve `usdaPlantId` contra los cinco registros de `plants` del asset. En `General`, origen y descripción `null` se muestran literalmente como «No disponible en fuente»; las partes muestran sus nombres/códigos registrados desde `FARMACY_NEW` + `PARTS`, no recomendaciones. El tipo de aceite figura como no aplicable: los registros de parte `Essential Oil` no son identidad de un aceite. La pestaña `Propiedades` indica que no hay propiedades medicinales evaluadas en este catálogo: `FARMACY_NEW` no es evaluación de propiedades.

Los campos de procedencia visibles en `General` (fuente, licencia CC0, versión, IDs de dataset/archivo, URL, fecha `inspectedOn` y cita recomendada) describen metadata del snapshot. La fecha de inspección no indica cobertura temporal; el rango 1992–2016 pertenece a la cita recomendada de USDA. Ni esos metadatos ni la cita general USDA son respaldo clínico de los usos.

En `Usos`, cada fila elegible muestra el `ETHNOBOT.ACTIVITY` literal en inglés, con la etiqueta «Registro tradicional» y la aclaración «No es una recomendación de uso ni evidencia de eficacia clínica». Cada actividad corresponde a su fila identificada por `GENUS`, `SPECIES`, `TAXON`, `ACTIVITY`, `REFERENCE` y `ETHNO`; cada `referenceId` debe resolver a una entrada `REFERENCES` con `LONGREF`. La bibliografía de `General` se deduplica por ID de referencia entre los usos de la planta; en `Usos` la cita vuelve a aparecer junto a cada registro que la usa. Tanto la actividad como la cita conservan el texto fuente, incluidos errores tipográficos, sin traducir ni corregir.

El asset contiene 10 usos elegibles para Lavanda, 51 para Eucalipto, 60 para Romero y cero para Manzanilla y Menta. Para ambas P05 muestra «No hay usos tradicionales con referencia verificable disponibles». Esto indica exactamente que no hay usos elegibles en este cruce taxonómico y bibliográfico del snapshot; no significa ausencia general de usos. Las exclusiones por identidad ambigua/no exacta o referencia ausente/no resoluble siguen aplicándose como se describe en «Selector y criterio de curación». No se añaden dosis, equivalencias modernas ni otras fuentes.

## Validación opcional desde la raíz del repositorio

El bloque siguiente usa solo Python estándar. Para esta validación opcional, descarga el archivo público una vez y lo mantiene en memoria, verifica su tamaño/MD5, inspecciona las tablas CSV sin extraerlas a disco, y valida los selectores/relaciones y el recuento de cada fila actual del asset. Ejecútese desde la raíz del repo. Requiere conectividad para descargarlo durante esa validación; no guarda ni requiere almacenar el ZIP en el repositorio, instalar paquetes, agregar scripts, cambiar CI ni habilitar HTTP en la app. No es una verificación offline ni debe usarse como test offline.

```sh
python3 - <<'PY'
import csv, hashlib, io, json, urllib.request, zipfile

asset = json.load(open('app/assets/data/plant_catalog.json', encoding='utf-8'))
url = 'https://ndownloader.figshare.com/files/43363335'
data = urllib.request.urlopen(url, timeout=60).read()
assert len(data) == asset['provenance']['fileSizeBytes'] == 6033990
assert hashlib.md5(data).hexdigest() == asset['provenance']['md5'] == '45ae44a0544586b8ac22a232beaac344'
archive = zipfile.ZipFile(io.BytesIO(data))

def table(name):
    # CSV tables in this source archive decode as Windows-1252.
    with archive.open(name + '.csv') as stream:
        text = stream.read().decode('cp1252')
    return list(csv.DictReader(io.StringIO(text)))

fnftax, farmacy, parts = table('FNFTAX'), table('FARMACY_NEW'), table('PARTS')
ethnobot, references = table('ETHNOBOT'), table('REFERENCES')
def val(row, key):
    value = row.get(key, '')
    return value.strip() if isinstance(value, str) else value

ref_rows = {}
for row in references:
    key = val(row, 'REFERENCE')
    if key and val(row, 'LONGREF'):
        ref_rows.setdefault(key, []).append(val(row, 'LONGREF'))
curated_refs = {r['id']: r for r in asset['references']}
curated_plants = asset['plants']
assert len(curated_plants) == 5
counts = []
for plant in curated_plants:
    identity = plant['identitySource']['selectors']
    taxon_rows = [r for r in fnftax if val(r, 'FNFNUM') == str(identity['FNFNUM'])]
    assert len(taxon_rows) == 1
    taxon = taxon_rows[0]
    assert all(val(taxon, k) == str(identity[k]) for k in ('FNFNUM', 'TAXON', 'GENUS', 'SPECIES'))
    assert plant['sourceScientificName'] == identity['TAXON']
    for part in plant['parts']:
        farmacy_sel = part['sources'][0]['selectors']
        assert farmacy_sel['FNFNUM'] == plant['usdaPlantId']
        assert farmacy_sel['PPCO'] == part['sourceCode']
        assert any(val(r, 'FNFNUM') == str(plant['usdaPlantId']) and val(r, 'PPCO') == part['sourceCode'] for r in farmacy)
        part_sel = part['sources'][1]['selectors']
        assert part_sel['PPCO'] == part['sourceCode'] and part_sel['PPNA'] == part['name']
        assert any(val(r, 'PPCO') == part_sel['PPCO'] and val(r, 'PPNA') == part_sel['PPNA'] for r in parts)
    exact = [r for r in ethnobot if all(val(r, k) == val(taxon, k) for k in ('GENUS', 'SPECIES', 'TAXON'))]
    eligible = [r for r in exact if val(r, 'REFERENCE') and len(ref_rows.get(val(r, 'REFERENCE'), [])) == 1]
    uses = plant['traditionalUses']
    assert len(uses) == len(eligible)
    for use in uses:
        sel = use['source']['selectors']
        matches = [r for r in eligible if all(val(r, k) == str(sel[k]) for k in ('GENUS', 'SPECIES', 'TAXON', 'ACTIVITY', 'REFERENCE', 'ETHNO'))]
        assert len(matches) == 1
        assert use['referenceIds'] == [sel['REFERENCE']]
        ref = curated_refs[sel['REFERENCE']]
        ref_sel = ref['source']['selectors']
        assert ref_sel['REFERENCE'] == sel['REFERENCE']
        assert ref_sel['LONGREF'] == ref['citation'] == ref_rows[sel['REFERENCE']][0]
    counts.append((plant['usdaPlantId'], len(exact), len(eligible), len(exact) - len(eligible)))
assert counts == [(544, 13, 10, 3), (401, 57, 51, 6), (873, 92, 60, 32), (605, 0, 0, 0), (619, 0, 0, 0)]
print('OK; asset bytes:', len(open('app/assets/data/plant_catalog.json', 'rb').read()), '; (FNFNUM, exact, eligible, excluded):', counts)
PY
```

Tests de fixture y pruebas CI del catálogo leen el JSON local; no descargan ni requieren el ZIP, y siguen siendo ejecutables sin red. El mapeo visual de P04 documentado arriba corresponde a la implementación actual de la lista. La correspondencia descrita para P05 documenta la pantalla y sus límites, no es una declaración de release ni implica que el recorrido integrado de Android esté listo: la navegación de las tareas OpenSpec 4.x sigue pendiente.
