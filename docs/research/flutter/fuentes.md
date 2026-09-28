# Fuentes de research: app Flutter Boticario AI

Registro de evidencia consultada en vivo para el state of the art de la app Flutter. Fecha de consulta: 2026-09-27. La fecha es el momento de consulta, no una aprobación legal ni una garantía de vigencia perpetua: versiones, políticas y requisitos cambian.

Acompaña a [README.md](README.md) y [plan-de-trabajo.md](plan-de-trabajo.md), que enlazan a los IDs `F01` a `F24` de este archivo. Los enlaces a plataformas y a paquetes comunitarios se distinguen en cada entrada. No se copian versiones exactas de dependencias: al ejecutar el scaffold hay que fijar versiones vigentes según el toolchain elegido.

## F01

**Arquitectura de aplicaciones Flutter (doc oficial de la plataforma).** [Guía de arquitectura](https://docs.flutter.dev/app-architecture/guide) y [recomendaciones](https://docs.flutter.dev/app-architecture/recommendations).

Respalda la separación entre capa UI y capa de datos, con views/viewmodels, repositorios y services, y dominio opcional. Las recomendaciones son guías, no reglas obligatorias ni una estructura de carpetas impuesta.

## F02

**Gestión de estado e inyección de dependencias.** [Opciones de state management (doc oficial)](https://docs.flutter.dev/data-and-backend/state-mgmt/options), [flutter_riverpod (paquete comunitario)](https://pub.dev/packages/flutter_riverpod) y [flutter_bloc (paquete comunitario)](https://pub.dev/packages/flutter_bloc).

Flutter no exige una solución de estado; Riverpod y Bloc son terceros. Cualquier recomendación concreta hacia una de ellas es decisión propia del proyecto, no oficial.

## F03

**Enrutado declarativo.** [go_router en pub.dev](https://pub.dev/packages/go_router).

Paquete publicado por `flutter.dev` para rutas declarativas y navegación basada en URL. No se fija aquí una versión exacta; revisar la vigente al integrarlo.

## F04

**Cliente HTTP.** [http en pub.dev](https://pub.dev/packages/http) y [dio en pub.dev](https://pub.dev/packages/dio).

`http` lo publica `dart.dev`; Dio es comunitario y aporta interceptores y cancelación. Elegir uno según necesidad; no usar ambos sin motivo.

## F05

**Offline first.** [Patrón offline-first (doc oficial de Flutter)](https://docs.flutter.dev/app-architecture/design-patterns/offline-first).

El repositorio combina fuente local y remota. La sincronización y la validez de los datos se diseñan explícitamente; no son automáticas solo por usar caché.

## F06

**Persistencia local.** [shared_preferences (paquete del equipo Flutter en pub.dev)](https://pub.dev/packages/shared_preferences) y [drift (paquete comunitario)](https://pub.dev/packages/drift).

`shared_preferences` sirve para preferencias simples, no para datos críticos. Drift es SQLite reactivo comunitario. No guardar credenciales ni historial sensible en preferencias.

## F07

**Toolchain y setup de plataformas.** [Setup Android (doc oficial)](https://docs.flutter.dev/platform-integration/android/setup), [setup iOS (doc oficial)](https://docs.flutter.dev/platform-integration/ios/setup) y [release notes de Flutter](https://docs.flutter.dev/release/release-notes).

Cubre `flutter doctor`, licencias de Android y requisitos de Xcode en macOS. Conviene partir del SDK stable oficial al hacer el scaffold; no inferir versiones desde footers ni desde pub.dev.

## F08

**Supabase y Row Level Security.** [Tutorial de Supabase con Flutter](https://supabase.com/docs/guides/getting-started/tutorials/with-flutter) y [Row Level Security en Postgres](https://supabase.com/docs/guides/database/postgres/row-level-security).

El SDK cliente usa una clave publicable con grants y RLS; la clave de servicio o secret privilegiado solo debe vivir en servidor. RLS no es un mecanismo de rate limit.

## F09

**Recuperación de texto.** [Full text search en PostgreSQL](https://www.postgresql.org/docs/current/textsearch.html) y [pgvector](https://github.com/pgvector/pgvector).

FTS es nativo de Postgres. pgvector hace búsqueda exacta por defecto y ofrece índices aproximados como opción, con un tradeoff de recall y latencia. Esto no demuestra que FTS baste para un corpus de unas 150 plantas: hay que medirlo.

## F10

**Protección de backend con Firebase.** [Firebase AI Logic](https://firebase.google.com/docs/ai-logic), [checklist de seguridad de AI Logic](https://firebase.google.com/docs/ai-logic/security-checklist) y [App Check](https://firebase.google.com/docs/app-check).

El SDK de Flutter puede pasar por un proxy; App Check es atestación complementaria a la autenticación, no elimina el abuso. No confundir auth, RLS y rate limits.

## F11

**Control de costes.** [Evitar facturas sorpresa en Firebase](https://firebase.google.com/docs/projects/billing/avoid-surprise-bills).

Las alertas no detienen servicios; los spend caps aplican solo a servicios elegibles y bajo ciertas condiciones, no son un techo global garantizado. Conviene además definir controles de límite o corte en backend o en el proveedor, no solo en la UI, que es eludible.

## F12

**Búsqueda textual en Firestore.** [Text search en Firestore Enterprise](https://firebase.google.com/docs/firestore/enterprise/text-search).

Según la fuente consultada, la búsqueda textual requiere la edición Enterprise. No asumirlo para Standard ni declarar su ausencia en todo Firebase; depende de la edición contratada.

## F13

**Riesgos de IA generativa.** [OWASP LLM01: Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

RAG y fine-tuning no eliminan la inyección de prompts. Respalda separar contenido no confiable, aplicar mínimo privilegio y validar/evaluar salidas. Citar IDs no demuestra respaldo semántico de una respuesta.

## F14

**Estrategia de tests.** [Testing overview (doc oficial)](https://docs.flutter.dev/testing/overview) y [integration tests (doc oficial)](https://docs.flutter.dev/testing/integration-tests).

Distingue tests unit, widget e integration según riesgo y flujos críticos. No es una exigencia de cobertura concreta ni de una herramienta determinada.

## F15

**UX, accesibilidad y rendimiento.** [Testing de accesibilidad](https://docs.flutter.dev/ui/accessibility/accessibility-testing), [buenas prácticas adaptativas y responsivas](https://docs.flutter.dev/ui/adaptive-responsive/best-practices), [rendimiento de UI](https://docs.flutter.dev/perf/ui-performance) y [diseño Material en Flutter](https://docs.flutter.dev/ui/design/material).

Cubre contraste, tamaños de toque, labels y text scaling, diseño adaptativo y medición de performance. La fuente de diseño Material confirma Material 3 como sistema oficial de Google, habilitado por defecto en releases recientes de Flutter. El profiling debe hacerse en dispositivo físico; el modo debug no sirve para juzgar rendimiento.

## F16

**Seguridad móvil.** [OWASP MASVS](https://mas.owasp.org/MASVS/) y [riesgo de filtración de logs en Android](https://developer.android.com/privacy-and-security/risks/log-info-disclosure).

MASVS es un marco de controles, no una certificación automática. Evitar registrar datos sensibles en logs. Queda como referencia de diseño, no como garantía de cumplimiento.

## F17

**Entrega y despliegue.** [Continuous delivery (doc oficial)](https://docs.flutter.dev/deployment/cd) y [despliegue Android (doc oficial)](https://docs.flutter.dev/deployment/android).

Cubre CI, release signing y manejo seguro de credenciales, y la publicación en AAB release. No fija un proveedor de CI ni un flujo único.

## F18

**Requisito de API de Google Play.** [Target API level para Play](https://support.google.com/googleplay/android-developer/answer/11926878).

Verificado el 2026-09-27: para apps nuevas y updates de Android móvil el target es Android 16 / API 36 desde 2026-08-31. Es `targetSdk`, no `minSdk`. Revisar al publicar y no extrapolar a Wear, TV ni otros factores de forma.

## F19

**Privacidad en Play.** [Política de privacidad obligatoria](https://support.google.com/googleplay/android-developer/answer/10144311) y [Data Safety](https://support.google.com/googleplay/android-developer/answer/10787469).

Respalda declarar política de privacidad y la sección Data Safety incluyendo SDKs y datos tratados, no solo los propios. Es una obligación de plataforma sujeta a cambios.

## F20

**Aplicaciones de salud en Play.** [Declaración de apps de salud](https://support.google.com/googleplay/android-developer/answer/14738291) y [requisitos para apps de salud y médicas](https://support.google.com/googleplay/android-developer/answer/16679511).

La declaración aplica también a closed, open y producción, con excepciones privadas o de sistema. Las apps de salud o médicas que no son dispositivo regulado deben incluir disclaimer en la descripción y recomendar consulta profesional, clasificando según funciones y mercado. No afirmar que la app no es legalmente médica ni que un disclaimer autoriza dar consejos.

## F21

**IA generativa en Play.** [Política de apps con IA generativa](https://support.google.com/googleplay/android-developer/answer/13985936).

Cubre el chat generativo entre los casos alcanzados y exige reporte o flag in-app sin salir de la app y prevención de contenido restringido. Aplica según la funcionalidad real de la app.

## F22

**Minimización de permisos en Android.** [Minimizar solicitudes de permisos](https://developer.android.com/privacy-and-security/minimize-permission-requests).

Los pickers puntuales no requieren permiso amplio de galería; `ACTION_IMAGE_CAPTURE` externa puede no necesitar `CAMERA`, mientras que una preview integrada sí requiere gestión de permiso en runtime. La distinción importa para no pedir permisos de más.

## F23

**Borrado de cuentas.** [Requisitos de borrado de cuenta](https://support.google.com/googleplay/android-developer/answer/13327111).

Es condicional: si la app permite crear cuentas, debe ofrecer borrado vía in-app y web, junto con los datos asociados. No asumir que la app tendrá login.

## F24

**Testing previo a producción en Play.** [Requisitos de testing de apps nuevas](https://support.google.com/googleplay/android-developer/answer/14151465).

Para cuentas personales creadas después del 2023-11-13, el requisito indicado es 12 testers durante 14 días continuos antes de solicitar producción. No es universal ni implica aprobación automática.

## Alcance y criterios de lectura

- **Docs oficiales de plataforma:** Flutter, Supabase, PostgreSQL, Firebase, Android y Google Play. Describen capacidades y requisitos del proveedor.
- **Paquetes oficiales del equipo Flutter o Dart en pub.dev:** go_router, http y shared_preferences.
- **Paquetes y proyectos comunitarios:** Riverpod, Bloc, dio y drift en pub.dev; pgvector es un proyecto comunitario. Reflejan el estado del paquete, no un estándar de plataforma.
- **Estándares de seguridad:** OWASP LLM Top 10 y MASVS son proyectos o estándares de seguridad, no proveedores de plataforma.
- **Tutoriales de Supabase:** documentación oficial del proveedor, no contenido comunitario.
- **IDs estables:** `F01` a `F24` se usan como anclas desde el README y el plan. No renumerar sin actualizar los enlaces entrantes.
- **Vigencia:** cada hecho se consultó el 2026-09-27. Las políticas de Play y los requisitos de API se revisan al momento de publicar; cuotas, límites de gasto y dependencias se revalidan antes de integrar.
- **Alcance:** este archivo registra evidencia de las fuentes consultadas. Las notas de alcance o lectura (por ejemplo, preferencias de almacenamiento o la distinción de IDs) no convierten la fuente en una decisión del proyecto ni sustituyen la validación con las fuentes.
