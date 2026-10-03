# QA 3.1 — Pasaporte P05 aislado

**Resultado: 28/28 casos QA pasan en host con Roboto del SDK; sin defectos de
producto confirmados. No se aprueba UI Android real ni navegación integrada.**
Ejecución: 2026-10-02 03:18–03:25 UTC (2026-10-01 local). Sin Jira.

## Alcance, entorno y trazabilidad

Leídos README, `.flutter-version`, `openspec/config.yaml`, mockup P05 en
`docs/mockups/pantallas.md`, design, tasks y specs delta completos
plant-passport, plant-catalog y explore-screen. Evaluado únicamente
`PlantPassportPage(plant, provenance, onBack, onHome)` de 3.1, después de code
review aprobado. El catálogo válido existente es precondición; la curación y
validación de entradas inválidas tienen pruebas unit/integración del proyecto.

- Flutter **3.47.6**, Dart **3.13.5**, SDK `/opt/homebrew/share/flutter`.
- Harness independiente: MaterialApp con tema real, widget de producto y JSON
  local parseado; contadores solo de callbacks, sin router/pantallas falsas.
- **H**: cada test aislado, viewport 360×640 dp, insets izquierda/derecha 8,
  arriba 24 y abajo 20 dp; escala 1 o 2. Cinco identidades del asset local.
- Fuente host representativa **Roboto** regular/medium ya disponible en el SDK;
  no se añadieron fuentes a producto ni se descargó/instaló nada. Esto **no**
  prueba tipografía/rasterizado/font scale reales del teléfono.
- No cambios de producto/configuración/casillas, commits ni push. P04 y su
  `test-plan.md`, `flutter/run.sh`, `evidence/rerun.log` se conservaron intactos.
- Playwright/axe no aplican: no target web. Postman/Newman no aplican: sin API.

Capabilities (specs delta bajo `../specs/`, correspondientes a `specs/<capability>`):

| Código | Capability / requerimiento |
|---|---|
| P-I | plant-passport / Identidad y composición del pasaporte |
| P-G | plant-passport / General con vacíos explícitos |
| P-P | plant-passport / Propiedades sin inferencia de eficacia |
| P-U | plant-passport / Usos como registros tradicionales trazables |
| P-N | plant-passport / Acciones no funcionales y retorno seguro (solo controles y callbacks en 3.1) |
| P-A | plant-passport / Accesibilidad del pasaporte |
| C-I/C-F/C-D/C-L | plant-catalog / Catálogo fijo con identidad de fuente; Procedencia verificable y límites del snapshot; Solo datos sustentados y ausencias explícitas; Disponibilidad local y errores de datos (solo disponibilidad de contenido válido aquí) |
| E-N | explore-screen / Barra inferior en pantallas del catálogo (solo selección/semántica/callbacks) |

## Plan y resultados por caso

Todos implementados en `flutter/passport_qa_test.dart`. Evidencia común de la
pasada final: **`evidence/passport-qa-rerun.log`**. Prioridad alta para identidad,
trazabilidad y no consejo; media para interacción/layout. Se mantienen las
assertions completas de texto y glifos, sin convertir fallos en skips.

