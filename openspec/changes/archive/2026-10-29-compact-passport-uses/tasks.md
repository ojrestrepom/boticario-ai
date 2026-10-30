# Tasks

## 1. Textos

- [x] 1.1 Actualizar `PassportTexts` en `passport_texts.dart`: añadir el resumen del grupo (`useGroupSummary(count, countries)`, con ` · ` y sin separador si no hay países), `showCitations(n)` («Ver N citas» / «Ver 1 cita»), `hideCitations` («Ocultar citas») y las etiquetas semánticas con la actividad; retirar `traditionalRecord`, `useGroupClarification` y `countriesLabel` y mantener `all` al día. Verificación: la prueba del escaneo de lenguaje de eficacia pasa, `grep` no encuentra los textos retirados en `app/lib` y `passport_sources_section_test.dart` ya no los lista.

## 2. Widget del grupo y del plegado

- [x] 2.1 Reescribir `_UseGroupCard` en `passport_uses_tab.dart`: actividad como título, una línea de datos y el control de citas; citas plegadas por defecto y, desplegadas, los `_Citation` actuales sin cambios (las no resueltas atenuadas y en cursiva); sin etiqueta, rótulo `Países` ni aclaración. Verificación: `flutter analyze` sin hallazgos y la prueba de la tarea 3.1.
- [x] 2.2 Control de citas: botón de 48 dp de alto y de ancho (`Ver N citas` / `Ver 1 cita` / `Ocultar citas`) con icono de estado (`expand_more` y `expand_less`), sin `maxLines` ni `ellipsis`, y semántica `button` y `expanded` con la etiqueta que incluye el texto visible y la actividad (D2 y D5). Verificación: pruebas de la tarea 4.1.
- [x] 2.3 Estado de plegado en `plant_passport_page.dart`: conjunto de claves de grupo desplegadas (posición, actividad y actividad original; la actividad sola no es única) en `_PlantPassportPageState`, pasado a `PassportUsesTab` con un callback; se vacía cuando cambia `plant.id` y se descarta con la página (D3). Verificación: pruebas de la tarea 3.2.

## 3. Pruebas de widget

- [x] 3.1 Reescribir `passport_uses_tab_test.dart`: grupo compacto (actividad, `12 registros` con tres países separados por comas, `Ver 2 citas`), citas plegadas por defecto, desplegar y plegar sin tocar los demás grupos, dos grupos con la misma actividad que se pliegan por separado, `Ver 1 cita`, sin países (solo el número), «Otros lugares» tal cual, cita sin resolver atenuada y en cursiva al desplegar, sin «Registro tradicional», `Países` ni la aclaración, aviso fijo y vacío explícito intactos, actividad sensible tal como llega y respaldo desde `uses`. Verificación: `flutter test test/features/passport/passport_uses_tab_test.dart` en verde.
- [x] 3.2 Estado del plegado en `plant_passport_page_test.dart`: un grupo desplegado sigue desplegado tras cambiar a `General` y volver a `Usos`, los demás siguen plegados, y al abrir otra planta o reabrir el pasaporte todos están plegados. Verificación: esa prueba en verde.
- [x] 3.3 Ajustar las pruebas existentes que cuentan «Registro tradicional» (`findsNWidgets(10)`, `46`, `findsNothing`) o buscan citas visibles sin desplegar (Lavanda con 10 usos, Romero con 59 usos y 46 grupos, planta sin usos): contar los controles `Ver N citas`, desplegar antes de buscar una cita y comprobar que el último grupo es alcanzable con desplazamiento. Verificación: `flutter test test/features/passport/plant_passport_page_test.dart` en verde.
- [x] 3.4 Muchos usos: con 46 grupos, desplegar uno en medio de la lista conserva la posición de desplazamiento y el control pulsado no se mueve; plegarlo vuelve a la altura anterior. Verificación: prueba nueva en verde.

## 4. Accesibilidad a 360x640

- [x] 4.1 Extender `passport_accessibility_test.dart`: el control de citas con `SemanticsController` (botón, `expanded` falso y verdadero, etiqueta con texto visible y actividad), `androidTapTargetGuideline` y `labeledTapTargetGuideline`, a 360x640 dp al 100 % y al 200 %, con una actividad larga y varias citas, sin desbordes ni truncado (línea de datos, control y citas). Verificación: `flutter test test/features/passport/passport_accessibility_test.dart` en verde.

## 5. Smoke

- [x] 5.1 Ajustar `app/integration_test/catalog_smoke.dart`: en `Usos`, comprobar que hay controles `Ver N citas`, que no aparece «Registro tradicional», desplegar uno y ver una cita, y plegarlo. Verificación: el smoke pasa en el emulador `boticario_catalog_api36` (misma invocación que los cambios anteriores) y se anota la salida. Si el sandbox impide compilar el APK, no se fuerza: se anota el motivo y se detiene el daemon de Gradle con `JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" ./gradlew --stop` desde `app/android`.

## 6. Documentación

- [x] 6.1 Actualizar la línea de `Usos` de `README.md` (grupos compactos por actividad con número de registros y países en una línea, citas plegadas con «Ver N citas», aviso fijo siempre visible, no resueltas atenuadas al desplegar) y `app/README.md` si describe `Usos` (hoy solo lista las pestañas y el respaldo; se comprueba y se deja igual si no hay nada que cambiar). Verificación: `python3 -I openspec/changes/archive/2026-10-16-deploy-backend-cloud-run/qa/scripts/check-md-lines.py README.md app/README.md` sin hallazgos y `grep` sin «todas las citas» en la línea de `Usos`.

## 7. Verificación global

- [x] 7.1 Ejecutar en `app/`: `flutter analyze`, `dart format --set-exit-if-changed .` y `flutter test` completo. Verificación: todo en verde y se anotan los conteos de pruebas.
- [x] 7.2 Ejecutar `openspec validate compact-passport-uses --strict` y el verificador de Markdown sobre los artefactos del cambio. Verificación: ambos sin hallazgos.

## 8. QA corta en el emulador

- [x] 8.1 Con el APK en el emulador `boticario_catalog_api36` (sin el teléfono físico `R5CR70M9GEE`), recorrer `Usos` de una planta con muchos grupos (Romero), una con citas sin resolver, una con un grupo de una sola cita, una con un grupo sin países y una sin usos: citas plegadas al abrir, desplegar y plegar en el mismo sitio, estado conservado al cambiar de pestaña y volver, 100 % y 200 % de texto. Verificación: capturas en `qa/evidence/` del cambio y un informe breve `qa/compact-passport-uses-results.md` con los casos, resultados y defectos. Al terminar, detener el daemon de Gradle si quedó vivo.
