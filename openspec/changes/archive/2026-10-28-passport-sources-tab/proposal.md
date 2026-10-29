# Proposal

## Why

La sección `Fuentes` aparece hoy al final de cada pestaña del pasaporte y muestra cada fuente completa (licencia, atribución, URL visible y un botón «Abrir en el navegador»), así que ocupa más pantalla que el contenido de la pestaña. Además, el usuario no quiere ver las URL como texto ni un botón aparte para abrirlas (decisión del 2026-10-28).

## What Changes

- `Fuentes` pasa de ser una sección bajo las otras tres pestañas a ser una **cuarta pestaña** del pasaporte, junto a `General`, `Propiedades` y `Usos`. Deja de aparecer bajo ellas.
- La pestaña `Fuentes` contiene el texto de licencias mixtas, una entrada por crédito, la entrada de la imagen y el vacío explícito cuando no hay créditos ni imagen.
- Los enlaces pasan a estar **sobre el nombre**, sin URL visible y sin botón aparte:
  - en cada crédito, el nombre de la fuente enlaza a su página (`url`) y el nombre de la licencia a su texto (`licenseUrl`), cuando existen; la atribución exigida pasa a texto secundario, más pequeño y gris;
  - en el pie de la foto de la cabecera, «Foto: [autor] · [licencia]»: el autor enlaza a la página del archivo en Commons (`pageUrl`) y la licencia a su texto (`licenseUrl`).
- Ninguna URL se muestra como texto. Si un enlace no se puede abrir, un aviso dice «No se pudo abrir el enlace». Una pulsación larga copia la URL al portapapeles con un aviso de confirmación. Solo se abren las URL `https`; una que no lo sea se muestra como texto sin enlace.
- `PassportLink` (URL visible más botón) se reemplaza por un enlace en línea; dejan de usarse sus textos «Enlace de la licencia», «Página», «Abrir en el navegador» y «Página del archivo».
- Se actualizan el README y `docs/data/fuentes-y-licencias.md` (qué licencias ve el usuario y dónde).

No hay cambios de backend, de contrato de la API ni de despliegue: solo hay que recompilar el APK.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plant-passport`: cuatro pestañas (`Fuentes` como cuarta); la sección «Sección Fuentes con licencias y atribución» pasa a ser la pestaña «Pestaña Fuentes con licencias y atribución»; el pie de la foto lleva enlaces sobre el autor y la licencia; un requisito nuevo fija el comportamiento de los enlaces (sin URL visible, solo `https`, aviso de fallo, copia con pulsación larga); la accesibilidad cubre los enlaces en línea.

`catalog-client` no cambia: `credits[].url`, `credits[].licenseUrl`, `image.pageUrl` e `image.licenseUrl` ya existen en el modelo. `goal-results-screen` tampoco: el pie `Foto: <autor> · <licencia>` de las tarjetas de P07 sigue siendo texto sin enlaces.

## Impact

- Código de la app, en `app/lib/features/passport/presentation/`: `plant_passport_page.dart` (cuarta pestaña y fin de la sección bajo las otras), `passport_sources_section.dart` (pasa a ser el contenido de la pestaña), `passport_link.dart` (reemplazado por un enlace en línea), `passport_header.dart` (pie con enlaces) y `passport_texts.dart` (textos nuevos y retiro de los antiguos).
- Pruebas de la app: `app/test/features/passport/` (enlace, sección de fuentes, cabecera, accesibilidad, pasaporte, cabecera alta) y el smoke `app/integration_test/catalog_smoke.dart`.
- Documentación: `README.md` y `docs/data/fuentes-y-licencias.md`.
- Sin cambios en el backend, la API, la semilla, la configuración de despliegue ni las dependencias (`url_launcher` ya está; el portapapeles es de Flutter).
