# Design

## Context

Véanse `proposal.md` y la spec delta de `backend-deployment` para los requisitos observables. Estado de partida:

- El `Dockerfile` de la raíz tiene tres etapas: compila Rust (`rust:1.99.0-slim-bookworm`), descarga el ZIP de USDA (unos 100 MB) y construye `catalog.db`, y un runtime `debian:bookworm-slim` con solo `/app/catalog-api` y `/app/catalog.db` (6 MB), usuario `app` sin privilegios, `HOST=0.0.0.0`, `PORT=8080`, `RUST_LOG=info`, `EXPOSE 8080`, sin `HEALTHCHECK` y con `ENTRYPOINT` en forma exec (SIGTERM llega al binario, que apaga de forma ordenada). La imagen final pesa unos 154 MB.
- Usa `RUN --mount=type=cache` de BuildKit para el registro de cargo, `target/` y el ZIP. Esas cachés viven en el almacenamiento del daemon y no persisten entre ejecuciones de Actions.
- La API no tiene estado: SQLite de solo lectura embebida, sin volúmenes ni servicios externos. Expone `GET /healthz`, `GET /openapi.json`, `GET /v1/plants` y `GET /v1/plants/{id}`.
- La única CI es `.github/workflows/flutter.yml` (formato, análisis y tests de la app), con acciones fijadas por SHA con comentario de versión, `permissions: contents: read` y `concurrency`. No hay CI del backend.
- El repositorio de GitHub es privado. La app (cambio `connect-app-to-backend`, ya implementado) lee `API_BASE_URL` por `--dart-define`, tiene `INTERNET` en el manifest principal y HTTP en claro solo en `debug` y `profile`, así que el build `release` necesita HTTPS.
- Proyecto académico, un solo desarrollador, presupuesto mínimo, tráfico de unas pocas peticiones al día y ráfagas pequeñas en demos.

## Goals / Non-Goals

**Goals:**

- Una URL HTTPS pública y estable del backend, desplegada desde `main` sin intervención y sin claves de larga duración.
- Costo esperado de 0 USD/mes y cota superior acotada, con una forma documentada de desmontarlo todo.
- Que un despliegue fallido sea visible (el job falla) y reversible sin reconstruir.

**Non-Goals:**

- `cargo test` como puerta previa del despliegue: sería un cambio «CI del backend» propio; hoy el despliegue se apoya en la verificación posterior por `curl` y en que la construcción de la imagen ya falla si el insumo no coincide con su MD5.
- Dominio propio (el mapeo de dominios sigue en preview y no está disponible en `southamerica-east1`), autenticación de la API, caché o CDN, entornos múltiples, otras nubes y cambios en el código de la app.
- Infraestructura como código (Terraform): la preparación única son comandos `gcloud` documentados.

## Decisions

### 1. Cloud Run con facturación por petición, escala a cero y 2 instancias como máximo

Servicio `boticario-api` en `southamerica-east1` (São Paulo), CPU asignada solo durante las peticiones, `min-instances=0`, `max-instances=2`, `--allow-unauthenticated` e ingress público. Con `min-instances=0` y facturación por petición no se factura mientras no hay instancias ni peticiones; el precio es el arranque en frío de la primera petición tras un periodo inactivo, cuya duración la documentación no da y se mide en QA. Fuentes: https://docs.cloud.google.com/run/docs/configuring/min-instances y https://cloud.google.com/run/pricing.

Región: `southamerica-east1` es Tier 2 (como Santiago), así que el equivalente gratuito en vCPU-s es menor que en Tier 1 (aprox. 128.000 en lugar de 180.000, porque la capa se aplica como descuento en dólares a precios Tier 1) y cuesta más fuera de ella (0,0000336 frente a 0,000024 USD por vCPU-s). Se elige por latencia con la app de usuarios en Latinoamérica; con unas pocas peticiones al día la diferencia es despreciable. Fuentes: https://docs.cloud.google.com/run/docs/locations y https://docs.cloud.google.com/free/docs/free-cloud-features.

Alternativas descartadas: una región Tier 1 como `northamerica-south1` (México) o `us-central1`, que dan la capa completa y salida gratuita pero más latencia; facturación por instancia o `min-instances=1`, que facturan en reposo; `max-instances` sin límite, que deja el gasto sin cota.

