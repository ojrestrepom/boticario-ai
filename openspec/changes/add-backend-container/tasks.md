# Tasks

## 1. Contexto de construcción e imagen

- [x] 1.1 Crear `.dockerignore` en la raíz que excluya `app/`, `.git/`, `docs/`, `openspec/`, `backend/target/`, `data/build/`, `data/.cache/`, `.claude/`, `.opencode/` y similares, sin excluir `backend/`, `data/migrations/`, `data/sources.toml` ni `Cargo.lock`; verificar con `docker build` (o `docker buildx build`) que el contexto transferido es pequeño y que la compilación encuentra `backend/` y `data/`.
- [x] 1.2 Crear el `Dockerfile` en la raíz con la etapa de compilación sobre la imagen oficial de Rust en la misma versión que `mise.toml`, que ejecute `cargo build --release --locked` de `catalog-ingest` y `catalog-api` con cachés de BuildKit para el registro y el git de cargo y para `target`, y copie los binarios fuera de la montura de caché; verificar que `docker build --target <etapa>` termina y que una segunda ejecución sin cambios reutiliza la caché.
- [x] 1.3 Añadir la etapa de catálogo que ejecuta `catalog-ingest download` y `catalog-ingest build` dentro de la construcción, con el ZIP en una caché de BuildKit para no descargarlo de nuevo, imprime el hash de contenido y deja `catalog.db` fuera de la montura; verificar que el log de construcción muestra el hash `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`, igual al de la construcción nativa.
- [x] 1.4 Añadir la etapa de runtime sobre `debian:bookworm-slim` con un usuario no root, solo el binario `catalog-api` y `catalog.db`, las variables `HOST=0.0.0.0`, `PORT=8080`, `CATALOG_DB` y `RUST_LOG=info`, `EXPOSE 8080` y `ENTRYPOINT` al binario, sin `HEALTHCHECK`; verificar con `docker run` que `/healthz` responde 200, que el proceso no corre como root y que la imagen no contiene `raw.db`, el ZIP, `cargo` ni código fuente.

## 2. Compose

- [x] 2.1 Crear `compose.yaml` en la raíz con el servicio `api` que construye la imagen desde la raíz y publica el puerto con `PORT` (por defecto 8080) en ambos lados, y pasa `PORT` y `RUST_LOG` al contenedor con valores por defecto; verificar con `docker compose config` y con `docker compose up --build` que `curl http://localhost:8080/healthz` responde 200 y que `PORT=9090 docker compose up` sirve en el 9090 y no publica el 8080.

## 3. Guardia de versión

- [x] 3.1 Añadir un test en `catalog-core` que lea `mise.toml` y el `Dockerfile` y falle, nombrando ambas versiones, si la versión de Rust de la imagen base no coincide con la de `mise.toml`, con la comparación en una función probada con casos de coincidencia, divergencia y formato inesperado; verificar con `cargo test --workspace`, y comprobar a mano que el test falla al alterar el pin en cualquiera de los dos archivos y pasa al restaurarlo.

## 4. Documentación

- [x] 4.1 Crear `backend/README.md` con el flujo de desarrollo nativo completo que hoy está en el README de la raíz (prerrequisitos con mise y compilador de C, construcción del catálogo con `download`, `build` y `rederive`, ejecución de la API y sus variables, regeneración del OpenAPI, verificación con fmt, clippy y tests incluidos los `--ignored`, y cambio de esquema con Diesel), una línea por párrafo o elemento y con las rutas ajustadas a su ubicación; verificar que no se pierde ningún comando del README antes de reescribirlo.
- [x] 4.2 Reescribir la sección «Backend: catálogo y API» del `README.md` de la raíz con solo Docker: prerrequisito, `docker compose up --build`, endpoints y `curl` de ejemplo, variables configurables (`PORT`, `RUST_LOG`), cómo ver el hash del catálogo en el log de construcción, cómo reconstruir y la opción `--platform linux/amd64`, con un enlace de una línea a `backend/README.md` para quien vaya a desarrollar el backend; actualizar el árbol de estructura del repo y el párrafo de CI, y mantener la regla de Markdown de una línea por párrafo; verificar con una búsqueda que el README de la raíz no contiene instrucciones de instalación de Rust, mise ni cargo.
- [x] 4.3 Revisar `docs/data/modelo-de-datos.md` y el resto de `docs/` y del README para que todos los enlaces y anclajes sigan siendo válidos y las referencias a comandos nativos apunten a `backend/README.md`; verificar comprobando cada enlace relativo y cada anclaje afectado.

