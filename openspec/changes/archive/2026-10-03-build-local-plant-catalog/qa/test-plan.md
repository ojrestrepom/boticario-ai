# QA tarea 2.1 — Explorar aislado

## Dictamen y alcance

**Aprobación parcial, únicamente automatización del componente aislado. Sin
defectos de producto reproducibles encontrados. No aprobación visual Android ni
del flujo P03→P04→P05.** Ejecución: 2026-10-02 02:36–02:49 UTC (noche local del
2026-10-01). Los timestamps precisos y comandos están en `evidence/*.log`.

Leídos README, `.flutter-version`, `openspec/config.yaml`, mockup P04, design,
tasks y specs delta completos de explore-screen, plant-catalog y
flutter-app-bootstrap. Los nombres archivados prevalecen sobre aliases del
mockup. Sin Jira. Cambio evaluado: `ExplorePage` y su suite existente; datos,
providers y asset previamente aceptados se consumen como precondición.

No se modificó producto, configuración, dependencias ni checklists; sin commits
ni push. Tarea 2.2 sigue pendiente en el proyecto: la suite QA independiente
complementa evidencia, no marca esa tarea. P05, router y navegación real son
entregas futuras 3.x/4.x, no defectos de 2.1.

## Entorno y herramientas

- Flutter 3.47.6 / Dart 3.13.5 en `/opt/homebrew/share/flutter`, pin comprobado.
- Pruebas desde `app/` con dependencias ya resueltas, `--no-pub`; sin instalaciones
  ni actualización/resolución de dependencias, descargas USDA, HTTP de negocio,
  aceptación de licencias o creación de AVD.
- Harness `ProviderScope(MaterialApp(home: ExplorePage(...)))`, tema real de la
  app y repositorio sustituido con loader local. Consulta y controles reales del
  widget; callbacks contadores, **no router ni fichas falsas**.
- `flutter/` se añade a la estructura QA para los scripts nativos Flutter.
  Playwright/axe no aplican (sin web autorizado); Postman/Newman no aplican (sin
  API). Ver READMEs de esas carpetas.
- `flutter devices` y `adb devices -l` detectaron **SM G998B, Android 15 API 35,
  serial R5CR70M9GEE**, autorizado por ADB. No hay emuladores. macOS y Chrome no
  cuentan como Android. Evidencia: `evidence/environment.log`.
- No se instaló/abrió una app ni se cambiaron ajustes/red/font scale en ese
  teléfono. No se afirma ausencia de dispositivo: la disponibilidad sí existe.
  La QA Android real de este componente **NO SE EJECUTÓ** en este encargo
  aislado; requiere una pasada/harness Android específica. El smoke integrado
  del catálogo está pendiente de 4.3 y aún no implementado; el smoke actual de
  Home no valida 2.1 y no se utilizó para acreditar P04.

## Trazabilidad y precondiciones

Capabilities delta bajo `../specs/` (corresponden a `specs/<capability>`):

- **E-C**: explore-screen / Composición y contenido de Explorar.
- **E-B**: explore-screen / Búsqueda local y filtros.
- **E-S**: explore-screen / Estados y navegación de resultados. En 2.1 solo
  estados locales y despacho del callback correcto; no destinos/pila.
- **E-N**: explore-screen / Barra inferior en pantallas del catálogo. En 2.1
  selección, disabled y callbacks; no ruta `/` real.
- **E-A**: explore-screen / Accesibilidad de Explorar.
- **C-I/C-L**: plant-catalog / Catálogo fijo con identidad de fuente;
  Disponibilidad local y errores de datos.
- **B-L/B-V**: flutter-app-bootstrap / Funcionamiento local sin autenticación ni
  servicios remotos; Verificaciones reproducibles del incremento.

Precondición **H**: harness anterior, viewport lógico 360×640, escala 1 salvo
indicación, JSON local congelado del asset actual con cinco identidades. Cada
test tiene scope propio; sin autenticación/secretos. Insets **I**: izquierda 8,
arriba 24, derecha 8, abajo 20 dp. La fuente artificial falla solo en los casos
negativos indicados, sin alterar el asset. Riesgo alto: identidad/búsqueda/error;
medio: accesibilidad y controles no disponibles.

## Casos y resultados

