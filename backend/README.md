# Backend: desarrollo nativo

Esta guía es para quien quiera modificar el código Rust del backend o ejecutarlo sin Docker. Para solo ejecutar el backend basta el [README de la raíz](../README.md#backend-catálogo-y-api), que usa Docker y no necesita nada de lo que se describe aquí.

El backend construye una base SQLite neutral con las plantas del catálogo y la sirve en modo de solo lectura. El modelo de datos y cómo añadir una fuente nueva a las herramientas están en la [guía del modelo de datos](../docs/data/modelo-de-datos.md#9-cómo-añadir-una-fuente-nueva-a-las-herramientas).

Los comandos de las secciones 2 a 4 se ejecutan desde la raíz del repositorio (usan `--manifest-path backend/Cargo.toml`). Los de la sección 5 y los de la sección 6 se ejecutan desde `backend/`. Cada bloque de código indica su directorio.

## 1. Prerrequisitos

- [`mise`](https://mise.jdx.dev) instalado. Desde la raíz, `mise install` instala Rust **1.99.0**, la versión fijada en [`mise.toml`](../mise.toml).
- Un compilador de C del sistema (en macOS, las Command Line Tools), porque SQLite se compila embebido.
- `diesel_cli` solo si se cambia el esquema: `mise exec -- cargo install diesel_cli --no-default-features --features sqlite-bundled`.
- La versión de Rust de [`mise.toml`](../mise.toml) debe coincidir con la de la imagen base del [`Dockerfile`](../Dockerfile) de la raíz: el test `toolchain_pin` de `catalog-core` ([`catalog-core/tests/toolchain_pin.rs`](catalog-core/tests/toolchain_pin.rs)) falla si divergen, así que al subir la versión hay que cambiar los dos archivos.

Desde la raíz del repositorio:

```bash
mise install
```

## 2. Construir el catálogo

La semilla del catálogo vive en [`data/seed/`](../data/seed/) (un JSON por planta, `goals.json` y `manifest.json`) y se genera con las herramientas de [`tools/catalog-seed/`](../tools/catalog-seed/README.md), que son solo para el desarrollador (véase la [regeneración de la semilla](../docs/data/regeneracion-de-la-semilla.md)). `catalog-ingest` solo tiene el subcomando `build`, que no usa la red. Desde la raíz del repositorio:

```bash
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- build
```

- `build` lee la semilla, verifica su formato, los objetivos, el número de plantas y el `seedHash` del manifiesto, y escribe la base neutral `data/build/catalog.db`. Imprime el número de plantas y el hash del contenido. Si un registro no coincide con el manifiesto, falla y no escribe la base.
- Con `--seed <ruta>` se lee otra carpeta de semilla, con `--out <ruta>` se escribe otro archivo y con `--data-dir <ruta>` se usa otro directorio de datos (por defecto, `<data-dir>/seed` y `<data-dir>/build/catalog.db`).

## 3. Ejecutar la API

`API_TOKENS` es obligatoria siempre, también en local. Desde la raíz del repositorio, con un token aleatorio solo para esa ejecución:

```bash
API_TOKENS=$(openssl rand -hex 32) mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-api
```

Para no repetirlo, se puede crear una vez el `.env` de la raíz (git lo ignora; es el mismo que lee `docker compose`) y cargarlo en el shell:

```bash
echo "API_TOKENS=$(openssl rand -hex 32)" > .env
set -a; . ./.env; set +a
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-api
```

`docker compose` interpola `API_TOKENS` en todos sus subcomandos (`up`, `down`, `ps`, `logs`) y falla con «required variable API_TOKENS is missing a value» si no está en el entorno ni en el `.env` de la raíz. Con ese `.env` no pasa. Si la exportaste solo en un shell, en otro shell hay que volver a definirla. Para detener basta un valor cualquiera, porque `down` no arranca la API: `API_TOKENS=x docker compose down`.

La API se niega a arrancar si no encuentra la base o si falta `API_TOKENS`. Se configura con argumentos y variables de entorno:

| Nombre | Por defecto | Uso |
|---|---|---|
| `CATALOG_DB` (o `--db <ruta>`) | `data/build/catalog.db` | Ruta de la base; el argumento tiene prioridad. |
| `HOST` | `127.0.0.1` | Dirección de escucha. |
| `PORT` | `8080` | Puerto de escucha. |
| `RUST_LOG` | `info` | Filtro de logs. |
| `API_TOKENS` | obligatoria | Tokens de API válidos, separados por comas (ver más abajo). `--help` y `--openapi` no la exigen. |
| `NO_COLOR` | sin definir | Con cualquier valor no vacío, los logs no llevan colores ni en una terminal. |

Los logs salen por stdout en texto, una línea por evento. Llevan colores (secuencias ANSI) solo si stdout es una terminal y `NO_COLOR` no tiene valor; redirigidos a un archivo, a una tubería o a un contenedor sin TTY salen en texto plano, que es lo que lee Cloud Logging. `RUST_LOG` fija el nivel, por ejemplo `RUST_LOG=warn`.

### Tokens de API

`API_TOKENS` es una lista separada por comas con uno o más tokens; así se pueden rotar sin cortar el servicio. Se ignoran los espacios alrededor de cada token y el salto de línea final. Cada token tiene de 32 a 256 caracteres y solo letras, dígitos y `-`, `.`, `_`, `~`, `+`, `/`. Si la variable falta, está vacía o tiene un token inválido, la API sale con código 2 y un mensaje que nombra la variable y el motivo, nunca el valor. Los tokens no aparecen en logs ni en el `Debug` de la configuración.

Endpoints, todos `GET`:

- `/health`: estado del servicio (público).
- `/v1/plants`: lista paginada, con búsqueda opcional por `q` en los nombres, los sinónimos y los identificadores anteriores (exige token).
- `/v1/plants/{id}`: detalle de una planta; el `id` puede ser también un identificador anterior (exige token).
- `/openapi.json`: el contrato OpenAPI (público).

Hay una colección de Postman con todos los endpoints y sus entornos en [`postman/`](postman/README.md).

Todo camino bajo `/v1`, también los inexistentes y los métodos no permitidos, exige `Authorization: Bearer <token>` (el nombre del esquema no distingue mayúsculas). Sin la cabecera, con otro esquema o con un token que no coincide con ninguno, la respuesta es 401 `application/problem+json` con `WWW-Authenticate: Bearer`, siempre igual para no revelar el motivo.

```bash
TOKEN=<uno-de-los-tokens-de-API_TOKENS>
curl -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:8080/v1/plants?q=lavand'
```

### Qué devuelve la API

Cada elemento del listado lleva `id`, `scientificName`, `displayName` (el nombre para mostrar que guarda la semilla: un nombre común en español o, si no hay, el científico), `commonNames` (con `displayName` primero si es un nombre común, el de idioma `es` antes si varios coinciden con él, y el resto por texto sin distinguir mayúsculas ni acentos, con el texto original y el idioma como desempate; el detalle usa el mismo orden en `names`) y `family`.

El detalle suma `names`, `parts` y `uses` (una fila por referencia resuelta, con la etiqueta de la referencia como cita) y los campos consolidados, siempre presentes (`null` o lista vacía si la planta no tiene el dato):

- `synonyms`, `description`, `origin` y `oil` (`{"type": "Esencial"}`).
- `useGroups`: grupos de uso tradicional por número de registros descendente y actividad (sin distinguir mayúsculas ni acentos), con `activity`, `activitySource`, `count`, `countries` y `references`; la `citation` de cada referencia es el texto completo de la cita y una cita sin obra identificada lleva `id` nulo, `resolved` falso y «<clave> (sin resolver)».
- `goals`: objetivos por nombre, con `id`, `name`, `subarea` (solo en «otros objetivos»), `area`, `evidence` y `references`.
- `safety`: `level` (`alto`, `medio`, `bajo` o `null` si las fuentes traen advertencias pero ninguna fija un nivel, como el eucalipto), `text` y `references`; es `null` solo cuando no hay ningún dato, lo que no significa que la planta sea segura.
- `image`: `url`, `pageUrl`, `author`, `license`, `licenseUrl` y `attributionRequired`, o `null`. La API solo entrega los datos del registro: no descarga ni sirve la imagen.
- `credits`: los datasets que respaldan los datos de la planta, sin repeticiones y ordenados por nombre, cada uno con `name`, `license`, `licenseUrl` (de `source.license_url`, `null` si la fuente no la tiene), `attribution` y `url`. Es neutral: no dice qué campo viene de qué dataset. Si la descripción resume un artículo, la `url` del crédito de ese dataset es la del artículo.

Una planta con `reviewFlags` se sirve igual, y la API no los expone. Solo omite lo que la semilla marca como pendiente de revisión: los objetivos con `plant_goal.pending_review` (hoy `relajacion-estres` del hipérico) y los grupos de uso con `plant_use_group.pending_review` (sin ninguna cita resuelta), que tampoco generan filas en `uses`. Un grupo con al menos una cita resuelta se sirve con todas sus citas. La regla depende solo de esas columnas; la API no interpreta códigos de flags.

Fragmentos de la respuesta real de `GET /v1/plants/lavandula-angustifolia` con la base construida desde la semilla (cada objeto está completo; se omiten el resto de los elementos de cada lista):

```bash
TOKEN=<token>
curl -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:8080/v1/plants/lavandula-angustifolia'
```

```json
"displayName": "Lavanda",
"oil": {"type": "Esencial"},
"useGroups[0]": {
  "activity": "Carminativo",
  "activitySource": "Carminative",
  "count": 2,
  "countries": [
    "Otros lugares",
    "Turquía"
  ],
  "references": [
    {
      "id": "usda_reference:Steinmetz",
      "citation": "Steinmetz, E.F. 1957. codex Vegetabilis. Published by the author, Amsterdam.",
      "resolved": true
    },
    {
      "id": "usda_reference:WOI",
      "citation": "The Wealth of India, vol. 6",
      "resolved": true
    }
  ]
},
"goals[0]": {
  "id": "mejorar-el-sueno",
  "name": "Mejorar el sueño",
  "subarea": null,
  "area": "Trastornos del sueño e insomnio pasajero",
  "evidence": "La EMA tiene una monografía de la flor y otra del aceite esencial en esta área.",
  "references": [
    {
      "id": "ema_herbal:lavandulae-aetheroleum",
      "citation": "EMA: Lavandulae aetheroleum"
    },
    {
      "id": "ema_herbal:lavandulae-flos",
      "citation": "EMA: Lavandulae flos"
    }
  ]
},
"image": {
  "url": "https://upload.wikimedia.org/wikipedia/commons/4/40/Lavandula_angustifolia_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-087.jpg",
  "pageUrl": "https://commons.wikimedia.org/wiki/File:Lavandula_angustifolia_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-087.jpg",
  "author": "Franz Eugen Köhler, Köhler's Medizinal-Pflanzen",
  "license": "Public domain",
  "licenseUrl": null,
  "attributionRequired": false
},
"credits[5]": {
  "name": "Wikipedia en español",
  "license": "CC BY-SA 4.0",
  "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
  "attribution": "Colaboradores de Wikipedia en español (https://es.wikipedia.org). Texto bajo CC BY-SA 4.0; el historial de cada artículo lista a sus autores.",
  "url": "https://es.wikipedia.org/wiki/Lavandula_angustifolia"
}
```

Los créditos de la lavanda son EFSA, las dos fuentes de la EMA, TPPT, USDA, Wikipedia en español y WCVP; los del eucalipto cambian TPPT por Wikidata. El crédito de Wikipedia enlaza al artículo de la planta porque la descripción lo resume.

### Objetivos

`GET /v1/goals` devuelve, sin paginar y en el orden de presentación del catálogo (`goal.position`), un array JSON en la raíz con los objetivos: `id`, `name` (en español), `plantCount` y `subareas` (lista vacía si no tiene; cada subárea con `id`, `name` y `plantCount`). Los nombres, el orden y las subáreas salen de `goal` y `goal_subarea`, y las subáreas sin plantas visibles se omiten. Los conteos son de plantas distintas visibles, así que el de «Otros objetivos» es la unión sin repetir de sus subáreas y coincide con el `total` de sus resultados.

`GET /v1/goals/{goalId}/plants` devuelve una página `{goal, subarea, items, total, limit, offset}`:

| Parámetro | Uso |
|---|---|
| `limit` | 1 a 100, por defecto 20, con las mismas reglas y errores que `GET /v1/plants`. |
| `offset` | Desde 0, por defecto 0; si supera el total devuelve una lista vacía y conserva el `total`. |
| `subarea` | Id de una subárea del objetivo. Sin él, un objetivo con subáreas devuelve la unión sin repetir plantas. |

Cada elemento lleva `id`, `scientificName`, `displayName`, `commonNames` y `family` como el listado, y además `areas` (nombres en español de las áreas de la EMA que respaldan a la planta en ese objetivo o subárea; 11 filas reales unen dos áreas con «; » y se muestran tal cual), `safetyLevel` (`alto`, `medio`, `bajo` o `null`, también `null` cuando hay precauciones sin nivel), `hasSafety` (verdadero si la planta tiene datos de precauciones aunque no tengan nivel) e `image`, el mismo objeto del detalle o `null`. La API no deriva miniaturas ni consulta la red.

Las plantas salen ordenadas por `displayName` normalizado (sin distinguir mayúsculas ni acentos, con la normalización de nombres de la búsqueda), luego por nombre científico normalizado y por último por id; el orden no depende del respaldo de la EMA. Solo aparecen las plantas con ese objetivo en `plant_goal`: las tóxicas que la semilla deja sin objetivos no salen, y las filas con `plant_goal.pending_review` no aparecen ni cuentan (hoy, el hipérico no sale en `relajacion-estres`, pero `GET /v1/plants/hypericum-perforatum` sigue respondiendo 200). Ningún otro `reviewFlag` oculta una planta.

| Caso | Respuesta |
|---|---|
| Sin token o con un token incorrecto | 401 con `WWW-Authenticate: Bearer`. |
| Objetivo desconocido | 404. |
| `subarea` que no es del objetivo, o sobre un objetivo sin subáreas | 400 con `param` igual a `subarea`. |
| `limit` u `offset` inválidos | 400 con `param` igual al parámetro. |
| Método distinto de `GET` | 405 con `Allow: GET`. |

Todos los errores son `application/problem+json`. Con la API en marcha (la variable `TOKEN` debe tener un token válido, nunca se escribe en archivos):

```bash
curl -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:8080/v1/goals'
curl -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:8080/v1/goals/relajacion-estres/plants?limit=1'
curl -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:8080/v1/goals/otros-objetivos/plants?subarea=molestias-oculares'
curl -i -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:8080/v1/goals/mejorar-el-sueno/plants?subarea=digestion'
```

Fragmento real de la primera respuesta (se omiten los demás objetivos y subáreas):

```json
[
  {"id": "relajacion-estres", "name": "Relajación / Estrés", "plantCount": 17, "subareas": []},
  {
    "id": "otros-objetivos",
    "name": "Otros objetivos",
    "plantCount": 135,
    "subareas": [
      {"id": "digestion", "name": "Digestión", "plantCount": 68},
      {"id": "molestias-oculares", "name": "Molestias oculares", "plantCount": 1}
    ]
  }
]
```

Respuesta real de la tercera petición:

```json
{
  "goal": {"id": "otros-objetivos", "name": "Otros objetivos"},
  "subarea": {"id": "molestias-oculares", "name": "Molestias oculares"},
  "items": [
    {
      "id": "hamamelis-virginiana",
      "scientificName": "Hamamelis virginiana",
      "displayName": "Avellano de bruja",
      "commonNames": [
        {"text": "Avellano de bruja", "language": "es"},
        {"text": "avellana que se rompe", "language": "es"},
        {"text": "escoba de bruja", "language": "es"},
        {"text": "Witch Hazel", "language": "en"}
      ],
      "family": "Hamamelidaceae",
      "areas": ["Molestias oculares"],
      "safetyLevel": null,
      "hasSafety": true,
      "image": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/aa/Hamamelis_virginiana_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-070.jpg",
        "pageUrl": "https://commons.wikimedia.org/wiki/File:Hamamelis_virginiana_-_K%C3%B6hler%E2%80%93s_Medizinal-Pflanzen-070.jpg",
        "author": "Franz Eugen Köhler, Köhler's Medizinal-Pflanzen",
        "license": "Public domain",
        "licenseUrl": null,
        "attributionRequired": false
      }
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

Con la base real hay 6 objetivos: `relajacion-estres` (17), `mejorar-el-sueno` (8), `cuidado-de-la-piel` (32), `alivio-respiratorio` (52), `cansancio-y-fatiga` (8) y `otros-objetivos` (135, con las subáreas `digestion` 68, `vias-urinarias-y-genitales` 42, `dolor-e-inflamacion` 22, `boca-y-garganta` 20, `circulacion` 17 y `molestias-oculares` 1).

### Identificadores anteriores

El ID de una planta es el slug de su nombre aceptado, y los anteriores se guardan como alias. `GET /v1/plants/{id}` busca primero el ID de planta (siempre gana) y luego el alias. Con un alias responde 200 con el detalle de la planta canónica, su `id` canónico en el cuerpo y la cabecera `Content-Location`, sin redirección; con un ID canónico no lleva esa cabecera, y con uno desconocido responde 404. Es la misma ruta, con el mismo token:

```bash
curl -i -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:8080/v1/plants/rosmarinus-officinalis'
```

```text
HTTP/1.1 200 OK
content-type: application/json
content-location: /v1/plants/salvia-rosmarinus
```

El listado nunca incluye alias como plantas. `q` sí los usa para encontrar la planta: además de los nombres, compara `slug(q)` (la consulta normalizada con los caracteres que no son letras ni dígitos reducidos a un guion) por subcadena con cada alias, de modo que `Acinos thymoides` encuentra `clinopodium-acinos`. Cada planta cuenta una vez aunque coincida por varias vías, el alias no se devuelve como nombre y una consulta sin letras ni dígitos (como `%`) no busca en alias. Respuesta real de `GET /v1/plants?q=acinos%20thymoides`:

```json
{
  "items": [
    {
      "id": "clinopodium-acinos",
      "scientificName": "Clinopodium acinos",
      "displayName": "Clinopodium acinos",
      "commonNames": [],
      "family": "Lamiaceae"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

La búsqueda es por subcadena, así que `mentha piperita` no encuentra nada (el alias de `mentha-x-piperita` que la menciona lleva una `x` en medio), mientras que `mentha x piperita` sí lo encuentra.

## 4. Contrato OpenAPI

[`openapi.json`](openapi.json) se genera desde el código de la API y la misma API lo sirve en `/openapi.json`. Tras cambiar rutas o DTO, se regenera desde la raíz del repositorio con:

```bash
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-api -- --openapi > backend/openapi.json
```

Un test falla si el archivo está desactualizado respecto al código.

## 5. Verificación

Desde `backend/`:

```bash
mise exec -- cargo fmt --all --check
mise exec -- cargo clippy --all-targets --workspace -- -D warnings
mise exec -- cargo test --workspace
```

Los tests marcados `#[ignore]` necesitan la salida real de `build` en `data/build/` (el fixture JSON que compara uno de ellos ya vive en `catalog-ingest/tests/fixtures/`). También desde `backend/`:

```bash
mise exec -- cargo test --workspace -- --ignored
```

### Integración continua

El workflow [`.github/workflows/backend-ci.yml`](../.github/workflows/backend-ci.yml) verifica el backend con tres pasos en serie: formato, clippy sin advertencias y las pruebas del workspace. Corre en cada pull request y en cada push a una rama distinta de `main` que toque `backend/`, `data/migrations/`, el `Dockerfile`, `mise.toml` o el propio workflow. El toolchain sale de [`mise.toml`](../mise.toml): la CI instala con mise esa versión de Rust, la misma que se usa en local. El comando local equivalente, desde `backend/`:

```bash
mise exec -- cargo fmt --check && mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings && mise exec -- cargo test --workspace --locked
```

## 6. Cambiar el esquema

1. Editar la migración de [`data/migrations/`](../data/migrations/).
2. Subir `SCHEMA_VERSION` en [`catalog-core/src/version.rs`](catalog-core/src/version.rs).
3. Regenerar [`catalog-core/src/schema.rs`](catalog-core/src/schema.rs) con Diesel, desde `backend/`, sobre una base temporal; [`diesel.toml`](diesel.toml) fija la carpeta de migraciones y la ruta del archivo generado: `DATABASE_URL=/tmp/esquema.db mise exec -- diesel migration run`.
4. Reconstruir el catálogo con `build` (sección 2).

La base no se migra: se regenera entera en cada construcción.
