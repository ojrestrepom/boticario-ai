# Proposal

## Why

El backend (`catalog-api` con el catálogo USDA embebido) solo corre en el Mac con `docker compose up`, así que la app únicamente funciona contra un backend local y el build `release` no puede usarse: exige HTTPS y todavía no hay una URL pública. Desplegarlo en Google Cloud Run con despliegue continuo desde GitHub Actions da una URL HTTPS estable, un camino reproducible de la imagen al servicio y un costo esperado de 0 USD/mes para un proyecto académico con tráfico de unas pocas peticiones al día.

## What Changes

- Nueva capacidad `backend-deployment`: un workflow `.github/workflows/deploy-backend.yml` construye la imagen del `Dockerfile` para linux/amd64, la única arquitectura que acepta Cloud Run, en un runner `ubuntu` de GitHub Actions, que es amd64 nativo, con `docker/build-push-action`, la etiqueta con el SHA del commit y `latest`, la publica en un repositorio Docker de Artifact Registry en `southamerica-east1` y despliega el servicio `boticario-api` en Cloud Run.
- Disparadores: `push` a `main` con filtros de ruta del backend (`backend/**`, `data/migrations/**`, `data/sources.toml`, `Dockerfile`, `.dockerignore` y el propio workflow) y `workflow_dispatch`. Un grupo de `concurrency` serializa los despliegues. Tras desplegar, el job verifica con `curl` que `/healthz` y `/v1/plants/lavandula-angustifolia` responden 200 sobre la URL del servicio y falla si no.
- Configuración del servicio: facturación por petición (CPU asignada solo durante las peticiones), `min-instances=0`, `max-instances=2`, acceso público sin autenticación, puerto 8080, sonda de arranque HTTP a `/healthz`, 1 vCPU y 256 MiB de memoria (justificado en el diseño) y HTTPS en la URL `*.run.app`.
- Identidad sin claves: Workload Identity Federation entre GitHub y GCP, con una cuenta de servicio de despliegue de permisos mínimos y una cuenta de servicio de ejecución dedicada sin roles. No se guardan claves JSON en GitHub. Las acciones `google-github-actions/auth`, `setup-gcloud` y `deploy-cloudrun` (hoy en la versión mayor v3) se fijan por SHA, como en `flutter.yml`.
- Control de costo: política de limpieza de Artifact Registry que conserva solo las últimas versiones (dentro de los 0,5 GB gratuitos), `max-instances=2` y una alerta de presupuesto de 1 USD.
- Nuevo documento `docs/deploy/cloud-run.md`: preparación única en GCP con comandos `gcloud`, secretos y variables de GitHub, runbook (despliegue manual, logs, rollback a la revisión anterior, medición del arranque en frío) y desmontaje completo para volver a costo cero.
- `README.md`: enlace al documento, actualización de «Despliegue en amd64» y de las secciones «2. Abrir y ejecutar en Android Studio» y «4. Smoke Android» con el build `release` y el smoke contra el backend desplegado por `--dart-define=API_BASE_URL=https://<url-de-cloud-run>`.
- Sin cambios en la app: la dirección por defecto sigue siendo la del emulador (`http://10.0.2.2:8080`). Se descarta fijar la URL de Cloud Run como valor por defecto en modo `release` para no meter una URL de entorno en el código.
- Sin cambios en el `Dockerfile`: la imagen ya honra `PORT`, sirve sin red, se apaga con SIGTERM y es amd64-compatible; ver el diseño.

### Costo esperado

- 0 USD/mes dentro de la capa gratuita de Cloud Run con facturación por petición, por cuenta de facturación y mes: 2 M de peticiones, 180.000 vCPU-s y 360.000 GiB-s. La capa exige una cuenta de facturación con tarjeta y se aplica como descuento en dólares a precios Tier 1, así que en una región Tier 2 como São Paulo el equivalente gratuito es menor (aprox. 128.000 vCPU-s).
- Artifact Registry: 0,5 GB de almacenamiento gratis al mes; cada imagen pesa unos 154 MB (menos comprimida en el registro), por eso la política de limpieza conserva pocas versiones. No se usa Cloud Build.
- Salida de red: la capa gratuita cubre 1 GB solo desde Norteamérica; las respuestas son pequeñas y el tráfico mínimo, pero es el único concepto que no queda cubierto por la capa en São Paulo.
- Cota superior acotada por `max-instances=2` y por la alerta de presupuesto de 1 USD. La alerta avisa por correo y no corta el gasto: el límite real es `max-instances` y la posibilidad de desmontar el servicio.

### Qué debe hacer el usuario a mano en GCP

La preparación requiere la cuenta de Google del usuario y una cuenta de facturación, así que la ejecuta él con los comandos de `docs/deploy/cloud-run.md`: crear el proyecto y vincular la facturación, habilitar las APIs, crear el repositorio de Artifact Registry y su política de limpieza, crear las dos cuentas de servicio con sus roles, crear el pool y el proveedor de Workload Identity Federation, crear la alerta de presupuesto y registrar en GitHub los secretos y variables (id de proyecto, proveedor de WIF, cuenta de servicio y región).

## Capabilities

### New Capabilities

- `backend-deployment`: publicación de la imagen del backend por CI, despliegue continuo en Cloud Run con verificación posterior, configuración del servicio, identidad sin claves, observabilidad y control de costo, y documentación de preparación, operación, rollback y desmontaje.

### Modified Capabilities

- `flutter-app-bootstrap`: la documentación de desarrollo cubre además el build `release` y el smoke contra el backend desplegado con `--dart-define=API_BASE_URL=https://…`.

## Impact

- Se crearán `.github/workflows/deploy-backend.yml` y `docs/deploy/cloud-run.md`, y se tocará `README.md`.
- Sin cambios en `Dockerfile`, `.dockerignore`, `compose.yaml`, `backend/`, `data/` ni `app/`; `backend-container` y `catalog-client` no llevan delta.
- Recursos externos nuevos en GCP: proyecto, repositorio de Artifact Registry, servicio de Cloud Run, dos cuentas de servicio, pool y proveedor de WIF y una alerta de presupuesto; y secretos y variables en el repositorio de GitHub (privado).
- Dependencia: este cambio se implementa después de archivar `connect-app-to-backend`, porque la spec delta de `flutter-app-bootstrap` parte del texto que ese cambio deja en `openspec/specs/`.
- Fuera de alcance: dominio propio, CI de tests del backend (`cargo test` como puerta previa al despliegue), autenticación de la API, caché o CDN, entornos múltiples, otras nubes y cualquier cambio en el código de la app.
