# Verificación 5.1 a 5.5: imagen, compose, caché y workspace

Fecha: 2026-10-13.

Entorno: macOS en Apple Silicon (`arm64`), Docker Desktop con Docker Engine 29.8.2, Docker Compose 5.6.0, BuildKit v0.33.1 (builder `desktop-linux`). Imagen base de compilación `rust:1.99.0-slim-bookworm`, runtime `debian:bookworm-slim`.

Resumen: las cinco tareas pasan.

| Construcción | Tiempo | Comentario |
|---|---|---|
| Fría (builder desechable `verif-backend`) | 38 s | compila 153 crates y descarga el ZIP |
| Con caché, sin cambios | 1 s | los 10 pasos `CACHED` |
| Tras un cambio trivial en `main.rs` | 1 s | recompila solo `catalog-api` (0,59 s) |
| Final, ya revertido el cambio | 1 s | los 10 pasos `CACHED` |

## 5.1 Construcción desde cero con un builder desechable

Comandos:

- `docker buildx create --name verif-backend --driver docker-container --use`
- `BUILDX_BUILDER=verif-backend docker compose --progress=plain build`
- `docker compose up -d`, tres `curl` y `docker compose down`
- `docker buildx rm verif-backend` y `docker buildx use desktop-linux`

Resultado:

- La imagen se construyó sin Rust, mise ni descargas manuales en el anfitrión, en 38 s (código 0). Con ese driver compose cargó la imagen en el almacén local sin necesidad de `--load`.
- El log muestra la compilación desde cero (153 líneas `Compiling`, `Finished \`release\` profile [optimized] target(s) in 28.49s`) y la descarga de crates (`Downloading crates ...`).
- La etapa de catálogo se ejecutó de verdad: `usda: descargado y verificado: /data/.cache/Duke-Source-CSV.zip`, `fuentes: 1`, `plantas: 2376`, `tiempo: 515.61ms`.
- Hash impreso: `hash: 48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`, igual al esperado (el de la construcción nativa).
- `GET /healthz` devuelve 200.
- `GET /v1/plants?q=lavand` devuelve plantas (`lavandula-angustifolia`, `lavandula-latifolia`, ...).
- `GET /v1/sources` devuelve la fuente `usda` (licencia CC0, cita y URL).
- `docker compose down` eliminó el contenedor y la red.
- El builder se eliminó con `docker buildx rm verif-backend` y `docker buildx ls` quedó como al inicio, con `desktop-linux*` como actual.

Pasa.

## 5.2 Contenido y seguridad de la imagen

Comandos: `docker image inspect`, `docker run --rm --entrypoint /bin/sh ... ls -la /app; find ...`, `docker run -d --name verif-api`, `docker exec verif-api id -u`, `docker run -d --name verif-sinred --network none` y `docker run --rm --network container:verif-sinred curlimages/curl ...`.

Resultado:

- Tamaño: 153 780 543 bytes (146,7 MiB; 153,8 MB decimales; Docker Desktop lo muestra como 154 MB).
- `Config.User` es `app`, el entrypoint es `["/app/catalog-api"]` y el entorno contiene `HOST=0.0.0.0`, `PORT=8080`, `CATALOG_DB=/app/catalog.db` y `RUST_LOG=info`.
- `/app` contiene solo `catalog-api` (`-rwxr-xr-x`, 7 008 240 bytes) y `catalog.db` (`-r--r--r--`, 6 025 216 bytes). El `find` de `raw.db`, `*.zip`, `cargo`, `rustc`, `*.rs` y `Cargo.toml` no encontró nada.
- `docker exec verif-api id -u` devuelve `10001`, distinto de 0.
- Con el contenedor `verif-sinred` en `--network none`, el contenedor auxiliar que comparte su espacio de red recibe `200` en `http://127.0.0.1:8080/v1/sources`.
- `verif-api` y `verif-sinred` se detuvieron y eliminaron.

