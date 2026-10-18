# Plan de trabajo provisional: app Flutter Boticario AI

Estado: PROVISIONAL, pendiente de aprobación. No es una decisión oficial ni un ADR. Fecha de consulta de fuentes: 2026-09-27. Contexto y hallazgos: [`README.md`](README.md). Evidencia y URLs: [`fuentes.md`](fuentes.md). Producto de referencia: [`../../canvas/modelo-de-negocio.md`](../../canvas/modelo-de-negocio.md) y [`../../mockups/pantallas.md`](../../mockups/pantallas.md).

No hay código ni se autoriza implementarlo todavía: este plan ordena pasos, entregables y gates. "Moderno" es mantenible, testeable, accesible y seguro, no "usar lo último". No fijar versiones desde pies de página; al hacer scaffold se eligen versiones vigentes del toolchain [F07](fuentes.md#f07).

## Cómo leer este plan

- HECHO: respaldado por fuente o producto. PROPUESTA: secuencia y gates sujetos a aprobación, no exclusiones aprobadas.
- Las fases no implican sacar IA o cámara del MVP sin aprobación explícita.

## Prerrequisitos, entregables y criterios de salida

Antes de iniciar implementación, resolver o documentar los supuestos de la fase 0: MVP y alcance por pantalla, plataforma, usuarios y país; equipo, presupuesto y plazo; fuente, licencia y experto; límites de bienestar y salud, y qué datos salen del teléfono.

- Entregable por fase: un incremento verificable, no solo documentos. Cada fase define sus criterios de salida.
- El gate de publicación aplica solo antes de exponer o lanzar, según el riesgo; no bloquea las fases iniciales.
- Nada de login, pagos, sincronización, offline, mercado, equipo ni presupuesto está confirmado; toda decisión que dependa de ello queda abierta.

## Fase 0. Decisiones previas (bloqueante)

Objetivo: cerrar las preguntas que bloquean el diseño [README](README.md).

- Decidir MVP pantalla por pantalla, usuarios iniciales, país, equipo, presupuesto y plazo.
- Definir fuente, licencia y experto responsable del catálogo, y el proveedor inicial de la base de unas 150 plantas.
- Fijar límites de bienestar y salud: qué no se afirma, qué no se recomienda y cuándo se deriva a un profesional [F20](fuentes.md#f20).
- Definir qué datos salen del teléfono hacia backend o IA y su retención [F16](fuentes.md#f16), [F19](fuentes.md#f19).
- Dejar por escrito los ADRs propuestos, marcados como NO aprobados.

Entregable: respuestas documentadas y ADRs propuestos. Criterio de salida: MVP, usuarios, país, equipo, presupuesto, licencia y experto resueltos.

## Fase 1. Base de desarrollo

Objetivo: entorno reproducible y CI mínimo antes de features.

- Flutter stable con la versión fijada en el proyecto, y el Dart que incluye [F07](fuentes.md#f07).
- Android Studio, SDK, JDK y Gradle compatibles según la guía de Flutter, sin fijar números arbitrarios [F07](fuentes.md#f07).
- Editor acordado; `flutter doctor` y licencias de Android. Dispositivo físico para pruebas; macOS y Xcode SOLO si iOS se confirma [F07](fuentes.md#f07).
- Versionar lockfile y toolchain. Dependencias por mantenimiento, licencia, tests y compatibilidad [F04](fuentes.md#f04), [F06](fuentes.md#f06). Convenciones de repo: formato, ramas, revisión y estructura feature-first [F01](fuentes.md#f01).
- Entornos dev, test y prod según necesidad. Secretos en backend o CI, nunca en el cliente: `--dart-define` no es un almacén de secretos.
- CI con format, analyze, unit, widget y build. Pipelines adicionales de integración si el flujo lo justifica [F14](fuentes.md#f14), [F17](fuentes.md#f17).

Comandos ilustrativos, válidos como referencia futura. NO ejecutados aquí:

```text
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test --coverage
flutter test integration_test/        # requiere dispositivo/emulador configurado
flutter build appbundle --release     # requiere firma release configurada
```

Entregable: proyecto compila, pasa CI y tiene lockfile. Criterio de salida: `flutter doctor` limpio, CI verde y build reproducible.

## Fase 2. Primer flujo completo validable

Objetivo: Inicio -> Explorar -> Pasaporte con datos de prueba.

- Repositorios fake o fixtures curados, sin backend real.
- Componentes accesibles con estados de carga, error y vacío [F15](fuentes.md#f15).
- Caché local solo si se decidió; no asumir offline-first [F05](fuentes.md#f05).
- Dataset versionado, licenciado y revisado por experto (propuesta de producto, ver [`../../canvas/modelo-de-negocio.md`](../../canvas/modelo-de-negocio.md)).
- Contratos y esquema de procedencia, revisión y validez, sin inventar dosis ni eficacia [F13](fuentes.md#f13).
- Persistencia de usuario o mezclas en SQLite/Drift si entra en alcance, nunca preferencias como verdad; definir actualización, retirada y migraciones [F06](fuentes.md#f06).
- Favoritos, historial y perfil no se asumen definidos; el panel no documenta su flujo ([`../../mockups/navegacion.md`](../../mockups/navegacion.md)).

Entregable: flujo navegable con datos curados y tests widget. Criterio de salida: flujo completo con estados y accesibilidad básica.

## Fase 3. Objetivos, formulación y chat

Objetivo: recomendaciones revisadas por experto.

- Reglas deterministas fuera del LLM para objetivos y formulación simple [README](README.md).
- Tests de restricciones y abstención; guardar una formulación no equivale a receta segura ni validada.
- Chat si entra al release: es RAG (recuperación más generación) con corpus autorizado y fuentes verificables. Puede recuperar datos estructurados o FTS sin embeddings [F09](fuentes.md#f09); usar vectores solo si la evaluación mejora la recuperación. El tamaño inicial de unas 150 plantas no demuestra calidad suficiente de recuperación [F13](fuentes.md#f13).
- Un ID existente no prueba respaldo semántico de la respuesta; definir con experto los casos adversariales de inyección y contraindicaciones.
- Abstención explícita, límites de latencia y costo, y reporte de contenido.
- Evaluación BLOQUEANTE antes de liberar, con criterios de experto. No inventar thresholds clínicos.

Entregable: informe de evaluación y reglas documentadas. Criterio de salida: evaluación superada y aprobada por experto.

## Fase 4. Cámara como piloto independiente

Objetivo: medir identificación visual separada del resto.

- Dataset autorizado y representativo; medir falsos positivos y calibración según el diseño acordado (criterio propuesto de ingeniería, no estándar).
- Estado "no identificado" como criterio propuesto, sin consejos a partir de la imagen sola; el "92 %" del mockup NO es garantía ni métrica real.
- API y permisos deben fallar de forma segura ante negación o timeout.
- Es una fase propuesta, no una exclusión aprobada de IA o cámara.

Entregable: resultado medido del piloto y decisión de continuar o detener. Criterio de salida: métricas definidas, revisadas y decisión documentada.

## Fase 5. Antes de publicar

Objetivo: cumplir calidad, accesibilidad, rendimiento y operación.

- Calidad: tests unit, widget e integration en rutas críticas [F14](fuentes.md#f14).
- Accesibilidad: TalkBack, texto aumentado, contraste, targets y labels [F15](fuentes.md#f15).
- Rendimiento medido en modo profile sobre dispositivo físico de gama objetivo [F15](fuentes.md#f15).
- Observabilidad sin prompts, imágenes ni datos sensibles, y plan de incidentes y reversión para contenido y crashes [F16](fuentes.md#f16).
- Autorización, grants, RLS o reglas se verifican siempre en un backend expuesto, incluidos usuarios anónimos [F08](fuentes.md#f08).
- Acceso cruzado entre usuarios: prueba adicional si hay cuentas.
- Atestación no sustituye autorización ni límite; son controles distintos, no un "secreto" estático en la app [F10](fuentes.md#f10).

Entregable: build candidata con checklist firmado. Criterio de salida: gates de calidad, seguridad y Play completados.

## Checklist de Google Play (condicionado)

Aplicable según funcionalidad real. Revalidar al publicar.

- `targetSdk`: para Android móvil, apps nuevas y updates requieren API 36 desde 2026-08-31 (verificado 2026-09-27) [F18](fuentes.md#f18); distinto de `minSdk`, decisión de compatibilidad. No extrapolar a otros factores de forma.
- AAB firmado en release con la clave de subida y Play App Signing configurado, protegiendo las claves [F17](fuentes.md#f17).
- Privacidad y Data Safety deben describir el tratamiento real de consultas, fotos y datos recogidos o compartidos por los SDKs [F19](fuentes.md#f19). Leyes por país a asesorar; un disclaimer no exime.
- Declaración de salud [F20](fuentes.md#f20). Si es de salud o médica y no es dispositivo regulado: disclaimer en la descripción y consulta profesional. Se clasifica según funciones, no se asume exención por decir "bienestar".
- Chat generativo: reportar o marcar contenido in-app sin salir [F21](fuentes.md#f21). Es un requisito nuevo respecto de los mockups.
- Permisos [F22](fuentes.md#f22): PhotoPicker puntual evita el permiso amplio de galería; preview integrada requiere runtime de `CAMERA`; `ACTION_IMAGE_CAPTURE` externa puede no requerirlo según plugins. No afirmar que toda cámara va sin permiso.
- Si se crean cuentas: borrado in-app y vía web con los datos asociados [F23](fuentes.md#f23). No inventar login.
- Si la cuenta Play personal se creó después del 2023-11-13: al menos 12 inscritos de forma continua durante 14 días en closed test antes de solicitar producción; no garantiza aprobación [F24](fuentes.md#f24).

## Costos y viabilidad

Sin precios inventados. Separar el presupuesto de tiempo (desarrollo y revisión experta) del costo operativo (cuentas, backend con DB/storage/egress, IA si se usa y mantenimiento).

Modelo mensual orientativo. Definir: `llamadas_mes` (llamadas al modelo por mes; puede haber varias o reintentos por interacción), `tokens_entrada_llamada` y `tokens_salida_llamada` (promedio por llamada), y `precio_entrada`, `precio_salida` (por millón de tokens, en una moneda común).

```text
coste_modelo_mes = llamadas_mes * ((tokens_entrada_llamada * precio_entrada
                   + tokens_salida_llamada * precio_salida) / 1_000_000)
coste_operativo_mes = coste_modelo_mes + infraestructura + extras
```

La caché y las tarifas cambian el resultado; misma moneda en todos los precios. Las alertas no cortan servicios; los caps aplican solo a servicios elegibles y no son un techo global [F11](fuentes.md#f11). El corte en backend o proveedor no es absoluto. Medir p50, p95 y costo por interacción, y decidir límites y SLO explícitos sin fingir benchmarks.

## ADRs propuestos (NO aprobados)

- ADR: usar Flutter stable fijado y Android como canal inicial.
- ADR: organización feature-first y estado/DI elegido [F01](fuentes.md#f01), [F02](fuentes.md#f02).
- ADR: navegación con go_router [F03](fuentes.md#f03) y cliente HTTP base con criterio para Dio [F04](fuentes.md#f04).
- ADR: persistencia en SQLite/Drift y preferencias solo no críticas [F06](fuentes.md#f06).
- ADR: backend y proveedor solo tras equipo, costo, región y licencia; si se elige Firestore/Firebase, búsqueda de texto según edición contratada [F12](fuentes.md#f12).
- ADR: estrategia de recuperación de texto sin asumir vectores [F09](fuentes.md#f09).
- ADR: controles separados de autorización, atestación y rate limit [F08](fuentes.md#f08), [F10](fuentes.md#f10).

## Puntos pendientes y riesgos

- MVP, usuarios, país, equipo, presupuesto, licencia y experto sin confirmar.
- IA y cámara: alcance en MVP no aprobado [README](README.md).
- Persistencia, offline, cuentas y datos enviados a IA, y fechas y políticas de Play por revalidar.
- Este plan se limita al alcance de las fuentes consultadas y es una propuesta; no garantiza exhaustividad ni constituye una revisión sistemática.
