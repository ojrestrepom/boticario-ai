# Design

## Context

Véase `proposal.md` para la motivación y las tres specs delta para los
requisitos observables. La app tiene un `GoRouter` provisto por Riverpod: `/`
construye `HomePage`, con `explore` como ruta hija; `ExplorePage` recibe los
callbacks de navegación del router y gestiona su presentación. Home requiere
actualmente `onExplore`; la acción `searchByGoal` solo emite el mensaje de
depuración existente. Home y Explore implementan cada una su barra inferior
provisional y mantienen inertes las demás pestañas. Las pruebas actuales de
Home, rutas de app y smoke compartido del catálogo codifican estos contratos;
algunas aserciones deberán acotarse al añadir la nueva ruta.

## Goals / Non-Goals

**Goals:** Añadir una ruta P06 aislada y solo presentacional, con callbacks de
navegación explícitos que sigan los patrones actuales de app/router y Explore.
Mantener P06 utilizable en los tamaños de pantalla/texto especificados y
preservar el catálogo actual y los logs de Home.

**Non-Goals:** Refactorizar el shell compartido, añadir
providers/modelos/repositorios, habilitar selección funcional de objetivos o
comportamiento P07/de recomendaciones, y modificar datos del catálogo o
dependencias.

## Decisions

1. **Pantalla de funcionalidad aislada y sin estado.** Añadir
   `app/lib/features/goal_search/presentation/goal_search_page.dart` con un
   `GoalSearchPage` `StatelessWidget` con callbacks obligatorios `onBack` y
   `onHome`. Mostrar texto vivo e iconos Material locales provisionales; las
   filas de objetivos son contenido sin wrappers táctiles ni semántica de
   botón. Sigue el límite de navegación por callbacks de Explore, sin añadir
   estado ni servicios. Alternativas: incluir P06 en Home o en catálogo
   acoplaría responsabilidades distintas; extraer un shell compartido no se
   justifica para esta presentación aislada.

2. **Ruta anidada `/goals`.** Añadir `goals` como ruta hija hermana de
   `explore` bajo `/`, con ubicación `/goals`. `HomePage` recibe el callback
   obligatorio `onSearchByGoal`; la tarjeta emite una vez el mensaje actual de
   acción y luego invoca el callback. El router hace push a `/goals`, Atrás de
   la app hace pop y la pestaña Inicio navega a `/` limpiando la pila. Atrás del
   sistema usa el pop habitual del router. Así se replica el patrón actual de
   Explore y se conserva su pila; una ruta de nivel superior o recrear el
   router en `build` no aportaría funcionalidad necesaria.

3. **Presentación local con estilos acotados.** Usar el tema Material 3 global,
   colores locales provisionales y las convenciones existentes de helpers
   privados, con duplicación mínima; sin refactorizar widgets/tokens entre
   pantallas ni añadir assets/paquetes. Mantener título, subtítulo y seis
   etiquetas exactas como texto vivo; excluir iconos/chevrons decorativos de
   semántica. Usar cuerpo desplazable y barra inferior dentro de zonas seguras
   para que el contenido sea alcanzable con texto al 100%/200%; controles con
   navegación tendrán áreas táctiles de al menos 48dp y semántica distinguible.
   El mapeo exacto de iconos y dimensiones menores se resuelve al implementar;
   no se busca fidelidad píxel a píxel.

4. **Actualizar contratos de regresión, no solo añadir pruebas.** Ajustar las
   pruebas widget de Home para el callback obligatorio; permitir navegación
   únicamente desde las tarjetas Explorar y Buscar por objetivo, preservando
   las otras nueve acciones inertes y todos los mensajes actuales. Extender
   pruebas de rutas para Atrás de app/sistema y limpieza de pila desde Inicio,
   y el smoke/contrato host compartido para inercia de filas P06 y regresiones
   existentes del catálogo. Ajustar solo supuestos contradichos por la ruta
   nueva; conservar cobertura de IME/insets/consulta/filtro/scroll del
   catálogo. Añadir pruebas widget específicas de contenido, semántica, taps,
   zonas seguras y viewport 360x640 al 100%/200%.

## Risks / Trade-offs

- [Riesgo] Aserciones o expectativas de smoke actuales codifican la regla
  anterior de diez acciones inertes o un conteo exacto de rutas/logs → Ajustar
  solo esos supuestos; conservar el mapeo de 11 mensajes y las otras nueve
  acciones inertes.
- [Riesgo] El texto grande o insets del sistema pueden comprimir la pantalla →
  Verificar por pruebas widget, en ambas escalas, scroll alcanzable, ausencia
  de overflow horizontal/recorte de texto esencial y áreas táctiles mínimas.
- [Compromiso] Iconos/colores locales provisionales pueden diferir del arte del
  mockup → Preservar jerarquía y orden sin añadir assets ni prometer fidelidad
  píxel a píxel.

## Migration Plan

No hay migración de datos ni dependencias. Añadir P06 y su ruta, conectarla a
Home, actualizar/añadir pruebas de regresión, y después ejecutar las
verificaciones host documentadas y la validación estricta de OpenSpec.
Actualizar el estado actual del README para aclarar que P06 es presentacional y
P07 no está implementada. Si falla la validación, revertir solo los cambios de
app, pruebas y documentación de este cambio; el flujo/datos del catálogo no se
afectan. La QA manual Android requiere autorización explícita y el AVD API 36
dedicado autorizado; si falta cualquiera, informar NOT RUN, no PASS. La
verificación host no equivale a QA visual Android; la guardia `HttpClient` del
smoke solo cubre clientes HTTP de la app, no radios ni conectividad offline
física. Restaurar cualquier configuración temporal de QA. No usar Samsung ni
otro AVD, ni aceptar licencias automáticamente. No inferir resultados de
binarios release/profile a partir de pruebas debug.

## Open Questions

No hay preguntas pendientes que afecten el comportamiento especificado o el
enfoque. El mapeo menor de iconos y dimensiones queda para implementación.