### 2. 1 vCPU, 256 MiB y primera generación del entorno de ejecución

La documentación oficial (https://docs.cloud.google.com/run/docs/configuring/services/cpu y https://docs.cloud.google.com/run/docs/configuring/services/memory-limits) fija: CPU mínima de 0,08 vCPU y, por encima de 1, solo enteros; con 0,08 vCPU hasta 512 MiB, con 0,5 hasta 1 GiB y con 1 vCPU hasta 4 GiB; memoria por defecto de 512 MiB; memoria mínima de 128 MiB en la primera generación del entorno de ejecución y de 512 MiB en la segunda, con la recomendación de usar la primera por debajo de 512 MiB. Una CPU fraccionaria (menos de 1 vCPU) exige concurrencia máxima 1, facturación por petición y primera generación.

Se elige 1 vCPU y 256 MiB con `--execution-environment=gen1`. La API es un binario Rust con una SQLite de 6 MB, así que 256 MiB sobra con margen (el consumo real se mide en QA con los logs de memoria de Cloud Run). No se baja de 1 vCPU porque una CPU fraccionaria obliga a concurrencia 1 (una ráfaga de una demo abriría una instancia por petición y chocaría con `max-instances=2`) y ralentiza el arranque en frío, mientras que con facturación por petición el costo es vCPU-s por duración de cada petición: una petición de milisegundos cuesta casi lo mismo con 0,08 que con 1 vCPU. El costo de la memoria (0,0000035 USD/GiB-s en Tier 2) es despreciable a 256 MiB.

Por confirmar en la implementación: que `gcloud run deploy` acepte `--cpu=1 --memory=256Mi --execution-environment=gen1` con esta imagen y que el arranque no supere el consumo de 256 MiB. Si fallara, el valor de respaldo es 512 MiB (el mínimo de la segunda generación y el valor por defecto), sin cambios en las specs salvo el escenario «Recursos del contenedor».

Alternativas descartadas: 0,08 vCPU con 128 MiB (concurrencia 1, ver arriba); 512 MiB con la segunda generación (el doble de memoria sin necesidad y arranque algo más lento).

### 3. Sonda de arranque HTTP a `/healthz`

Sin sonda configurada, Cloud Run añade una sonda TCP de arranque. Se configura una sonda HTTP a `/healthz` en el puerto 8080 (`--startup-probe httpGet.path=/healthz,httpGet.port=8080,…`) para que una revisión solo reciba tráfico cuando la API ya responde. Cualquier 2xx o 3xx cuenta como éxito, y `failureThreshold × periodSeconds` no puede pasar de 600 s. Valores propuestos: `periodSeconds=2`, `timeoutSeconds=1`, `failureThreshold=10`. Fuente: https://docs.cloud.google.com/run/docs/configuring/healthchecks. El contrato de contenedor exige escuchar en `0.0.0.0:$PORT` en 4 minutos y entrega SIGTERM y SIGKILL a los 10 s, lo que la imagen ya cumple: https://docs.cloud.google.com/run/docs/container-contract.

No se añaden sondas de liveness: con instancias de vida corta y sin estado, un reinicio por sonda no aporta. No se toca el `Dockerfile`: no necesita `HEALTHCHECK` y `PORT` ya se honra.

### 4. Imagen construida en GitHub Actions y publicada en Artifact Registry

El job construye con `docker/setup-buildx-action` y `docker/build-push-action` en un runner `ubuntu` (amd64 nativo, sin emulación) con `platforms: linux/amd64`, etiquetas `…/boticario-api:<sha>` y `…:latest`, y la publica en un repositorio Docker de Artifact Registry de `southamerica-east1`. Cloud Run solo despliega directamente imágenes de registries externos si son públicas; con un repositorio de GitHub privado, GHCR obligaría a un repositorio remoto o a hacer pública la imagen. Artifact Registry es además el registry recomendado: https://docs.cloud.google.com/run/docs/deploying. El login al registry usa el token de acceso de la identidad federada (`oauth2accesstoken`, vía `gcloud auth configure-docker` o `docker/login-action`). Cloud Build no se usa para no tener otra API ni otro costo.

El despliegue referencia la imagen por la etiqueta del SHA (cada revisión apunta a un contenido concreto y el rollback es determinista); `latest` es una comodidad para pruebas manuales.

Alternativas descartadas: GHCR (ver arriba); Cloud Build o `gcloud run deploy --source` (construye en la nube con otro servicio facturable y sin la caché de capas de Actions); construir en el Mac (en un Mac con Apple Silicon la construcción amd64 corre bajo emulación con Rosetta, más lenta y menos fiable que la nativa, y no es reproducible).

### 5. Caché de capas `type=gha` y riesgo aceptado de las monturas de caché

`cache-from: type=gha` y `cache-to: type=gha,mode=max` reutilizan las capas entre ejecuciones. Las monturas `RUN --mount=type=cache` del `Dockerfile` (registro de cargo, `target/` y ZIP de USDA) no forman parte de las capas, así que no persisten entre ejecuciones de Actions: cuando cambia `backend/` se recompila el workspace entero y, si la capa del catálogo se invalida, se vuelve a bajar el ZIP. Es un riesgo aceptado: con cambios poco frecuentes la construcción tardará varios minutos, dentro de los minutos gratuitos de Actions de un repositorio privado (por confirmar en la implementación según el plan de la cuenta). Cuando solo cambia el workflow o `.dockerignore`, las capas en caché se reutilizan.

Mejora futura si el tiempo molesta: `reproducible-containers/buildkit-cache-dance` para guardar y restaurar las monturas de caché con el caché de Actions. No se adopta ahora porque añade una acción de terceros y complejidad sin necesidad probada.

### 6. Limpieza de Artifact Registry

Política de limpieza del repositorio con una regla `Keep` por `mostRecentVersions` con `keepCount` de 5, aplicada con `gcloud artifacts repositories set-cleanup-policies … --policy=… --no-dry-run`. Cinco versiones de una imagen de 154 MB descomprimida (menos comprimida en el registro, y con capas compartidas entre versiones) caben en los 0,5 GB gratuitos y dejan rollback a las revisiones recientes. Los cambios de la política pueden tardar hasta un día en aplicarse; antes se puede probar con `--dry-run`. Una política `Keep` tiene prioridad sobre una `Delete`. Fuente: https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy.

Por confirmar en la implementación: el tamaño real de la imagen en el registro (si cinco versiones superan 0,5 GB, bajar a 3) y que `latest` quede entre las versiones conservadas.

### 7. Workload Identity Federation y dos cuentas de servicio

Se crea un pool y un proveedor OIDC de `https://token.actions.githubusercontent.com` con una condición de atributo que solo admite `assertion.repository == 'sebastianrodriguez1115/boticario-ai'` (la documentación de `google-github-actions/auth` advierte que siempre debe restringirse la entrada al pool). Se concede `roles/iam.workloadIdentityUser` sobre la cuenta de despliegue a ese `principalSet` por repositorio. Cuentas de servicio:

- `boticario-deployer`: `roles/run.admin` en el proyecto, `roles/artifactregistry.writer` solo en el repositorio de imágenes y `roles/iam.serviceAccountUser` solo sobre `boticario-runtime`.
- `boticario-runtime`: cuenta de ejecución del servicio, sin roles; la API no llama a ningún servicio de Google. Evita que el servicio corra con la cuenta por defecto de Compute Engine, que suele tener el rol Editor.

La documentación de `deploy-cloudrun` pide `roles/run.admin` y «Service Account User» sobre la cuenta de ejecución (la de Compute por defecto, o aquella que se fije con `--service-account`); aquí se limita a la cuenta dedicada. Fuentes: https://github.com/google-github-actions/auth y https://github.com/google-github-actions/deploy-cloudrun. Secretos y variables de GitHub: el nombre del recurso del proveedor de WIF y el correo de la cuenta de despliegue van como secretos para que GitHub los enmascare en los logs y no queden a la vista en el YAML ni en las ejecuciones; proyecto, región y repositorio de imágenes son configuración no sensible y van como variables.

Alternativas descartadas: claves JSON de cuenta de servicio en secretos (credencial de larga duración, rotación manual); WIF directo sin cuenta de servicio (la documentación lo prefiere, pero no todos los recursos aceptan `principalSet` y el token dura como máximo 10 minutos, lo que complica el push del registry y el despliegue; con cuenta de servicio el comportamiento es el estándar de `deploy-cloudrun`); una sola cuenta para despliegue y ejecución (daría al servicio los permisos de despliegue).

### 8. Acciones oficiales de Google fijadas por SHA

`google-github-actions/auth`, `setup-gcloud` y `deploy-cloudrun` están hoy en la versión mayor v3 (verificado en sus repositorios el 2026-10-15), `docker/build-push-action` en v7. Por confirmar en la implementación: la última versión mayor y su SHA de cada acción al escribir el workflow. Todas se fijan por SHA completo con comentario de versión, como en `flutter.yml`. `permissions` del workflow: `contents: read` e `id-token: write` (necesario para el token OIDC). `auth` se ejecuta después de `checkout`.

`deploy-cloudrun` recibe `service`, `region`, `image` y `flags` (`--execution-environment=gen1`, `--cpu=1`, `--memory=256Mi`, `--min-instances=0`, `--max-instances=2`, `--allow-unauthenticated`, `--service-account`, `--port=8080`, `--startup-probe=…`); su salida `url` alimenta la verificación. La facturación por petición es el valor por defecto de Cloud Run y se fija de forma explícita con `--cpu-throttling` para que el servicio no dependa de un valor por defecto futuro. El uso de `setup-gcloud` es para `gcloud` en pasos de verificación y diagnóstico; si la implementación no lo necesitara, se omite sin cambiar las specs.

### 9. Disparadores, concurrencia y verificación posterior

`on: push` a `main` con `paths` (`backend/**`, `data/migrations/**`, `data/sources.toml`, `Dockerfile`, `.dockerignore`, `.github/workflows/deploy-backend.yml`) y `workflow_dispatch`. `concurrency` con un grupo fijo y `cancel-in-progress: false`: los despliegues se serializan y uno en curso no se interrumpe a medias (a diferencia de `flutter.yml`, que sí cancela tests obsoletos). Se omiten `pull_request` y otras ramas: el despliegue es solo desde `main`.

Tras desplegar, un paso con `curl --fail --retry` consulta `${url}/healthz` y `${url}/v1/plants/lavandula-angustifolia` (reintentos breves para absorber el arranque en frío) y falla el job si no hay 200. No revierte automáticamente: Cloud Run ya mantiene la revisión anterior y el rollback manual está en el runbook. Una revisión que no pasa la sonda de arranque no recibe tráfico, así que ese fallo no deja el servicio caído.

### 10. Alerta de presupuesto, no tope de gasto

Presupuesto de 1 USD en la cuenta de facturación, con los umbrales por defecto (50 %, 90 % y 100 %) por correo. Una alerta no corta el gasto (la documentación lo aclara; los topes son una función aparte para servicios elegibles), así que el control efectivo es `max-instances=2`, el desmontaje documentado y el hecho de que la facturación por petición no cobra en reposo. Crear el presupuesto requiere el rol de Billing Account Costs Manager o Administrator. La página de presupuestos no documenta `gcloud billing budgets create`, así que el comando se toma de la referencia de la CLI y queda por confirmar en la implementación (alternativa: la consola). Fuente: https://docs.cloud.google.com/billing/docs/how-to/budgets.

### 11. Documentación en `docs/deploy/cloud-run.md` y README

Un documento nuevo reúne la preparación única (comandos `gcloud` que ejecuta el usuario porque requieren su cuenta y facturación), los secretos y variables de GitHub, el runbook (despliegue manual con `workflow_dispatch` y con `gcloud run deploy`, logs con `gcloud run services logs read`, rollback con `gcloud run services update-traffic boticario-api --to-revisions=<revisión>=100`, medición del arranque en frío) y el desmontaje (eliminar servicio, repositorio, cuentas de servicio, proveedor y pool, y presupuesto; o borrar el proyecto). El `README.md` enlaza al documento, actualiza «Despliegue en amd64» (la construcción amd64 y el despliegue los hace el workflow; `docker build --platform linux/amd64 .` sigue sirviendo para pruebas locales) y la nota final de «Integración continua» sobre el backend sin CI. `openspec/specs/backend-container/spec.md` no se modifica: su requisito de imagen y de construcción reproducible sigue siendo cierto y el despliegue lo consume.

### 12. La app usa la URL desplegada solo por `--dart-define`

La dirección por defecto sigue siendo `http://10.0.2.2:8080`. Para el build `release` y el smoke contra el backend desplegado se pasa `--dart-define=API_BASE_URL=https://<url-de-cloud-run>`, documentado en README. El guard del smoke (solo el host y el puerto de la URL base) sigue siendo válido porque Cloud Run sirve en el 443. No se toca código de la app.

Alternativa descartada: fijar la URL de Cloud Run como valor por defecto en modo `release` (por ejemplo con `kReleaseMode`), que mete una URL de entorno en el código y obligaría a recompilar o cambiar el código si el servicio se recrea con otra URL.

### 13. Specs

Se añade `backend-deployment` (capacidad nueva) y se modifica `flutter-app-bootstrap` solo en el requisito «Flujo de desarrollo reproducible y documentado», a partir del texto que deja `connect-app-to-backend` (este cambio se implementa después de archivarlo). No hay delta de `backend-container` ni de `catalog-client`.

## Risks / Trade-offs

- [Arranque en frío tras inactividad: la primera petición espera a que arranque el contenedor y la documentación no da una cifra] → medirlo en QA tras al menos 15 minutos sin tráfico (varias muestras); la app ya tiene tiempo máximo de 10 s con error reintentable. Si molesta, `min-instances=1` costaría dinero; se deja fuera.
- [La alerta de 1 USD no corta el gasto] → `max-instances=2`, facturación por petición y desmontaje documentado; el peor caso teórico (dos instancias activas todo el mes) no es alcanzable con este tráfico, pero la API es pública y sin autenticación, y un cliente abusivo puede consumir la capa; se acepta en un proyecto académico.
- [Región Tier 2: capa gratuita menor y salida de red fuera de la capa] → tráfico mínimo y respuestas pequeñas; se lee el consumo en QA frente a la capa.
- [Sin recompilación incremental: cada cambio del backend recompila todo en Actions] → riesgo aceptado, ver la decisión 5.
- [La política de limpieza puede borrar la imagen de una revisión antigua y volver imposible su rollback] → conservar 5 versiones y hacer rollback solo a revisiones recientes.
- [Sin `cargo test` previo, un backend roto puede desplegarse] → la verificación posterior falla el job y la revisión sin sonda válida no recibe tráfico; la CI del backend es un cambio posterior.
- [Dependencia de la capa gratuita y de una tarjeta en la cuenta de facturación] → documentado; el desmontaje devuelve el costo a cero.
- [Preparación manual con la cuenta de Google del usuario] → comandos reproducibles en el documento y verificación de cada paso en las tareas; ninguna tarea de GCP la ejecuta un agente.
- [Versiones y comandos de Google que cambian] → los puntos marcados «por confirmar» se resuelven al implementar y se registran en el documento.

## Migration Plan

Orden de las tareas: (1) guía de preparación en `docs/deploy/cloud-run.md`; (2) preparación en GCP por el usuario con esa guía; (3) workflow de imagen y despliegue, con la primera ejecución manual; (4) resto de la documentación y README; (5) QA. Este cambio se implementa después de archivar `connect-app-to-backend`.

Primer despliegue: tras la preparación y los secretos, lanzar el workflow con `workflow_dispatch`; el servicio se crea en esa ejecución. Verificar la URL y registrarla en README como ejemplo de `--dart-define`, o dejar el marcador `<url-de-cloud-run>`.

Rollback de una revisión: `gcloud run services update-traffic boticario-api --to-revisions=<revisión-anterior>=100 --region=southamerica-east1`; no reconstruye ni toca la imagen. Para revertir el cambio en el repositorio, borrar el workflow y los documentos con un commit de reversión; el servicio sigue corriendo hasta desmontarlo.

Desmontaje para volver a costo cero: eliminar el servicio (`gcloud run services delete`), el repositorio de Artifact Registry, las dos cuentas de servicio, el proveedor y el pool de WIF y el presupuesto, y quitar los secretos y variables de GitHub; o eliminar el proyecto entero, que lo borra todo tras el periodo de recuperación de 30 días. La app sigue funcionando contra el backend local con `docker compose up`.

## Open Questions

- Ninguna que cambie las specs ni la secuencia de tareas; los datos marcados «por confirmar» (combinación de recursos, tamaño de la imagen, comando del presupuesto, SHA de las acciones y minutos de Actions) se resuelven al implementar y se anotan en el documento.
