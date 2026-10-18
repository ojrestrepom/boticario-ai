# Design

## Context

Véanse `proposal.md` y las specs delta (`backend-ci`, `backend-deployment`, `catalog-api`) para los requisitos observables. Estado de partida, comprobado en este repositorio el 2026-10-17:

- **Despliegue sin puerta.** `.github/workflows/deploy-backend.yml` tiene un único job `deploy` (build, push, deploy y verificación con `curl`), con `permissions: contents: read` e `id-token: write` a nivel de workflow, `concurrency: deploy-backend` sin cancelación y `timeout-minutes: 45`. Se dispara en `push` a `main` con `paths` y en `workflow_dispatch`. El diseño archivado `openspec/changes/archive/2026-10-16-deploy-backend-cloud-run/design.md` dejó anotado el riesgo («sin `cargo test` previo, un backend roto puede desplegarse») y la CI del backend como cambio posterior.
- **CI de referencia.** `.github/workflows/flutter.yml` corre en `push` y `pull_request` con `paths`, permisos `contents: read`, concurrency con cancelación (`flutter-ci-${{ github.workflow }}-${{ github.ref }}`), `timeout-minutes: 20` y acciones fijadas por SHA con comentario de versión.
- **Toolchain.** `mise.toml` fija `[tools] rust = "1.99.0"` como cadena simple. El `Dockerfile` usa `rust:1.99.0-slim-bookworm`. La prueba `backend/catalog-core/tests/toolchain_pin.rs` lee `mise.toml` y `Dockerfile` desde el repositorio y falla si divergen; obtiene `tools.rust` con `as_str()` (función `mise_rust_version`, al inicio del archivo), así que la clave debe seguir siendo una cadena y no una tabla `{ version, components }`.
- **Logs.** `backend/catalog-api/src/main.rs:35-39` llama a `tracing_subscriber::fmt()` con `EnvFilter` y sin tocar ANSI. `tracing-subscriber` es la 0.3.23 (`backend/Cargo.lock`) con la feature `env-filter` añadida a las predeterminadas (`backend/Cargo.toml:33`).

### Resultados medidos del estado actual del backend

Ejecutados desde `backend/` con `mise exec -- cargo …` (Rust 1.99.0, macOS arm64, Apple Silicon):

| Verificación | Resultado | Tiempo |
| --- | --- | --- |
| `cargo fmt --check` | pasa, sin diferencias | menos de 1 s |
| `cargo clippy --workspace --all-targets --locked -- -D warnings` | pasa, sin advertencias | 0,3 s con `target/` caliente; 8 s con un `CARGO_TARGET_DIR` vacío |
| `cargo test --workspace --locked` | pasa: 63 pruebas en catalog-api, 13 en catalog-core y 84 en catalog-ingest; 3 ignoradas | 4 s caliente; 11 s compilando las pruebas sobre la caché de dependencias que dejó clippy, y 2 s en la ejecución siguiente |

Notas sobre esas cifras: la medición «en frío» usó un directorio de destino vacío en la carpeta temporal de la sesión; no es representativa de un runner de GitHub (2 vCPU, disco compartido), donde una compilación sin caché tardará bastante más. El primer run real de la CI es la medición que cuenta y queda como tarea. Como fmt, clippy y test pasan hoy, no hay nada que arreglar antes de activar la puerta.

### Qué necesitan las pruebas

- **Red:** ninguna prueba normal la usa. El único literal de red en `backend/*/tests` es una URL dentro del fixture JSON `catalog-ingest/tests/fixtures/plant_catalog.json`, que no se descarga.
- **Dataset descargado:** las tres pruebas que necesitan `data/build/` (`catalog-api/tests/real_catalog.rs:12`, `catalog-ingest/tests/real_build.rs:21` y `catalog-ingest/tests/asset_crosscheck.rs:21`) están marcadas `#[ignore]`, y `cargo test` las cuenta como ignoradas (3 en total). Se ejecutan a mano con `--ignored`, como indican sus comentarios.
- **Docker:** ninguna prueba lo usa.
- **Archivos fuera de `backend/`:** `catalog-core/tests/toolchain_pin.rs` lee `Dockerfile` y `mise.toml` de la raíz, y `catalog-core/build.rs:5` (`cargo:rerun-if-changed=../../data/migrations`) junto con las migraciones embebidas necesitan `data/migrations/` en tiempo de compilación. Basta con el checkout completo del repositorio; ningún archivo ignorado por git es necesario.
- **Deriva de `backend/openapi.json`:** ya existe la prueba `versioned_document_matches_the_generated_one` (`backend/catalog-api/src/openapi.rs:58-65`) que compara el archivo versionado con `openapi_json()` y explica cómo regenerarlo. Se ejecuta en `cargo test --workspace`.

