# Colección de Postman de la API

Esta carpeta tiene una colección de Postman con todos los endpoints de la API del backend (los de [`backend/openapi.json`](../openapi.json)) y dos entornos, uno para la API local y otro para Cloud Run.

## Archivos

- `boticario-api.postman_collection.json`: la colección (formato v2.1), con las carpetas Público, Plantas, Objetivos y Errores. Cada petición lleva aserciones sobre el código de estado, el `Content-Type` y la forma mínima del cuerpo.
- `local.postman_environment.json`: `baseUrl` igual a `http://localhost:8080`, el puerto por defecto de `docker compose` y del binario.
- `cloud-run.postman_environment.json`: `baseUrl` igual a `https://boticario-api-d3xv5q3iaa-pv.a.run.app`.

En los dos entornos `token` va vacío y es de tipo `secret`. Ningún archivo del repositorio lleva un token.

## Importar

1. En Postman, `Import` y se seleccionan los tres archivos (o se arrastran).
2. Se elige el entorno (`Boticario local` o `Boticario Cloud Run`) en el selector de la esquina superior derecha.
3. En `Environments`, se abre el entorno y se pega el token en el valor actual (`Current value`) de `token`. No hace falta guardarlo en el valor inicial, que es el que se sincroniza.

Si la API local usa otro puerto (`PORT=9090 docker compose up`), se cambia `baseUrl` en el entorno.

## De dónde sale el token

Las peticiones de `/v1` envían `Authorization: Bearer {{token}}`, heredado de la colección. Las de `/health` y `/openapi.json`, y las de la carpeta Errores que prueban el 401, desactivan la autenticación de forma explícita.

- **API local:** uno de los valores de `API_TOKENS` con los que se arrancó la API (ver [`backend/README.md`](../README.md#tokens-de-api) y el [README de la raíz](../../README.md#backend-catálogo-y-api)). Si se arrancó con `docker compose`, está en el `.env` de la raíz.
- **Cloud Run:** el token de la app que guarda el secreto, según [`docs/deploy/cloud-run.md`](../../docs/deploy/cloud-run.md).

El token se pone solo en el entorno de Postman (o en una variable de entorno del shell para la línea de comandos), nunca en los archivos de esta carpeta.

## Ejecutar por línea de comandos

Con el CLI de Postman, el token se pasa por una variable de entorno del shell, sin escribirlo en un archivo ni en el historial:

```bash
export API_TOKEN=<uno-de-los-tokens-de-API_TOKENS>
postman collection run backend/postman/boticario-api.postman_collection.json \
  -e backend/postman/local.postman_environment.json \
  --env-var "token=$API_TOKEN"
```

Con Newman es equivalente:

```bash
newman run backend/postman/boticario-api.postman_collection.json \
  -e backend/postman/local.postman_environment.json \
  --env-var "token=$API_TOKEN"
```

Para Cloud Run se cambia el entorno por `cloud-run.postman_environment.json` y se usa el token de la app.

## Cloud Run aún no tiene los endpoints nuevos

El servicio de Cloud Run todavía no tiene los endpoints de objetivos (`/v1/goals` y `/v1/goals/{goalId}/plants`) ni los campos nuevos del detalle de planta hasta que se desplieguen los cambios en curso. Mientras tanto, esas peticiones y las aserciones sobre esos campos fallan contra Cloud Run (404 o campos ausentes). Contra la API local, construida desde este repositorio, pasan todas.
