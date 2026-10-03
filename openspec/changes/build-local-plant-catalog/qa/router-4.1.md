# QA tarea 4.1 — router real (host)

Fecha: 2026-10-03. **Aprobación parcial de 4.1 en host; no aprobación Android ni del incremento completo.** Code review recibido como aprobado. Sin defectos de producto reproducibles.

## Entorno, alcance y precondiciones

- Leídos completos: `README.md`, `.flutter-version`, `openspec/config.yaml`, delta specs `explore-screen`, `plant-passport`, `home-screen`, `flutter-app-bootstrap`, `design.md` y `tasks.md` del cambio.
- Flutter **3.47.6**, Dart **3.13.5**, macOS; comandos desde `app/`. Versiones/fecha: `evidence/router-environment.log`.
- Bajo prueba: `app/lib/app/router.dart` y `app/test/app/app_test.dart` (7 casos). Harness independiente: `flutter/router_qa_test.dart`, con **BoticarioApp + ProviderScope + GoRouter reales**, tema real, viewport 360×640 dp y Roboto Regular/Medium desde fixtures relativas autorizadas. Sin Navigator simulado ni MaterialApp sustituto.
- Fuente determinista: JSON real `app/assets/data/plant_catalog.json` mediante loader sustituido en Riverpod; parser/repositorio reales. Casos de error usan loader persistentemente fallido; carga usa un Completer controlado. Sin HTTP, ZIP, nuevas dependencias ni cambios de producto/configuración/checklists.
- Home→P04 se abre por `router.push('/explore')`: única intervención programática del flujo normal. Filas, chevrons, búsquedas, filtros, reintento e Inicio se activan en UI. Entradas directas autorizadas: `router.go('/explore/<id>')` desde Home.
- Framework Back = `binding.handlePopRoute()` en host, **no botón/gesto Atrás real de Android**. El padre de una entrada directa se evalúa después de pop, sin exigir que P04 esté visible/montado debajo de P05.
- Tarjeta Home Explorar todavía inerte: habilitación/logs integrados pertenecen a 4.2, no se defecta aquí.

## Plan y resultados por caso

Precondición común: proceso de widget test aislado, nuevo ProviderScope/router arrancando en `/`, catálogo local disponible salvo inyección explícita de error/carga. Evidencia de todos los casos RQ: `evidence/router-qa.log`; IDs completos aparecen en el log y en el archivo ejecutable.

| ID / prioridad | Requerimiento / capability | Técnica | Pasos | Resultado esperado | Resultado |
|---|---|---|---|---|---|
| RQ01 / alta (1 caso, 5 identidades) | `specs/explore-screen`: Estados y navegación de resultados; `specs/plant-passport`: Identidad y composición | Particiones por identidad | Abrir P04, seleccionar cada fila mediante UI, inspeccionar P05 y volver por chevron | `/explore/544,401,873,605,619` respectivamente; común y científico exactos en P05; regreso P04, una carga local compartida | **PASA** para Lavanda, Eucalipto, Romero, Manzanilla y Menta |
| RQ02-chevron, RQ02-frameworkBack / alta (2) | `specs/explore-screen`: Abrir y volver de una ficha / Volver desde Pasaporte | Transición de estados; límite offset > 0 | P04: filtro Plantas, consulta `a`, drag −180 dp, tocar Menta; regresar por cada mecanismo; comprobar offset antes de volver a desplazar hacia búsqueda | ID 619; offset idéntico > 0, misma instancia de estado y controllers, query `a` y filtro Plantas retenidos | **PASA** ambos: **48.0 → 48.0 dp**; una carga |
| RQ03-chevron, RQ03-frameworkBack / alta (2) | `specs/explore-screen`: Volver desde Explorar a Inicio; `specs/flutter-app-bootstrap`: Sin navegación adicional | Transición de estados | Abrir P04, regresar mediante cada mecanismo | `/`, Home única, `canPop=false`, sin P04/P05 retenidos en pila | **PASA** ambos |
| RQ04-{619,999999,not-a-plant}-{chevron,frameworkBack} / alta (6) | `specs/plant-passport`: Identidad inexistente / retorno seguro; `specs/explore-screen`: Navegación y estado; diseño 4.1 padre inicial | Tabla de decisión: conocido / desconocido numérico / texto × regreso | Desde Home, `go` a cada ID; comprobar ficha/no encontrado; pop a P04; pop a Home | P05 resuelve 619 o muestra `Planta no encontrada`, sin redirect; tras pop P04 nace con Todas/query vacía/offset 0; después Home única sin excepción | **PASA** 6/6; una carga por escenario |
| RQ05-{P04,P05,unknown,error} / alta (4) | `specs/explore-screen`: Inicio desde pantallas del catálogo; `specs/plant-passport`: retorno seguro; diseño limpieza de pila | Transición de sesión; particiones estado normal/no encontrado/error | En P04 y P05 normales crear query `a`/Plantas (P05 por fila Menta); para desconocido/error usar entrada directa; activar Inicio; reabrir P04 y regresar | `/`, `canPop=false`, una sola Home incluyendo offstage, ningún P04/P05 retenido; nueva P04 Todas/query vacía/offset 0 | **PASA** 4/4 |
| RQ06-{chevron,frameworkBack} / media (2) | `specs/explore-screen`: Error local reintentable / retorno; `specs/flutter-app-bootstrap`: retorno y estados de error | Inyección de fallo; transición error→reintento→error→padre→Home | Loader fallido persistente; entrada P05 619; Reintentar; regreso P04; regreso Home | Error legible, 2 cargas tras reintento (sin retry automático), P04 inicial en error; retorno seguro a Home | **PASA** ambos |
| RQ07 / media (1) | `specs/explore-screen`: Carga del catálogo / retorno seguro; `specs/flutter-app-bootstrap`: retorno | Transición async/cancelación de navegación | Mantener carga pendiente, entrar P05, chevron a P04, framework Back a Home, completar carga | Carga distinguible; P04 inicial; Home sigue única tras resolución async; una carga | **PASA** |

