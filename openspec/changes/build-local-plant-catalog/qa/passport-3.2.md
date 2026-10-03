# QA 3.2 — Resolución de identidad dentro de P05

**APROBADA en alcance de componente aislado: 27/27 casos QA nuevos pasan;
sin defectos de producto reproducidos. Android y navegación integrada pendientes.**
Ejecución: 2026-10-02, 13:58–14:00 UTC. Sin Jira.

## Alcance y entorno

Leídos README, `.flutter-version`, `openspec/config.yaml`, specs delta completas
`plant-passport`, `plant-catalog`, `explore-screen`, design y tasks del cambio.
Requerimiento: resolver IDs dentro de P05 sin redirects, distinguir fallo local
de identidad inexistente, carga/reintento explícitos, salidas seguras mediante
callbacks y acciones de favorito/formulaciones inertes, sin datos inventados.

- Flutter **3.47.6**, Dart **3.13.5**, SDK `/opt/homebrew/share/flutter`.
- Harness **H**: `ProviderScope` con loader de asset local inyectado,
  `MaterialApp` y tema real, `PlantPassportRoutePage` de producto; JSON real leído
  fuera de fake async. IDs actualizados sobre el mismo widget/provider.
- Viewport **360×640 dp**, escala 1 o 2; safe insets izquierda/arriba/derecha/abajo
  **8/24/8/20 dp**. Fuente Roboto regular/medium existente en SDK, solo QA.
  Sus métricas son más representativas que Ahem, pero no equivalen al
  rasterizado, fuente o font scale reales del dispositivo Android.
- Contadores de Back/Home: prueban contrato de salida, **no** destinos reales.
  No router falso, redirects ni pantallas sustitutas en el harness.
- Sin cambios de producto, checklists, dependencias, configuración, commits ni
  push. QA P04 y P05 3.1 conservadas; regresión 3.1 escribe un log nuevo.

## Trazabilidad

Capabilities corresponden a `specs/<capability>`; deltas en `../specs/`:

| Clave | Capability / requerimiento |
|---|---|
| P-I | plant-passport / Identidad y composición del pasaporte |
| P-N | plant-passport / Acciones no funcionales y retorno seguro |
| P-A | plant-passport / Accesibilidad del pasaporte |
| P-G/P-P/P-U | plant-passport / General con vacíos explícitos; Propiedades sin inferencia de eficacia; Usos como registros tradicionales trazables |
| C-I | plant-catalog / Catálogo fijo con identidad de fuente, identidad desconocida |
| C-L | plant-catalog / Disponibilidad local y errores de datos |
| C-D | plant-catalog / Solo datos sustentados y ausencias explícitas |
| E-N | explore-screen / Barra inferior en pantallas del catálogo |

## Plan y resultados por caso

Implementación: `flutter/passport_route_qa_test.dart`.
Evidencia común por cada ID: **`evidence/passport-route-qa.log`**, reporter
expanded con nombre y resultado de cada prueba. H es precondición común;
prioridad alta para identidad/error/contenido, media para layout/semántica.

