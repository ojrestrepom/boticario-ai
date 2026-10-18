# Tasks

## 1. Presentación P06

- [x] 1.1 Crear `GoalSearchPage` stateless en `app/lib/features/goal_search/presentation/goal_search_page.dart` con callbacks obligatorios Atrás/Inicio; verificar título, subtítulo y seis etiquetas exactas en orden, decoración Material local y barra inferior con Inicio seleccionado.
- [x] 1.2 Implementar filas no interactivas, cabecera/barra segura y scroll vertical; verificar en pruebas widget que cada texto se anuncia una vez sin rol/acción/selección de botón y que tocar cada fila no cambia la UI ni produce navegación, overlay o log.
- [x] 1.3 Añadir pruebas widget P06 para viewport 360x640 dp al 100% y 200% con insets; verificar integridad/alcance por scroll, ausencia de overflow horizontal/excepciones, semántica y áreas táctiles de Atrás/Inicio, y pestañas restantes inertes.

## 2. Navegación y contratos de Inicio

- [x] 2.1 Integrar en `app/lib/app/router.dart` la ruta hija `/goals` hermana de `explore`, el callback obligatorio `onSearchByGoal` de `HomePage` y su conexión desde la tarjeta tras emitir el mensaje existente; actualizar constructores de producción/tests y verificar entrada, Atrás app/sistema, Inicio con pila limpia, ambas tarjetas permitidas y los 11 mensajes exactos.
- [x] 2.2 Ajustar `app/test/features/home/home_page_test.dart` para la nueva navegación; verificar ausencia de logs por render, nueve acciones restantes inertes, accesibilidad/selección actuales y política de emisión permitida/no permitida en host, sin afirmar pruebas de binarios release/profile.
- [x] 2.3 Extender `app/test/app/app_test.dart` para entrada a P06, Atrás de app y sistema, retorno Inicio con pila limpia y pestañas inertes; verificar que el recorrido Explorar/Pasaporte y la preservación de estado siguen pasando.

## 3. Smoke y regresión integrada

- [x] 3.1 Extender `app/integration_test/catalog_smoke.dart` y `app/test/app/catalog_smoke_contract_test.dart` para abrir P06 desde Home, comprobar inercia de las seis filas y retornos, conservando casos existentes de catálogo/IME/insets/consulta/filtro/scroll; verificar mediante contrato host compartido.
- [x] 3.2 Actualizar solo expectativas de acciones/rutas/logs que cambien por P06 en el smoke integrado; verificar cobertura existente de catálogo/pasaporte, 11 mensajes Home y ausencia de solicitudes remotas o logs por render.
- [x] 3.3 Actualizar en `README.md` el estado actual para describir P06 como pantalla visual no funcional y P07/recomendaciones como aún no implementadas; verificar que no se alteran reportes históricos ni instrucciones ajenas.

## 4. Verificación de integración y QA

- [x] 4.1 Desde `app/`, ejecutar `flutter pub get --enforce-lockfile`, `dart format --output=none --set-exit-if-changed .`, `flutter analyze` y `flutter test test/`; verificar exit 0 y lockfile sin cambios.
- [x] 4.2 Ejecutar el smoke Android solo con autorización explícita y tras verificar que `emulator-5566` corresponde al AVD `boticario_catalog_api36`; usar ese ID confirmado para `flutter test integration_test/app_test.dart -d emulator-5566`. Si falta dispositivo o autorización, reportar NOT RUN, nunca PASS; no usar Samsung/otro AVD ni aceptar licencias automáticamente. Registrar resultado y evidencia en `openspec/changes/add-goal-search-screen/qa/`.
- [x] 4.3 Después de aprobar el code review y superar las verificaciones automatizadas, si existe autorización explícita y se confirma la identidad de `emulator-5566` como `boticario_catalog_api36`, realizar QA visual manual en ese AVD: revisar Inicio→P06, textos y orden, taps inertes y pestañas restantes, Atrás app/sistema e Inicio, visualización al 100%/200%, zonas seguras y áreas táctiles. Restaurar cualquier ajuste temporal; registrar observaciones y limitaciones en `openspec/changes/add-goal-search-screen/qa/` sin sobrescribir evidencia anterior. No activar TalkBack; reportar explícitamente como NOT RUN toda cobertura manual no realizada y no inferir PASS de evidencia previa.
- [x] 4.4 Ejecutar `openspec validate add-goal-search-screen --strict` y revisar diff/árbol de cambios; verificar validación exitosa, solo archivos del alcance modificados y sin cambios de catálogo/dependencias.
