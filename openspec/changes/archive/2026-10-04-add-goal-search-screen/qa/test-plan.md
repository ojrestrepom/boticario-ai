# Plan QA Android — tarea 4.2

Fecha: 2026-10-04. Alcance: smoke nativo automatizado, no QA manual 4.3.
Requerimiento: presentar las seis opciones P06 sin funcionalidad; permitir entrada
desde Inicio y retorno Atrás/Inicio, conservar catálogo y contrato de logs Home.
Specs delta: `../specs/{goal-search-screen,home-screen,flutter-app-bootstrap}/spec.md`.

Precondición común para A01–A07: autorización explícita, identidad exacta
`boticario_catalog_api36` en `emulator-5566`, estado `device`, API 36 y métricas
confirmadas; SDK fijado Flutter 3.47.6/Dart 3.13.5. Sin otras plataformas/devices.
Implementación revisada: diff real Home/router/smoke y pantalla P06 leídos.
Los casos se ejecutan mediante el único `testWidgets` del entrypoint existente
`app/integration_test/app_test.dart`; no se añadieron tests ni cambiaron assertions.

| ID / prioridad | Capability y requisito | Técnica | Pasos | Esperado | Resultado |
|---|---|---|---|---|---|
| A00 / alta | flutter-app-bootstrap: Smoke Android sin dispositivo; tasks 4.2 | Partición disponible/ausente; caso negativo | Consultar identidad AVD, estado, modelo/API/tamaño/densidad del único serial autorizado | Solo ejecutar con identidad/estado confirmados; si ausente, detener y NOT RUN | PASS de la regla de bloqueo; conexión rechazada y device ausente. No es PASS Android |
| A01 / alta | flutter-app-bootstrap: Arranque; home-screen: nueve acciones inertes | Tabla de decisión navegar/no navegar | Arranque en Home; tocar nueve controles no navegables | Home permanece en `/`, Inicio seleccionado, mensajes normativos individuales; sin overlays | NOT RUN |
| A02 / alta | goal-search-screen: Presentación visual; home-screen: entrada P06 | Particiones de contenido | Abrir Buscar por objetivo tres veces durante el flujo | `/goals`, título/subtítulo y seis etiquetas exactas; un log de entrada por visita | NOT RUN |
| A03 / alta | goal-search-screen: Filas sin acción; barra inferior; sin resultados | Particiones: seis filas y tres pestañas inertes | En cada visita tocar cada fila y Favoritos/Historial/Perfil | Sin cambio de ruta, diálogo, SnackBar o selección; Inicio sigue seleccionado | NOT RUN |
| A04 / alta | goal-search-screen: Retorno; flutter-app-bootstrap: recorrido P06 | Transición de estados | Visita 1: Atrás app; 2: `handlePopRoute`; 3: Inicio | Home en `/` con pila limpia en las tres variantes | NOT RUN |
| A05 / alta | home-screen: Contrato depuración 11 acciones | Tabla de decisión; repetición | Completar flujo y contrastar secuencia de logs capturados | Exactamente 16 entradas: nueve inertes + tres Buscar + cuatro Explorar; cubre 11 mapeos, cero logs adicionales | NOT RUN |
| A06 / alta | flutter-app-bootstrap: Sin servicios remotos | Caso negativo; guard de contrato | Ejecutar flujo con guard `HttpClient` habilitado | Cero creaciones de cliente HTTP de la app; no demuestra radios/offline real | NOT RUN |
| A07 / alta | flutter-app-bootstrap: Catálogo/Pasaporte y retornos; regresiones existentes | Particiones de búsqueda/filtros/vacíos; estados de sesión | Completar flujo compartido P04/P05: cinco identidades, consultas/filtros, IME/scroll, retorno y Inicio | Se conservan búsqueda/filtros, cinco plantas, límites de pasaporte y estado de retorno | NOT RUN |

Evidencia común: `evidence/android-smoke-4.2.log`. A00 ejecutado mediante ADB;
A01–A07 bloqueados antes de iniciar Flutter. No hay defectos de producto
reproducidos. Contenido/orden geométrico, semántica exhaustiva y layout 100%/200%
están en tests host existentes o QA manual posterior, no se infieren del smoke.
`handlePopRoute` es pop de framework, no pulsación física Android.
Exploración manual, accesibilidad manual, TalkBack, perfil/release y offline real
quedan NOT RUN; ninguna cobertura anterior se convierte en resultado Android.

Reejecución: ver preflight y comando en `android-smoke-4.2.md`.
No se instalaron herramientas; Playwright/Postman no aplican a app nativa sin API.