| ID / técnica | Requerimiento | Precondición adicional | Pasos | Esperado | Resultado |
|---|---|---|---|---|---|
| RQA01-{544,401,873,605,619}; particiones de equivalencia | P-I/P-G/P-N, C-I/C-L, E-N | Loader válido, escala 1 | Abrir cada ID; inspeccionar nombres/General/vacíos; pulsar barra inferior y Back | Identidad exacta, General inicial, ausencias explícitas, aceite no aplicable; lectura local única; Home activo, otros disabled sin acción tap ni callbacks; Back/Home invocan una vez, P05 permanece en harness | **PASA 5/5** |
| RQA02-{0…7}; particiones y límites | P-N, C-I, E-N | Loader válido, escala 1 | Abrir respectivamente `999999`, `text`, `-544`, `-1`, `0`, cadena vacía, overflow positivo y negativo; activar salidas/disabled | “Planta no encontrada”, sin ficha sustitutiva, error, retry, tabs, throw ni overlays; Back/Home disponibles y disabled inertes dentro de P05 | **PASA 8/8** |
| RQA03; transición de identidad/estado | P-I/P-N, C-I | Provider y key estables | 544→Usos→texto inválido→401→Propiedades→619 | Contenido actualizado; notfound sin datos viejos; cada identidad nueva abre General; sin recarga del catálogo | **PASA 1/1** |
| RQA04; transición async | C-L, P-I/P-N, E-N | Primera lectura diferida con Completer | Inspeccionar carga; activar salidas; cambiar 544→605 aún cargando; completar JSON | Carga explícita sin sustituto, callbacks operativos; resuelve Manzanilla, no Lavanda; una lectura | **PASA 1/1** |
| RQA05-{read-known,invalid-known,read-unknown}; tabla de decisión, negativos, transiciones | C-L, P-N/C-I, E-N | Primera lectura falla o JSON malformado; segundo intento diferido; ID873 o desconocido | Abrir; inspeccionar error; avanzar 30s virtuales para detectar autoretry; activar salidas; Reintentar; completar segundo intento | Error legible distinto de notfound, sin mensaje técnico/sustituto/autoretry; retry muestra carga explícita; exactamente dos lecturas; mismo ID873 resuelve Romero o unknown resuelve notfound | **PASA 3/3** |
| RQA06-{loading,error,notfound}-{1.0,2.0}; límites viewport/escala, semántica | P-A/P-N, E-N | H ambas escalas; carga retenida/error/datos con ID desconocido | Inspeccionar texto y glyph boxes reales; medir controles, safe areas y hit test; activar barra/Back | Sin overflow ni ellipsis/recorte de glifos; textos esenciales visibles; Back/Home/disabled y Retry cuando existe ≥48 dp en ambas dimensiones y dentro de safe areas; callbacks disponibles, disabled sin tap, Home seleccionado | **PASA 6/6** |
| RQA07; negativos y transición de tabs | P-N/P-P/P-U, C-D | ID544 resuelto por route entry | Recorrer tres tabs; intentar corazón y formulaciones; inspeccionar semántica/callbacks/estado/overlays y límites del texto | Acciones sin tap/callback habilitado, favorito sigue vacío, CTA onPressed=null; tab y P05 no cambian, sin dialogs/snackbars; no nuevas secciones Dosis/Recomendaciones, propiedades sin evaluación y aviso no recomendatorio | **PASA 1/1** |
| RQA08; entorno negativo local | C-L/C-I | HTTP denegado y contabilizado en harness | Fallar lectura local; reintentar; recorrer cinco IDs y desconocido | Cero HttpClient, sin Image remota, exactamente dos lecturas locales, contenido correcto sin red | **PASA 1/1** |
| RQA09; transición de estados, error repetido | C-L, P-N | ID619, dos fallos seguidos; intentos 2/3 diferidos | Error→Retry→Carga→Error; avanzar 30s virtuales; Retry→Carga→JSON | Segundo fallo legible sin detalles ni sustituto/autoretry; tercer intento explícito recupera misma Menta | **PASA 1/1** |

Los 30 segundos son avance de reloj virtual para buscar timers de autoretry,
no esperas reales ni sleeps de sincronización. Assertions de UI se resuelven
mediante pump/pumpAndSettle y Completers.

Identidades verificadas: 544 Lavanda / `Lavandula angustifolia`; 401 Eucalipto /
`Eucalyptus globulus`; 873 Romero / `Rosmarinus officinalis`; 605 Manzanilla /
`Matricaria recutita`; 619 Menta /
`Mentha x piperita subsp. nothosubsp. piperita`.

## Regresiones y evidencia adicional

