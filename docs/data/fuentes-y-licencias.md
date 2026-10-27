# Fuentes y licencias de la semilla del catálogo

Esta guía lista cada fuente que alimenta la semilla del catálogo (`data/seed/`), con su versión o snapshot, licencia, atribución y página, las notas que exigen algunas licencias y las fuentes que se descartaron. La fuente de verdad de los datos es `tools/catalog-seed/sources.json`, que valida `catalog_seed/sources.py`; el sellado (`seal`) copia cada fuente activa al manifiesto de la semilla (`data/seed/manifest.json`), y `catalog-ingest build` copia ese nombre, versión, licencia, URL de la licencia, atribución, URL y checksum a la tabla `source` de `catalog.db`. Cómo se usa la semilla está en el [modelo de datos](modelo-de-datos.md); la guía de USDA está en [la fuente USDA](usda-catalog.md).

Los términos de reutilización de la EMA y de TPPT no se verificaron contra el texto legal (véanse las notas más abajo). Esta guía describe lo que el repositorio declara; no es asesoría legal.

## Resumen

La licencia y la atribución son las del campo `license` y `attribution` de `sources.json`. La URL de la licencia (`licenseUrl`, guardada en `source.license_url`) es opcional: es la URL oficial de Creative Commons en las fuentes CC0 (`usda`, `wfo`, `wikidata`), CC BY 3.0 (`wcvp`), CC BY 4.0 (`efsa`) y CC BY-SA 4.0 (`wikipedia_es`), y es `null` en `commons` (la licencia es por archivo y cada imagen guarda la suya), `ema_json`, `ema_pdf` y `tppt` (términos propios). El tamaño y el checksum de cada archivo están en ese mismo archivo.

