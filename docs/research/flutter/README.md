# Flutter: propuesta de aplicación moderna (research)

Estado: propuesta pendiente de aprobación, no decisión oficial ni ADR. Fecha de consulta de fuentes: 2026-09-27. Evidencia y URLs: [`fuentes.md`](fuentes.md). Pasos, gates y release: [`plan-de-trabajo.md`](plan-de-trabajo.md).

Este documento sintetiza investigación revisada para orientar una app Flutter moderna. No es un guion de implementación completo ni un conjunto de verdades aprobadas. Aquí "moderno" significa mantenible, testeable, accesible y seguro, no "usar lo último" ni migrar a microservicios.

## 1. Resumen accionable

- Moderno aquí significa mantener, testear, ser accesible y seguro por defecto, con dependencias justificadas. No equivale a microservicios ni a "latest".
- Alcance propuesto: Android en Google Play como canal inicial; iOS queda como expansión potencial, no confirmada.
- Origen del contexto de producto:
  - [`../../canvas/modelo-de-negocio.md`](../../canvas/modelo-de-negocio.md)
  - [`../../mockups/README.md`](../../mockups/README.md)
  - [`../../mockups/pantallas.md`](../../mockups/pantallas.md)
  - [`../../mockups/navegacion.md`](../../mockups/navegacion.md)
- La base especializada ronda 150 plantas, cifra distinta de la cantidad de documentos y del tamaño del corpus para búsqueda o IA.
- No hay requisitos confirmados de login, pagos, sincronización, offline, SLA, presupuesto ni tamaño de equipo. Toda decisión que dependa de ellos queda abierta por ahora.

### Cómo leer este documento

HECHOS son fuentes y contexto del repo. RECOMENDACIONES son preferencias provisionales sujetas a aprobación. DECISIONES abiertas son preguntas que bloquean el diseño.

## 2. HECHOS

### Producto y pantallas

- El canvas propone orientación personalizada, pasaportes digitales, recomendaciones explicables, consulta asistida y reconocimiento visual experimental. Marca Google Play como canal inicial y App Store como posibilidad futura.
- Los mockups describen 10 pantallas: Splash, Onboarding, Inicio, Explorar, Pasaporte digital, Buscar por objetivo, Resultados, Formular mezcla, Identificar con cámara y Chat, con barra inferior Inicio/Favoritos/Historial/ Perfil cuyos flujos no detalla.
- Los datos de las capturas (nombres, dosis, "Confianza: 92 %", fuentes) son ilustrativos, no afirmaciones validadas ni métricas reales; la lámina es una maqueta simplificada, no una especificación funcional.

### Evidencia técnica revisada