Todos los casos QA01–QA10 están en `flutter/explore_qa_test.dart`. Los cuatro
casos parametrizados en dos escalas suman **14 tests**. Evidencia común:
`evidence/qa-tests-final.log` (14/14 pasan). Los pasos se ejecutan con textos,
tooltips y etiquetas semánticas; medidas sobre el control completo, no sobre
el icono decorativo.

| ID / prioridad | Requisito / técnica | Precondiciones | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|---|
| QA01 / alta | E-C, E-S, C-I; particiones de identidad | H | Abrir; comprobar orden y ambos nombres; desplazar y pulsar cada fila | Lavanda/544, Eucalipto/401, Romero/873, Manzanilla/605, Menta/619; callback una vez por fila; nombres científicos fuente exactos, sin aliases del mockup | PASA |
| QA02 / alta | E-B; equivalencia y límites | H | Introducir `  ÁNZÁ  `, `  ROSMARÍNUS   OFFICINALIS  `, `NOTHOSUBSP.`, solo espacios/tab y emoji | Subcadena en común/científico, case/diacríticos/espacios normalizados; Manzanilla/Romero/Menta; whitespace recupera cinco; emoji vacío sin fallo | PASA |
| QA03 / alta | E-B, E-S; tabla decisión y transiciones | H | Buscar `lav`; pasar por Plantas/Todas/Aceites; borrar en Aceites; Plantas→unknown→borrar; pulsar filtro ya activo | Filtro AND consulta; Aceites nunca plantas, vacío específico; no-match distinto; borrar preserva filtro y devuelve su conjunto; filtro activo no se deselecciona | PASA |
| QA04 / alta | E-S, C-L; errores y transiciones | H, loader JSON malformado dos veces, tercera carga diferida | Abrir; escribir `glob`, elegir Plantas; reintentar dos veces; resolver tercer intento | Error legible sin detalle interno; sin retry automático; carga al reintentar; éxito con solo Eucalipto, filtro/consulta conservados | PASA |
| QA05 / alta | E-S; transición carga→datos | H, loader diferido | Durante carga seleccionar Aceites y escribir no-match; resolver carga | Carga prevalece sobre vacíos; tras resolver, vacío de Aceites, no vacío de búsqueda | PASA |
| QA06-100, QA06-200 / media | E-N; decisión/semántica/no mutación | H, escalas 1/2, contadores de callbacks y semantics activos | Buscar lav/Plantas; inspeccionar y pulsar Favoritos/Historial/Perfil; pulsar Inicio y back | Las tres: isEnabled=false, isSelected=false, sin acción tap, labels únicos “no disponible”; no callbacks, overlays ni mutación; Inicio activo y callback correcto; back callback correcto | PASAN 2/2 |
| QA07-100, QA07-200 / media | E-A; límites viewport/text scale, recorrido | H+I, escalas 1/2, semantics | Recorrer todos los controles/filas y textos, incluida Menta científica; inspeccionar bounds y párrafos; escribir y comprobar clear | Safe areas; scroll/hit targets alcanzables; controles completos ≥48 dp; todo texto esencial íntegro, sin exceder líneas ni límites horizontales, alcanzable completo dentro del viewport; clear ≥48 dp | PASAN 2/2 |
| QA08-100, QA08-200 / media | E-A, E-S; estado error y límites | H+I, escalas 1/2, error local | Desplazar a error y botón Reintentar | Error sin truncado; retry alcanzable y ≥48 dp; ninguna excepción de layout | PASAN 2/2 |
| QA09 / alta | E-C, C-L, B-L; entorno negativo | H, HTTP rechazado por HttpOverrides | Abrir datos locales, buscar científico, elegir Aceites | Cinco plantas disponibles; UI funciona; cero intentos de HttpClient; ningún widget Image externo | PASA |
| QA10-100, QA10-200 / media | E-S, E-A; estados y límites | H+I, escalas 1/2, carga diferida | Recorrer texto carga; resolver; buscar no-match; elegir Aceites | Tres mensajes diferenciados, sin truncado, íntegros y alcanzables en viewport seguro | PASAN 2/2 |

Literal fuente usado en QA01: `Lavandula angustifolia`, `Eucalyptus globulus`,
`Rosmarinus officinalis`, `Matricaria recutita`,
`Mentha x piperita subsp. nothosubsp. piperita`.

