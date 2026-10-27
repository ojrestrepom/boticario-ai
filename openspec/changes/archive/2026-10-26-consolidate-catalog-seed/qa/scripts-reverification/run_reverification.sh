#!/bin/bash
# Reverificación de QA de consolidate-catalog-seed.
# Uso: run_reverification.sh <catalog-api compilado> [<catalog-ingest compilado>]
# Compilar fuera del repositorio: CARGO_TARGET_DIR=<tmp>/target cargo build --release -p catalog-api -p catalog-ingest (desde backend/).
# El token se genera al vuelo y no se escribe en ningún archivo; la API se detiene al terminar.
set -u
API_BIN=$1
cd "$(git rev-parse --show-toplevel)"
REPO=$PWD
QA=$REPO/openspec/changes/consolidate-catalog-seed/qa
EV=$QA/evidence-reverification
mkdir -p $EV/api $EV/app $EV/seed $EV/barridos
python3 -I $QA/scripts-reverification/seed_checks.py . $EV/seed $QA/evidence/ids/id-map.tsv > /dev/null
python3 -I $QA/scripts-content-review/global_scans.py --out $EV/barridos > /dev/null
python3 -I tools/catalog-seed/cli.py validate --records data/seed/plants --bundles data/work/bundles | tee $EV/seed/validador.txt
TOKEN=$(openssl rand -hex 32)
API_TOKENS=$TOKEN CATALOG_DB=$REPO/data/build/catalog.db $API_BIN > /dev/null 2>&1 &
APIPID=$!
trap 'kill $APIPID 2>/dev/null; wait $APIPID 2>/dev/null' EXIT
for i in $(seq 1 50); do curl -s -o /dev/null http://127.0.0.1:8080/health && break; sleep 0.3; done
export QA_TOKEN=$TOKEN QA_DB=$REPO/data/build/catalog.db QA_OLD_MAP=$QA/evidence/ids/id-map.tsv
python3 -I $QA/scripts/api_tests.py . $EV/api 2>&1 | sed "s/$TOKEN/<token>/g" | tee $EV/api/api_tests-console.txt
python3 -I $QA/scripts-reverification/api_checks.py . $EV/api 2>&1 | sed "s/$TOKEN/<token>/g" > $EV/api/api_checks-console.txt
npx --yes newman@6.2.1 run $QA/postman/consolidate-catalog-seed.collection.json --env-var "token=$TOKEN" 2>&1 | sed "s/$TOKEN/<token>/g" > $EV/api/newman-run.txt
(cd app && flutter analyze > $EV/app/flutter-analyze.txt 2>&1; flutter test > $EV/app/flutter-test.txt 2>&1
 flutter test integration_test/app_test.dart -d flutter-tester --dart-define=API_BASE_URL=http://127.0.0.1:8080 --dart-define=API_TOKEN=$TOKEN 2>&1 | sed "s/$TOKEN/<token>/g" > $EV/app/smoke.txt)
grep -rl "$TOKEN" $EV 2>/dev/null && echo "TOKEN EN EVIDENCIA" || echo "token ausente de la evidencia"