| Verificación ejecutada | Resultado real | Evidencia |
|---|---|---|
| Suite producto P05 solicitada | **15/15 pasan** | `evidence/passport-route-existing-tests.log` |
| Suite completa `app/test/` | **117/117 pasan**; incluye los 15, no sumarlos | `evidence/passport-route-project-suite.log` |
| QA 3.1 existente sin alterar | **28/28 pasan** | `evidence/passport-route-3.1-regression.log` |
| Analyze producto, sin pub | Sin issues | `evidence/passport-route-quality.log` |
| Formato test QA | 1 archivo, 0 cambios | `evidence/passport-route-quality.log`, `passport-route-format.log` |
| SDK y estado inicial | Versiones fijadas verificadas | `evidence/passport-route-environment.log` |

Los recuentos observados **15 y 117** difieren del reporte Worker 15/16 y 118;
se reporta la ejecución real, no una estimación. La regresión 3.1 añade cotejo
completo de texto/citas contra datos locales, vacíos, listas y ausencia de
claims/dosis generados, así como recorrido de fichas 100%/200%; su plan está en
`passport-3.1.md`. No se duplicó esa auditoría extensa dentro del nuevo test.

## Exploración y defectos

Charters ejecutados: X1, identidad cambiante durante carga y entre tabs
(RQA03/RQA04); X2, error técnico/malformed y recuperación después de fallos
repetidos sin autoretry (RQA05/RQA09); X3, estados sin ficha y footer accesible
a 200% (RQA06). No defectos reproducidos; no severidades ni reproducciones de
producto pendientes. Un error inicial del harness (`HttpOverrides.global`
no tiene getter) se corrigió solo en QA usando `current`; la pasada final
compila y pasa, no es un defecto del producto.

## Cobertura pendiente y riesgos residuales

- **No ejecutados:** Android Back, pila real, padre Explorar/restauración de
  consulta/filtro/scroll y Home real. Pertenecen a 4.1; callbacks no los prueban.
- Sin entrypoint P05 real integrado todavía: no se instaló APK ni se tocó el
  teléfono SM G998B/R5CR70M9GEE registrado en QA previa. No se rediagnosticó el
  dispositivo ni se cambiaron ajustes, radios, fuentes o licencias.
- Sin TalkBack, revisión visual manual, swipes reales, fuente ampliada Android,
  rasterizado real, release/profile, cold start ni modo avión real. Semántica
  automatizada y bloqueo HTTP host **no** equivalen a esas verificaciones.
- No re-curación USDA ni afirmación clínica; parser/contratos cubiertos por
  suite proyecto. Sin API/auth/credenciales; Postman/Newman no aplica. Sin web:
  Playwright/axe no aplica y no se añade target web. Sin CI/smoke Android.
- Evidencia son logs y assertions host; no capturas, videos ni traces de
  dispositivo. La aprobación no cierra 3.3/4.x ni QA manual pendiente.

## Reejecución

Desde `app/`, sin actualizar paquetes ni instalar herramientas:

```sh
export PATH=/opt/homebrew/share/flutter/bin:$PATH
flutter test --no-pub --reporter expanded test/features/passport/plant_passport_page_test.dart
flutter test --no-pub --reporter expanded ../openspec/changes/build-local-plant-catalog/qa/flutter/passport_route_qa_test.dart
flutter test --no-pub --reporter expanded ../openspec/changes/build-local-plant-catalog/qa/flutter/passport_qa_test.dart
flutter test --no-pub --reporter expanded test/
```

Si SDK/fuentes están en otra ubicación, definir `QA_FLUTTER_SDK` o
`QA_PASSPORT_ROBOTO_DIR` con las fuentes ya existentes. No usar `flutter/run.sh`
de P04: sobrescribiría su log anterior. **Herramientas instaladas: ninguna.**
Artefactos nuevos solo `passport-3.2.md`, `flutter/passport_route_qa_test.dart`
y `evidence/passport-route-*` dentro de esta carpeta QA.
