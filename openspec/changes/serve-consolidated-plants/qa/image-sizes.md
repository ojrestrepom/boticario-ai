# Medición de tamaños de imágenes (tarea 6.4)

Medición hecha el 2026-10-26 sobre `data/build/catalog.db` (tabla `plant_image`, 1.860 filas, todas en `upload.wikimedia.org`) con peticiones `HEAD` de una en una, pausa de 1,1 s y `User-Agent: BoticarioAI/0.1.0`, sin email ni otros datos.

La muestra son 20 plantas: lavanda, manzanilla (romana y común), menta (`mentha-x-piperita`), romero (`salvia-rosmarinus`), eucalipto y 14 al azar.

Todas las peticiones `HEAD` devolvieron `Content-Length`, así que no hizo falta `GET` con rango.

Wikimedia respondió 429 con `Retry-After` en varias peticiones (dos veces con 600 s); la medición esperó ese tiempo antes de reintentar.

## Tamaños de los originales

| Planta | Archivo | Tamaño | Tipo | Código |
|---|---|---|---|---|
| chamaemelum-nobile | Anthemis_nobilis_prg_1.jpg | 3.12 MB | image/jpeg | 200 |
| eucalyptus-globulus | Eucalyptus_globulus_globulus_buds.jpg | 0.09 MB | image/jpeg | 200 |
| lavandula-angustifolia | Lavandula_angustifolia_-_K%C3%B6hl... | 0.16 MB | image/jpeg | 200 |
| matricaria-chamomilla | Matricaria_recutita_0.1_R.jpg | 4.80 MB | image/jpeg | 200 |
| mentha-x-piperita | Mentha_%C3%97_piperita_-_K%C3%B6hl... | 0.13 MB | image/jpeg | 200 |
| euphrasia-officinalis | Euphrasia_officinalis_subsp._rostk... | 3.10 MB | image/jpeg | 200 |
| sambucus-racemosa | Sambucus_racemosa_%281%29.jpg | 0.44 MB | image/jpeg | 200 |
| helianthus-annuus | Helianthus_annuus_exposed_2004-05-... | 0.15 MB | image/jpeg | 200 |
| schinus-molle | Arequipa_-_Canyon_de_Colca_123_Sch... | 2.40 MB | image/jpeg | 200 |
| petiveria-alliacea | Petiveria_-_Ehret.jpg | 0.02 MB | image/jpeg | 200 |
| ocimum-kilimandscharicum | Westcoastlady.JPG | 0.85 MB | image/jpeg | 200 |
| caraipa-densifolia | Caraipa_densifolia_Mart..jpg | 0.63 MB | image/jpeg | 200 |
| strophanthus-hispidus | Strophanthus_hispidus_-_K%C3%B6hle... | 0.16 MB | image/jpeg | 200 |
| parthenium-integrifolium | Parthenium-integrifolium-wild-quin... | 2.43 MB | image/jpeg | 200 |
| juniperus-communis | Juniperus_communis_fruits_-_Keila.jpg | 16.04 MB | image/jpeg | 200 |
| chamaecytisus-albus | Chamaecytisus_albus_2016-07-19_325... | 7.47 MB | image/jpeg | 200 |
| pogostemon-cablin | Pogostemon_cablin_001.jpg | 1.51 MB | image/jpeg | 200 |
| grindelia-camporum | Grindelia_camporum_002.JPG | 1.53 MB | image/jpeg | 200 |
| berberis-aquifolium | %28MHNT%29_Berberis_aquifolium_hab... | 74.65 MB | image/jpeg | 200 |
| salvia-rosmarinus | P1090247%284x3%29-Rosmarinus_offic... | 1.04 MB | image/jpeg | 200 |

## Resumen

- Mínimo 0,02 MB (21.138 bytes), mediana 1,28 MB (1.275.597 bytes) y máximo 74,65 MB (`berberis-aquifolium`).
- 8 de 20 originales (40 %) superan 2 MB y 11 de 20 superan 1 MB. Dos pasan de 7 MB (`chamaecytisus-albus`, 7,5 MB; `juniperus-communis`, 16,0 MB) y el máximo supera 74 MB.
- Tipo de contenido: `image/jpeg` en las 20. En toda la tabla las extensiones son 1.806 `.jpg`, 13 `.jpeg`, 36 `.png`, 3 `.gif` y 2 `.svg`, así que la app debe tolerar PNG y que un SVG no se decodifique (se cae al arte local).
- Lavanda (161 KB), menta (129 KB) y eucalipto (90 KB) son ligeras. Manzanilla común (4,8 MB) y manzanilla romana (3,1 MB) son pesadas.

## Miniaturas de ancho acotado

Wikimedia sirve miniaturas en `upload.wikimedia.org` con la ruta `/wikipedia/commons/thumb/<a>/<ab>/<archivo>/<ancho>px-<archivo>`. Se construyen a partir de `image.url` insertando `thumb/` tras `/commons/` y añadiendo `/<ancho>px-<archivo>` al final, con el nombre de archivo tal como viene (ya codificado).

Solo admite anchos estándar: `640px` respondió 400 (HTML de error) para las 20 plantas, mientras que `500px` y `960px` respondieron 200 `image/jpeg`.

Con `500px` se midieron: lavanda 82 KB (original 161 KB), `berberis-aquifolium` 115 KB (de 74,65 MB), `juniperus-communis` 82 KB (de 16 MB), manzanilla común 33 KB (de 4,8 MB), `petiveria-alliacea` 40 KB (el original pesa 21 KB, así que amplía) y eucalipto 42 KB (original 90 KB). Con `960px`, lavanda 196 KB.

Para PNG, GIF y SVG la miniatura se serviría rasterizada; no se probó.

## Recomendación

Como el original supera 2 MB en el 40 % de la muestra y llega a 74 MB, conviene pedir un ancho acotado (500 px para la cabecera). La tarea 6.4 pide abrir la decisión con el usuario antes de seguir en ese caso, así que no se implementó la miniatura: `PlantImagePolicy.providerFor` carga hoy `image.url` tal cual.

La opción es una función pura que convierta `image.url` en la URL de miniatura (solo si la ruta es `/wikipedia/commons/<a>/<ab>/<archivo>`) y que la política aplique en la cabecera; si la ruta no encaja se usaría el original o el arte local. La decisión es del usuario.