## 5. Verificación de extremo a extremo y QA

- [x] 5.1 Verificar desde cero, con un builder aislado y desechable (`docker buildx create --name verif-backend --driver docker-container`, de modo que las cachés de capas y las monturas `type=cache` parten vacías; compose no obedece a `docker buildx use`, así que hay que fijar el builder con la variable de entorno `BUILDX_BUILDER=verif-backend` al construir; al terminar se elimina con `docker buildx rm verif-backend` y se vuelve al builder inicial que mostraba `docker buildx ls`, en Docker Desktop `desktop-linux`, sin tocar las cachés de otros proyectos), que `docker compose build` construye sin Rust, mise ni descargas manuales, y que `docker compose up` responde 200 en `/healthz` y devuelve datos reales en `/v1/plants?q=lavand` y `/v1/sources`; registrar el hash impreso y compararlo con `48d71b6b…`.
- [x] 5.2 Verificar el contenido y la seguridad de la imagen: sin `raw.db`, ZIP, `cargo` ni código fuente, proceso como usuario no root, y servicio de `/v1/sources` con el contenedor sin red; registrar el tamaño de la imagen.
- [x] 5.3 Verificar el apagado ordenado: `docker stop` termina el contenedor con código 0, sin esperar al cierre forzado, y el log contiene «apagado completado».
- [x] 5.4 Verificar la caché: una segunda construcción sin cambios reutiliza las capas, y un cambio trivial en un archivo Rust recompila sin volver a descargar el ZIP; revertir el cambio de prueba.
- [x] 5.5 Ejecutar `cargo fmt --all --check`, `cargo clippy --all-targets --workspace -- -D warnings` y `cargo test --workspace` desde `backend/`, y `openspec validate add-backend-container --strict`; verificar que todo queda en verde.
- [x] 5.6 Pasar QA sobre el cambio completo (arranque con un solo comando, configuración por entorno, documentación y enlaces), registrar el informe en `qa/` dentro del cambio y corregir los defectos hallados.

## 6. Correcciones tras la QA

- [x] 6.1 Reintento de descarga en el `Dockerfile`: si `catalog-ingest download` falla, se vacía `/data/.cache` y se ejecuta una vez más antes de `build`; verificar que `docker compose build` sigue imprimiendo el hash `48d71b6b…` y que, con un MD5 alterado sobre una caché válida, el log muestra el rechazo del ZIP cacheado, el borrado de la caché y la nueva descarga (la construcción termina fallando por el MD5 alterado, que es lo esperado).
- [x] 6.2 Apagado con tiempo máximo en `catalog-api` (`SHUTDOWN_GRACE`, función `serve` probada con tests de conexión inactiva y colgada, reproducción en Docker).
- [x] 6.3 Actualizar la spec delta `backend-container`, el delta nuevo de `catalog-api`, `proposal.md` y `design.md` con las correcciones de la QA y validar con `openspec validate --strict`.
- [x] 6.4 Repetir la QA de los casos afectados (CONT-04 con el reintento, CONT-09 con el escenario corregido, CONT-26 con el apagado forzado y CONT-12 normal) y actualizar `qa/container-results.md`.
- [x] 6.5 Bajar `SHUTDOWN_GRACE` a 2 s por DEF-03 (el plazo por defecto de `docker stop` en Docker 29 es de unos 3 s), actualizar specs y diseño, y verificar con `docker stop` sin `-t` que una conexión colgada termina con código 0 en unos 2 s.
