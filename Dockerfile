# Imagen del backend en tres etapas: compilación, catálogo y runtime.
# Contexto de construcción: la raíz del repo, porque hacen falta backend/ y data/
# (catalog-core embebe data/migrations al compilar y catalog-ingest lee data/sources.toml).
#
# Se separa en tres etapas para que el toolchain, el código fuente, el ZIP de USDA y
# raw.db (la capa cruda, que la API no lee) nunca lleguen a la imagen final.

# ---------------------------------------------------------------------------
# Etapa 1: compilación. La versión de Rust debe coincidir con mise.toml (un test lo vigila,
# por eso va literal y no como ARG). Misma distribución (bookworm) que el runtime para que
# la libc coincida. La imagen trae gcc, necesario para compilar SQLite embebido (bundled).
# ---------------------------------------------------------------------------
FROM rust:1.99.0-slim-bookworm AS build

WORKDIR /src
COPY backend/ backend/
COPY data/migrations/ data/migrations/

# Las monturas de caché de BuildKit conservan el registro de cargo y target entre construcciones
# (compilación incremental, sin volver a bajar crates). sharing=locked evita que dos
# construcciones escriban a la vez en las cachés de cargo. --locked impide que la
# construcción resuelva dependencias distintas a las de Cargo.lock.
# El contenido de una montura de caché no queda en la capa, así que los binarios se copian
# a /out dentro del mismo RUN.
RUN --mount=type=cache,id=boticario-cargo-registry,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,id=boticario-cargo-git,target=/usr/local/cargo/git,sharing=locked \
    --mount=type=cache,id=boticario-backend-target,target=/src/backend/target \
    cargo build --release --locked --manifest-path backend/Cargo.toml -p catalog-ingest -p catalog-api \
    && mkdir -p /out \
    && cp backend/target/release/catalog-ingest backend/target/release/catalog-api /out/

# ---------------------------------------------------------------------------
# Etapa 2: catálogo. Descarga el ZIP de USDA y construye catalog.db. Se hace al construir
# la imagen para que el contenedor sirva sin red y sin esperar al arrancar.
# No se instala ca-certificates: ureq usa rustls con webpki-roots (raíces incluidas en el binario).
# ---------------------------------------------------------------------------
FROM debian:bookworm-slim AS catalog

COPY --from=build /out/catalog-ingest /usr/local/bin/catalog-ingest
COPY data/sources.toml /data/sources.toml

# El ZIP vive en una montura de caché para no descargarlo en cada reconstrucción
# (download lo verifica por tamaño y MD5 y reutiliza uno válido). /data/build no es montura,
# así que catalog.db queda en la capa. build imprime el hash de contenido en el log.
#
# Reintento: download nunca sobrescribe un ZIP que no pasa la verificación (falla pidiendo borrarlo),
# y como el ZIP vive en una montura de caché el usuario no puede borrarlo a mano. Si cambian el MD5
# o el tamaño declarados, sin el reintento la construcción quedaría bloqueada hasta un
# `docker builder prune`. Por eso, si download falla, se vacía /data/.cache y se ejecuta una vez más;
# el ZIP nuevo se vuelve a verificar por tamaño y MD5, así que borrar la caché es seguro.
RUN --mount=type=cache,id=boticario-data-cache,target=/data/.cache,sharing=locked \
    { catalog-ingest download --data-dir /data \
      || { echo "download falló: se vacía /data/.cache y se reintenta una vez" >&2 \
           && find /data/.cache -mindepth 1 -delete \
           && catalog-ingest download --data-dir /data; }; } \
    && catalog-ingest build --data-dir /data

# ---------------------------------------------------------------------------
# Etapa 3: runtime. Solo el binario de la API y catalog.db, con un usuario sin privilegios.
# ---------------------------------------------------------------------------
FROM debian:bookworm-slim AS runtime

RUN useradd --system --uid 10001 --user-group --no-create-home app

COPY --from=build --chmod=0755 /out/catalog-api /app/catalog-api
COPY --from=catalog --chmod=0444 /data/build/catalog.db /app/catalog.db

# HOST=0.0.0.0: dentro de un contenedor, 127.0.0.1 haría la API inalcanzable desde fuera.
ENV HOST=0.0.0.0 \
    PORT=8080 \
    CATALOG_DB=/app/catalog.db \
    RUST_LOG=info

EXPOSE 8080
USER app

# Sin HEALTHCHECK: la imagen no lleva curl ni otras herramientas; /health queda para sondas externas.
# Forma exec: el binario es PID 1 y recibe SIGTERM directamente (apagado ordenado).
ENTRYPOINT ["/app/catalog-api"]