| ID / técnica | Requisito | Precondiciones | Pasos | Esperado | Resultado |
|---|---|---|---|---|---|
| PQA01-{544,401,873,605,619}; particiones, transiciones | P-I/P-G/P-P/P-U, C-I/C-F/C-D | H, escala 1 | Abrir cada identidad; inspeccionar campos/procedencia/bibliografía; General→Propiedades→Usos→General y repetir General | Ambos nombres exactos; General inicial; origen/descripción “No disponible en fuente”; partes reales con código, rotuladas como dato fuente; aceite “No aplicable: ficha de planta”; USDA/CC0/v1/artículo 24660351/archivo 43363335/fecha 2026-10-01 diferenciada de cobertura; propiedad literal sin evaluación; sin aliases ni campos inventados del mockup | **PASA 5/5** |
| PQA02-{544,401,873,605,619}; equivalencia, límites 0/10/51/60, comparación ordenada | P-U, C-I/C-D | H, escala 1 | Abrir Usos; cotejar secuencia completa de actividad y cita por fila contra ACTIVITY y REFERENCES.LONGREF; alcanzar última cita | Lavanda 10, Eucalipto 51, Romero 60, sin cap; “Registro tradicional”, aviso no recomendación ni evidencia clínica; cada fila con referencia resuelta íntegra y correctamente asociada, sin textos adicionales/dosis/claims generados; Manzanilla/Menta 0 con vacío explícito | **PASA 5/5** |
| PQA03; transición de identidad/estado | P-I | H | Seleccionar Usos; actualizar misma identidad; cambiar a Menta; seleccionar Propiedades; cambiar a Eucalipto | Misma identidad conserva tab; identidad diferente reinicia General y sustituye contenido | **PASA 1/1** |
| PQA04-{1,2}; tabla de decisión, negativos y semántica | P-N, E-N | H, semantics y contadores | En cada tab inspeccionar/pulsar corazón, CTA y tres ítems inferiores no disponibles; activar Inicio y regreso | Labels únicos “no disponible”, enabled=false, sin acción semántica tap; sin callbacks, cambio de tab/pantalla, dialogs o snackbars al intentar disabled; CTA persistentemente alcanzable; Inicio seleccionado/verde/habilitado y un callback; regreso un callback | **PASA 2/2** |
| PQA05-{cinco IDs}-{1,2}; límites viewport/escala y recorrido | P-A/P-I/P-G/P-U, E-N | H, ambas escalas, semantics | Recorrer cabecera y todos los párrafos de las tres tabs; comprobar glyph boxes, líneas alcanzables por scroll, zonas seguras, labels/controles y footer | Nombre científico largo de Menta completo; todas las líneas de campos/citas alcanzables sin ellipsis ni ocultación de glifos; controles ≥48 dp; footer seguro y CTA persistente. Texto de chips se verifica separadamente en PQA08 para no bloquear recorrido del resto | **PASA 10/10** |
| PQA06-{1,2}; vacío negativo y estrés de longitud | P-G/P-U/P-A | H, planta sintética solo en harness: sin partes y una cita de 90 segmentos numerados | Leer vacío de partes; recorrer cita en General y Usos por segmentos solapados, incluida última línea | Vacío explícito; cita mayor que viewport completa, todos los glifos alcanzables mediante scroll y footer visible; no exigencia imposible de párrafo gigante entero en un frame | **PASA 2/2** |
| PQA07; entorno negativo sin red | P-I, C-L | H, HttpOverrides rechaza HTTP | Abrir cinco identidades y tres tabs, inspeccionar arte | Cero intentos HttpClient; ninguna Image externa; iconografía local provisional; contenido sigue disponible | **PASA 1/1** |
| PQA08-{1,2}; límites y render de controles | P-I/P-A | H, ambas escalas | Activar y medir cada tab; cotejar cajas de todos los glifos con ancho del párrafo | General/Propiedades/Usos completos, alcanzables, sin glyph clipping | **PASA 2/2 con Roboto** |

Identidades comprobadas: Lavanda/544 `Lavandula angustifolia`; Eucalipto/401
`Eucalyptus globulus`; Romero/873 `Rosmarinus officinalis`; Manzanilla/605
`Matricaria recutita`; Menta/619 `Mentha x piperita subsp. nothosubsp. piperita`.

| Verificación adicional | Resultado | Evidencia |
|---|---|---|
| Suite P05 existente | **9/9 pasan** | `evidence/passport-existing-tests.log` (incluye versión SDK) |
| Suite completa actual `app/test/` | **111/111 pasan** (incluye los 9 anteriores; no sumarlos) | `evidence/passport-project-suite.log` |
| QA con Roboto explícito, antes del rerun default | **28/28 pasan** | `evidence/passport-qa-roboto.log` |
| Formato producto sin escritura | 24 archivos, 0 cambios | `evidence/passport-quality-final.log` |
| `flutter analyze --no-pub` del producto | Sin issues | `evidence/passport-quality-final.log` |
| Android/manual/TalkBack/flujo integrado | **NO EJECUTADOS / pendientes** | Alcance explicado abajo |

## Exploración, observaciones y defectos

Charters: (X1) preservar identidad/cita y evitar interpretación como consejo al
recorrer listas largas y vacíos; PQA01/PQA02. (X2) estrés a 200%, footer estable,
controles inaccesibles y bibliografía extrema; PQA04–PQA06/PQA08.

