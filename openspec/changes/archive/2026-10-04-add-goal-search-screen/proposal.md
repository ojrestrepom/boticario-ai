# Proposal

## Why

La tarjeta «Buscar por objetivo» de Inicio ya está visible, pero no permite entrar a la pantalla P06 representada en los mockups. Se propone incorporar esa pantalla como una presentación informativa de las opciones del mockup, sin activar todavía selección de objetivos ni resultados.

## What Changes

- Añadir P06 «Buscar por objetivo», con el título «¿Qué deseas lograr?», el subtítulo «Selecciona un objetivo principal» y las seis filas del mockup en su orden: «Relajación / Estrés», «Mejorar el sueño», «Cuidado de la piel», «Alivio respiratorio», «Concentración» y «Otros objetivos».
- Permitir el recorrido mínimo Inicio → P06 desde la tarjeta existente y el retorno a Inicio mediante Atrás o Inicio. Conservar la barra inferior compartida, con Inicio resaltado; las otras pestañas no adquieren acciones.
- Mantener las seis filas como contenido visual sin selección ni efecto al activarlas. No abrir P07 ni ofrecer recomendaciones, resultados o efectos secundarios.
- Preservar el contrato actual de los 11 mensajes de Inicio, incluido `[Home] Buscar por objetivo`; el contrato de navegación cambia solo para Buscar por objetivo, Explorar conserva su navegación y las nueve acciones restantes continúan inertes. La nueva navegación funciona también fuera de depuración, sin logs nuevos ni registro de datos de usuario.
- Actualizar explícitamente los contratos de Inicio y del alcance de navegación/bootstrap para permitir únicamente este recorrido adicional.

## Capabilities

### New Capabilities
- `goal-search-screen`: presentación de P06 y sus opciones visuales no funcionales.

### Modified Capabilities
- `home-screen`: Buscar por objetivo abre P06; Explorar conserva su navegación y las nueve acciones restantes permanecen inertes, preservando los 11 mensajes normativos de Inicio.
- `flutter-app-bootstrap`: el recorrido permitido incluye Inicio → P06 y su retorno, sin ampliar el alcance a P07 u otras pantallas.

## Impact

- App Flutter: pantalla de Inicio, router existente con go_router y nueva pantalla P06, con texto vivo e iconos locales provisionales; sin nuevas dependencias ni descargas, backend, API, persistencia ni cambios al catálogo.
- Pruebas Home/router/smoke: actualizar las expectativas que hoy prohíben navegar desde las diez acciones de Inicio, preservando las regresiones del catálogo; añadir cobertura de P06 al 100%/200% y semántica accesible.
- Especificaciones: nueva capacidad `goal-search-screen` y deltas para `home-screen` y `flutter-app-bootstrap`, cuyos límites actuales restringen las acciones de Inicio y las rutas admitidas.
- La referencia visual es P06 en `docs/mockups/pantallas.md` y `docs/mockups.png`; el diagrama muestra P06 → P07, pero esa transición queda expresamente fuera de este cambio.
