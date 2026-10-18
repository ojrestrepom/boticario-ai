# Despliegue del backend en Cloud Run

Esta guía despliega la API del catálogo (`backend/`, ver [`README.md`](../../README.md)) en Google Cloud Run: una URL HTTPS pública y estable, construida y publicada desde GitHub Actions sin claves de larga duración, que escala a cero y debería costar 0 USD al mes con el tráfico de un proyecto académico.

Este documento reúne la preparación única en Google Cloud, que haces tú a mano porque requiere tu cuenta y tu facturación; después el workflow del repositorio se encarga de construir y desplegar en cada cambio del backend en `main`.

## Arquitectura e inventario

Esta sección resume la infraestructura de corrido: cómo llega un cambio a producción, qué recursos existen, qué permisos tiene cada identidad y qué límites acotan el costo y el riesgo.

### Flujo de despliegue

```text
push a main (o ejecución manual)
   |
   v
GitHub Actions (deploy-backend.yml)
   |
   v
job verify (backend-ci.yml): cargo fmt --check, clippy -D warnings y cargo test
   |  si alguna falla, el flujo se detiene aquí: no se publica ninguna imagen ni se crea ninguna revisión
   v
job deploy (needs: verify)
   |  pide un token OIDC (id-token: write, solo en este job)
   v
Workload Identity Federation (pool "github", proveedor "boticario-ai")
   |  acepta solo el repositorio sebastianrodriguez1115/boticario-ai
   v
cuenta de servicio boticario-deployer (token de acceso de corta duración)
   |  inicia sesión en Artifact Registry con ese token (oauth2accesstoken)
   v
construcción linux/amd64 en el runner, con caché de capas en GitHub Actions
   |  publica la imagen con las etiquetas <sha> y latest
   v
Artifact Registry (repositorio "boticario")
   |  despliega la imagen del <sha> como una revisión nueva
   v
Cloud Run (servicio "boticario-api", corre como boticario-runtime)
   |  inyecta API_TOKENS desde Secret Manager (secreto boticario-api-tokens, versión fijada)
   |  el workflow comprueba con curl /health, el detalle con token (200) y sin token (401)
   v
la app, por HTTPS en la URL *.run.app, con Authorization: Bearer <token>
```

### Recursos

| Recurso | Qué es y para qué sirve | Quién lo creó | Cómo inspeccionarlo |
| --- | --- | --- | --- |
| Proyecto de GCP | Contenedor de todo lo demás; borrarlo lo desmonta todo | Tú, paso 1 | `gcloud projects describe "$PROJECT_ID"` |
| Región `northamerica-south1` | Dónde viven el repositorio y el servicio (Tier 1) | Decisión de diseño | `gcloud config list` y `gcloud run services list` |
| Repositorio de imágenes `boticario` | Artifact Registry Docker donde el workflow publica la imagen | Tú, paso 2 | `gcloud artifacts repositories describe "$REPO" --location="$REGION"` |
| Política de limpieza | Borra versiones de más de un día salvo las 5 más recientes | Tú, paso 2 | `gcloud artifacts repositories list-cleanup-policies "$REPO" --location="$REGION"` |
| Servicio `boticario-api` | Cloud Run: 1 vCPU, 256 MiB, 0 a 2 instancias, puerto 8080, público, corre como `boticario-runtime` y su sonda de arranque apunta a `/health`, ruta que también responde desde fuera (`/healthz` no se usa porque Cloud Run reserva algunas rutas terminadas en «z», como `/healthz`, y devuelve su propio 404; `/healthz/`, `/readyz` y `/livez` sí llegan a la API) | El workflow, primer despliegue | `gcloud run services describe "$SERVICE" --region="$REGION"` |
| Pool `github` y proveedor `boticario-ai` | Workload Identity Federation: aceptan tokens OIDC de GitHub solo del repositorio | Tú, paso 4 | `gcloud iam workload-identity-pools providers describe "$PROVIDER" --location=global --workload-identity-pool="$POOL"` |
| Cuenta `boticario-deployer` | Identidad que el workflow asume para publicar y desplegar | Tú, pasos 3 y 4 | `gcloud iam service-accounts describe "$DEPLOYER_EMAIL"` |
| Cuenta `boticario-runtime` | Identidad con la que corre el contenedor, sin roles en el proyecto y con acceso de lectura solo al secreto `boticario-api-tokens` | Tú, paso 3 | `gcloud iam service-accounts describe "$RUNTIME_EMAIL"` |
| Presupuesto | Alerta por correo del equivalente a 1 USD, no corta el gasto | Tú, paso 5 | `gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID"` |
| Secreto `boticario-api-tokens` | Secret Manager (API `secretmanager.googleapis.com`): la lista de tokens de API separados por comas (`<token-app>,<token-ci>`); Cloud Run la inyecta como `API_TOKENS` con la versión fijada en el workflow | Tú, paso 7 | `gcloud secrets describe "$SECRET_NAME"` y `gcloud secrets versions list "$SECRET_NAME"` (nunca muestran el valor) |
| Secretos de GitHub | `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_DEPLOYER_SERVICE_ACCOUNT` y `API_VERIFY_TOKEN` (el token de CI, que forma parte de `API_TOKENS`) | Tú, pasos 6 y 7 | `gh secret list --repo "$GITHUB_REPO"` |
| Variables de GitHub | `GCP_PROJECT_ID`, `GCP_REGION` y `GCP_ARTIFACT_REPOSITORY` | Tú, paso 6 | `gh variable list --repo "$GITHUB_REPO"` |
| Workflow `deploy-backend.yml` | En `push` a `main` con cambios en la imagen o en `workflow_dispatch`: primero el job `verify` ejecuta las verificaciones del backend (`backend-ci.yml`) y, solo si pasan, el job `deploy` construye la imagen amd64, la publica con las etiquetas `<sha>` y `latest`, despliega el `<sha>` con `API_TOKENS` desde Secret Manager y verifica con `curl` (200 con token, 401 sin token) | El repositorio, en `.github/workflows/` | `gh workflow view deploy-backend.yml` |

### Roles y permisos

