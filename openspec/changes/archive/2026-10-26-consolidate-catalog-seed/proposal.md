# Proposal

## Why

El catálogo actual tiene 2.376 plantas de USDA Duke (CC0) y la identidad de cada una es el nombre literal de USDA. Los usos solo se enlazan por coincidencia exacta de nombre, así que se pierden las filas registradas bajo sinónimos: la manzanilla tiene 0 usos aunque hay 91 filas bajo *Matricaria chamomilla*, y la menta tiene 0 aunque hay 49 bajo *Mentha piperita*. 1.196 de las 2.376 plantas (el 50 %) no tienen ningún uso en `catalog.db`. Tampoco hay datos para «Buscar por objetivo»: la pestaña Propiedades está vacía por diseño y no existe ninguna fuente de objetivos, seguridad ni imágenes en el catálogo.

Además, el cruce de citas es frágil: 31.629 filas de ETHNOBOT (38 %, 899 claves distintas) citan una REFERENCE que no coincide exactamente con ninguna de las 2.043 claves de las referencias de USDA, y el LONGREF propio de ETHNOBOT está vacío en todas las filas. Unas 6.055 solo difieren en formato (`Burkill,1966` frente a `Burkill, 1966`), 9.576 son `Woi.<n>` (existe la entrada `WOI`, «The Wealth of India»), 10.992 son `Eb<vol>:<pág>` (existe `EB`, «Economic Botany»), 3.040 son `Woi.Syria`, de obra poco clara, y 1.966 son otras. Hoy esas filas se descartan.

Un piloto de 20 plantas mostró que se puede consolidar varias fuentes abiertas en un registro limpio por planta con un LLM que solo elige, traduce y resume lo que está en un paquete de datos con citas, y que el costo es manejable (12.000 a 15.500 tokens por planta). También mostró que la resolución taxonómica con WCVP (Kew) recupera la sinonimia: WCVP y WFO resuelven por igual (2.125 frente a 2.127 de 2.376 plantas), pero WCVP trae distribución para el 99,6 % de las plantas, marca la homotipia (indispensable para no fusionar bergamota, lima y limón) y deja menos nombres sin aceptado (3 frente a 12). La manzanilla solo resuelve con WCVP.

Este es el primero de tres cambios. Aquí se construye la semilla consolidada y el build que la convierte en `catalog.db`; los siguientes la exponen en la API y la app.

## What Changes

- **Capa offline nueva** (herramientas de desarrollador, no van en la imagen): descarga de fuentes con versión y checksum, resolución taxonómica, paquete por planta (*bundle*), consolidación con LLM (Claude Code, una sola vez y de forma incremental) y un validador automático. El prompt, el esquema del registro, el mapa de objetivos y el validador se versionan en el repo.
- **Semilla versionada en el repo** (`data/seed/`): un registro JSON por planta más un manifiesto con versiones de fuentes, checksums, versión de prompt y modelo. Todos los entornos usan la misma semilla.
- **BREAKING (identificadores públicos)**: el ID de planta pasa a ser el slug del nombre aceptado en WCVP, generado una vez y fijo en la semilla. Cambian 629 de los 2.376 IDs actuales (el piloto estimaba unos 500); por ejemplo `rosmarinus-officinalis` pasa a `salvia-rosmarinus` y `matricaria-recutita` a `matricaria-chamomilla`. Hasta donde se sabe nada guarda IDs todavía (la app no persiste, el despliegue solo verifica `lavandula-angustifolia`, que se conserva); los IDs anteriores se guardan como alias en la semilla.
- **BREAKING (contenido)**: el universo pasa de 2.376 a 2.354 plantas en la semilla, de 2.355 en el universo (el piloto estimaba unas 2.411; `malachra-alaceaefolia` queda fuera por no tener datos en ninguna fuente) y varias plantas se fusionan o se separan según la taxonomía y el criterio de Wikipedia (los heterotípicos con artículo propio en español, o en la lista de excepciones, son plantas separadas; los demás se fusionan con revisión). Los usos, nombres y la actividad pasan a ser texto consolidado en español con cita, en lugar de las etiquetas literales de USDA.
- **Build desde la semilla**: `catalog-ingest build` lee la semilla y escribe `catalog.db` sin red y sin LLM. Se eliminan la descarga de figshare, la capa cruda `raw.db`, el adaptador de USDA y la configuración de fuentes activas.
- **Esquema ampliado sin cambiar el contrato HTTP**: los campos nuevos (sinónimos con alias, descripción, origen, tipo de aceite, objetivos, seguridad, imagen, grupos de uso con países y `reviewFlags`) se guardan en tablas nuevas. La API sigue sirviendo exactamente los mismos endpoints y campos; el cambio 2 expondrá los nuevos.
- **Dockerfile sin figshare**: la etapa `catalog` construye desde `data/seed/` y ya no descarga nada.
- **Citas abreviadas resueltas por el LLM**: el paquete conserva las claves cortas de USDA y suma las entradas candidatas de las referencias; el LLM empareja cada clave con su cita completa entre esas candidatas, sin reglas deterministas de normalización por fuente. Se espera que queden sin resolver unas 5.000 filas (6 %), marcadas «(sin resolver)» y con un `reviewFlag`.
- **Política de consolidación («variante A»)**: el LLM no aporta conocimiento propio; cada campo cita refs del paquete; se prohíben dosis, posologías, indicaciones de tratamiento y promesas de eficacia. Los objetivos salen solo de las áreas terapéuticas de la EMA con monografía o entrada de lista, y una planta tóxica según TPPT no recibe objetivos.
- **Atribución en la semilla**: la semilla guarda dataset, licencia y atribución de cada dato (WCVP, EFSA, Wikipedia, Commons, TPPT y EMA exigen atribución; Wikipedia es CC BY-SA). La sección «Fuentes» del pasaporte la muestra el cambio 2.
- **Documentación** en `docs/data/` de las fuentes, licencias, el flujo de regeneración y el modelo ampliado.

