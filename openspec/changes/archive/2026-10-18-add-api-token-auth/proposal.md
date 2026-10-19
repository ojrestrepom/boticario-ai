# Proposal

## Why

La API del catálogo está publicada en Cloud Run con `--allow-unauthenticated` y no comprueba nada: cualquiera que conozca la URL `*.run.app` puede consultarla y generar consumo facturable, aunque los datos sean públicos (catálogo USDA, CC0). El usuario pidió una capa de autorización en el backend con un token de API «o algo similar», sin involucrar mucha infraestructura. Este cambio añade esa capa mínima: la app envía un token en cada petición y la API rechaza con 401 las que no lo traen.

El alcance es deliberadamente modesto y esta propuesta lo declara sin adornos: el token va embebido en el APK y se puede extraer, así que autoriza a «la app» frente a clientes casuales y escáneres, no a usuarios; las peticiones rechazadas con 401 llegan al contenedor y Cloud Run las factura igual (solo las denegadas por IAM no se facturan); y no sustituye a una protección de borde. Firebase App Check, Cloud Armor, API Gateway y el límite de tasa quedan fuera de alcance por decisión del usuario.

## What Changes

- **BREAKING (política de acceso, no de datos)**: todas las rutas bajo `/v1` exigen `Authorization: Bearer <token>`. Sin token o con un token inválido responden 401 con `application/problem+json`, `WWW-Authenticate: Bearer` y un mensaje genérico que nunca incluye ni registra el token. `/health` y `/openapi.json` siguen públicos.
- La API lee los tokens válidos de la variable de entorno `API_TOKENS` (lista separada por comas, para rotar sin cortar el servicio), los compara en tiempo constante y no arranca si la variable falta, está vacía o contiene un token de menos de 32 caracteres. No hay modo «sin autenticación»: así no se despliega abierta por accidente.
- El documento OpenAPI declara el esquema de seguridad Bearer y la respuesta 401 en las rutas de `/v1`; `backend/openapi.json` se regenera.
- Cloud Run recibe el token desde Secret Manager con `--set-secrets` (versión fijada, no `latest`), con `roles/secretmanager.secretAccessor` para `boticario-runtime` solo sobre ese secreto. Crear el secreto y el rol son pasos manuales del usuario documentados en `docs/deploy/cloud-run.md`. El usuario descartó la alternativa del secreto de GitHub con `--set-env-vars` (decisión del 2026-10-18): la documentación de Cloud Run no recomienda las variables de entorno para secretos y recomienda Secret Manager. El diseño conserva la comparación como motivo.
- La verificación posterior del workflow de despliegue comprueba que `/v1/plants/lavandula-angustifolia` sin token responde 401 y, con un token propio de verificación guardado como secreto de GitHub, responde 200.
- `compose.yaml` y la ejecución local con `cargo run` requieren `API_TOKENS`; las pruebas del backend inyectan un token de prueba.
- La app lee el token de la definición de compilación `API_TOKEN` (`--dart-define`, nunca en el repositorio) y `HttpCatalogRepository` lo envía en cada petición. Una respuesta 401 se muestra como un error del catálogo legible, sin exponer el token. El smoke de integración y los comandos documentados pasan el define.
- Se modifican el contrato `catalog-client` y las promesas de `flutter-app-bootstrap` («sin autenticación») y de `catalog-api` («API sin autenticación»), y se ajustan los requisitos de `backend-container` y `backend-deployment` que asumían acceso sin credenciales.
- Documentación: `README.md`, `backend/README.md` y `docs/deploy/cloud-run.md` (inventario, roles, rotación del token y desmontaje del secreto).
- Este cambio debe archivarse después de `add-backend-ci-and-plain-logs`: ambos modifican el requisito «Despliegue automático con verificación posterior» y el texto modificado aquí se construye sobre el de ese cambio.

## Capabilities

### New Capabilities

Ninguna: la autorización se modela como cambios de comportamiento de las capabilities existentes de la API, la app y el despliegue.

### Modified Capabilities

- `catalog-api`: el requisito «API de solo lectura sin autenticación» se renombra y pasa a exigir el token en `/v1`; se añaden los requisitos de autorización por token y de configuración de tokens; se modifican «Endpoint de salud», «Errores estandarizados» (401), «Documento OpenAPI» (esquema Bearer), «Arranque y configuración» (`API_TOKENS`) y «Compatibilidad dentro de `/v1`» (la política de acceso no es el contrato de datos).
- `catalog-client`: «Consumo de la API v1 del catálogo» envía el token en cada petición; «Errores de red y del servidor» trata el 401; nuevo requisito «Token de API configurable» para `API_TOKEN`.
- `flutter-app-bootstrap`: «Funcionamiento local sin autenticación ni servicios remotos» distingue entre autenticación de usuario (ninguna) y el token de la app.
- `backend-container`: «Imagen autocontenida», «Arranque con un solo comando» y «Configuración por entorno» incorporan `API_TOKENS`.
- `backend-deployment`: «Despliegue automático con verificación posterior» (comprobación del 401 y del 200 con token), «Configuración del servicio en Cloud Run» (token desde Secret Manager) e «Identidad de despliegue sin claves de larga duración» (acceso de la cuenta de ejecución solo a su secreto).

## Impact

- Backend (`backend/catalog-api`): `src/config.rs` (lectura y validación de `API_TOKENS` con un tipo que no se imprime), un módulo nuevo de autorización y su middleware en `src/http.rs`, `src/error.rs` (variante 401), `src/startup.rs`, `src/openapi.rs` y `backend/openapi.json`, y las pruebas existentes que construyen el router (`tests/fixture_end_to_end.rs`, `tests/shutdown.rs`, `tests/real_catalog.rs`). Dependencia nueva: el crate `subtle` para la comparación en tiempo constante.
- App (`app/lib/features/catalog/data/`): `catalog_api_config.dart`, `catalog_repository.dart`, `catalog_providers.dart`, la excepción de cliente y las pruebas de `app/test/features/catalog/data/`; el smoke `app/integration_test/catalog_smoke.dart` y `app_test.dart`.
- Infraestructura: `.github/workflows/deploy-backend.yml` (`--set-secrets`, verificación con y sin token), `compose.yaml`, y en Google Cloud la API `secretmanager.googleapis.com`, un secreto, y un enlace de IAM sobre ese secreto (acciones del usuario o del orquestador con aprobación). En GitHub, un secreto nuevo para la verificación.
- Costo: Secret Manager queda dentro de su capa gratuita (6 versiones activas y 10 000 operaciones de acceso al mes); las peticiones rechazadas con 401 consumen cuota de Cloud Run como cualquier otra. Sin cambios en el número de instancias.
- Documentación: `README.md`, `backend/README.md`, `docs/deploy/cloud-run.md`.
- Fuera de alcance: Firebase App Check, Cloud Armor, API Gateway, límite de tasa, autenticación de usuarios, tokens por usuario o con expiración, IAP, y cualquier cambio en el contenido de las respuestas.