Identidades científicas verificadas en RQ01: `Lavandula angustifolia`, `Eucalyptus globulus`, `Rosmarinus officinalis`, `Matricaria recutita`, `Mentha x piperita subsp. nothosubsp. piperita`.

Charter exploratorio guiado: intentar abandonar destinos excepcionales (no encontrado, error persistente, carga pendiente) usando retornos/Inicio y reabrir una sesión limpia. RQ04–RQ07 ejecutan estas variantes reproducibles; no se observaron rutas rotas, overlays nuevos ni Home adicional. La anidación real conserva P04 en flujo normal; no se confunde presencia offstage con visibilidad en entradas directas.

## Ejecuciones y evidencia

| Ejecución | Resultado | Evidencia |
|---|---|---|
| Focused `test/app/app_test.dart` | **7 passed** | `evidence/router-focused.log` |
| QA independiente | **18 passed**, todos los IDs de la tabla pasan | `evidence/router-qa.log` |
| Regresión global `test/` | **133 passed** | `evidence/router-regression.log` |

Log counts: focused emite **4 mensajes `[Home]`**: Cabecera Perfil, Pestaña Favoritos, Pestaña Perfil, Pestaña Favoritos (las cuatro activaciones existentes). Los **18 casos QA afirman 0 llamadas `debugPrint` de producto**, incluido flujo con query `a`; por tanto 0 `[Home]`/logs de consulta en estas navegaciones. Los mensajes `ROUTER-QA` los emite exclusivamente el harness por `print`; no son logs de producto. No se afirma auditoría de todos los canales/logging del SO ni prueba release/profile.

Incidencia del propio test, resuelta: primera ejecución dejó `debugPrint` sustituido hasta `addTearDown`; Flutter verifica invariantes antes de ese teardown y fallaron los 18 casos por variable de debug global. Se corrigió **solo el harness QA**, restaurando dentro del body con `finally`; la reejecución completa quedó verde. Se conserva `evidence/router-harness-initial.log` como evidencia de fallo del harness, **no defecto del producto**.

## Defectos y límites

- **Defectos de producto: ninguno reproducido**; no hay severidad/repro pendiente para Worker.
- La suite global incluye checks existentes de accesibilidad/áreas 48 dp/legibilidad 100% y 200% de Home/P04/P05; no se duplicaron en estos nuevos tests de transiciones. No representa TalkBack ni observación visual Android.
- **No ejecutado:** instalación/apertura de teléfono, smoke Android, Android Back real/predictivo, revisión visual, offline físico, deep links del SO, binarios release/profile, integración desde tarjeta Home y contrato integrado de 11 logs tras 4.2. El teléfono históricamente disponible no se consultó ni asumió presente.
- Sin URL web ni API/credenciales. Playwright/Postman no aplican y no se usaron como sustituto del target Android.
- No se exigieron redirects, global 404 ni rutas extra; router inspeccionado limita este incremento a `/`, `/explore`, `/explore/:plantId`. Riesgo residual: comportamiento real Android y entrada integrada desde Home aún pendientes en tareas posteriores.
- No se modificaron fuentes del producto, checklists 4.5/5.x ni evidencia anterior a esta ejecución; no commits/push. Lockfile sin diff.

## Reejecución

Desde `app/`:

```sh
export PATH=/opt/homebrew/share/flutter/bin:$PATH
flutter test test/app/app_test.dart --reporter expanded
flutter test ../openspec/changes/build-local-plant-catalog/qa/flutter/router_qa_test.dart --reporter expanded
flutter test test/ --reporter expanded
```

Formateo limitado al nuevo harness: `dart format ../openspec/changes/build-local-plant-catalog/qa/flutter/router_qa_test.dart`.

Herramientas instaladas: **ninguna**. Flutter hizo su resolución habitual de paquetes con dependencias/lock existentes; no se actualizaron dependencias ni se descargaron datasets. Todos los artefactos de esta pasada están bajo esta carpeta QA con prefijo `router-*` y `flutter/router_qa_test.dart`.