Pasa.

## 5.3 Apagado ordenado

Comandos: `docker run -d --name verif-stop boticario-backend`, espera de 1 s, `docker stop verif-stop` medido, `docker inspect ... .State.ExitCode`, `docker logs`.

Resultado:

- `docker stop` tardó 0,11 s, muy por debajo de los 10 s de gracia.
- Código de salida: 0.
- El log termina con `escuchando addr=0.0.0.0:8080 db=/app/catalog.db` y `apagado completado`.
- El contenedor se eliminó.

Pasa.

## 5.4 Caché

Comandos: `docker compose --progress=plain build` tres veces (sin cambios, con el cambio y tras revertir), con el builder normal (`desktop-linux`).

Resultado:

- Sin cambios: 1 s, los 10 pasos de etapa (`#9` a `#18`) aparecen `CACHED`, sin `Compiling`.
- Cambio temporal: se añadió `// verificación temporal 5.4` al final de `backend/catalog-api/src/main.rs`. La construcción tardó 1 s. El log muestra `Compiling catalog-api v0.1.0 (/src/backend/catalog-api)` y `Finished \`release\` profile [optimized] target(s) in 0.59s`. No aparece ninguna línea `Downloading`, `Downloaded` ni `descargado`. Los pasos de la etapa de catálogo (`COPY --from=build /out/catalog-ingest`, `COPY data/sources.toml` y `RUN catalog-ingest download ... && build`) salen `CACHED`, así que el ZIP ni siquiera se consultó y no hay línea de `download` que citar: el binario `catalog-ingest` no cambió.
- Reversión: `git checkout -- backend/catalog-api/src/main.rs`. `git status --short backend/` muestra solo los cambios previos ajenos a la tarea (`backend/Cargo.lock`, `backend/catalog-core/Cargo.toml`, `backend/README.md`, `backend/catalog-core/tests/`) y nada en `main.rs`.
- Construcción final: 1 s, los 10 pasos `CACHED`. La imagen `boticario-backend` queda alineada con el código real (id `5ebce24e02df`).

Pasa.

## 5.5 Workspace y OpenSpec

Desde `backend/`:

| Comando | Resultado |
|---|---|
| `mise exec -- cargo fmt --all --check` | código 0, sin diferencias |
| `mise exec -- cargo clippy --all-targets --workspace -- -D warnings` | sin avisos |
| `mise exec -- cargo test --workspace` | todos los grupos en `ok`: 157 pruebas pasan (58, 1, 1, 7, 6 y 84), 3 ignoradas (`real_catalog`, `asset_crosscheck`, `real_build`), 0 fallos |

Desde la raíz: `openspec validate add-backend-container --strict` devuelve `Change 'add-backend-container' is valid` (código 0).

Pasa.

## Observaciones

- `docker compose build` ignora el builder seleccionado con `docker buildx use`: con `--use` la primera construcción siguió usando `desktop-linux` y salió en 1 s con todo en caché. Para que compose usara el builder desechable hubo que exportar `BUILDX_BUILDER=verif-backend`. La construcción fría válida es la segunda.
- La indicación `--progress=plain` después de `build` provoca el aviso `--progress is a global compose flag, better use docker compose --progress xx build`; se usó como opción global.
- `docker buildx ls` muestra un builder `default` en error (`failed to connect to the docker API at unix:///var/run/docker.sock`), previo a esta verificación. El builder actual real es `desktop-linux`, así que la instrucción «volver a `default`» de la tarea 5.1 se cumplió volviendo a `desktop-linux`.
- `docker exec verif-api ps` falla porque la imagen no trae `ps`; es esperado (imagen mínima). El usuario se comprobó con `id -u`.
- `docker image inspect` informa `Config.User` como `app` (nombre), no `10001`; el UID numérico se confirmó con `id -u`.
- El log de la construcción final y los intermedios no se guardan en el repositorio.
