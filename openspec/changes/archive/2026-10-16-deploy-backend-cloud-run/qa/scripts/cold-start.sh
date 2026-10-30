#!/usr/bin/env bash
# Mide el arranque en frío de boticario-api: comprueba la última petición en Cloud Logging, exige >= 15 min de
# inactividad, hace la primera petición y 3 inmediatas. Uso: cold-start.sh <n-de-muestra> (desde la raíz del repo).
set -u
N="${1:?uso: cold-start.sh <n>}"
cd "$(git rev-parse --show-toplevel)"
source .env.cloud-run
URL="https://boticario-api-d3xv5q3iaa-pv.a.run.app/health"
OUT="openspec/changes/deploy-backend-cloud-run/qa/evidence/cold-start-$N.txt"
LAST="$(gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="boticario-api" AND httpRequest.requestMethod:*' --freshness=1d --limit=1 --order=desc --format='value(timestamp)')"
IDLE="$(python3 -I - "$LAST" <<'PY'
import sys
from datetime import datetime, timezone
t = datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00"))
print(round((datetime.now(timezone.utc) - t).total_seconds() / 60, 1))
PY
)"
{
  echo "muestra=$N"
  echo "ultima_peticion_previa_utc=$LAST"
  echo "inactividad_min=$IDLE"
  echo "inicio_utc=$(date -u +%FT%TZ)"
  echo "--- primera peticion (frio)"
  curl -s -o /dev/null -w 'total=%{time_total}s connect=%{time_connect}s tls=%{time_appconnect}s ttfb=%{time_starttransfer}s codigo=%{http_code}\n' "$URL"
  for i in 1 2 3; do
    echo "--- peticion caliente $i"
    curl -s -o /dev/null -w 'total=%{time_total}s codigo=%{http_code}\n' "$URL"
  done
} | tee "$OUT"
