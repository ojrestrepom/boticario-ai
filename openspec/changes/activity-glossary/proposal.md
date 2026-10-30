# Proposal

## Why

La pestaña `Usos` titula cada grupo con la actividad que Dr. Duke registra y la semilla traduce. Muchas se entienden solas (Fiebre, Tos, Diarrea), pero otras son términos farmacéuticos antiguos que el usuario no entiende: Diurético, Tónico, Astringente, Carminativo, Anodino, Emenagogo, Demulcente, Emoliente, Sudorífico, Emético, Depurativo, Estomacal y otros.

Las 200 actividades más frecuentes cubren el 80 % de los 17.160 grupos visibles, y unos 85 términos de este tipo suman por sí solos el 35 % de los grupos (6.031). El usuario decidió el 2026-10-29 que bajo esos términos vaya una explicación breve, tomada de una fuente abierta citada, Wikcionario en español, y no escrita por el modelo.

## What Changes

- **Glosario en la semilla.** Un archivo nuevo `data/seed/glossary.json` con, por término, el texto literal de una acepción de Wikcionario recortado a la primera oración, la URL permanente de la revisión, la licencia (CC BY-SA 4.0) y la fecha de descarga. Se arma con el mismo proceso de `tools/catalog-seed`: lista versionada de términos, descarga con caché y revisión fija, validación y sellado en el manifiesto.
- **Fuente nueva `wiktionary_es`.** Wikcionario en español se declara en `sources.json` como servicio en línea (CC BY-SA 4.0, con `licenseUrl`) y se añade a las fuentes admitidas. Aparece en el manifiesto y en la tabla `source`.
- **Lista inicial de unos 85 términos candidatos**, elegidos por frecuencia y por ser un término de acción (no una enfermedad ni una parte del cuerpo). Wikcionario tiene entrada para 57; con una acepción adecuada y sin patrones prohibidos quedan unos 40, que cubren cerca del 22 % de los grupos y a 1.141 de las 1.456 plantas con usos visibles. Los términos sin entrada, o sin una acepción adecuada, quedan sin explicación y registrados con su motivo.
- **Validación propia del glosario.** Rechaza dosis, los patrones de dosis y eficacia del validador de la semilla (salvo aprobación expresa por término), las enfermedades graves y las señales de riesgo de `sensitive-activities.json`, y cualquier texto que no sea literal respecto de la caché.
- **Base y API.** Una migración nueva añade la tabla `activity_glossary` y una columna en los grupos de uso que enlaza cada grupo con su término (`SCHEMA_VERSION` pasa de 2 a 3). La API suma, de forma aditiva, el campo `glossary` en cada elemento de `useGroups` (`{text, url}` o `null`) y el crédito de Wikcionario en `credits` cuando la planta muestra alguna explicación. Un cliente anterior ignora el campo.
- **App.** La explicación sale bajo el título del grupo, en texto secundario, solo en los términos con definición, con el encabezado fijo «Según Wikcionario:» y el texto entre comillas, para que se lea como cita del diccionario y no como una afirmación sobre la planta. La atribución completa va en `Fuentes`.
- **Qué no cambia.** Los registros de plantas, el prompt (sigue en la versión 7), los `bundleHash` y el `seedHash` no cambian: el glosario se sella con su propio hash. Los grupos «Uso tradicional, sin eficacia demostrada: …» no llevan glosario.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `catalog-seed`: Wikcionario en español pasa a ser fuente admitida (requisito de fuentes); nuevos requisitos para el glosario de actividades (lista versionada de términos, descarga con revisión fija, acepción y texto literal, validación, sellado con hash propio, licencia y atribución).
- `catalog-ingest`: nuevos requisitos para la tabla del glosario, el enlace de cada grupo de uso con su término por la forma base de la actividad y la verificación del glosario antes de construir.
- `catalog-api`: nuevos requisitos para el campo aditivo `glossary` de los grupos de uso y para el crédito de Wikcionario.
- `catalog-client`: nuevo requisito de lectura tolerante de `glossary`.
- `plant-passport`: nuevo requisito para la explicación bajo el título del grupo y su encabezado. No modifica el requisito «Usos como registros tradicionales trazables», que el cambio paralelo `compact-passport-uses` reescribe.

## Impact

- **Herramientas** (`tools/catalog-seed/`): `sources.json` (fuente nueva), `catalog_seed/sources.py` y `catalog_seed/wiki.py` (servicio nuevo, con caché, pausa y `Retry-After`), un módulo del glosario (descarga, selección de acepción, armado y validación), `cli.py` (comandos nuevos), `glossary-terms.json` (lista versionada) y pruebas con fixtures sin red. El README de las herramientas.
- **Semilla** (`data/seed/`): `glossary.json` nuevo y `manifest.json` con `glossaryHash` y `glossaryCount`. Ningún registro de planta cambia.
- **Backend**: migración `data/migrations/2026-10-30-000000_catalog_v3`, `catalog-core` (versión del esquema, filas, esquema de Diesel), `catalog-ingest` (lectura y verificación del glosario, mapeo), `catalog-api` (DTO, repositorio, créditos y `openapi.json`) y la colección de Postman.
- **App** (`app/lib/features/`): modelo, parser y `passport_uses_tab.dart` y `passport_texts.dart`. Depende de `compact-passport-uses` solo en el diseño del grupo: se implementa después, o sobre el diseño vigente si aquel aún no se aplicó.
- **Documentación**: `docs/data/fuentes-y-licencias.md`, `docs/data/modelo-de-datos.md`, `docs/data/regeneracion-de-la-semilla.md`, `backend/README.md` y `README.md`.
- **Despliegue**: hay cambios en `data/seed/`, `data/migrations/` y `backend/`, así que el push a `main` redespliega Cloud Run. El orden y la compatibilidad están en el diseño.