| Principal | Rol | Ámbito | Por qué | Sin él |
| --- | --- | --- | --- | --- |
| `boticario-deployer` | `roles/run.admin` | Proyecto | Crear y actualizar el servicio de Cloud Run | El despliegue falla con permiso denegado |
| `boticario-deployer` | `roles/artifactregistry.writer` | Repositorio `boticario` | Subir la imagen | El push de la imagen es rechazado |
| `boticario-deployer` | `roles/iam.serviceAccountUser` | Cuenta `boticario-runtime` | Desplegar un servicio que corre como esa cuenta | El despliegue falla al asignar la cuenta de ejecución |
| `principalSet` del repositorio | `roles/iam.workloadIdentityUser` | Cuenta `boticario-deployer` | Que el workflow de ese repositorio actúe como el deployer | La autenticación del workflow falla |
| `boticario-runtime` | Ninguno | Proyecto | La API no llama a otros servicios de Google | No aplica: sin roles en el proyecto, un contenedor comprometido no alcanza nada de él |
| `boticario-runtime` | `roles/secretmanager.secretAccessor` | Secreto `boticario-api-tokens` | Leer `API_TOKENS` al arrancar cada instancia | El despliegue falla: Cloud Run comprueba el acceso a los secretos |
| Tu usuario | Billing Account Costs Manager o Administrator | Cuenta de facturación | Crear el presupuesto del paso 5 | No puedes crear la alerta |