**Defectos de producto confirmados: ninguno; sin severidades/reproducciones de
producto pendientes.** Observación de harness **O1**, no defecto Android:

- Con la fuente **Ahem** predeterminada en Flutter Test, PQA08-2.0 reproduce fade
  de “Propiedades”: glifos ~309.15 dp frente a párrafo ~246 dp. Resultado:
  **27 pasan/1 falla**, `evidence/passport-qa-final.log` (el nombre “final” es
  histórico, no el dictamen final). Se reproduce con `QA_PASSPORT_USE_AHEM=1`.
- Ahem tiene métricas cuadradas artificiales. Con Roboto del SDK, misma UI,
  viewport, escala y **mismas assertions**, Propiedades mide ~158.5 dp y pasa;
  no se reproduce recorte. El harness final carga Roboto por defecto para medir
  texto representativo Android. No se atribuye el fallo Ahem al producto real
  ni se afirma equivalencia del host con el teléfono. Riesgo residual: confirmar
  fuente real y TalkBack en Android.
- `passport-qa-initial.log` y `passport-qa-diagnostic.log` conservan borradores
  fallidos del harness: slivers lazy no construidos, header fuera de pantalla,
  offsets restaurados al cambiar tab, selection boxes de espacios colgantes y
  límite artificial de 100 gestos para cita gigante. Corregidos: alcanzar/resetear
  slivers, comprobar glifos no whitespace con su letter spacing real y derivar
  límite de recorrido de altura del párrafo. No se reportaron como bugs.
- `passport-quality.log` conserva un intento adicional inválido de `dart analyze`
  sobre el test fuera del package Flutter (339 diagnósticos de resolución,
  incluido dart:ui). No indica errores del producto; análisis del producto sí
  pasó. El test QA se compila/ejecuta con contexto del package mediante
  `flutter test` desde `app/`. No se añadieron configs/dependencias para ese
  comando ajeno al package.

## Cobertura pendiente y riesgos

- Sin revisión visual real, TalkBack, rasterizado/fuentes del sistema, fuente
  ampliada Android, swipes físicos, cold start/release/profile o radios apagadas.
  No hay capturas/videos/traces de dispositivo ni afirmación de modo avión.
- P04 detectó SM G998B / R5CR70M9GEE / API 35 en su evidencia histórica
  `evidence/environment.log`; no se rediagnosticó ni tocó el teléfono aquí.
  La causa de la QA Android pendiente es **alcance aislado sin entrypoint P05**,
  no falta de dispositivo. No instalación ni cambios de red/settings/font scale.
- Resolver ID desconocido/carga/error P05 es 3.2; router/pila/Android Back/
  regreso a Explorar conservando estado y Home real son 4.1. No probados ni
  clasificados como defectos de 3.1. Se verificaron solo callbacks de salida.
- No recuración del ZIP USDA ni evidencia clínica: snapshot válido recibido,
  unidades/integración existentes ejecutadas. No autenticación/API/secretos.
- No CI remota, build APK ni smoke antiguo Home usado como prueba del catálogo.
  No se marcaron tareas 3.2/3.3/4.x ni se sustituyó QA manual por host.

## Reejecución

Desde `app/`, con dependencias existentes (sin pub get/instalaciones):

```sh
export PATH=/opt/homebrew/share/flutter/bin:$PATH
flutter test --no-pub test/features/passport/plant_passport_page_test.dart
flutter test --no-pub ../openspec/changes/build-local-plant-catalog/qa/flutter/passport_qa_test.dart
flutter test --no-pub test/
```

Si el SDK está en otra ubicación, definir `QA_FLUTTER_SDK` (o
`QA_PASSPORT_ROBOTO_DIR` con las fuentes existentes). `QA_PASSPORT_USE_AHEM=1`
es exclusivamente variante diagnóstica O1 y reproduce su fallo host esperado;
no es el comando de aprobación. No ejecutar `flutter/run.sh` de P04 para esta
pasada porque escribiría su `rerun.log` histórico.

**Herramientas instaladas: ninguna.** Solo nuevos artefactos `passport-*` y
`flutter/passport_qa_test.dart` dentro de esta carpeta QA.