## Capabilities

### New Capabilities

- `catalog-seed`: fuentes con versión y checksum, resolución taxonómica y universo, regla de colisiones (criterio de Wikipedia con excepciones y decisiones registradas) e IDs, paquete por planta, política de consolidación y validador, formato de la semilla, regeneración incremental, `reviewFlags` y licencias.

### Modified Capabilities

- `catalog-ingest`: el ingest de USDA desde figshare se sustituye por el build desde la semilla. Se eliminan los requisitos del contrato de adaptador, la capa cruda, la consolidación multi-fuente, la identidad única por fuente, la resolución de campos de valor único, las fuentes activas y el adaptador de USDA. Se modifican el esquema neutral, el identificador público, la procedencia, la construcción determinista, la verificación del insumo, el fallo ante datos inconsistentes y «Datos sin interpretación clínica».
- `plant-passport`: el requisito de Usos deja de prohibir modelos generativos (los usos salen de una semilla consolidada con cita) y su ejemplo de nombre principal ya no depende de datos de USDA. La sección de fuentes y los créditos son del cambio 2.
- `backend-container`: la construcción del catálogo y la caché ya no descargan el ZIP de USDA ni verifican su MD5; verifican la semilla.

## Non-goals

- **Cambio 2**: exponer los campos nuevos en la API, mostrarlos en el pasaporte, la sección de fuentes, los créditos y las imágenes, y resolver IDs anteriores por alias en la API.
- **Cambio 3**: hacer funcional «Buscar por objetivo» (P06) y los resultados (P07), incluido el ajuste de nombres de objetivos en la app («Cansancio y fatiga» sustituye a «Concentración»).
- La capa de validación humana (un panel para revisar los `reviewFlags`): aquí los `reviewFlags` solo se registran en la semilla.
- El chat «Boticario» (RAG). El registro limpio se diseña para poder alimentarlo después, pero no se construye nada de él.
- El permiso para uso comercial de TPPT (Agroscope): el proyecto es académico y se usa con atribución. Si cambia el enfoque hay que pedir permiso; queda documentado.
- Fuentes descartadas por licencia o formato: AromaDb, EssOilDB, sCentInDB, FDA PPDB, Comisión E, OMS, NHPID, iNaturalist y DrugBank.
- Cambios en el contrato HTTP de `/v1`, en la app Flutter o en el despliegue de Cloud Run.

## Impact

- **Nuevo**: `tools/catalog-seed/` (Python: descarga, resolvedor, paquetes, prompt, esquema, mapa de objetivos, validador), `data/seed/` (registros y manifiesto, unos 2.400 archivos de unos 6,5 KB).
- **Backend**: `backend/catalog-ingest` (módulo nuevo de lectura de la semilla; se retiran `usda.rs`, `raw.rs`, `download.rs`, el contrato `SourceAdapter` y `default_registry`), `backend/catalog-core` (migración y filas de las tablas nuevas, `SCHEMA_VERSION`), `data/sources.toml` (se elimina). `backend/catalog-api` no cambia de código; cambian sus pruebas que fijan IDs o conteos (`tests/real_catalog.rs`) y el fixture de contraste `plant_catalog.json`.
- **Contenedor**: `Dockerfile` (etapa `catalog`), `compose.yaml` si referencia la caché, y `.gitignore`/`.dockerignore` (`data/.cache/` y `data/work/` fuera del contexto).
- **Datos**: `data/.cache/` (descargas con checksum, ya ignorada), `data/work/` (paquetes y salidas intermedias, ignorado), `data/build/catalog.db` (cambia el contenido y el hash).
- **Documentación**: `docs/data/usda-catalog.md`, `docs/data/modelo-de-datos.md`, un documento nuevo de fuentes y licencias, `backend/README.md` y `README.md` en lo que describan el ZIP de USDA.
- **App y despliegue**: sin cambios de código. Los fixtures de la app (`rosmarinus-officinalis` y otros) son archivos estáticos y no se rompen; la verificación posterior del despliegue usa `lavandula-angustifolia`, cuyo ID debe conservarse.
- **Costo y riesgo**: la generación completa (unos 23 millones de tokens, unos 240 lotes) es la última tarea y requiere una decisión explícita del usuario sobre el modo de ejecución. Los términos de reutilización de la EMA y de TPPT no están verificados contra el texto legal (véase `design.md`).
