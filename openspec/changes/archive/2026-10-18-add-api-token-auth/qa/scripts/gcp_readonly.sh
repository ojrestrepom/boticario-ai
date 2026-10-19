#!/usr/bin/env bash
# DEP-01, DEP-02, DEP-04 a DEP-08: inspección de solo lectura de Cloud Run, IAM, Secret Manager y GitHub.
# Uso: bash gcp_readonly.sh   (desde cualquier directorio; requiere gcloud y gh autenticados)
# No ejecuta ningún comando de escritura. No imprime valores de secretos: solo cuenta apariciones de los tokens reales
# (leídos de la versión 1 del secreto a variables de shell) y su forma (número y longitud).
set -uo pipefail
cd "$(dirname "$0")/../../../../.."
EV=openspec/changes/add-api-token-auth/qa/evidence/cloud
mkdir -p "$EV"
export CLOUDSDK_CORE_DISABLE_PROMPTS=1
P=boticario-ai; R=northamerica-south1; S=boticario-api; SEC=boticario-api-tokens
RT="boticario-runtime@$P.iam.gserviceaccount.com"
{ gcloud run services describe $S --region $R --project $P --format=yaml; } > "$EV/service-describe.yaml" 2>&1
gcloud run services describe $S --region $R --project $P --format='yaml(spec.template.spec.containers[0].env,spec.template.metadata.annotations,spec.template.spec.containers[0].resources,spec.template.spec.containers[0].startupProbe,spec.template.spec.serviceAccountName,status.latestReadyRevisionName,status.traffic)' > "$EV/service-config.txt" 2>&1
gcloud run services get-iam-policy $S --region $R --project $P > "$EV/service-iam.txt" 2>&1
gcloud run revisions list --service $S --region $R --project $P > "$EV/revisions.txt" 2>&1
gcloud secrets list --project $P > "$EV/secrets-list.txt" 2>&1
gcloud secrets versions list $SEC --project $P > "$EV/secret-versions.txt" 2>&1
gcloud secrets get-iam-policy $SEC --project $P > "$EV/secret-iam.txt" 2>&1
gcloud projects get-iam-policy $P --format=json > "$EV/project-iam.json" 2>&1
python3 -I - "$EV" "$RT" <<'PY'
import json, sys
ev, rt = sys.argv[1:3]
d = json.load(open(f"{ev}/project-iam.json"))
rows = []
for b in d.get("bindings", []):
    for m in b["members"]:
        rows.append((m.split(":")[0] + ":" + (m.split(":",1)[1].split("@")[0] if m.startswith(("user:",)) else m.split(":",1)[1]), b["role"]))
rows = [(("user:<propietario>" if m.startswith("user:") else m), r) for m, r in rows]
with open(f"{ev}/project-iam-summary.txt", "w") as f:
    f.write("miembro -> rol (los correos de usuario se sustituyen por <propietario>)\n")
    for m, r in sorted(rows):
        f.write(f"{m} -> {r}\n")
    f.write(f"\nroles de {rt.split('@')[0]} en el proyecto: {[r for m, r in rows if rt in m]}\n")
PY
rm -f "$EV/project-iam.json"
# ¿Los roles básicos concedidos a otras identidades permiten leer el valor del secreto? (permisos de secretmanager en roles/editor y roles/owner)
for role in roles/editor roles/owner roles/run.admin; do
  echo "== $role: permisos secretmanager.versions.* =="
  gcloud iam roles describe $role --format='value(includedPermissions)' 2>&1 | tr ';' '\n' | grep -E '^secretmanager\.versions\.(access|list|get)$' || echo "(ninguno)"
done > "$EV/roles-secret-permissions.txt"
gcloud iam service-accounts get-iam-policy "$RT" --project $P > "$EV/runtime-sa-iam.txt" 2>&1
gcloud iam workload-identity-pools providers list --workload-identity-pool=github --location=global --project $P --format='yaml(name,attributeCondition,oidc.issuerUri)' > "$EV/wif-provider.txt" 2>&1
gh secret list --repo sebastianrodriguez1115/boticario-ai > "$EV/gh-secrets.txt" 2>&1
gh run list --workflow deploy-backend.yml --repo sebastianrodriguez1115/boticario-ai --limit 8 > "$EV/gh-runs.txt" 2>&1
# Forma del secreto (conteo y longitudes, sin valores) y apariciones de los tokens reales en cada archivo de evidencia.
SECRET_VALUE="$(gcloud secrets versions access 1 --secret=$SEC --project $P)"
{
  echo "elementos: $(printf '%s' "$SECRET_VALUE" | tr ',' '\n' | awk 'END {print NR}')"
  printf '%s' "$SECRET_VALUE" | tr ',' '\n' | awk '{print "longitud: " length($0) "  hex64: " ($0 ~ /^[0-9a-f]{64}$/ ? "si" : "no")}'
} > "$EV/secret-shape.txt"
printf '%s\n' "$SECRET_VALUE" | tr ',' '\n' > "${TMPDIR:-/tmp}/.qa-tokens.$$"
echo "apariciones de cada token real en los archivos de $EV (deben ser 0):" > "$EV/token-counts.txt"
i=0; while IFS= read -r t || [ -n "$t" ]; do i=$((i+1)); printf 'token %s: %s\n' "$i" "$(grep -rcF -- "$t" "$EV" | awk -F: '{s+=$NF} END {print s+0}')" >> "$EV/token-counts.txt"; done < "${TMPDIR:-/tmp}/.qa-tokens.$$"
rm -f "${TMPDIR:-/tmp}/.qa-tokens.$$"
unset SECRET_VALUE
cat "$EV/secret-shape.txt" "$EV/token-counts.txt"
