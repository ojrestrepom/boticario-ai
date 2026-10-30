# Design

## Context

Estado actual, con sus fuentes:

- La API no comprueba credenciales: el requisito vigente es «API de solo lectura sin autenticación» (`openspec/specs/catalog-api/spec.md`). El router monta `/health`, `/openapi.json` y `/v1/plants[/{id}]` con un `fallback` y un `method_not_allowed_fallback` que responden `application/problem+json` (`backend/catalog-api/src/http.rs:22-33`).
- El servicio de Cloud Run se despliega con `--allow-unauthenticated` y la cuenta de ejecución `boticario-runtime` (`.github/workflows/deploy-backend.yml:109,117`); esa cuenta no tiene roles (`docs/deploy/cloud-run.md:67`, tabla «Roles y permisos»). La verificación posterior consulta `/health` y `/v1/plants/lavandula-angustifolia` sin credenciales (`.github/workflows/deploy-backend.yml:125-140`).
- La configuración se resuelve en `Config` (`backend/catalog-api/src/config.rs:48-58`), que deriva `Debug` y `PartialEq`, y `from_env_and_args` recibe el entorno como función (`config.rs:91`), lo que permite probar sin tocar el entorno real. Los códigos de salida son 0, 1 (arranque) y 2 (configuración inválida) (`backend/catalog-api/src/main.rs:3`).
- La app envía únicamente `Accept: application/json` (`app/lib/features/catalog/data/catalog_repository.dart:39`), mapea 5xx y 400 a errores de cliente (`catalog_repository.dart:99-120`) y todos los tipos de error son reintentables por el usuario (`catalog_client_exception.dart:10`). `HttpCatalogRepository` se construye en `catalog_providers.dart:19`.
- La propuesta `add-backend-ci-and-plain-logs` ya está aprobada y en implementación: el despliegue llamará a `backend-ci.yml` como job `verify` y modifica el mismo requisito «Despliegue automático con verificación posterior». Este cambio se construye sobre ese texto y debe archivarse después.

Motivación y límites: véase `proposal.md`. Resumen de las limitaciones, que la documentación del cambio repetirá:

- El token va embebido en el APK, así que se puede extraer (descompilando o inspeccionando el tráfico). Autoriza a «la app» frente a clientes casuales y escáneres, no a personas.
- Un 401 lo produce la API dentro del contenedor, así que la petición se factura como cualquier otra. Cloud Run no factura las peticiones rechazadas por IAM antes de llegar al contenedor (https://cloud.google.com/run/pricing, sección de peticiones; la capa gratuita es de 2 millones de peticiones al mes), pero eso exigiría quitar `--allow-unauthenticated` y autenticar con identidades de Google, que la app no tiene. El `max-instances=2` sigue siendo el tope real del gasto.
- No sustituye a una protección de borde (Cloud Armor, API Gateway, límite de tasa o App Check), que el usuario descartó por ahora.

## Goals / Non-Goals

**Goals:**

- Que la API rechace con 401 toda petición a `/v1` sin un token válido, con el mínimo de piezas nuevas: un middleware, una variable de entorno y un secreto.
- Que no se pueda desplegar la API abierta por accidente.
- Que el token pueda rotarse sin cortar el servicio ni dejar de poder compilar la app.
- Que el token no aparezca nunca en el repositorio, en logs, en mensajes de error ni en los artefactos de QA.

**Non-Goals:**

- Autenticar usuarios, tokens por usuario, expiración, revocación inmediata o límite de tasa.
- Proteger de verdad el token dentro del APK (ofuscación, Play Integrity, App Check).
- Cambiar el contenido de las respuestas de datos ni el prefijo `/v1`.

## Decisions

### D1. `Authorization: Bearer` sobre `/v1/*`, 401 con `problem+json` y `WWW-Authenticate: Bearer`

El esquema Bearer (RFC 6750, https://www.rfc-editor.org/rfc/rfc6750) es el estándar para un token opaco y lo soportan los clientes, Postman y `curl` sin trabajo extra. El nombre del esquema no distingue mayúsculas (RFC 9110 §11.1, https://www.rfc-editor.org/rfc/rfc9110#section-11.1). Un 401 debe llevar `WWW-Authenticate` (RFC 9110 §15.5.2) y el cuerpo usa el `application/problem+json` que ya emiten los demás errores (RFC 9457, ya exigido por el requisito «Errores estandarizados»).

El mensaje es el mismo si el token falta, está mal formado o es incorrecto, y se omite el parámetro `error="invalid_token"` de RFC 6750 §3: así la respuesta no ayuda a un atacante a distinguir casos y el cliente legítimo no necesita la diferencia, porque la app tiene un único token y nada que corregir en tiempo de ejecución. Se acepta perder esa precisión de diagnóstico; el servidor puede registrar a nivel `debug` la clase del fallo (ausente, esquema distinto, no coincide) sin el valor, y Cloud Run ya registra el 401 en sus logs de petición.

El middleware se aplica en el router raíz con un predicado por ruta: exige el token a cualquier ruta cuyo camino sea `/v1` o empiece por `/v1/`, antes del enrutado. Así una ruta inexistente o un método no permitido bajo `/v1` también devuelve 401 y no 404/405, de modo que sin token no se aprende qué rutas existen. Un test recorre los caminos del documento OpenAPI y falla si hay uno de datos fuera de `/v1` que no sea `/health` ni `/openapi.json`, para que una ruta nueva no quede pública por omisión.

Alternativas descartadas:

- Cabecera propia `X-Api-Key`: sin ventaja y obliga a documentar un esquema no estándar; el esquema Bearer ya tiene soporte en OpenAPI (`http`/`bearer`).
- Token en la query (`?token=`): acaba en logs de acceso, historiales y cabeceras `Referer`.
- Denegar por defecto todo salvo `/health` y `/openapi.json` (lista de permitidos): es más seguro ante rutas futuras, pero convierte los 404 de rutas desconocidas fuera de `/v1` en 401 y cambia más escenarios vigentes. Se cubre el mismo riesgo con el test de rutas descrito arriba.
- Aplicar la capa solo con `route_layer` sobre el sub-router de `/v1`: no cubriría el `fallback` (404) ni el 405.

Nota sobre Cloud Run: con `--allow-unauthenticated` el servicio no valida identidades de Google y la cabecera `Authorization` llega al contenedor. La documentación de Cloud Run (https://docs.cloud.google.com/run/docs/authenticating/overview) describe `Authorization` como el lugar del token de identidad cuando la invocación exige IAM; si algún día se activara IAM, la app tendría que enviar el token de API en otra cabecera. La QA comprueba contra el servicio real que la cabecera llega intacta.

### D2. `/health` público; `/openapi.json` público (U3)

`/health` lo usan la sonda de arranque de Cloud Run (`deploy-backend.yml:118`) y la verificación posterior, que no pueden llevar el token sin complicar la sonda; solo informa de que el proceso está vivo (`http.rs:75-77`) y no revela datos.

`/openapi.json` queda público: el contrato ya está versionado en el repositorio (`backend/openapi.json`), describe rutas que están en el código fuente y no contiene valores de token, solo el esquema de seguridad. Protegerlo no añade seguridad real y obligaría a las herramientas de documentación a pasar el token. Decisión U3 tomada el 2026-10-18: `/openapi.json` público.

### D3. Tokens por entorno: `API_TOKENS`, obligatorio siempre, comparación en tiempo constante (U2, U7)

- Variable `API_TOKENS`: lista separada por comas con uno o más tokens. Más de uno permite rotar sin cortar el servicio (D7) y tener un token por cliente (la app y la verificación de CI, D6).
- Validación al arrancar: se recortan espacios y el salto de línea final (Secret Manager puede guardar el valor con uno); cada token tiene entre 32 y 256 caracteres del conjunto `token68` de RFC 6750 §2.1 (letras, dígitos y `-._~+/`); no hay elementos vacíos. Un valor inválido termina con código 2 y un mensaje que nombra la variable y el motivo, nunca el valor. 32 caracteres hexadecimales dan 128 bits, de sobra para un secreto compartido; `openssl rand -hex 32` produce 64 caracteres.
- Obligatorio siempre: sin `API_TOKENS` la API no arranca. `--help` y `--openapi` no sirven rutas y no lo exigen (el flujo de regeneración del OpenAPI y su test no necesitan token). Decisión U2 tomada el 2026-10-18: el token es obligatorio siempre, también en local, con un `.env` local. Un modo «auth desactivada» solo existiría como una variable que alguien puede olvidar fijada en producción; el objetivo es que desplegar sin token sea imposible. El costo está en el desarrollo local, que se resuelve así:
  - `cargo run`: `API_TOKENS=$(openssl rand -hex 32) cargo run -p catalog-api`, o un valor fijo local en el shell.
  - `compose.yaml`: `API_TOKENS: ${API_TOKENS:?define API_TOKENS ...}`; Compose lee `.env` de la raíz (`.gitignore` ya ignora `.env`, línea «Entorno y secretos»), así que basta crearlo una vez con `echo "API_TOKENS=$(openssl rand -hex 32)" > .env`. Sin él, `docker compose up` falla antes de arrancar con un mensaje claro (https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).
  - Pruebas: el router recibe el conjunto de tokens como parámetro y las pruebas usan un valor ficticio de 32 o más caracteres; no leen el entorno.
- `Config` deriva `Debug`: los tokens viven en un tipo propio cuyo `Debug` imprime `ApiTokens(<n> tokens)` y que no implementa `Display`; sus errores de validación no incluyen el valor.
- Comparación en tiempo constante con el crate `subtle` (`ConstantTimeEq`, https://docs.rs/subtle), recorriendo todos los tokens configurados sin cortocircuito. `subtle` compara primero las longitudes, así que la longitud puede filtrarse por temporización; no es relevante porque todos los tokens válidos tienen formato público y cota inferior conocida. Decisión U7 tomada el 2026-10-18: se acepta la dependencia `subtle`, pequeña y ampliamente usada; escribir el bucle a mano evitaría la dependencia pero pondría el riesgo (optimización del compilador) en el código propio.

Alternativas descartadas: un único token (`API_TOKEN`) sin lista, que obliga a cortar a los clientes al rotar; un token por defecto en el código o en `compose.yaml` (comodidad local, pero es un secreto conocido que alguien puede llevar a un despliegue real); un archivo de tokens (más piezas que una variable).

### D4. Entrega del token a Cloud Run: Secret Manager con versión fijada (U1)

Decisión U1 tomada el 2026-10-18: Secret Manager con versión fijada, no `latest`. Comparación con la alternativa descartada para este proyecto (un propietario, un servicio, sin datos de usuario):

| Aspecto | Secret Manager + `--set-secrets` | Secreto de GitHub + `--set-env-vars` |
| --- | --- | --- |
| Pasos manuales | Habilitar `secretmanager.googleapis.com`, crear el secreto con su primera versión, un enlace de IAM sobre ese secreto para `boticario-runtime` (tres comandos) | Crear el secreto de GitHub (un comando) |
| Costo | 0 dentro de la capa gratuita: 6 versiones activas y 10 000 accesos al mes; después 0,06 USD por versión activa al mes y 0,03 USD por 10 000 accesos (https://cloud.google.com/secret-manager/pricing). Con variable de entorno hay un acceso por arranque de instancia | 0 |
| Dónde queda el valor | En Secret Manager; el servicio solo guarda la referencia (`gcloud run services describe` muestra el nombre del secreto, no su valor, https://docs.cloud.google.com/run/docs/configuring/services/secrets) | En la configuración de cada revisión: lo ve quien pueda leer el servicio (`roles/run.viewer` o superior), y las revisiones viejas conservan el valor anterior |
| Rotación | Nueva versión del secreto y despliegue con la versión nueva; las versiones viejas se desactivan o destruyen | Cambiar el secreto de GitHub y volver a desplegar; el valor viejo sigue en las revisiones antiguas |
| IAM nueva | `roles/secretmanager.secretAccessor` solo sobre el secreto para la cuenta de ejecución; el deployer no necesita acceso al valor, solo `roles/run.admin` y `serviceAccountUser` (docs de secretos arriba) | Ninguna |
| Auditoría | Los accesos al secreto pueden auditarse | No |

Cloud Run comprueba en el despliegue que la cuenta de ejecución puede acceder a los secretos; si no, el despliegue falla. Con variables de entorno el valor se resuelve al arrancar la instancia, por eso la documentación de Cloud Run recomienda fijar una versión concreta y no usar `latest`: con `latest`, instancias del mismo servicio podrían arrancar con valores distintos durante una rotación, y una rotación no tiene efecto visible hasta que arrancan instancias nuevas (https://docs.cloud.google.com/run/docs/configuring/services/secrets). Por eso se fija la versión en el workflow (`--set-secrets=API_TOKENS=boticario-api-tokens:<n>`) y rotar es un commit, que además dispara un despliegue.

Se elige Secret Manager: cuesta tres comandos de una sola vez y evita que el token viva en la configuración de las revisiones. La alternativa del secreto de GitHub con `--set-env-vars` queda descartada: la documentación oficial de Cloud Run dice «we don't recommend them as a way to store secrets such as database credentials or API keys» y «For storing secrets, we recommend that you use Secret Manager» (https://docs.cloud.google.com/run/docs/configuring/services/environment-variables). Los pasos manuales (habilitar la API, crear el secreto con los dos tokens sin dejarlos en el historial del shell, dar el rol sobre el secreto, crear el secreto de GitHub `API_VERIFY_TOKEN`, rotar y desmontar) quedan documentados como pasos reproducibles con comandos en `docs/deploy/cloud-run.md` (tareas 7.2 y 8.1 a 8.4), y esa guía es la que seguirá el usuario.

El enlace de IAM sobre el secreto modifica el requisito «La cuenta de servicio de ejecución SHALL NOT tener roles»: se reescribe como «sin roles en el proyecto; su único permiso es `secretAccessor` sobre ese secreto», que el delta de `backend-deployment` refleja.

### D5. Verificación posterior del workflow: token propio de CI en un secreto de GitHub (U5)

La verificación necesita llamar a `/v1/plants/lavandula-angustifolia` y ejercita la base de datos. Opciones:

- Secreto de GitHub `API_VERIFY_TOKEN` con un token dedicado a la CI, que forma parte de `API_TOKENS` junto al de la app. Elegida (decisión U5, 2026-10-18; reutilizar el token de la app queda descartado porque la rotación de uno obligaría a la del otro): no exige permisos nuevos al deployer, y permite revocar el de CI sin tocar el de la app. GitHub enmascara el valor en los logs; el workflow lo pasa por `env` y lo usa en una cabecera de `curl`, nunca en la línea de comandos de un `echo`.
- Leer el token de Secret Manager desde el workflow: daría al deployer acceso al valor y rompe el principio de que solo la cuenta de ejecución lo lee.
- Verificar solo `/health`: se pierde la comprobación de la base y de que el servicio exige token.

Se añade además una consulta sin token que debe responder 401: prueba que la autorización está activa en lo desplegado, y falla el job si respondiera 200 (servicio abierto por error). El secreto de GitHub puede quedar obsoleto tras una rotación: el job falla con 401 y el escenario correspondiente lo cubre; el procedimiento de rotación (D7) lo actualiza antes de desplegar.

### D6. App: `--dart-define=API_TOKEN`, envío en cada petición y 401 como error de autorización (U6)

- `catalog_api_config.dart` añade `apiTokenFromEnvironment = String.fromEnvironment('API_TOKEN')` (por defecto vacío), igual que `API_BASE_URL`. Sin define la app arranca y no envía `Authorization`; el 401 resultante se muestra como error. Ni el repositorio ni los valores por defecto contienen un token; un define no queda en el código fuente pero sí dentro del APK (limitación declarada).
- `HttpCatalogRepository` recibe el token por constructor (el cliente HTTP ya se inyecta) y añade `Authorization: Bearer <token>` a las cabeceras de `_get`. Las pruebas unitarias existentes con el cliente falso comprueban la cabecera exacta en listado y detalle, la ausencia de cabecera sin token y que un 401 produce el error nuevo.
- Un 401 (y un 403, por si un intermediario lo devolviera) produce `CatalogClientErrorKind.unauthorized` con un mensaje fijo en español que no contiene el token. El 404 del detalle sigue siendo «no encontrada»; un 401 en el detalle no debe confundirse con él. El botón de reintento de la interfaz se conserva como en todos los errores (`catalog_client_exception.dart:10`): reintentar un 401 con el mismo token es inútil pero inofensivo, y quitar el botón obligaría a tocar Explorar y el pasaporte. Decisión U6 tomada el 2026-10-18: el 401 conserva el reintento genérico, sin cambios de interfaz; la spec solo exige que no haya reintentos automáticos.
- Para no escribir el token en cada comando, Flutter admite `--dart-define-from-file=<json>`: la documentación sugiere un archivo local ignorado por git (`app/dart_defines.local.json`, que se añadiría a `.gitignore`) con `API_BASE_URL` y `API_TOKEN`. Es opcional.
- Revisión de lo que llama a la API: `app/integration_test/app_test.dart` y `catalog_smoke.dart` (el smoke contra el backend real, con su guarda de host) leen `API_BASE_URL`; deben pasar también `API_TOKEN`, y los comandos del README (líneas 78-123) se actualizan. Las pruebas de widget y `catalog_smoke_contract_test.dart` usan un cliente falso: se les da un token ficticio. No hay otros scripts en el repositorio que llamen a la API salvo los de QA archivados, que no se tocan.

### D7. Rotación sin cortar el servicio

El secreto guarda la lista (`<token-app>,<token-ci>`) en una versión. Rotar el token de la app:

1. Generar el token nuevo (`openssl rand -hex 32`).
2. Crear una versión nueva del secreto con `<nuevo>,<viejo>,<ci>`, fijar esa versión en el workflow y desplegar: la API acepta ambos.
3. Compilar y distribuir la app con el token nuevo.
4. Cuando no queden instalaciones con el token viejo, crear otra versión sin él, fijarla, desplegar y desactivar las versiones anteriores.

Rotar el de CI es igual y exige además actualizar `API_VERIFY_TOKEN` entre los pasos 2 y 3. Si el valor se filtra, se hace el paso 4 de inmediato; las apps ya instaladas con el token viejo dejan de funcionar, que es el comportamiento esperado de la revocación y se acepta. Alternativas descartadas: volúmenes de secretos, que reflejan una versión nueva sin reiniciar pero obligan a leer un archivo en cada petición o a vigilarlo, más piezas de las que el cambio pide.

### D8. La política de acceso queda fuera del contrato de compatibilidad de `/v1` (U4)

El requisito «Compatibilidad dentro de `/v1`» solo admite cambios aditivos porque la app es ya consumidor (`README.md:138`). Exigir un token rompe a cualquier cliente sin token, pero no cambia rutas, parámetros ni campos. Se trata como política de acceso y no como cambio de contrato, y el delta de `catalog-api` lo dice de forma explícita en ese requisito en lugar de saltarlo en silencio. Decisión U4 tomada el 2026-10-18: la autorización es política de acceso y no cambia el contrato de `/v1`, y se acepta que los APK sin token dejen de funcionar; fallan con 401 y se resuelven recompilando con `API_TOKEN`. No hay periodo de transición.

### D9. Registro, contrato OpenAPI y ordenación de entrega

- Logs: ningún camino registra la cabecera `Authorization` ni los tokens configurados; las rutas con 401 se registran a nivel `debug` con la clase del fallo. Una prueba fija `RUST_LOG=trace`, envía tokens válido e inválido y comprueba que el log capturado no contiene ninguno de los dos valores.
- OpenAPI: se declara un `securitySchemes.bearerAuth` (`http`, `bearer`), `security` en las operaciones de `/v1` y una respuesta 401 con `ProblemDto`; `/health` y `/openapi.json` se marcan sin seguridad. `backend/openapi.json` se regenera con el comando que el propio test indica (`openapi.rs:63`).
- Orden de entrega: si se hace `push` a `main` con el código nuevo antes de crear el secreto, el despliegue falla (Cloud Run comprueba el acceso al secreto y, aun sin `--set-secrets`, el contenedor terminaría con código 2 sin `API_TOKENS`) y la revisión anterior sigue sirviendo; es seguro pero ruidoso. Las tareas por eso integran los grupos locales y dejan el `push` para después de crear el secreto y el secreto de GitHub.

## Risks / Trade-offs

- [El token se extrae del APK] → Se declara en README, spec y documentación; el valor del cambio es frenar clientes casuales; rotar y revocar es barato (D7). Si el abuso real aparece, la siguiente capa es App Check o un límite de tasa, fuera de alcance.
- [Las peticiones 401 se facturan y consumen la cuota gratuita de Cloud Run] → `max-instances=2` acota el gasto y la alerta de presupuesto existente avisa; un ataque de volumen requiere protección de borde, descartada ahora.
- [Cambio roto para clientes sin token] → La app se actualiza en el mismo cambio y no hay instalaciones externas (D8); las apps antiguas fallan con un mensaje claro.
- [Despliegue falla si falta el secreto o su permiso] → Las tareas crean el secreto y el rol antes del `push`; el despliegue conserva la revisión anterior.
- [Secreto de GitHub de verificación obsoleto tras rotar] → El procedimiento de rotación lo actualiza antes del despliegue; si falla, el job lo indica por el 401.
- [Longitud filtrada por temporización en la comparación] → Aceptado: el formato y la cota inferior no son secretos.
- [Un token con salto de línea desde Secret Manager o el shell] → La validación recorta el espacio exterior y el test lo cubre.
- [El token aparece en el historial del shell o en un artefacto de QA] → Las guías usan variables de entorno y `read -s`; la QA usa valores de marcador y un paso final busca patrones de token (32 o más caracteres hexadecimales) antes de confirmar la evidencia.
- [Secret Manager deja de ser gratuito] → Dentro de 6 versiones activas y 10 000 accesos al mes no se cobra; la documentación pide desactivar las versiones viejas tras rotar para mantenerse por debajo del límite. Los precios se verifican de nuevo al ejecutar la tarea de creación del secreto, porque pueden cambiar.

## Migration Plan

1. Implementar y probar en local (grupos 1 a 6), sin `push`.
2. [usuario u orquestador con aprobación] Crear el secreto, su versión inicial con los dos tokens y el rol sobre el secreto; crear `API_VERIFY_TOKEN` en GitHub (grupo 8).
3. `push` a `main` por el orquestador con aprobación: corre `verify`, `deploy` con `--set-secrets` y la verificación con y sin token.
4. Compilar la app con `API_TOKEN` y ejecutar la QA (grupo 9).
5. Rollback: volver a la revisión anterior de Cloud Run (`docs/deploy/cloud-run.md`, «Revisiones y rollback») restaura la API sin autorización de esa revisión; para volver al estado previo completo basta revertir los commits y desmontar el secreto con el procedimiento documentado.

## Decisiones tomadas

Decisiones del usuario, tomadas el 2026-10-18:

- U1. Secret Manager con versión fijada (no `latest`). El secreto de GitHub con `--set-env-vars` queda descartado: la documentación de Cloud Run no lo recomienda para secretos (D4). Los pasos manuales quedan documentados en `docs/deploy/cloud-run.md`.
- U2. Token obligatorio siempre, también en local, con un `.env` local (D3).
- U3. `/openapi.json` público (D2).
- U4. La autorización es política de acceso y no cambia el contrato de `/v1`; se acepta que los APK sin token dejen de funcionar (D8).
- U5. Token dedicado a la verificación de CI dentro de `API_TOKENS` (D5).
- U6. Ante un 401 la app conserva el reintento genérico, sin cambios de interfaz (D6).
- U7. Se acepta la dependencia `subtle` para la comparación en tiempo constante (D3).

## Open Questions

- Ninguna que cambie las specs o la lista de tareas. El valor exacto de los precios de Secret Manager se revalida en la tarea 8.1 antes de crear el secreto.