| Id | Fuente | Versión o snapshot | Licencia | Página |
| --- | --- | --- | --- | --- |
| `usda` | USDA Dr. Duke's Phytochemical and Ethnobotanical Databases | Ag Data Commons 24660351, v1 (`Duke-Source-CSV.zip`, file ID 43363335) | CC0 | [doi.org/10.15482/USDA.ADC/1239279](https://doi.org/10.15482/USDA.ADC/1239279) |
| `wcvp` | World Checklist of Vascular Plants (Kew) | WCVP v16 (`wcvp.zip`, Kew SFTP) | CC BY 3.0 | [powo.science.kew.org](https://powo.science.kew.org/) |
| `wfo` | World Flora Online | Plant List 2026-06 (Zenodo 20782718, `_DwC_backbone_R.zip`) | CC0 | [zenodo.org/records/20782718](https://zenodo.org/records/20782718) |
| `ema_json` | EMA, Herbal medicines for human use (listado) | Snapshot fijado el 2026-10-20, `meta.timestamp` 2026-10-20T18:00:54Z | Reutilización citando a la EMA (términos no verificados) | [ema.europa.eu](https://www.ema.europa.eu/) |
| `ema_pdf` | EMA, monografías y declaraciones públicas del HMPC | 205 PDF de las fichas del snapshot de `ema_json`, con tamaño y sha256 por archivo | Reutilización citando a la EMA (términos no verificados) | [ema.europa.eu](https://www.ema.europa.eu/) |
| `tppt` | Agroscope, Toxic Plants and Phytotoxins database (TPPT) | Snapshot fijado el 2026-10-20 (`tppt-db.zip`, SQLite fechada 2026-05-11 en el ZIP) | Uso abierto citando la fuente; el uso comercial requiere permiso (opendata.swiss) | [agroscope.admin.ch](https://www.agroscope.admin.ch/) |
| `efsa` | EFSA Compendium of Botanicals | 2016 (Zenodo 996024, publicado 2016-07-05; `BOTANIC.xls` y `ENDPOINTSTUDY.xls`) | CC BY 4.0 | [doi.org/10.5281/zenodo.996024](https://doi.org/10.5281/zenodo.996024) |
| `wikidata` | Wikidata | Wikidata Query Service, consulta por nombre científico (P225); cada respuesta se guarda con su fecha | CC0 1.0 | [wikidata.org](https://www.wikidata.org) |
| `wikipedia_es` | Wikipedia en español | API REST `page/summary` de los artículos enlazados desde Wikidata; cada respuesta se guarda con su revisión y fecha | CC BY-SA 4.0 | [es.wikipedia.org](https://es.wikipedia.org) |
| `commons` | Wikimedia Commons | API `imageinfo` con `extmetadata` de las imágenes P18 de Wikidata; cada respuesta se guarda con su fecha | Por archivo: CC0, dominio público, CC BY o CC BY-SA | [commons.wikimedia.org](https://commons.wikimedia.org) |

## Qué aporta cada fuente y cómo se atribuye

- **USDA (CC0).** Plantas, nombres comunes, partes con compuestos, usos tradicionales y sus referencias. Atribución: Duke, James A. (2016). Dr. Duke's Phytochemical and Ethnobotanical Databases. Ag Data Commons. <https://doi.org/10.15482/USDA.ADC/1239279>. Detalle en [la guía de USDA](usda-catalog.md).
- **WCVP (CC BY 3.0).** Backbone taxonómico principal: nombre aceptado, sinónimos, homotipia y distribución. Atribución obligatoria: Royal Botanic Gardens, Kew. World Checklist of Vascular Plants (WCVP), v16. <https://powo.science.kew.org/>. La licencia es la que declara el README del dataset.
- **WFO (CC0).** Respaldo: se usa solo si WCVP no resuelve un nombre y WFO da un único aceptado. Esas plantas llevan el `reviewFlag` `respaldo-wfo`. Atribución: World Flora Online (2026). WFO Plant List, June 2026. Zenodo. <https://zenodo.org/records/20782718>.
- **EMA, JSON y PDF.** Áreas terapéuticas con monografía de la UE o entrada de lista (de ellas salen los objetivos) y las secciones de contraindicaciones, advertencias e interacciones de los PDF (de ellas sale parte de la seguridad). Atribución: European Medicines Agency (EMA). Herbal medicines for human use. <https://www.ema.europa.eu/>.
- **TPPT (Agroscope).** Toxicidad humana de las plantas, que fija el nivel de seguridad y anula los objetivos de una planta muy tóxica. Atribución: Agroscope (Swiss Confederation). TPPT, Toxic Plants and Phytotoxins database. <https://www.agroscope.admin.ch/>.
- **EFSA (CC BY 4.0).** Sustancias de posible preocupación para la salud humana: una planta con alguna sustancia de la lista versionada de alta preocupación recibe como mínimo nivel medio de seguridad. Atribución obligatoria: EFSA (2016). EFSA's compendium of botanicals. Zenodo. <https://doi.org/10.5281/zenodo.996024>.
- **Wikidata (CC0).** Nombres comunes en español, ítems de Wikipedia y de imagen, filtrados a los nombres que resuelven al aceptado de la planta para no mezclar homónimos.
- **Wikipedia en español (CC BY-SA 4.0).** Resumen del artículo, que alimenta `description`, y el criterio de la regla de colisiones. Véase la nota siguiente.
- **Commons (licencia por archivo).** La imagen de la planta. Véase la regla de licencias más abajo.

## Notas de licencia

### Términos de la EMA sin verificar

La reutilización de los datos de la EMA se declara como «citando a la EMA», según lo que dice el portal, pero no se verificó contra el texto legal de los términos de uso. Es una condición abierta del cambio `consolidate-catalog-seed`: hay que verificarla antes de publicar la app. Hasta entonces, cada dato que sale de la EMA lleva su ref y la fuente figura en la atribución.

### TPPT: uso académico, con permiso si cambia el enfoque

Según opendata.swiss, el uso de TPPT es abierto citando la fuente y el uso comercial requiere permiso. Tampoco se verificaron más términos en el portal de Agroscope, ni el texto legal. El proyecto es académico y usa TPPT con atribución a Agroscope. Si el enfoque cambia a uno comercial, hay que pedir permiso a Agroscope antes de publicar. Esto queda documentado como una limitación aceptada, no resuelta.

### Wikipedia: CC BY-SA 4.0

El resumen de Wikipedia que alimenta `description` probablemente es una obra derivada, así que ese campo se registra con la licencia CC BY-SA 4.0 y el enlace al artículo (el ref de `wikipedia_es` con esa licencia exige `url`, y el validador lo comprueba). El resto del registro es una compilación con licencias mixtas, y cada dato conserva su ref, dataset y licencia (`reference.dataset`, `reference.license`, `reference.url` en `catalog.db`). La licencia CC BY-SA obliga a conservar la licencia en lo derivado y a atribuir a los autores, cuyo historial lista cada artículo. La sección «Fuentes» y los créditos que muestran todo esto en la app son del cambio siguiente, `serve-consolidated-plants`.

Mantener Wikipedia fue una decisión del usuario. Retirarla después es un cambio de configuración: se pone `"enabled": false` en la fuente `wikipedia_es` de `sources.json`, `plan` marca solo las plantas afectadas y `description` queda `null` o se resume de otras fuentes del paquete.

### Imágenes de Commons: licencias admitidas

Solo se admite una imagen con licencia CC0, dominio público, CC BY o CC BY-SA, en cualquier versión y variante portada. La atribución es obligatoria en CC BY y CC BY-SA, y cada imagen guarda autor, URL de la página, licencia, URL de la licencia y si la atribución es obligatoria (`plant_image`). Se descartan, con su motivo:

- `no-comercial` (NC) y `sin-derivadas` (ND): una restricción NC o ND prima sobre la familia, así que CC BY-NC-SA no cuenta como CC BY-SA.
- `gfdl`: GFDL sola. Una imagen con GFDL y además CC BY-SA se admite por la segunda.
- `otra-licencia`: licencia conocida pero fuera de la lista, como Free Art License.
- `licencia-desconocida`: sin metadatos de licencia.
- `sin-autor`: exige atribución y no trae ni `Artist` ni `Credit`, así que no se podría atribuir.
- `archivo-no-encontrado`.

La misma regla la aplican el validador de las herramientas y la construcción de `catalog.db` (error `UnsupportedImageLicense`).

## Fuentes descartadas

Las herramientas rechazan estas fuentes con un mensaje específico («la fuente '…' está descartada y no puede declararse») y cualquier otra que no esté en la lista de admitidas: AromaDb, EssOilDB, sCentInDB, FDA PPDB, Comisión E, OMS, NHPID, iNaturalist y DrugBank. La propuesta del cambio las descarta «por licencia o formato». El repositorio no registra un motivo por fuente: no se afirma aquí uno que no esté documentado, y volver a evaluar una de ellas exige revisar su licencia y su formato y modificar `ADMITTED_SOURCES` y `DISCARDED_SOURCES` en `catalog_seed/sources.py`.

## Cómo cambiar una fuente

- Retirar una fuente: poner `"enabled": false` en `sources.json`. Sus filas y refs salen de los paquetes, `plan` regenera solo las plantas afectadas y el manifiesto deja de listarla.
- Actualizar un snapshot (EMA, TPPT): poner `size` y `checksum` en `null`, borrar el archivo de la caché y ejecutar `python3 -I tools/catalog-seed/cli.py pin --source <id>`. El cambio de checksum queda visible en Git.
- Añadir una fuente nueva: véase «Cómo añadir una fuente nueva a las herramientas» en el [modelo de datos](modelo-de-datos.md).
