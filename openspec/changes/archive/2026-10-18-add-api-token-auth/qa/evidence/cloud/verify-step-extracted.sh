set -euo pipefail
if [ -z "${API_VERIFY_TOKEN}" ]; then
  echo "::error::Falta el secreto de GitHub API_VERIFY_TOKEN (un token de CI de los que contiene boticario-api-tokens); ver docs/deploy/cloud-run.md"
  exit 1
fi
plant=/v1/plants/lavandula-angustifolia

# Con reintentos para el arranque en frio; --fail convierte un 4xx/5xx en reintento y error.
expect_200() {
  status="$(curl --fail --silent --show-error --retry 5 --retry-delay 3 --retry-all-errors \
    --output /dev/null --write-out '%{http_code}' "$@")"
  echo "GET ${path} -> ${status}"
  if [ "$status" != "200" ]; then
    echo "::error::${path} respondio ${status} y se esperaba 200"
    exit 1
  fi
}

path=/health
expect_200 "${SERVICE_URL}${path}"

path="$plant"
printf 'Authorization: Bearer %s\n' "$API_VERIFY_TOKEN" |
  expect_200 -H @- "${SERVICE_URL}${path}"

# Sin token debe dar 401. Sin --fail ni reintentos: un 401 es el resultado correcto y un
# fallo de red debe fallar el job, no reintentarse hasta parecer otra cosa. El servicio
# ya respondio dos veces, asi que no hay arranque en frio que absorber.
status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  "${SERVICE_URL}${plant}")"
echo "GET ${plant} (sin token) -> ${status}"
if [ "$status" = "200" ]; then
  echo "::error::${plant} respondio 200 sin token: el servicio estaria abierto, la autorizacion no esta activa"
  exit 1
fi
if [ "$status" != "401" ]; then
  echo "::error::${plant} sin token respondio ${status} y se esperaba 401"
  exit 1
fi
echo "Servicio disponible en ${SERVICE_URL}"