- Arquitectura: Flutter documenta guías de arquitectura, UI y datos, y MVVM con capa domain opcional [F01](fuentes.md#f01).
- Paquetes: hay opciones oficiales para HTTP y navegación, y opciones comunitarias para estado/DI y persistencia; offline-first figura como patrón [F02](fuentes.md#f02), [F03](fuentes.md#f03), [F04](fuentes.md#f04), [F05](fuentes.md#f05), [F06](fuentes.md#f06).
- Backend y recuperación: Postgres cubre búsqueda de texto completo y extensión vectorial; Supabase aporta integración con RLS; Firebase ofrece proxy de IA, atestación y alertas de facturación, con búsqueda de texto completa en Firestore Enterprise y no en Standard según su documentación [F08](fuentes.md#f08), [F09](fuentes.md#f09), [F10](fuentes.md#f10), [F11](fuentes.md#f11), [F12](fuentes.md#f12).
- Calidad: testing e integración, accesibilidad/adaptabilidad/performance, controles MASVS, prevención de filtración en logs y CI/despliegue Android [F14](fuentes.md#f14), [F15](fuentes.md#f15), [F16](fuentes.md#f16), [F17](fuentes.md#f17).
- Google Play: exige cumplir la API objetivo, política de privacidad/Data Safety y completar la declaración de salud para la publicación prevista. Los requisitos adicionales dependen del caso: contenido de salud/médico, reporte in-app si hay chat generativo, borrado si se crean cuentas y pruebas previas para ciertas cuentas personales nuevas [F18](fuentes.md#f18), [F19](fuentes.md#f19), [F20](fuentes.md#f20), [F21](fuentes.md#f21), [F23](fuentes.md#f23), [F24](fuentes.md#f24).

## 3. RECOMENDACIONES provisionales

### 3.1 Stack

- Flutter stable como propuesta, con la versión fijada en el proyecto y el Dart que incluye. Las actualizaciones se tratan como cambios deliberados y probados, no automáticos [F07](fuentes.md#f07).
- Organización feature-first: cada feature con UI y data, y dentro views, viewmodels, repositorios y servicios. Capa domain solo para lógica compleja o de seguridad [F01](fuentes.md#f01).
- Estado e inyección de dependencias: Riverpod como preferencia para estado asíncrono y DI [F02](fuentes.md#f02). No es recomendación oficial de Flutter ni conviene mezclar provider, get_it y Bloc en el mismo proyecto.
- Bloc es alternativa razonable si el equipo ya tiene expertise o si predominan flujos de eventos [F02](fuentes.md#f02).
- Navegación: go_router [F03](fuentes.md#f03).
- UI: Material 3 como preferencia nuestra, no como mandato, con componentes y tokens derivados de los mockups. Incluir estados vacíos, loading, error y offline, y accesibilidad desde el inicio [F15](fuentes.md#f15).
- HTTP: http basta como base [F04](fuentes.md#f04). Dio solo si requisitos concretos lo justifican (interceptores, cancelación, reintentos). No usar ambos a la vez.
- Preferencias: shared_preferences para ajustes no críticos únicamente [F06](fuentes.md#f06).
- Datos locales: JSON en assets para el prototipo validado. Si entran datos de usuario, guardado de mezclas o caché consultable, usar SQLite/Drift con migraciones [F06](fuentes.md#f06). Nunca usar preferencias como historial sensible.
- Evitar codegen múltiple y monorepos de paquetes preventivos sin necesidad.

### 3.2 Arquitectura sugerida

Flujo base dentro de una feature:

```text
Vista -> VM/controlador -> repositorio -> servicio -> (red o almacenamiento)
```

Caso opcional cuando hay lógica compleja:

```text
VM -> caso de uso (domain) -> uno o varios repositorios
```

- Flutter no obliga a tener backend. Como propuesta nuestra, para chat o corpus controlado conviene una API pequeña o funciones server/proxy con validación y límites centralizados, no microservicios; los controles en servidor se apoyan en [F08](fuentes.md#f08) y [F10](fuentes.md#f10).
- Postgres gestionado o Supabase es candidato razonado: relaciones, procedencia, migraciones y búsqueda de texto completo [F08](fuentes.md#f08), [F09](fuentes.md#f09).
- Firebase es alternativa por sus SDKs, capacidades offline y servicios gestionados, según el caso. Ojo con la búsqueda de texto y las ediciones: Firestore Enterprise tiene búsqueda que no está en Standard [F12](fuentes.md#f12).
- No fijar lenguaje de backend, proveedor ni modelo sin equipo, costos, región y licencia resueltos.
- Si se usa un SDK cliente gestionado, exponer solo claves publicables. En Supabase eso exige grants y políticas RLS; en Firebase, reglas de acceso propias del servicio. No son intercambiables. Los secretos privilegiados nunca van en Flutter [F08](fuentes.md#f08), [F10](fuentes.md#f10).
- Firebase AI Logic permite mantener la clave del proveedor en el servidor mediante un proxy; la seguridad depende de la configuración (autenticación, atestación, límites), no del hecho de usar un SDK. No hay que afirmar que toda llamada de SDK de IA es insegura [F10](fuentes.md#f10).

### 3.3 Datos e IA del dominio

- Catálogo curado y versionado, con fuentes, licencias, procedencia y revisión experta.
- Distinguir especie, planta, material, aceite y quimiotipo cuando aplique. Esa distinción la definen expertos, no la app.
- No inventar datos clínicos, dosis ni eficacia. Los ejemplos del mockup no son datos válidos.
- Definir actualización, retirada y validez de caché porque el contenido cambia. Los assets no son una estrategia de publicación automática.
- Objetivos y recomendaciones simples pueden resolverse con reglas y contenido curado sin LLM.
- Baseline con datos estructurados o búsqueda de texto completo, a evaluar contra consultas reales [F09](fuentes.md#f09). Embeddings o índice vectorial solo si una evaluación muestra mejora frente al baseline.
- Chat: recuperación y generación (RAG). Debe recuperar solo corpus autorizado y citar fuentes verificables. Que un ID exista no prueba que soporte la respuesta. Sin decisiones de seguridad ni dosis inventadas. Reglas deterministas validadas fuera del modelo, con abstención y evaluación antes del release: groundedness, riesgos, inyección, latencia y costo [F13](fuentes.md#f13). La cautela sobre el corpus aplica también al baseline: 150 plantas no demuestran calidad de recuperación suficiente.
- Cámara: la recomendación de tratarla como experimento independiente es de ingeniería y se basa en el carácter experimental del reconocimiento visual en el Canvas. Exige pruebas reales, sin tratar "92 %" como métrica, manejar desconocido y abstención, y no derivar recomendaciones de una confianza visual sin confirmación y validación. Los permisos mínimos que la respaldan están en [F22](fuentes.md#f22); no cubren umbrales ni validación botánica.

### 3.4 Seguridad y operación mínimas

- Separar tres controles distintos: autorización (grants y políticas RLS), atestación tipo AppCheck y rate limiting [F08](fuentes.md#f08), [F10](fuentes.md#f10).
- No usar credenciales privilegiadas en el cliente ni tratar un token estático como autorización. Una configuración o clave publicable no es un secreto. Si existen tokens de usuario, proteger su almacenamiento. Proteger también a usuarios sin login: el abuso y los costos aplican igual.
- Definir límites de tokens, requests y timeouts, con corte propio y alertas. Son mitigaciones, no un techo absoluto [F11](fuentes.md#f11).
- Minimizar, retener y borrar datos según política. No registrar logs ni prompts sensibles [F16](fuentes.md#f16). Si se introducen tokens, guardarlos con el almacenamiento seguro del sistema operativo. Datos locales sensibles bajo threat model explícito.
- Testing y observabilidad saneada desde la base, no como añadido tardío [F14](fuentes.md#f14).
- El release en Play tiene requisitos propios (API objetivo, declaraciones y pruebas). No se repiten aquí: ver [`plan-de-trabajo.md`](plan-de-trabajo.md) y [F18](fuentes.md#f18), [F19](fuentes.md#f19), [F20](fuentes.md#f20), [F21](fuentes.md#f21), [F23](fuentes.md#f23), [F24](fuentes.md#f24).

### 3.5 Alcance propuesto por fases

1. Catálogo curado y navegación base (Explorar y Pasaporte; Favoritos básico solo si se confirma en el MVP).
2. Objetivos y recomendaciones con experto.
3. IA evaluada (chat con recuperación y fuentes).
4. Cámara como experimento separado.

- Formulaciones solo si entran al release con límites y revisión validada.
- Este documento no afirma que el usuario haya aceptado sacar IA o cámara del MVP. Solo propone secuencia y gates.
- Pasos, criterios de aceptación y orden de release: ver [`plan-de-trabajo.md`](plan-de-trabajo.md).

### 3.6 Qué posponer

- Kubernetes y microservicios.
- Base de datos vectorial separada sin evidencia que la justifique.
- Agentes autónomos.
- Login, pagos y sincronización sin requisito confirmado.
- Exceso de codegen y de plataformas objetivo.

No posponer: observabilidad, pruebas y privacidad. Deben nacer con el producto.

## 4. DECISIONES abiertas prioritarias

1. Qué funcionalidades exactas forman el MVP, pantalla por pantalla.
2. Plataforma y usuarios iniciales, y país de lanzamiento.
3. Equipo, presupuesto y plazo disponibles.
4. Fuente, licencia y experto del catálogo, más los límites de bienestar.
5. Persistencia, offline, cuentas y qué datos se envían a servicios de IA.

Próximo paso: validar estas respuestas. Con ellas se pueden preparar ADRs y el scaffold. No implementar nada de esto todavía.

## 5. Supuestos y limitaciones

Se asume un equipo pequeño y validación previa con expertos, sin cifras confirmadas. Los banners y pies de las fuentes pueden variar, así que no se fijan versiones exactas. El alcance se acota a las fuentes consultadas, sin garantía de exhaustividad. Estas recomendaciones son provisionales y no sustituyen ADRs ni pruebas con datos reales.