El deployer no necesita acceso al valor del secreto: para referenciarlo en `--set-secrets` basta con `roles/run.admin` y `roles/iam.serviceAccountUser` sobre la cuenta de ejecución, según [Configurar secretos en Cloud Run](https://docs.cloud.google.com/run/docs/configuring/services/secrets). Por eso el deployer no cambia y el token de CI vive en un secreto de GitHub, no se lee de Secret Manager.

### Controles de costo y seguridad

- Costo: `max-instances=2` acota el gasto del servicio y `min-instances=0` con facturación por petición no cobra en reposo.
- Costo: la política de limpieza mantiene el repositorio dentro de los 0,5 GB gratuitos.
- Costo: la alerta de presupuesto avisa por correo al 50 %, 90 % y 100 %, pero no corta el gasto; el desmontaje es el control final.
- Seguridad: no hay claves JSON de larga duración; GitHub se autentica con tokens OIDC de corta duración.
- Seguridad: la condición de atributo del proveedor solo admite tu repositorio y el `principalSet` se limita a él.
- Seguridad: cada rol del deployer está en el ámbito más estrecho posible y la cuenta de ejecución no tiene roles en el proyecto: su único permiso es `secretAccessor` sobre `boticario-api-tokens`.
- Seguridad: la API exige `Authorization: Bearer <token>` en `/v1`. El servicio sigue desplegándose con `--allow-unauthenticated` (sin autenticación de Cloud Run, para que la app alcance la URL), pero `/v1` responde 401 sin un token de `API_TOKENS`; `/health` y `/openapi.json` quedan abiertos.
- Seguridad: `API_TOKENS` llega desde Secret Manager con la versión fijada (`--set-secrets=API_TOKENS=boticario-api-tokens:1`), nunca `latest`, así que rotar es cambiar ese número en un commit; el valor no queda en la configuración de las revisiones, solo la referencia.
- Seguridad: el workflow pasa `API_VERIFY_TOKEN` por `env` y la cabecera a `curl` por stdin (`-H @-`), sin `set -x` ni `echo` del valor; GitHub además enmascara el secreto en el log.
- Seguridad: el workflow se dispara con `push` a `main` (solo si cambian `backend/`, `data/migrations/`, `data/sources.toml`, `Dockerfile`, `mise.toml`, `.dockerignore` o el propio workflow) o a mano con `workflow_dispatch`; los permisos del workflow son solo `contents: read`, y el permiso `id-token: write` lo tiene únicamente el job `deploy`, no `verify`.
- Seguridad: los despliegues se serializan con `concurrency` y no se cancelan a medias.
- Seguridad: las acciones de terceros están fijadas por SHA con un comentario de versión.
- Fiabilidad: el despliegue usa la etiqueta del SHA, no `latest`, y un paso con `curl` falla el job si `/health` o el detalle de una planta con el token de CI no responden 200, o si el mismo detalle sin token no responde 401 (un 200 significaría que el servicio quedó abierto); sin `API_VERIFY_TOKEN` el paso falla antes de consultar; no hay rollback automático, Cloud Run conserva la revisión anterior.
- Fiabilidad: el job `deploy` depende de `verify` (`needs: verify`), así que un formato, un lint o una prueba que falle impide construir y publicar la imagen y crear la revisión; el servicio sigue sirviendo la anterior.
- Fiabilidad: una revisión que no pasa la sonda de arranque no recibe tráfico.

## Costo esperado

Con el tráfico de un proyecto académico, el servicio debería costar 0 USD al mes: Cloud Run factura por petición, escala a cero y tiene una capa gratuita mensual muy por encima de ese uso.

La capa gratuita de Cloud Run con facturación por petición incluye cada mes, por cuenta de facturación, 2 millones de peticiones, 180.000 vCPU-segundos, 360.000 GiB-segundos y 1 GB de salida de red desde Norteamérica.

`northamerica-south1` (Querétaro) es una región Tier 1 y está en Norteamérica, así que la capa aplica completa y sin recortes por región.

La capa se aplica como un descuento en dólares sobre el uso de cada mes, no como un contador aparte, y exige una cuenta de facturación activa aunque no llegue a cobrarse nada.

Secret Manager tiene capa gratuita: 6 versiones activas del secreto y 10.000 accesos al mes (https://cloud.google.com/secret-manager/pricing; es un valor de la página de precios, revalídalo al crear el secreto en el paso 7). Con una variable de entorno desde un secreto hay un acceso por arranque de instancia, y con un secreto y pocas versiones el uso queda muy por debajo; pasado ese límite serían 0,06 USD por versión activa al mes y 0,03 USD por 10.000 accesos.

Los 401 de la API se facturan como cualquier otra petición a Cloud Run (cuentan para los 2 millones mensuales gratuitos): el token no frena el tráfico hacia el servicio, solo las respuestas.

Artifact Registry incluye 0,5 GB de almacenamiento gratis al mes; la política de limpieza del paso 2 mantiene pocas versiones de la imagen para quedar dentro de ese límite.

Lo que se paga fuera de la capa, con las tarifas Tier 1 (consúltalas en la página de precios, porque pueden cambiar):

| Concepto | Tarifa Tier 1 |
| --- | --- |
| CPU | 0,000024 USD por vCPU-segundo |
| Memoria | 0,0000025 USD por GiB-segundo |
| Peticiones | 0,40 USD por millón |

Controles que acotan el gasto:

- `max-instances=2` limita cuánto puede escalar el servicio ante un pico de tráfico.
- `min-instances=0` y la facturación por petición (`--cpu-throttling`) hacen que en reposo no haya instancias ni cobro.
- La alerta de presupuesto del equivalente a 1 USD en la moneda de la cuenta (5000 COP en esta cuenta) avisa por correo, pero no corta el gasto ni apaga el servicio; el control final es el [desmontaje](#desmontaje).

Para leer el consumo real, abre la consola de Facturación, Informes, y filtra por proyecto (`boticario-ai`) y por servicio (Cloud Run); allí se ve el uso y el descuento de la capa gratuita.

`gcloud run services describe` no muestra consumo, solo la configuración del servicio.

Fuentes: [funciones gratuitas de Google Cloud](https://docs.cloud.google.com/free/docs/free-cloud-features), [precios de Cloud Run](https://cloud.google.com/run/pricing) y [ubicaciones de Cloud Run](https://docs.cloud.google.com/run/docs/locations) (nivel de precio de cada región).

## Preparación única en Google Cloud

### Prerrequisitos

- Una cuenta de Google.
- Una cuenta de facturación de Google Cloud con tarjeta, creada en la consola siguiendo [Create a new Cloud Billing account](https://docs.cloud.google.com/billing/docs/how-to/create-billing-account). Cloud Run tiene capa gratuita, pero Google exige una cuenta de facturación activa para habilitar las APIs.
- El CLI de gcloud. Con Homebrew: `brew install --cask gcloud-cli` (el nombre antiguo `google-cloud-sdk` sigue funcionando como alias). El cask enlaza `gcloud` en el `PATH` por sí mismo; solo necesitas añadir `/opt/homebrew/share/google-cloud-sdk/bin` al `PATH` si luego instalas componentes adicionales con `gcloud components install`. Alternativa: el [instalador oficial para macOS](https://docs.cloud.google.com/sdk/docs/install-sdk), que en su `install.sh` ofrece añadir `gcloud` al `PATH` (abre una terminal nueva después).
- `gh` (GitHub CLI) ya instalado.

Inicia sesión en ambos CLI:

```bash
gcloud auth login
gh auth login
```

`gh auth login` pide por defecto el alcance `repo`, que `gh secret set` y `gh variable set` necesitan sobre un repositorio privado.

El proyecto de gcloud se fija en el paso 1, cuando ya exista.

Comprobación: `gcloud auth list` debe mostrar tu cuenta de Google como activa (marcada con `*`) y `gh auth status` debe decir «Logged in to github.com» e incluir `repo` entre los alcances del token.

```bash
gcloud auth list
gh auth status
```

### Variables

Las variables que usan todos los comandos viven en `.env.cloud-run.example`, en la raíz del repo, y no contienen secretos. Cópialo a `.env.cloud-run`, que es el archivo que editas y que git ignora, y cambia en él los dos valores marcados como «Edita estos dos valores»: `PROJECT_ID` (único en todo Google Cloud, con un sufijo propio) y `BILLING_ACCOUNT_ID`.

```bash
cp .env.cloud-run.example .env.cloud-run
```

Obtén tu `BILLING_ACCOUNT_ID` con el siguiente comando y copia la columna `ACCOUNT_ID` de la cuenta con `OPEN` en `True`:

```bash
gcloud billing accounts list
```

Carga las variables con `source` desde la raíz del repo, en cada terminal nueva (las variables no sobreviven al cerrarla):

```bash
source .env.cloud-run
```

`PROJECT_NUMBER`, que es distinto del id y que usan los pasos 4 a 6, queda vacío hasta que el proyecto exista: tras el paso 1 vuelve a ejecutar `source .env.cloud-run` (o la línea de `PROJECT_NUMBER` del archivo) para que deje de estarlo.

### Paso 1. Proyecto y facturación

Crea el proyecto, apúntalo como proyecto por defecto de gcloud, vincúlale la facturación y habilita las APIs que usan los pasos siguientes.

```bash
gcloud projects create "$PROJECT_ID" --name="boticario-ai"
gcloud config set project "$PROJECT_ID"
gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudresourcemanager.googleapis.com \
  billingbudgets.googleapis.com
```

`billingbudgets.googleapis.com` es la API que usa `gcloud billing budgets create` en el paso 5; el resto las necesitan Cloud Run, Artifact Registry y la federación de identidades.

Comprobación: `gcloud billing projects describe` debe mostrar `billingEnabled: true` y `gcloud services list --enabled` debe listar las siete APIs.

```bash
gcloud billing projects describe "$PROJECT_ID"
gcloud services list --enabled
```

Errores típicos:

- `The project ID you specified is already in use by another project`: el id es global, elige otro `PROJECT_ID`, edita `PROJECT_ID` en `.env.cloud-run`, vuelve a ejecutar `source .env.cloud-run` y repite.
- Un comando posterior falla con `API [...] not enabled` justo después de habilitarla: la propagación tarda hasta un minuto, espera y repite.
- `gcloud billing projects link` falla con permiso denegado: la cuenta con la que iniciaste sesión no administra esa cuenta de facturación.

### Paso 2. Artifact Registry

Crea el repositorio de imágenes Docker en la región del servicio y limita su tamaño con una política de limpieza que borra las versiones de más de un día salvo las 5 más recientes, para quedar dentro de los 0,5 GB gratuitos.

```bash
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Imágenes del backend de boticario-ai"

cat > /tmp/cleanup-policy.json <<'JSON'
[
  {
    "name": "delete-old",
    "action": {"type": "Delete"},
    "condition": {"tagState": "any", "olderThan": "1d"}
  },
  {
    "name": "keep-last-5",
    "action": {"type": "Keep"},
    "mostRecentVersions": {"keepCount": 5}
  }
]
JSON
```

Prueba primero la política sin borrar nada y después aplícala de verdad:

```bash
gcloud artifacts repositories set-cleanup-policies "$REPO" \
  --location="$REGION" \
  --policy=/tmp/cleanup-policy.json \
  --dry-run

gcloud artifacts repositories set-cleanup-policies "$REPO" \
  --location="$REGION" \
  --policy=/tmp/cleanup-policy.json \
  --no-dry-run
```

La regla `delete-old` borra cualquier versión de más de un día y la regla `keep-last-5` protege de ese borrado las 5 versiones más recientes de cada paquete (sin `packageNamePrefixes` aplica a todo el repositorio), por lo que la imagen en producción, que es una de las 5 últimas, nunca se borra; una regla `Keep` sola no borraría nada, porque Artifact Registry solo elimina lo que cumple una regla `Delete`.

Comprobación: `gcloud artifacts repositories describe` debe mostrar en `cleanupPolicies` las dos reglas, `delete-old` (Delete, más de un día) y `keep-last-5` (Keep, `keepCount: 5`), y `cleanupPolicyDryRun: false`.

```bash
gcloud artifacts repositories describe "$REPO" --location="$REGION"
```

Nota: la política no borra nada al instante, los cambios tardan hasta un día en aplicarse.

Si al describir sale `cleanupPolicyDryRun: true`, repite el segundo comando con `--no-dry-run`.

### Paso 3. Cuentas de servicio y roles

Dos cuentas con responsabilidades separadas: `boticario-deployer` es la identidad que GitHub Actions asume para publicar la imagen y desplegar, y `boticario-runtime` es la identidad con la que corre el contenedor.

```bash
gcloud iam service-accounts create "$DEPLOYER_SA" --display-name="Despliegue desde GitHub Actions"
gcloud iam service-accounts create "$RUNTIME_SA" --display-name="Ejecución de boticario-api"
```

Concede al deployer solo lo necesario, cada rol en el ámbito más estrecho posible:

```bash
# Crear y actualizar servicios de Cloud Run (a nivel de proyecto).
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEPLOYER_EMAIL" \
  --role="roles/run.admin"

# Publicar imágenes, solo en este repositorio.
gcloud artifacts repositories add-iam-policy-binding "$REPO" \
  --location="$REGION" \
  --member="serviceAccount:$DEPLOYER_EMAIL" \
  --role="roles/artifactregistry.writer"

# Poder desplegar un servicio que corre como la cuenta de ejecución, solo sobre esa cuenta.
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_EMAIL" \
  --member="serviceAccount:$DEPLOYER_EMAIL" \
  --role="roles/iam.serviceAccountUser"
```

La cuenta de ejecución no recibe ningún rol a propósito: la API no llama a ningún otro servicio de Google Cloud (SQLite va embebida en la imagen), así que si el contenedor se viera comprometido no tendría acceso a nada del proyecto.

Cloud Run extrae la imagen con su propio agente de servicio, que no necesita roles aquí.

Comprobación: el primer comando debe mostrar para el deployer solo `roles/run.admin` a nivel de proyecto; el segundo, que sobre la cuenta de ejecución el único binding es `roles/iam.serviceAccountUser` para el deployer.

```bash
gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$DEPLOYER_EMAIL" \
  --format="table(bindings.role)"

gcloud iam service-accounts get-iam-policy "$RUNTIME_EMAIL"
```

Si un comando falla con `Service account ... does not exist` justo después de crearla, espera unos segundos y repite: la creación de cuentas es eventualmente consistente.

### Paso 4. Workload Identity Federation

Esto permite que GitHub Actions se autentique como el deployer con un token OIDC de corta duración, sin guardar ninguna clave JSON en GitHub.

```bash
gcloud iam workload-identity-pools create "$POOL" \
  --location="global" \
  --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
  --location="global" \
  --workload-identity-pool="$POOL" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository == '$GITHUB_REPO'"
```

La condición de atributo es la defensa principal: sin ella, cualquier repositorio de GitHub podría presentar un token válido ante este proveedor; con ella, solo el tuyo.

Ahora permite que las identidades de ese repositorio actúen como el deployer:

```bash
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_EMAIL" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository/$GITHUB_REPO" \
  --role="roles/iam.workloadIdentityUser"
```

Comprobación: `describe` del proveedor debe mostrar `attributeCondition` con tu repositorio y `state: ACTIVE`; el segundo comando imprime el nombre completo del proveedor, que es el valor del secreto `GCP_WORKLOAD_IDENTITY_PROVIDER` del paso 6 y debe verse como `projects/<número>/locations/global/workloadIdentityPools/github/providers/boticario-ai`.

```bash
gcloud iam workload-identity-pools providers describe "$PROVIDER" \
  --location="global" \
  --workload-identity-pool="$POOL"

gcloud iam workload-identity-pools providers describe "$PROVIDER" \
  --location="global" \
  --workload-identity-pool="$POOL" \
  --format="value(name)"
```

Ese nombre también es `projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER`.

Si `PROJECT_NUMBER` está vacío, el `principalSet` queda malformado: vuelve a ejecutar `source .env.cloud-run` (sección «Variables»).

### Paso 5. Alerta de presupuesto

Un presupuesto del equivalente a 1 USD en la moneda de tu cuenta de facturación, con avisos al 50 %, 90 % y 100 % del gasto, acotado a este proyecto.

Es solo una alerta: no corta el gasto ni apaga el servicio.

El control efectivo del costo es el máximo de 2 instancias del servicio y el desmontaje documentado.

El importe de `--budget-amount` debe ir en la moneda de la cuenta de facturación; con otra moneda el comando falla con `INVALID_ARGUMENT`. Mira cuál es la tuya:

```bash
gcloud billing accounts describe "$BILLING_ACCOUNT_ID" --format='value(currencyCode)'
```

El valor por defecto de `.env.cloud-run.example` es `BUDGET_AMOUNT="5000COP"`, el equivalente aproximado a 1 USD para una cuenta en pesos colombianos como la de este proyecto. Si la cuenta responde otra moneda, cambia `BUDGET_AMOUNT` en `.env.cloud-run` por el equivalente aproximado a 1 USD en esa moneda, por ejemplo `BUDGET_AMOUNT="1USD"`; el tipo de cambio es aproximado y la cifra la eliges tú. Después recarga las variables con `source .env.cloud-run` y crea el presupuesto:

```bash
gcloud billing budgets create \
  --billing-account="$BILLING_ACCOUNT_ID" \
  --display-name="boticario-ai presupuesto" \
  --budget-amount="$BUDGET_AMOUNT" \
  --filter-projects="projects/$PROJECT_NUMBER" \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0
```

Sin flags de notificación, los avisos llegan por correo a los administradores y usuarios de la cuenta de facturación, es decir, a ti.

Crear presupuestos requiere el rol Billing Account Costs Manager o Administrator sobre la cuenta de facturación.

Errores típicos:

- `INVALID_ARGUMENT`: casi siempre la moneda de `BUDGET_AMOUNT` no coincide con la de la cuenta; revisa `currencyCode` arriba y corrige el sufijo (`USD`, `COP`, etc.).
- Queja de un proyecto de cuota o de que la API no está habilitada: comprueba que `billingbudgets.googleapis.com` figura en el paso 1 y añade `--billing-project="$PROJECT_ID"`.

Comprobación: `gcloud billing budgets list` debe mostrar el presupuesto `boticario-ai presupuesto` con su importe en la moneda de la cuenta y sus tres reglas de umbral.

```bash
gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID"
```

Si prefieres la consola: Facturación, Presupuestos y alertas, Crear presupuesto; nombre `boticario-ai presupuesto`; en Alcance filtra por el proyecto; en Importe elige «Importe específico» con el equivalente a 1 USD en la moneda de la cuenta; deja los umbrales 50 %, 90 % y 100 % y mantén activo el aviso por correo a los administradores de la cuenta.

### Paso 6. Secretos y variables de GitHub

Desde la raíz del repositorio, con `gh` autenticado (paso de prerrequisitos), registra los datos que usará el workflow.

Ninguno es una clave: los dos secretos solo identifican el proveedor y la cuenta de servicio, y sin el token OIDC del repositorio no sirven para nada.

| Nombre | Tipo | Valor | De dónde sale |
| --- | --- | --- | --- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | secreto | `projects/<número>/locations/global/workloadIdentityPools/github/providers/boticario-ai` | Paso 4 |
| `GCP_DEPLOYER_SERVICE_ACCOUNT` | secreto | `boticario-deployer@<proyecto>.iam.gserviceaccount.com` | `$DEPLOYER_EMAIL` |
| `GCP_PROJECT_ID` | variable | el id del proyecto | `$PROJECT_ID` |
| `GCP_REGION` | variable | `northamerica-south1` | `$REGION` |
| `GCP_ARTIFACT_REPOSITORY` | variable | `northamerica-south1-docker.pkg.dev/<proyecto>/boticario` | `$REGION`, `$PROJECT_ID` y `$REPO` |

```bash
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$GITHUB_REPO" \
  --body "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER"
gh secret set GCP_DEPLOYER_SERVICE_ACCOUNT --repo "$GITHUB_REPO" --body "$DEPLOYER_EMAIL"

gh variable set GCP_PROJECT_ID --repo "$GITHUB_REPO" --body "$PROJECT_ID"
gh variable set GCP_REGION --repo "$GITHUB_REPO" --body "$REGION"
gh variable set GCP_ARTIFACT_REPOSITORY --repo "$GITHUB_REPO" \
  --body "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO"
```

Comprobación: ambos listados muestran los nombres y las fechas de actualización, nunca los valores; deben aparecer los dos secretos y las tres variables.

```bash
gh secret list --repo "$GITHUB_REPO"
gh variable list --repo "$GITHUB_REPO"
```

Si `gh` responde `HTTP 403` o `Resource not accessible`, el token no tiene el alcance `repo`: ejecuta `gh auth refresh -s repo` y repite.

### Paso 7. Token de API (Secret Manager)

La API exige un token en `/v1`. Los tokens viven en un único secreto de Secret Manager, `boticario-api-tokens`, como una lista separada por comas: `<token-app>,<token-ci>`. Cloud Run lo inyecta como la variable `API_TOKENS` con la versión fijada en el workflow (`--set-secrets=API_TOKENS=boticario-api-tokens:1`). La app usa el primero y la verificación del workflow el segundo, con `API_VERIFY_TOKEN`. Esta preparación debe estar hecha antes del primer despliegue con autenticación: sin el secreto, el despliegue falla (Cloud Run comprueba el acceso) y la revisión anterior sigue sirviendo.

`SECRET_NAME` viene de `.env.cloud-run.example` (`boticario-api-tokens`) y debe coincidir con el nombre que usa el workflow. Con las variables cargadas (`source .env.cloud-run`), habilita la API:

```bash
gcloud services enable secretmanager.googleapis.com
```

Genera los dos tokens en variables de shell, sin mostrarlos (32 bytes aleatorios en hexadecimal son 64 caracteres, dentro del rango que acepta la API):

```bash
TOKEN_APP="$(openssl rand -hex 32)"
TOKEN_CI="$(openssl rand -hex 32)"
```

Crea el secreto con la versión 1 leyendo el valor de la entrada estándar, para que no quede en el historial del shell ni en la lista de procesos (`printf` es un comando interno del shell). La replicación es automática porque Cloud Run no admite secretos regionales:

```bash
printf '%s,%s' "$TOKEN_APP" "$TOKEN_CI" | gcloud secrets create "$SECRET_NAME" \
  --replication-policy=automatic \
  --data-file=-
```

Da a la cuenta de ejecución acceso de lectura solo a este secreto:

```bash
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
  --member="serviceAccount:$RUNTIME_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

Guarda el token de CI como secreto de GitHub, también por la entrada estándar (`gh secret set` la lee cuando no se pasa `--body`), y borra las dos variables del shell; a partir de aquí el valor solo existe en Secret Manager y en GitHub:

```bash
printf '%s' "$TOKEN_CI" | gh secret set API_VERIFY_TOKEN --repo "$GITHUB_REPO"
unset TOKEN_APP TOKEN_CI
```

Cuando haga falta compilar la app, lee el token de la app del secreto (es el primer elemento de la lista) y escríbelo en `app/dart_defines.local.json`, el archivo que git ignora y que usa el [`README.md`](../../README.md), sin mostrarlo; desde la raíz:

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
TOKEN_APP="$(gcloud secrets versions access 1 --secret="$SECRET_NAME" | cut -d, -f1)"
printf '{\n  "API_BASE_URL": "%s",\n  "API_TOKEN": "%s"\n}\n' "$SERVICE_URL" "$TOKEN_APP" > app/dart_defines.local.json
chmod 600 app/dart_defines.local.json
unset TOKEN_APP
```

Si todavía no existe el servicio (antes del primer despliegue), el primer comando no devuelve la URL: repite este bloque cuando el despliegue haya terminado. La app se compila con `flutter build apk --release --dart-define-from-file=dart_defines.local.json` desde `app/`.

Comprobación: los tres comandos muestran nombres, versiones y miembros, nunca el valor. El primero debe listar la versión 1 en estado `enabled`; el segundo, `roles/secretmanager.secretAccessor` solo para `boticario-runtime`; el tercero, `API_VERIFY_TOKEN` junto a los otros dos secretos.

```bash
gcloud secrets versions list "$SECRET_NAME"
gcloud secrets get-iam-policy "$SECRET_NAME"
gh secret list --repo "$GITHUB_REPO"
```

Un token del tamaño y juego de caracteres incorrectos hace que la API no arranque (código de salida 2) y el despliegue falle en la sonda de arranque; el error del log nombra `API_TOKENS` y el motivo, nunca el valor.

### Rotación del token

La rotación no corta el servicio porque el secreto guarda una lista: durante la transición la API acepta el token nuevo y el viejo. El workflow fija la versión del secreto, así que cada versión nueva exige cambiar ese número en un commit, que además despliega. Con las variables cargadas:

1. Genera el token nuevo y crea la versión 2 con `<nuevo>,<token-app>,<token-ci>`, construida a partir de la versión actual sin mostrarla:

   ```bash
   TOKEN_NEW="$(openssl rand -hex 32)"
   CURRENT="$(gcloud secrets versions access latest --secret="$SECRET_NAME")"
   printf '%s,%s' "$TOKEN_NEW" "$CURRENT" | gcloud secrets versions add "$SECRET_NAME" --data-file=-
   unset CURRENT
   gcloud secrets versions list "$SECRET_NAME"
   ```

   Comprobación: aparecen las versiones 1 y 2, ambas `enabled`.

2. Cambia `API_TOKENS=boticario-api-tokens:1` por `:2` en `.github/workflows/deploy-backend.yml`, haz commit y push a `main`, y espera el despliegue (`gh run watch <id>`). Comprobación: el job termina en verde y `gcloud run services describe "$SERVICE" --region="$REGION" --format='yaml(spec.template.spec.containers[0].env)'` muestra `secretKeyRef` con `key: '2'` y ningún valor.

3. Compila y distribuye la app con el token nuevo (`TOKEN_NEW` es ahora el primer elemento de la versión 2):

   ```bash
   TOKEN_APP="$(gcloud secrets versions access 2 --secret="$SECRET_NAME" | cut -d, -f1)"
   ```

   Escríbelo en `app/dart_defines.local.json` como en el paso 7 y compila. Comprobación: la app abre el catálogo con el token nuevo.

4. Cuando no queden instalaciones con el token viejo, crea la versión 3 sin él (`<token-nuevo>,<token-ci>`), fija `:3` en el workflow, haz commit y push, espera el despliegue y desactiva las versiones anteriores:

   ```bash
   V2="$(gcloud secrets versions access 2 --secret="$SECRET_NAME")"
   printf '%s,%s' "$(printf '%s' "$V2" | cut -d, -f1)" "$(printf '%s' "$V2" | cut -d, -f3)" | gcloud secrets versions add "$SECRET_NAME" --data-file=-
   unset V2
   # Tras desplegar con :3:
   gcloud secrets versions disable 1 --secret="$SECRET_NAME"
   gcloud secrets versions disable 2 --secret="$SECRET_NAME"
   gcloud secrets versions list "$SECRET_NAME"
   ```

   Comprobación: la versión 3 está `enabled`, las 1 y 2 `disabled`, y el despliegue con `:3` termina en verde. Una revisión anterior de Cloud Run que referencia una versión desactivada no puede arrancar instancias nuevas, así que no hagas rollback a ella.

Para rotar el token de CI, haz lo mismo con `<token-app>,<token-ci-nuevo>,<token-ci-viejo>` en el paso 1 (versión 2) y, antes del paso 4, actualiza el secreto de GitHub con el token de CI nuevo; en el paso 4 conserva los dos primeros elementos (`cut -d, -f1,2`):

```bash
printf '%s' "$TOKEN_CI_NEW" | gh secret set API_VERIFY_TOKEN --repo "$GITHUB_REPO"
gh secret list --repo "$GITHUB_REPO"
```

Si un token se filtra, haz el paso 4 de inmediato: las apps ya instaladas con el token viejo dejan de funcionar (reciben 401), que es el comportamiento esperado de la revocación.

### Qué sigue

Con los pasos 1 a 7 hechos, el workflow de despliegue (`.github/workflows/deploy-backend.yml`) se crea en el repositorio y se lanza con `gh workflow run deploy-backend.yml`.

Desde entonces, cada cambio del backend que llegue a `main` se construye y se despliega solo.

## Operación

Los comandos de esta sección suponen que estás en la raíz del repositorio, con `gcloud` y `gh` autenticados y las variables cargadas:

```bash
source .env.cloud-run
```

La URL pública del servicio es `https://boticario-api-d3xv5q3iaa-pv.a.run.app`.

### Despliegue automático

El workflow `deploy-backend.yml` se dispara con un `push` a `main` que toque `backend/**`, `data/migrations/**`, `data/sources.toml`, `Dockerfile`, `mise.toml`, `.dockerignore` o el propio workflow; un cambio solo en `app/` o en `docs/` no despliega.

Primero corre el job `verify`, que reutiliza `backend-ci.yml` (`cargo fmt --check`, `cargo clippy` con `-D warnings` y `cargo test` sobre el workspace); solo si pasa, el job `deploy` construye la imagen `linux/amd64`, la publica en Artifact Registry con las etiquetas `<sha>` y `latest`, despliega la imagen del `<sha>` como una revisión nueva y verifica con `curl` que `/health` responda 200, que `/v1/plants/lavandula-angustifolia` responda 200 con el token de CI (`API_VERIFY_TOKEN`) y que la misma ruta responda 401 sin token; si responde 200 sin token, el job falla porque el servicio estaría abierto.

Si `verify` falla, `deploy` se omite y el servicio sigue con la revisión anterior. Corrige el fallo (el log sale con `gh run view <id> --log-failed`), súbelo a `main` o, si la corrección ya está en `main`, relanza el workflow con `workflow_dispatch` como se explica en «Despliegue manual». El rollback de Cloud Run (sección «Revisiones y rollback») no pasa por la CI: mueve el tráfico a una revisión existente sin ejecutar `verify`.

Tarda alrededor de 1 minuto cuando no cambia el código Rust (caché de capas) y unos 5 minutos cuando cambia `backend/`.

Para ver las ejecuciones, seguir una en vivo o leer por qué falló:

```bash
gh run list --workflow deploy-backend.yml --limit 5
gh run watch <id>
gh run view <id> --log-failed
```

### Despliegue manual

Lanza el workflow sin necesidad de un cambio en el backend (así se hizo el primer despliegue); también pasa por `verify` antes de construir. Síguelo con los comandos anteriores:

```bash
gh workflow run deploy-backend.yml --ref main
gh run list --workflow deploy-backend.yml --limit 1
```

### Despliegue de emergencia sin CI

Si GitHub Actions no está disponible y la imagen ya está publicada, despliégala a mano indicando su SHA (lista las etiquetas con `gcloud artifacts docker images list "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO"`):

```bash
gcloud run deploy "$SERVICE" \
  --region="$REGION" \
  --image="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/boticario-api:<sha>"
```

Por confirmar: la ayuda de `gcloud run deploy --help` no dice si los flags de configuración que no pasas se conservan de la revisión anterior; para no depender de eso, repite los flags del paso «Desplegar en Cloud Run» de `.github/workflows/deploy-backend.yml` (`--allow-unauthenticated`, `--execution-environment=gen1`, `--cpu=1`, `--memory=256Mi`, `--min-instances=0`, `--max-instances=2`, `--cpu-throttling`, `--port=8080`, `--service-account`, `--set-secrets=API_TOKENS=boticario-api-tokens:<n>` con la versión que fija el workflow y `--startup-probe`). Sin el flag de los secretos la nueva revisión no recibiría `API_TOKENS` y la API no arrancaría.

### Logs

Las últimas 50 entradas del servicio:

```bash
gcloud run services logs read "$SERVICE" --region="$REGION" --limit=50
```

Con `--log-filter="severity>=ERROR"` se limita a los errores y con `--freshness` se amplía la ventana (por defecto, 1 día).

La API escribe sus logs en texto plano, sin secuencias ANSI de color, porque en Cloud Run stdout no es una terminal. Los colores solo aparecen al ejecutarla en una terminal local, y `NO_COLOR` con un valor no vacío los quita también allí. El nivel por defecto es `info` y se cambia con `RUST_LOG` (ver [`backend/README.md`](../../backend/README.md)).

Para buscar con más detalle, usa el Logs Explorer de la consola de Google Cloud (Logging, Explorador de registros) con este filtro:

```text
resource.type="cloud_run_revision" resource.labels.service_name="boticario-api"
```

### Revisiones y rollback

Cada despliegue crea una revisión nueva y Cloud Run conserva las anteriores. El rollback mueve el tráfico entre revisiones que ya existen y no ejecuta la CI. Lista las revisiones y mira cuál recibe el tráfico:

```bash
gcloud run revisions list --service="$SERVICE" --region="$REGION"
gcloud run services describe "$SERVICE" --region="$REGION" --format='yaml(status.traffic)'
```

Para volver a una revisión anterior sin reconstruir ni tocar la imagen, envíale todo el tráfico:

```bash
gcloud run services update-traffic "$SERVICE" --region="$REGION" --to-revisions=<revisión>=100
```

Para volver a la última revisión desplegada, y que los despliegues siguientes vuelvan a recibir el tráfico solos:

```bash
gcloud run services update-traffic "$SERVICE" --region="$REGION" --to-latest
```

Comprobación: el `describe` anterior debe mostrar la revisión elegida con `percent: 100` tras el primer comando y `latestRevision: true` tras el segundo.

Mientras el tráfico esté fijado a una revisión concreta, un despliegue nuevo crea su revisión pero no le da tráfico; termina el rollback con `--to-latest`.

### Medir el arranque en frío

Espera al menos 15 minutos sin tráfico para que la instancia se apague y mide varias veces la primera petición:

```bash
curl -s -o /dev/null -w 'total=%{time_total}s codigo=%{http_code}\n' https://boticario-api-d3xv5q3iaa-pv.a.run.app/health
```

Repite el mismo comando justo después, con la instancia ya caliente, para compararlo con el arranque en frío; la diferencia es el costo de arrancar la instancia.

### Comprobaciones rápidas

```bash
curl -i https://boticario-api-d3xv5q3iaa-pv.a.run.app/health
curl -s https://boticario-api-d3xv5q3iaa-pv.a.run.app/openapi.json | head -c 300
curl -i 'https://boticario-api-d3xv5q3iaa-pv.a.run.app/v1/plants?q=lavandula&limit=1'
```

Las comillas de la tercera son necesarias: sin ellas el shell interpreta el `&`. Sin token, la tercera debe responder 401. Con token, pásalo por la entrada estándar para que no quede en la línea de comandos:

```bash
TOKEN_APP="$(gcloud secrets versions access 1 --secret="$SECRET_NAME" | cut -d, -f1)"
printf 'Authorization: Bearer %s\n' "$TOKEN_APP" | curl -s -H @- 'https://boticario-api-d3xv5q3iaa-pv.a.run.app/v1/plants?q=lavandula&limit=1'
unset TOKEN_APP
```

## Desmontaje

Estos pasos devuelven el proyecto a costo cero, en orden inverso a la preparación; no los ejecutes mientras quieras conservar el servicio. Cada uno tiene su comprobación: el listado debe salir vacío. Con las variables cargadas (`source .env.cloud-run`):

1. Elimina el servicio de Cloud Run:

   ```bash
   gcloud run services delete "$SERVICE" --region="$REGION"
   gcloud run services list --region="$REGION"
   ```

2. Elimina el secreto de Secret Manager, que borra todas sus versiones y su política de acceso:

   ```bash
   gcloud secrets delete "$SECRET_NAME"
   gcloud secrets list
   ```

3. Elimina el repositorio de Artifact Registry, lo que borra también todas las imágenes:

   ```bash
   gcloud artifacts repositories delete "$REPO" --location="$REGION"
   gcloud artifacts repositories list --location="$REGION"
   ```

4. Quita el binding `workloadIdentityUser` del `principalSet` y borra las dos cuentas de servicio (al borrar una cuenta desaparecen sus bindings sobre ella):

   ```bash
   gcloud iam service-accounts remove-iam-policy-binding "$DEPLOYER_EMAIL" \
     --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository/$GITHUB_REPO" \
     --role="roles/iam.workloadIdentityUser"
   gcloud iam service-accounts delete "$DEPLOYER_EMAIL"
   gcloud iam service-accounts delete "$RUNTIME_EMAIL"
   gcloud iam service-accounts list
   ```

   El listado no debe mostrar ni `boticario-deployer` ni `boticario-runtime`. El rol `roles/run.admin` del proyecto queda como una referencia huérfana a la cuenta borrada, sin efecto.

5. Elimina el proveedor y el pool de Workload Identity Federation; quedan en estado eliminado 30 días antes de borrarse del todo (los listados normales ya no los muestran, `--show-deleted` sí):

   ```bash
   gcloud iam workload-identity-pools providers delete "$PROVIDER" --location=global --workload-identity-pool="$POOL"
   gcloud iam workload-identity-pools delete "$POOL" --location=global
   gcloud iam workload-identity-pools list --location=global
   ```

6. Elimina el presupuesto; `gcloud billing budgets delete` pide el id, que se obtiene del listado por nombre:

   ```bash
   BUDGET_ID="$(gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID" --filter='displayName="boticario-ai presupuesto"' --format='value(name)')"
   gcloud billing budgets delete "$BUDGET_ID" --billing-account="$BILLING_ACCOUNT_ID"
   gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID"
   ```

7. Quita los secretos y las variables de GitHub:

   ```bash
   gh secret delete GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$GITHUB_REPO"
   gh secret delete GCP_DEPLOYER_SERVICE_ACCOUNT --repo "$GITHUB_REPO"
   gh secret delete API_VERIFY_TOKEN --repo "$GITHUB_REPO"
   gh variable delete GCP_PROJECT_ID --repo "$GITHUB_REPO"
   gh variable delete GCP_REGION --repo "$GITHUB_REPO"
   gh variable delete GCP_ARTIFACT_REPOSITORY --repo "$GITHUB_REPO"
   gh secret list --repo "$GITHUB_REPO"
   gh variable list --repo "$GITHUB_REPO"
   ```

Con el workflow aún en el repositorio, un `push` al backend volvería a fallar en la autenticación; si no vas a volver a desplegar, bórralo también con un commit.

Alternativa: borrar el proyecto entero elimina todo lo anterior (salvo el presupuesto, que vive en la cuenta de facturación, y los secretos y variables de GitHub) y se puede recuperar durante 30 días:

```bash
gcloud projects delete "$PROJECT_ID"
gcloud projects list --filter="projectId=$PROJECT_ID"
```

El desmontaje no toca la app ni el repositorio: la app sigue funcionando contra el backend local con `docker compose up`.

## Referencias

- https://docs.cloud.google.com/billing/docs/how-to/create-billing-account
- https://docs.cloud.google.com/run/docs/configuring/services/secrets
- https://docs.cloud.google.com/run/docs/configuring/services/environment-variables (Google no recomienda las variables de entorno para guardar secretos como credenciales de bases de datos o claves de API, y recomienda Secret Manager)
- https://cloud.google.com/secret-manager/pricing
- https://docs.cloud.google.com/sdk/gcloud/reference/secrets/create
- https://docs.cloud.google.com/sdk/gcloud/reference/secrets/add-iam-policy-binding
- https://docs.cloud.google.com/sdk/gcloud/reference/secrets/versions
- https://docs.cloud.google.com/sdk/docs/install-sdk
- https://docs.cloud.google.com/sdk/gcloud/reference/billing/projects/link
- https://docs.cloud.google.com/sdk/gcloud/reference/billing/projects/describe
- https://docs.cloud.google.com/sdk/gcloud/reference/artifacts/repositories/create
- https://docs.cloud.google.com/sdk/gcloud/reference/artifacts/repositories/set-cleanup-policies
- https://docs.cloud.google.com/artifact-registry/docs/repositories/cleanup-policy
- https://docs.cloud.google.com/sdk/gcloud/reference/artifacts/repositories/add-iam-policy-binding
- https://docs.cloud.google.com/sdk/gcloud/reference/iam/service-accounts/add-iam-policy-binding
- https://docs.cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/create
- https://docs.cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/providers/create-oidc
- https://docs.cloud.google.com/sdk/gcloud/reference/billing/budgets/create
- https://cli.github.com/manual/gh_secret_set
- https://cli.github.com/manual/gh_variable_set
- https://docs.cloud.google.com/free/docs/free-cloud-features
- https://cloud.google.com/run/pricing
- https://docs.cloud.google.com/run/docs/locations
- https://docs.cloud.google.com/sdk/gcloud/reference/run/services/logs/read
- https://docs.cloud.google.com/sdk/gcloud/reference/run/services/update-traffic
- https://docs.cloud.google.com/sdk/gcloud/reference/run/revisions/list
- https://docs.cloud.google.com/sdk/gcloud/reference/run/services/delete
- https://docs.cloud.google.com/sdk/gcloud/reference/artifacts/repositories/delete
- https://docs.cloud.google.com/sdk/gcloud/reference/iam/workload-identity-pools/delete
- https://docs.cloud.google.com/sdk/gcloud/reference/billing/budgets/delete
- https://docs.cloud.google.com/sdk/gcloud/reference/projects/delete
- https://cli.github.com/manual/gh_run_list
- https://cli.github.com/manual/gh_workflow_run
- https://cli.github.com/manual/gh_secret_delete
- https://cli.github.com/manual/gh_variable_delete