## Goals / Non-Goals

**Goals:**

- Que un backend que no pase formato, lint o pruebas no llegue a Cloud Run, con una sola definición de las verificaciones.
- Que la CI use exactamente el Rust de `mise.toml`, sin repetir la versión.
- Logs de la API en texto plano en Cloud Run, con colores en una terminal local, cubierto por pruebas automatizadas.

**Non-Goals:**

- Autenticación o límite de tasa de la API (otro cambio).
- Logs JSON estructurados, auditoría de dependencias (`cargo audit`/`deny`), cobertura, protección de ramas, entornos de GitHub con aprobación.
- Ejecutar en CI las pruebas ignoradas que necesitan el dataset.
- Cambiar la política de caché de Docker o el `Dockerfile`.

## Decisions

### 1. Qué verifica la CI: formato, clippy y pruebas; sin paso aparte para OpenAPI

Tres pasos, en este orden y desde `backend/`: `mise exec -- cargo fmt --check`, `mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings` y `mise exec -- cargo test --workspace --locked`. El orden va de lo más barato a lo más caro, para fallar rápido. `--locked` evita que la CI resuelva dependencias distintas a las del `Cargo.lock` versionado.

La deriva de `openapi.json` ya la cubre una prueba del workspace (hecho citado en el contexto), así que un paso aparte (regenerar con `--openapi` y hacer `git diff --exit-code`) duplicaría la comprobación y compilaría el binario otra vez. Se deja a `cargo test`, y la spec `backend-ci` lo exige como escenario para que no se pierda si alguien borra la prueba.

Alternativas descartadas: añadir `cargo audit`/`cargo deny` (útil, pero amplía el alcance y trae falsos positivos que bloquearían despliegues; mejor un cambio propio); `cargo build --release` (la construcción de la imagen ya lo hace); medir cobertura (sin objetivo definido); `cargo test --include-ignored` (necesitaría descargar el ZIP de USDA de unos 100 MB y construir el catálogo: minutos y red en cada ejecución).

### 2. Un workflow reutilizable que `deploy-backend.yml` invoca con `needs`

Nuevo `.github/workflows/backend-ci.yml` con tres disparadores: `workflow_call`, `pull_request` (con `paths`) y `push` con `branches-ignore: [main]` (con `paths`). `deploy-backend.yml` añade un job `verify` con `uses: ./.github/workflows/backend-ci.yml` y `permissions: contents: read`, y el job `deploy` pasa a tener `needs: verify`. Así:

- La definición vive en un solo archivo y no se puede olvidar la verificación en ninguna de las dos rutas.
- En `main`, el `push` solo dispara `deploy-backend.yml` (la CI excluye `main` en su propio `push`), de modo que no hay doble ejecución. En ramas y pull requests, el despliegue no corre (ya está limitado a `main`) y la CI sí.
- `workflow_dispatch` del despliegue también pasa por `verify`, lo que cumple el escenario «Ejecución manual».
- Una referencia local (`./.github/workflows/…`) usa el mismo commit que el llamador, así que no hay SHA que fijar ni versiones que desincronizar, y el SHA verificado es el que se construye.

**Permisos.** Un workflow reutilizable no puede ganar permisos que el llamador no concede. Hoy `deploy-backend.yml` los declara a nivel de workflow; el cambio los baja a `permissions: contents: read` a nivel de workflow, declara `contents: read` en el job `verify` y `contents: read` más `id-token: write` en el job `deploy`. Así el job de pruebas nunca puede pedir un token OIDC.

