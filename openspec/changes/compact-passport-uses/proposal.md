# Proposal

## Why

En la pestaña `Usos`, cada grupo muestra la actividad, la etiqueta «Registro tradicional», el número de registros, la lista de países con su rótulo, la aclaración «Es un registro, no un consejo de uso.» y todas las citas completas. Con decenas de grupos y varias citas por grupo, las citas opacan el uso, que es lo que el usuario busca. El usuario mandó una captura de esa pestaña y eligió un diseño compacto (decisión del 2026-10-29).

## What Changes

- Cada grupo de `Usos` pasa a tres elementos: la actividad como título, una sola línea de datos con el número de registros y los países («5 registros · China, Otros lugares, Trinidad»; sin países, solo «5 registros») y un control «Ver N citas».
- Las citas van **plegadas por defecto**. «Ver N citas» las despliega en el mismo sitio y pasa a «Ocultar citas»; con una sola cita dice «Ver 1 cita». Desplegadas se ven igual que hoy, con las no resueltas como «(sin resolver)» en gris y cursiva.
- Se retiran de cada grupo la etiqueta «Registro tradicional», el rótulo «Países» y la aclaración «Es un registro, no un consejo de uso.». El aviso fijo al inicio de la pestaña ya cubre toda la pestaña y se mantiene igual.
- El control de plegado es un botón de 48 dp de alto y de ancho, con semántica de expandido o plegado y con el número de citas y la actividad en su etiqueta.
- Sin cambios: el orden de los grupos, el vacío explícito, el respaldo para un backend anterior (los grupos se derivan de `uses`), las actividades sensibles (se muestran tal como llegan), el aviso fijo y el texto de los países (un «Otros lugares» genérico se queda tal cual, porque la app no reescribe lo que llega de la API).

No hay cambios de backend, de contrato de la API ni de despliegue: solo hay que recompilar el APK.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `plant-passport`: el requisito «Usos como registros tradicionales trazables» describe el grupo compacto y las citas plegables, y cambia el escenario «Registro tradicional elegible», que exigía la etiqueta y la aclaración por grupo (ahora las cubre el aviso fijo); se añaden los escenarios de plegado y de ausencia de etiqueta por grupo; el requisito «Accesibilidad del pasaporte» añade el control de plegado (botón, 48 dp, expandido o plegado, número de citas).

Ninguna otra especificación exige la etiqueta ni la aclaración por grupo (`catalog-client` y las demás no las mencionan).

## Impact

- Código de la app, en `app/lib/features/passport/presentation/`: `passport_uses_tab.dart` (grupo compacto y control de plegado), `plant_passport_page.dart` (estado de plegado que sobrevive al cambio de pestaña) y `passport_texts.dart` (textos nuevos y retiro de `traditionalRecord`, `useGroupClarification` y `countriesLabel`).
- Pruebas de la app: `app/test/features/passport/` (`passport_uses_tab_test.dart`, `plant_passport_page_test.dart`, `passport_accessibility_test.dart` y la lista de textos de `passport_sources_section_test.dart`) y el smoke `app/integration_test/catalog_smoke.dart`.
- Documentación: `README.md` (línea de `Usos`) y `app/README.md` si describe `Usos`.
- Sin cambios en el backend, la API, la semilla, la configuración de despliegue ni las dependencias.