| Verificación independiente | Resultado | Evidencia |
|---|---|---|
| Suite existente de ExplorePage | PASA 10/10 | `evidence/existing-explore-tests.log` |
| Suite completa actual `app/test/` | PASA 96/96 (incluye los 10 anteriores, no sumarlos) | `evidence/project-suite.log` |
| Formato producto, sin escritura | PASA, 22 archivos, 0 cambios | `evidence/quality.log` |
| Flutter analyze --no-pub | PASA, sin issues | `evidence/quality.log` |
| Reejecución mediante `flutter/run.sh` | PASA, exit 0; repite 10/14/96 y calidad | `evidence/rerun.log`, `evidence/final-status.log` |
| Smoke Android catálogo / QA manual P04 | NO EJECUTADOS, no aprobados | `evidence/environment.log`; explicación de alcance arriba |
| Playwright/axe y Postman/Newman | NO APLICAN | READMEs respectivos |

La suite completa aporta cobertura de carga real del **asset registrado** y
validación de datos, búsqueda pura, provider y regresión de Home. QA09 es una
prueba UI con fuente local inyectada; no se presenta como carga Android real del
asset ni como modo avión. No se duplicó la curación/ingestión USDA en E2E.

## Exploración guiada y defectos

- **Charter X1 (estados adversos):** consulta/filtro durante carga o error,
  reintento repetido y recuperación; QA03–QA05. Sin defecto reproducible.
- **Charter X2 (asistencia/layout):** recorre controles deshabilitados, nombres
  largos, insets y mensajes a 200%; QA06–QA08/QA10. Sin defecto reproducible en
  este harness. No es recorrido real TalkBack ni revisión de píxeles.

**Defectos: ninguno confirmado.** No hay severidades ni reproducciones de
producto pendientes en 2.1. La falta prevista de P05/router no es regresión.

Los logs `qa-tests-first.log` a `qa-tests-fourth.log` son borradores de
construcción del test, **no evidencia de defectos**: comparaciones booleanas
corregidas a `Tristate`, import correspondiente, disposal de semantics antes
de verificación, búsqueda de slivers lazy con scroll y medición del IconButton
completo en lugar del RawTooltip interno de 40 dp. El IconButton real mide
48×48 dp. Un intento de duplicar bundle IO en fake time terminó en timeout del
harness; se retiró esa duplicación y se mantuvo el test de bundle existente en
la suite del proyecto más QA09 con la fuente local inyectada. Pasada final
limpia en `qa-tests-final.log`. No se reportó ninguno de esos fallos como bug.

## Cobertura pendiente y riesgos residuales

- No validada fidelidad visual, tipografía real, TalkBack, teclado Android/IME,
  fuente de sistema al 200%, swipes reales ni comportamiento offline con radios
  apagadas. Los tests usan layout y semántica Flutter en host (fuente de test),
  no captura de Android. No hay capturas/traces/videos de dispositivo.
- No probado Android Back ni retorno real a Home o ficha, preservación de
  consulta/filtro/scroll tras P05, pila/ruta `/` ni IDs desconocidos en P05:
  alcance pendiente 3.x/4.x. Se probaron solo los callbacks expuestos en 2.1.
- No CI remota ni release/profile, APK/build/instalación o paquetes Android
  comprobados. `pub get --enforce-lockfile` no se repitió: no cambian dependencias
  y este encargo prohíbe updates/red; las suites usaron la resolución existente.
- El teléfono disponible permite planificar la futura QA Android, pero no basta
  para declarar éxito del smoke o de la revisión manual. Conviene acordar la
  pasada del harness aislado/flujo integrado con el Orchestrator.

## Reejecución

Desde el root del repositorio (dependencias resueltas previamente):

```sh
bash openspec/changes/build-local-plant-catalog/qa/flutter/run.sh
```

Guarda fecha/comandos/resultados nuevos en `evidence/rerun.log`, usa el SDK pin
por PATH en cada ejecución y no instala herramientas. Alternativa desde `app/`:

```sh
export PATH=/opt/homebrew/share/flutter/bin:$PATH
flutter test --no-pub --reporter expanded ../openspec/changes/build-local-plant-catalog/qa/flutter/explore_qa_test.dart
```

**Herramientas instaladas: ninguna.** Para Android futuro, rediagnosticar
devices/serial; no asumir disponibilidad permanente de R5CR70M9GEE. No ejecutar
el smoke viejo como si cubriera el flujo pendiente.