**Concurrency.** `deploy-backend.yml` mantiene `deploy-backend` sin cancelar. `backend-ci.yml` declara su propio grupo con un literal, `backend-ci-${{ github.ref }}`, porque dentro de un workflow llamado `github.workflow` es el nombre del llamador y reutilizar el patrón de `flutter.yml` podría chocar con el grupo del llamador. Con `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}` se cancelan las ejecuciones obsoletas de ramas y pull requests (como `flutter.yml`), pero en `main` nunca se cancela una verificación que forma parte de un despliegue en curso. Por confirmar en la implementación: que GitHub aplique el `concurrency` del workflow llamado cuando se invoca con `workflow_call` y que la expresión de `cancel-in-progress` se evalúe como se espera (documentación de reutilización: https://docs.github.com/en/actions/using-workflows/reusing-workflows). Si no, el respaldo es mover el grupo a un nivel de job o dejar solo el de `push`/`pull_request`.

**Paths.** `backend/**`, `data/migrations/**`, `Dockerfile`, `mise.toml` y el propio workflow. `data/migrations/` entra porque las migraciones se compilan dentro del binario; `Dockerfile` y `mise.toml` entran porque los lee `toolchain_pin.rs`. `data/sources.toml` y `.dockerignore` no: ninguna prueba normal los lee y, si cambian, el despliegue de `main` pasa por `verify` igualmente. En el despliegue se añade `mise.toml` a los `paths` para que un cambio del toolchain en `main` ejecute la guarda de versión (si no, un `push` directo solo de `mise.toml` no dispararía nada).

Alternativas descartadas:

- **Dos workflows independientes, uno de CI en todas las ramas incluida `main` y otro de despliegue con `workflow_run`.** Dispara el despliegue tras la CI, pero `workflow_run` corre con el contexto de la rama por defecto, hay que reconstruir el SHA desde `workflow_run.head_sha` y se pierde la garantía de que el SHA verificado es el construido.
- **Copiar los pasos de verificación dentro de `deploy-backend.yml`.** Es lo más simple, pero duplica la definición con la CI de ramas y pull requests: se desalinean con el tiempo.
- **Verificar en el mismo job que despliega.** Mezcla `id-token: write` con la ejecución de código de pruebas y alarga el job crítico; descartado por seguridad y claridad.
- **Una acción compuesta (`composite action`) en lugar de un workflow reutilizable.** Compartiría los pasos, pero no el job: cada llamador repetiría el runner, los permisos, el timeout y la caché, y `needs` no aplicaría a pasos.
- **Dejar que la CI corra también en `push` a `main` y que el despliegue no la llame.** Dos ejecuciones por `push` a `main` y sin garantía de orden: el despliegue podría salir antes de que la CI falle.

### 3. Toolchain: `jdx/mise-action` instala el Rust de `mise.toml`

El job usa `jdx/mise-action` (v5.2.0, commit `9b200bcecbfd6303e69a4a261b2e09e3757440a7`, obtenido con `gh api repos/jdx/mise-action/releases/latest` y `git/ref/tags/v5.2.0`) con la instalación por defecto (`install: true`), que ejecuta `mise install` sobre el `mise.toml` de la raíz. Los comandos se lanzan con `mise exec -- cargo …`, igual que en local y en `backend/README.md`. Efectos:

- La versión sale de un único archivo. `toolchain_pin.rs` ya vigila `mise.toml` frente al `Dockerfile`, así que los tres coinciden y la guarda corre dentro de esta misma CI.
- `mise` instala Rust a través de `rustup` y selecciona el toolchain con `RUSTUP_TOOLCHAIN` (observado localmente: `rustup show` informa «active because: overridden by environment variable RUSTUP_TOOLCHAIN»), por lo que el Rust preinstalado del runner no se usa. Fuente: https://mise.jdx.dev/lang/rust.html.
- **Componentes.** La misma página documenta el perfil `minimal` (rustc, rust-std, cargo) frente a `default` (añade rustfmt y clippy) y que, sin `profile`, mise usa el perfil configurado de rustup. Localmente clippy y rustfmt están instalados (`rustup component list --installed`); en el runner no se da por supuesto. Para no convertir `tools.rust` en una tabla (lo que rompería `toolchain_pin.rs`), el workflow ejecuta un paso explícito `mise exec -- rustup component add rustfmt clippy`, idempotente y barato, justo después de instalar.
- Por defecto `mise-action` cachea el propio mise (`cache: true`) y, con `version` sin fijar, instala el release más reciente de al menos 24 h de antigüedad (`action.yml` y README de la acción). Se acepta que mise se mueva: la versión que importa, la de Rust, está fijada por `mise.toml`.

Por confirmar en el primer run: que `mise` confíe en el `mise.toml` del checkout sin pasos extra (si pidiera confianza, se resuelve con `MISE_TRUSTED_CONFIG_PATHS` o `mise trust`) y que el compilador efectivo sea 1.99.0 (el job ejecuta `mise exec -- rustc --version` para dejarlo en el log).

Alternativas descartadas: `dtolnay/rust-toolchain` o `rustup toolchain install` con la versión escrita en el workflow (duplica la versión, y la guarda `toolchain_pin.rs` no la vigilaría); extraer la versión de `mise.toml` con un script de shell y pasarla a `rustup` (sin dependencia nueva, pero hay que mantener el parser, y la ruta diverge de la local); usar el Rust del runner (versión que cambia sin aviso).

### 4. Caché de compilación con `Swatinem/rust-cache`

Un paso `Swatinem/rust-cache` (v2.9.2; el tag `v2.9.2` es un objeto de tag anotado, `63fed3e2…`, que se dereferencia al commit `6323deb102c322ba6fcbdcafc7e3dddab59af2b6`; este último es el SHA que se fija) con `workspaces: backend` y `save-if: ${{ github.ref == 'refs/heads/main' }}` (la entrada `save-if` existe en su README: https://github.com/Swatinem/rust-cache). La acción cachea el registro de Cargo y `target/` con una clave que incluye la versión de `rustc` y el `Cargo.lock`. Guardar solo desde `main` evita llenar el límite de 10 GB de caché por repositorio con una entrada por rama: las ramas restauran la de `main` y no la escriben. Como las verificaciones de `main` van dentro del despliegue, la caché se actualiza en cada despliegue.

Riesgo: el límite de 10 GB lo comparten esta caché, la de mise y la `type=gha` de Docker (`cache-to: type=gha,mode=max` del despliegue). Si el espacio se agota, GitHub expulsa lo menos usado; el coste es tiempo, no corrección.

Alternativas descartadas: sin caché (más simple, pero cada verificación recompila el árbol de dependencias desde cero); `actions/cache` a mano (hay que acertar con claves y rutas de `target/`, que `rust-cache` ya resuelve); `sccache` (otra herramienta y otro almacenamiento para ahorrar poco con este tamaño de proyecto).

### 5. Detalles del workflow de CI

- Runner `ubuntu-24.04`, el mismo que los otros workflows.
- `timeout-minutes: 20`, como Flutter; se ajusta con el primer run real.
- Variables de entorno del job: `CARGO_INCREMENTAL: 0` (la compilación incremental no ayuda en un runner efímero y engorda la caché) y `CARGO_TERM_COLOR: always` (el visor de Actions interpreta ANSI y facilita leer los errores; no tiene relación con los logs de la API).
- `actions/checkout` con `persist-credentials: false`, en el mismo SHA que el resto (`3d3c42e5aac5ba805825da76410c181273ba90b1`, v7.0.1, confirmado como última versión con `gh api repos/actions/checkout/releases/latest`).
- `working-directory: backend` para los comandos de Cargo.
- Un solo job con los tres pasos de verificación en serie: más barato que tres jobs que reinstalan y reconstruyen.

### 6. Logs sin ANSI: decidir con terminal y `NO_COLOR`

Hechos verificados en el código de `tracing-subscriber 0.3.23` (`~/.cargo/registry/src/index.crates.io-*/tracing-subscriber-0.3.23`):

- La feature `ansi` es predeterminada (`Cargo.toml`: `default = ["smallvec", "fmt", "ansi", "tracing-log", "std"]`), y `fmt::Layer::default` activa ANSI si la feature está y `NO_COLOR` no está definida o está vacía (`src/fmt/fmt_layer.rs:741-743`). No hay detección de terminal: por eso Cloud Run recibe ANSI.
- `with_ansi(bool)` fuerza el valor y, según su documentación (`src/fmt/fmt_layer.rs:305-314`), `with_ansi(true)` sobrescribe `NO_COLOR`. Existe también en `SubscriberBuilder` (`src/fmt/mod.rs:633`).
- `std::io::IsTerminal` (estable desde Rust 1.70) permite preguntar `std::io::stdout().is_terminal()`.

**Decisión:** ANSI solo si stdout es una terminal **y** `NO_COLOR` no tiene valor no vacío. Se implementa con `.with_ansi(use_ansi(...))` sobre el builder actual. Hay que reproducir a mano la regla de `NO_COLOR` porque pasar `with_ansi(true)` al detectar la terminal la saltaría. La decisión va en una función pura, p. ej. `fn use_ansi(stdout_is_terminal: bool, no_color: Option<&str>) -> bool`, para probarla sin tocar el entorno global; `main` solo le pasa `std::io::stdout().is_terminal()` y `std::env::var("NO_COLOR")`. Es el comportamiento que propone https://no-color.org/ y conserva los colores en `cargo run` local.

**Pruebas:**

- Unitaria de `use_ansi` con la tabla de combinaciones (terminal sí/no × `NO_COLOR` ausente/vacía/`1`).
- De integración: lanza el binario compilado (`env!("CARGO_BIN_EXE_catalog-api")`) con stdout redirigido a una tubería, sobre una base de fixture (la que construye `fixture_end_to_end.rs`), lee hasta la línea «escuchando», comprueba que no contiene `\x1b`, y termina el proceso. Una terminal real no es portable en CI, así que la combinación «terminal con colores» queda cubierta solo por la prueba unitaria.
- La comprobación en Cloud Logging tras el despliegue queda como verificación final del orquestador.

**Impacto en compose:** `docker compose up` sin TTY asignado también emite texto plano; con TTY, conserva los colores. Es un efecto aceptado.

Alternativas descartadas:

- **Solo `with_ansi(false)` siempre.** Lo más simple y suficiente para Cloud Run, pero quita los colores en local, donde ayudan.
- **Solo `NO_COLOR=1` en el servicio de Cloud Run.** No toca el código, pero el comportamiento depende de configurar cada entorno y no hay prueba en el repositorio; la imagen seguiría emitiendo ANSI en cualquier otro destino sin terminal.
- **Solo detección de terminal.** Cubre Cloud Run, pero ignora `NO_COLOR` en terminales locales donde el usuario lo pide.
- **Logs JSON estructurados** (feature `json` de `tracing-subscriber`, presente en 0.3.23). Cloud Logging indexa mejor los campos de un `jsonPayload`, pero la severidad y el mensaje se leen de claves concretas (`severity` y `message`, según la documentación de logs estructurados de Cloud Logging, que no se pudo consultar en esta sesión y debe confirmarse antes de adoptarlo), mientras que el formateador JSON de `tracing-subscriber` emite `level` y `fields.message`. Hacerlo bien exige un formateador propio o una dependencia nueva, cambia el formato local y amplía el alcance. Con un solo servicio y pocos logs, el texto plano es suficiente. Se deja como mejora futura si se necesita filtrar por campos.

## Risks / Trade-offs

- [Una CI frágil o lenta bloquea despliegues urgentes] → El workflow se puede relanzar; el `timeout-minutes: 20` evita cuelgues; el rollback de Cloud Run sigue disponible sin pasar por la CI.
- [Cambios en las acciones de terceros rompen la puerta] → Acciones fijadas por SHA; su actualización periódica queda fuera de alcance.
- [Un `push` a `main` con cambios solo en `docs/` o `app/` no ejecuta ninguna verificación del backend] → Es el comportamiento deseado; la CI de Flutter cubre la app.
- [Las pruebas ignoradas que necesitan el dataset no corren en CI] → Son tres y ya existían así. El despliegue sigue verificando `/v1/plants/lavandula-angustifolia` después de publicar.
- [El primer run de CI es más lento de lo esperado o la caché se desborda] → Se mide en la verificación final y se ajustan `timeout-minutes` y `save-if`.
- [La puerta depende de que `verify` exista siempre en `deploy-backend.yml`] → La spec `backend-deployment` lo hace un requisito y el escenario «Verificaciones fallidas» se demuestra en una rama temporal (grupo 4 de las tareas).
- [`NO_COLOR` definido en una terminal desactiva los colores] → Es lo que el estándar pide.
- [La prueba de integración de logs puede ser inestable si el binario tarda en arrancar] → Espera con un plazo explícito y, si vence, falla con lo capturado en el mensaje.
- [El escenario «Acciones fijadas» de `backend-deployment` habla de «los permisos del job» (`contents: read` e `id-token: write`)] → Sigue siendo cierto para el job `deploy`; el job `verify` tiene permisos menores y se rige por `backend-ci`. No se modifica ese requisito.
- [`push` directo a `main`: la CI no puede impedirlo, solo impedir el despliegue] → El código roto llega a `main` pero no a Cloud Run. La protección de rama queda fuera de alcance.

## Migration Plan

1. Integrar la CI y la puerta (grupos 1 y 2 de las tareas) antes del cambio de logs, de modo que el despliegue de este último ya pase por las verificaciones.
2. Sin migración de datos ni de infraestructura; el `Dockerfile` y GCP no cambian.
3. Rollback: revertir el commit del workflow devuelve el despliegue sin puerta; el cambio de logs se revierte aparte. Una revisión de Cloud Run mala se revierte con el runbook existente de `docs/deploy/cloud-run.md`.
