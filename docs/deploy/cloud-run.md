# Despliegue del backend en Cloud Run

Esta guía despliega la API del catálogo (`backend/`, ver [`README.md`](../../README.md)) en Google Cloud Run: una URL HTTPS pública y estable, construida y publicada desde GitHub Actions sin claves de larga duración, que escala a cero y debería costar 0 USD al mes con el tráfico de un proyecto académico.

Este documento reúne la preparación única en Google Cloud, que haces tú a mano porque requiere tu cuenta y tu facturación; después el workflow del repositorio se encarga de construir y desplegar en cada cambio del backend en `main`.

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

Un presupuesto de 1 USD con avisos al 50 %, 90 % y 100 % del gasto, acotado a este proyecto.

Es solo una alerta: no corta el gasto ni apaga el servicio.

El control efectivo del costo es el máximo de 2 instancias del servicio y el desmontaje documentado.

```bash
gcloud billing budgets create \
  --billing-account="$BILLING_ACCOUNT_ID" \
  --display-name="boticario-ai 1 USD" \
  --budget-amount=1USD \
  --filter-projects="projects/$PROJECT_NUMBER" \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0
```

Sin flags de notificación, los avisos llegan por correo a los administradores y usuarios de la cuenta de facturación, es decir, a ti.

Crear presupuestos requiere el rol Billing Account Costs Manager o Administrator sobre la cuenta de facturación.

La moneda de `--budget-amount` debe coincidir con la de tu cuenta: si no es USD, cambia `1USD` por `1` y se usará la de la cuenta (el umbral es entonces 1 unidad de esa moneda).

Si el comando se queja de un proyecto de cuota o de que la API no está habilitada, comprueba que `billingbudgets.googleapis.com` figura en el paso 1 y añade `--billing-project="$PROJECT_ID"`.

Comprobación: `gcloud billing budgets list` debe mostrar el presupuesto `boticario-ai 1 USD` con sus tres reglas de umbral.

```bash
gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID"
```

Si prefieres la consola: Facturación, Presupuestos y alertas, Crear presupuesto; nombre `boticario-ai 1 USD`; en Alcance filtra por el proyecto; en Importe elige «Importe específico» de 1 USD; deja los umbrales 50 %, 90 % y 100 % y mantén activo el aviso por correo a los administradores de la cuenta.

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

### Qué sigue

Con esto hecho, el workflow de despliegue (`.github/workflows/deploy-backend.yml`) se crea en el repositorio y se lanza con `gh workflow run deploy-backend.yml`.

Desde entonces, cada cambio del backend que llegue a `main` se construye y se despliega solo.

### Referencias

- https://docs.cloud.google.com/billing/docs/how-to/create-billing-account
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

<!-- Las secciones de costo, runbook y desmontaje se añaden en las tareas 4.1 y 4.2 -->
