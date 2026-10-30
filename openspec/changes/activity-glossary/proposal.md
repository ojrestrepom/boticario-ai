# Proposal

## Why

La pestaña `Usos` titula cada grupo con la actividad que Dr. Duke registra y la semilla traduce. Muchas se entienden solas (Fiebre, Tos, Diarrea), pero otras son términos farmacéuticos antiguos que el usuario no entiende: Diurético, Tónico, Astringente, Carminativo, Anodino, Emenagogo, Demulcente, Emoliente, Sudorífico, Emético, Depurativo, Estomacal y otros.

Las 200 actividades más frecuentes cubren el 80 % de los 17.160 grupos visibles, y unos 85 términos de este tipo suman por sí solos el 35 % de los grupos (6.031). El usuario decidió el 2026-10-29 que bajo esos términos vaya una explicación breve, tomada de fuentes abiertas citadas y no escrita con conocimiento del modelo: Wikcionario en español y, para los términos que este no tiene o define de forma circular o insuficiente («Que estimula», «Que purga», «Calmante»), Wikipedia en español.

## What Changes

- **Glosario en la semilla.** Un archivo nuevo `data/seed/glossary.json` con, por término, la fuente y el texto: el literal de una acepción de Wikcionario recortado a la primera oración o, en Wikipedia, la primera oración del artículo si define bien el término o, si no basta, una paráfrasis breve hecha solo con el texto del artículo y marcada como adaptada. Cada fila lleva la URL permanente de la revisión, la licencia (CC BY-SA 4.0) y la fecha de descarga. Se arma con el mismo proceso de `tools/catalog-seed`: lista versionada de términos, descarga con caché y revisión fija, validación y sellado en el manifiesto.
- **Fuente nueva `wiktionary_es`.** Wikcionario en español se declara en `sources.json` como servicio en línea (CC BY-SA 4.0, con `licenseUrl`) y se añade a las fuentes admitidas. Aparece en el manifiesto y en la tabla `source`. Wikipedia en español (`wikipedia_es`) ya es fuente de la semilla con la misma licencia; el glosario también la usa y su atribución se amplía.
- **Lista inicial de unos 85 términos candidatos**, elegidos por frecuencia y por ser un término de acción (no una enfermedad ni una parte del cuerpo). Wikcionario tiene entrada para 57 y una acepción adecuada para unos 40, que cubren cerca del 22 % de los grupos y a 1.141 de las 1.456 plantas con usos visibles; Wikipedia completa los demás cuando su artículo define el término. `Emenagogo` se incluye. Las enfermedades arcaicas (Hidropesía, Escrófula) son trabajo futuro. Los términos sin texto adecuado en ninguna fuente quedan sin explicación y registrados con su motivo. El usuario aprueba la tabla completa de textos, marcados como literales o adaptados, antes de sellar.
- **Validación propia del glosario.** Rechaza dosis, los patrones de dosis y eficacia del validador de la semilla (salvo aprobación expresa por término: el usuario aprobó Antiséptico, Bactericida, Vulnerario, Antidiarreico, Fungicida y Parasiticida), las enfermedades graves y las señales de riesgo de `sensitive-activities.json`, y cualquier texto literal que no coincida con la caché. Los textos adaptados guardan la evidencia literal del artículo y se revisan a mano.
- **Base y API.** Una migración nueva añade la tabla `activity_glossary` y una columna en los grupos de uso que enlaza cada grupo con su término (`SCHEMA_VERSION` pasa de 2 a 3). La API suma, de forma aditiva, el campo `glossary` en cada elemento de `useGroups` (`{term, text, sourceName, url, adapted}` o `null`) y los créditos de Wikcionario y de Wikipedia en `credits` cuando la planta muestra alguna explicación de esa fuente, sin duplicar el de Wikipedia si ya existe. Un cliente anterior ignora el campo.
- **App.** Bajo el título del grupo, solo en los términos con explicación, una etiqueta en gris «Significado del término» y debajo `<Término>: «<definición>» (Wikcionario)` o `(Wikipedia)`, con el nombre de la fuente enlazado a la entrada o al artículo, en línea (un texto adaptado dice «adaptado de Wikipedia»), para que se lea como el significado de la palabra y no como una afirmación sobre la planta. La atribución completa va en `Fuentes`.
- **Qué no cambia.** Los registros de plantas, el prompt (sigue en la versión 7), los `bundleHash` y el `seedHash` no cambian: el glosario se sella con su propio hash. Los grupos «Uso tradicional, sin eficacia demostrada: …» no llevan glosario.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `catalog-seed`: Wikcionario en español pasa a ser fuente admitida (requisito de fuentes); nuevos requisitos para el glosario de actividades (lista versionada de términos, descarga con revisión fija de Wikcionario y de Wikipedia, texto literal o adaptado, validación, sellado con hash propio, licencia y atribución).
- `catalog-ingest`: nuevos requisitos para la tabla del glosario, el enlace de cada grupo de uso con su término por la forma base de la actividad y la verificación del glosario antes de construir.
- `catalog-api`: nuevos requisitos para el campo aditivo `glossary` de los grupos de uso y para los créditos de las fuentes del glosario.
- `catalog-client`: nuevo requisito de lectura tolerante de `glossary`.
- `plant-passport`: nuevo requisito para la explicación bajo el título del grupo, con su etiqueta y la fuente enlazada. `compact-passport-uses` ya está implementado y archivado; este cambio no modifica el requisito «Usos como registros tradicionales trazables».

## Impact

- **Herramientas** (`tools/catalog-seed/`): `sources.json` (fuente nueva y atribución de Wikipedia), `catalog_seed/sources.py` y `catalog_seed/wiki.py` (pasos nuevos de Wikcionario y de artículos de Wikipedia, con caché, pausa y `Retry-After`), módulos del glosario (extracción, selección de acepción o texto, armado y validación), `cli.py` (comandos nuevos), `glossary-terms.json` (lista versionada) y pruebas con fixtures sin red. El README de las herramientas.
- **Semilla** (`data/seed/`): `glossary.json` nuevo y `manifest.json` con `glossaryHash` y `glossaryCount`. Ningún registro de planta cambia.
- **Backend**: migración `data/migrations/2026-10-30-000000_catalog_v3`, `catalog-core` (versión del esquema, filas, esquema de Diesel), `catalog-ingest` (lectura y verificación del glosario, mapeo), `catalog-api` (DTO, repositorio, créditos y `openapi.json`) y la colección de Postman.
- **App** (`app/lib/features/`): modelo, parser y `passport_uses_tab.dart` y `passport_texts.dart`. Se implementa sobre el diseño del grupo de `compact-passport-uses`, ya archivado.
- **Documentación**: `docs/data/fuentes-y-licencias.md`, `docs/data/modelo-de-datos.md`, `docs/data/regeneracion-de-la-semilla.md`, `backend/README.md` y `README.md`.
- **Despliegue**: hay cambios en `data/seed/`, `data/migrations/` y `backend/`, así que el push a `main` redespliega Cloud Run. El orden y la compatibilidad están en el diseño.
