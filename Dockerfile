# Imagen del backend en tres etapas: compilación, catálogo y runtime.
# Contexto de construcción: la raíz del repo, porque hacen falta backend/ y data/
# (catalog-core embebe data/migrations al compilar y catalog-ingest lee la semilla de data/seed/).
#
# Se separa en tres etapas para que el toolchain, el código fuente y la semilla
# (data/seed/) nunca lleguen a la imagen final. La semilla solo entra en la etapa del catálogo,
# no en la de compilación, así que un cambio en la semilla no recompila la API.

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
# Etapa 2: catálogo. Construye catalog.db desde la semilla de data/seed/, sin red: la etapa
# no descarga nada ni necesita certificados. Se hace al construir la imagen para que el
# contenedor sirva sin red y sin esperar al arrancar.
# ---------------------------------------------------------------------------
FROM debian:bookworm-slim AS catalog

COPY --from=build /out/catalog-ingest /usr/local/bin/catalog-ingest
COPY data/seed/ /data/seed/

# build verifica la semilla (tipos, manifiesto y hashes) y falla si un registro no coincide,
# lo que detiene la construcción de la imagen. Imprime el hash de contenido en el log, que debe
# ser igual al de una construcción nativa de la misma semilla. catalog.db queda en la capa.
# --network=none hace que la construcción falle si algo intentara salir a la red.
RUN --network=none catalog-ingest build --data-dir /data

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
