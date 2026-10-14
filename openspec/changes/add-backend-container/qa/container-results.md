# Resultados de QA: add-backend-container

Fecha: 2026-10-13 (ronda 1) y 2026-10-14 (rondas 2 y 3, tras las correcciones). Plan: [`test-plan-container.md`](test-plan-container.md). Evidencias resumidas en [`evidence/`](evidence/) (`CONT-*.txt`).

## Entorno

- macOS en Apple Silicon (arm64), Docker Engine 29.8.2, Docker Compose v5.6.0, BuildKit v0.33.1 (builder `desktop-linux`), mise 2026.10.9 con Rust 1.99.0.
- Imagen bajo prueba: `boticario-backend` (arm64, 154 MB), construida desde el repo en su estado actual sin confirmar (`git status`: `Dockerfile`, `compose.yaml`, `.dockerignore`, `backend/README.md`, `toolchain_pin.rs` sin versionar).
- Herramientas: `curl`, Python 3 (comprobador de enlaces y cliente de sockets, en el scratch), `docker`, `docker buildx`. Se descargó la imagen `curlimages/curl` (para el caso sin red) y se eliminó al terminar. No se instaló nada en el proyecto.
- Sin Postman ni Playwright: la API es de solo lectura, sin credenciales ni interfaz web, y `curl` basta.

## Resumen

39 casos: 39 PASS, 0 FAIL, 0 NOT RUN. No queda ningún defecto abierto.

- Ronda 1: 30 casos, 28 PASS y 2 FAIL (CONT-09, defecto conocido, y CONT-26, defecto nuevo).
- Ronda 2: se repitieron CONT-09, CONT-12, CONT-26 y CONT-13, y se añadieron CONT-31 a CONT-39 por los escenarios nuevos. CONT-09 y CONT-30 pasaron; CONT-26 siguió fallando por otra causa (DEF-03: `SHUTDOWN_GRACE` de 5 s mayor que los ~3 s que `docker stop` concede en este Docker).
- Ronda 3 (`SHUTDOWN_GRACE` de 2 s): se repitieron CONT-12, CONT-26, CONT-31, CONT-32, CONT-33 y CONT-34. CONT-26 pasa con `docker stop` sin opciones.
- Los demás casos de la ronda 1 no se repitieron en el código final salvo lo que cubren CONT-38 y CONT-39 (construcción en frío, workspace, enlaces, guardia de versión).
- DEF-01 resuelto por la corrección de la spec, DEF-02 y DEF-03 corregidos y verificados, OBS-02 resuelta.

## Resultados por caso

| ID | Resultado | Evidencia resumida |
|---|---|---|
| CONT-01 | PASS | Con `--network none` (solo `lo`), `GET /v1/sources` devuelve 200 con la fuente `usda` y `/v1/plants?q=lavand` 200; `https://example.com` desde ese espacio de red falla (000). `evidence/CONT-runtime.txt` |
| CONT-02 | PASS | `/app` solo tiene `catalog-api` (rwxr-xr-x) y `catalog.db` (r--r--r--); el `find` no encuentra `raw.db`, ZIP, `cargo`, `rustc`, `*.rs`, `*.toml`, `catalog-ingest` ni `sources.toml`; no existen `/src`, `/data` ni `/usr/local/cargo`. `docker history` solo muestra `useradd`, los dos `COPY`, `ENV`, `USER` y `ENTRYPOINT` |
| CONT-03 | PASS | Hash de la construcción (arm64, limpia, `--no-cache` y amd64) y nativo: `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`. Además, el `catalog.db` de la imagen, el nativo y `data/build/catalog.db` tienen el mismo SHA-256 (`3b784dc1...01dd`). `evidence/CONT-hash-*.txt` |
| CONT-04 | PASS | Con MD5 declarado `000...0`: `error: checksum MD5 distinto del declarado: se esperaba 000... y se obtuvo 45ae44a0...`; con tamaño declarado 6033991: `error: tamaño distinto del declarado: se esperaban 6033991 bytes y hay 6033990`. Ambas construcciones salen con código 1 en la etapa de catálogo y no crean imagen (`docker images -q` vacío; `boticario-backend` no cambió). Ver OBS-02. `evidence/CONT-insumo-alterado.txt` |
| CONT-05 | PASS | Builder desechable sin cachés: `docker compose build` termina con código 0 en 36,8 s, 153 líneas `Compiling`, `usda: descargado y verificado`, `plantas: 2376`, hash esperado. Salvedad: el anfitrión de la prueba tiene Rust y mise instalados; la prueba demuestra que la construcción no los usa (el contexto excluye `target/`, `data/.cache` y `data/build`, y una exportación de git sin esos directorios da el mismo contexto, CONT-21), pero no se probó en una máquina sin ellos. `evidence/CONT-hash-build-limpia.txt` |
| CONT-06 | PASS | `docker compose up --build -d` y `GET /healthz`: 200 `{"status":"ok"}` |
| CONT-07 | PASS | `/v1/plants?q=lavand`: 200, 7 plantas (`lavandula-angustifolia`, `lavandula-latifolia`, ...); `/v1/plants?limit=1`: total 2376; `/v1/sources`: 200 (USDA, CC0). Adicionales: `/v1/plants/nope` 404, `limit=0` 400, `POST /healthz` 405 con `allow: GET`, `/openapi.json` 200 |
| CONT-08 | PASS | `PORT=9090 docker compose up -d`: `0.0.0.0:9090->9090/tcp`, `:9090/healthz` 200, `:8080/healthz` sin conexión, log `addr=0.0.0.0:9090`. `docker compose down` sin `PORT` también limpia |
| CONT-09 | PASS | Escenario corregido (ronda 2): con `RUST_LOG=warn` el log tiene 0 líneas y 0 «escuchando»; con el valor por defecto tiene 2 líneas, 1 «escuchando» y 1 «apagado completado». En la ronda 1, con el escenario antiguo, fallaba (DEF-01, resuelto por la corrección de la spec). `evidence/CONT-ronda2.txt` |
| CONT-10 | PASS | Ronda 1 (no repetido): `error` deja el log vacío; con `info` y `debug` hay 2 líneas INFO y 0 DEBUG; con `trace` aparecen 7 líneas TRACE de `axum::serve`. Ya no es un escenario de la spec |
| CONT-11 | PASS | `docker top`: usuario/UID 10001, `/app/catalog-api` es el PID 1, `CapEff` 0; `Config.User` es `app`. Descriptores de `catalog.db`: flags `02500000` (O_RDONLY). Un `echo >> /app/catalog.db` falla con `Permission denied` |
| CONT-12 | PASS | Repetido en las rondas 2 y 3 con la imagen final (ronda 3: 0,12 s, código 0, «escuchando» y «apagado completado»): `docker stop` 0,13 s, `ExitCode=0` y el log con las dos líneas. Ronda 1: `docker stop`: 0,13 s, `ExitCode=0`, `OOMKilled=false`, log `INFO catalog_api: apagado completado`. Con `docker compose up` en primer plano y `docker compose stop`: `api-1 exited with code 0` |
| CONT-13 | PASS | `docker compose build` sin cambios: 10 pasos `CACHED`, 0 `Compiling`, 0 descargas, 0,6 s en la copia y 1 s en el repo |
| CONT-14 | PASS | Cambio en `catalog-api/src/main.rs`: `Compiling catalog-api`, `Finished ... in 0.57s`, sin `descargado`. Cambio en `catalog-ingest` (el binario cambia): se repite la etapa de catálogo y dice `usda: ya estaba y está verificado`, sin descarga. Cambio en `catalog-core` (comentario): recompila, el binario de ingesta no cambia y la etapa de catálogo sigue en caché. Tras restaurar el archivo en el repo, vuelve a 10 pasos `CACHED`. `evidence/CONT-cache.txt` |
| CONT-15 | PASS | El README no tiene instrucciones de instalación de Rust, mise ni cargo; las 7 menciones son descriptivas (estado, estructura, enlace a `backend/README.md`). La sección «Backend: catálogo y API» cubre Docker, `docker compose up --build`, endpoints, variables (`PORT`, `RUST_LOG`), hash, reconstruir y parar, y un único enlace a `backend/README.md` |
| CONT-16 | PASS | `backend/README.md` tiene seis secciones: prerrequisitos con mise, construir el catálogo, ejecutar la API, contrato OpenAPI, verificación y cambiar el esquema. Los comandos y la tabla de variables son idénticos a la sección antigua del README en `HEAD`. El comando de regeneración del OpenAPI produce un archivo igual a `backend/openapi.json` |
| CONT-17 | PASS | 93 enlaces relativos y anclajes en 9 archivos (`README.md`, `backend/README.md`, `docs/**/*.md`), 0 rotos. El comprobador detecta 3 de 3 roturas sembradas en un control negativo. `evidence/CONT-docs-y-guardia.txt` |
| CONT-18 | PASS | `cargo test -p catalog-core --test toolchain_pin`: 6 pruebas ok |
| CONT-19 | PASS | `mise.toml` en 1.98.0: `la versión de Rust difiere: mise.toml fija 1.98.0 y el Dockerfile usa 1.99.0`; `Dockerfile` en 1.98.0: `mise.toml fija 1.99.0 y el Dockerfile usa 1.98.0`. Ambos archivos restaurados (SHA-1 idéntico al respaldo; `git diff --stat mise.toml Dockerfile` vacío) |
| CONT-20 | PASS | Tocar `README.md`, `compose.yaml`, `openspec/`, `docs/` y `app/`: 10 pasos `CACHED` |
| CONT-21 | PASS | Exportación de los archivos versionables (más los nuevos sin versionar) construida con el builder desechable: 10 pasos `CACHED`, contexto idéntico al del repo |
| CONT-22 | PASS | `HOST=127.0.0.1` en el anfitrión no cambia nada (`addr=0.0.0.0:8080`, 200); `PORT=` vacío usa 8080; `PORT=80` sirve sin root (200); `PORT=abc` y `PORT=70000` fallan en Compose con `invalid containerPort` y no dejan contenedor |
| CONT-23 | PASS | `--read-only --cap-drop ALL --security-opt no-new-privileges`: `/healthz` 200 y `/v1/plants?q=lav` 200 |
| CONT-24 | PASS | Base ausente: `no se pudo arrancar: no existe la base del catálogo en /nope.db`, salida 1. `PORT=abc`: `error de configuración: PORT inválido`, salida 2 |
| CONT-25 | PASS | Con una conexión keep-alive inactiva abierta, `docker stop` tarda 0,13 s, salida 0 y «apagado completado» |
| CONT-26 | PASS | Escenario «Conexión colgada» con `docker stop` sin `-t`, ronda 3 con `SHUTDOWN_GRACE` de 2 s: 2,15 s, 2,15 s y 2,16 s en tres repeticiones, siempre código 0 y `OOMKilled=false`; el log tiene `INFO ... escuchando`, `WARN catalog_api: se fuerza el apagado: quedaban conexiones abiertas tras 2 s grace_secs=2` e `INFO catalog_api: apagado completado`. `docker compose stop` 2,19 s con código 0 y las mismas líneas; `docker compose down` 2,33 s. Con el plazo de 5 s (ronda 2) fallaba con 137 a los ~3,15 s (DEF-03, corregido); en la ronda 1 fallaba porque la API esperaba sin límite (DEF-02, corregido). `evidence/CONT-ronda2.txt` |
| CONT-27 | PASS | `docker build --platform linux/amd64 .` (comando del README) termina en 66 s con el mismo hash; el contenedor `x86_64` sirve `/healthz` 200 y sale con 0 al detenerlo. `evidence/CONT-hash-nativo-y-amd64.txt` |
| CONT-28 | PASS | Con caché, `docker compose --progress=plain build` no imprime línea `hash:` (10 `CACHED`); `docker compose --progress=plain build --no-cache 2>&1 \| grep 'hash:'` la imprime en 30 s, como dice el README |
| CONT-29 | PASS | Ronda 2: `cargo test --locked --workspace`: 58, 1, 1, 2 (las de `shutdown`), 7, 6 y 84 pruebas ok, 3 ignoradas, 0 fallos |
| CONT-30 | PASS | Ronda 1: con un ZIP cacheado que no pasa la verificación la construcción fallaba con «ya existe pero no es íntegro ... bórralo» sin salida para el usuario (OBS-02). Resuelto: ahora la construcción se recupera (CONT-35) |

| CONT-31 | PASS | Con una conexión de cabeceras incompletas abierta, `docker kill -s TERM`: el contenedor pasa a `exited` a los 2,12 s (ronda 3; con el plazo de 5 s eran 5,48 s) con código 0 y el log tiene `WARN catalog_api: se fuerza el apagado: quedaban conexiones abiertas tras 2 s grace_secs=2` y después `INFO catalog_api: apagado completado`. Es el escenario «Conexión colgada» de `catalog-api` |
| CONT-32 | PASS | `docker stop -t 10` con la conexión colgada: 2,16 s en la ronda 3 (5,14 s con el plazo de 5 s), código 0 y las dos líneas |
| CONT-33 | PASS | «Conexiones inactivas» de `catalog-api`: `docker stop` sin peticiones 0,12 s con código 0; con una conexión keep-alive inactiva abierta (ronda 3) 0,13 s y código 0; `idle_keep_alive_connection_does_not_delay_shutdown` ok |
| CONT-34 | PASS | Repetido en la ronda 3: `cargo test -p catalog-api --test shutdown`: 2 pruebas ok (`idle_keep_alive_connection_does_not_delay_shutdown` e `incomplete_request_forces_shutdown_after_grace`) |
| CONT-35 | PASS | «Insumo cacheado inválido»: con un ZIP corrupto de 6 033 994 bytes en la caché, el `Dockerfile` real muestra `ya existe pero no es íntegro (tamaño distinto ...)`, `download falló: se vacía /data/.cache y se reintenta una vez`, `usda: descargado y verificado`, `plantas: 2376` y el hash `48d71b6b...5812d`; código 0 |
| CONT-36 | PASS | Con la caché ya sana y un binario de ingesta distinto: `usda: ya estaba y está verificado`, sin reintento ni descarga |
| CONT-37 | PASS | Con el MD5 declarado `000...0`: un solo reintento y `error: checksum MD5 distinto del declarado`, código 1, sin imagen; igual con la caché vacía en un builder nuevo y con `--no-cache` (no hay bucle ni éxito falso). Ver OBS-06 |
| CONT-38 | PASS | Builder desechable, `docker compose --progress=plain build` con el `Dockerfile` nuevo: código 0, 153 `Compiling`, descarga del ZIP, 2376 plantas y el hash esperado |
| CONT-39 | PASS | `docker compose build` en el repo: 10 pasos `CACHED` (también en la ronda 3, con la imagen ya construida con el plazo de 2 s), y la imagen contiene `se fuerza el apagado`; 93 enlaces, 0 rotos; `toolchain_pin` ok dentro del workspace |

## Defectos

### DEF-01 (resuelto): `RUST_LOG=debug` no produce registros debug

- Severidad: baja. Resuelto por la corrección del escenario «Otro nivel de logs», que ahora comprueba que `warn` oculta la línea de arranque y que el valor por defecto la muestra (CONT-09 PASS).

### DEF-02 (corregido y verificado): una solicitud HTTP incompleta impedía el apagado ordenado

- Severidad original: media. La API esperaba sin límite a las conexiones abiertas.
- Verificado: con `SIGTERM`, `docker stop` y `docker stop -t 10`, la API termina al agotarse el plazo con código 0 y registra el aviso de apagado forzado y «apagado completado» (CONT-26, CONT-31, CONT-32, CONT-34). El caso inactivo sigue siendo inmediato (CONT-33).

### DEF-03 (corregido y verificado): `docker stop` sin opciones mataba el contenedor con 137 si había una conexión colgada

- Severidad original: media. Con `SHUTDOWN_GRACE` de 5 s, `docker stop` sin `-t` (y `docker compose stop` y `down`) volvía a los ~3,15 s con código 137 y sin las líneas de apagado, porque en este entorno (Docker Engine 29.8.2, Docker Desktop, macOS arm64) el plazo por defecto es de unos 3 s y no de 10 s (un contenedor que ignora SIGTERM muere a los 3,12 s).
- Corrección: `SHUTDOWN_GRACE` de 2 s. Verificado en la ronda 3: `docker stop` sin opciones tarda 2,15 s con código 0, WARN con `tras 2 s` e INFO «apagado completado» (3 de 3 repeticiones); `docker compose stop` 2,19 s con código 0.
- Margen: el plazo de 2 s deja menos de 1 s de holgura frente a los ~3 s observados; si Docker concediera menos, el escenario volvería a fallar.

## Observaciones (no son defectos)

- OBS-01: los logs del contenedor llevan secuencias ANSI de color aunque no haya TTY (`^[[32m INFO^[[0m`). La frase «apagado completado» queda contigua, así que el escenario se cumple, pero los agregadores de logs verán caracteres de control.
- OBS-02 (resuelta): una caché de datos con un ZIP inválido ya no bloquea la construcción; el `Dockerfile` vacía la caché y descarga de nuevo una vez (CONT-35, CONT-37). Con una descarga que falla por red tras el vaciado se pierde el ZIP cacheado, pero la verificación posterior por tamaño y MD5 protege el contenido.
- OBS-03: con `RUST_LOG=warn` o `error` el log queda vacío, incluido «apagado completado»; el requisito de apagado solo es observable con el nivel `info` (el predeterminado). Coherente con el filtro, pero conviene tenerlo presente al elegir la redacción del escenario de logs.
- OBS-04: la guardia de versión (`toolchain_pin`) solo corre si alguien ejecuta `cargo test`; el README declara que `backend/` no tiene CI, así que la divergencia no se detecta de forma automática en integración continua.
- OBS-06 (con causa): construir una copia del repo con código alterado, por ejemplo el MD5 de `usda.rs`, usando los mismos ids de montura de caché de cargo y de `target` que el repo real (`boticario-backend-target` y los de cargo) en el mismo builder contamina la caché compartida. Cargo decide qué recompilar por la fecha de modificación de los archivos; los de la copia eran más recientes que los del repo, así que la caché `target` quedó con un `catalog-ingest` compilado con el MD5 alterado y la construcción siguiente del repo real lo reutilizó (el fallo «se esperaba 55ae44a0… y se obtuvo 45ae44a0…» que vio el implementador del reintento). `docker compose build --no-cache` lo resuelve. En mi ronda 2 vi el mismo tipo de efecto sin entenderlo: en el builder desechable `qa-cold`, que ya había construido el repo, la copia alterada terminó con código 0 y todos los pasos `CACHED`, y falló como debía con `--no-cache` y en un builder nuevo (CONT-37). Mitigación: todo experimento con código alterado debe usar un builder desechable nuevo o ids de montura propios para cargo y `target`, nunca los del repo; ante un éxito inesperado tras cambiar el código, repetir con `--no-cache`. Hecho así en esta QA salvo en esa ronda 2.
- OBS-05: el comando `docker compose ... build` depende del builder activo; con `docker buildx use` no cambia el que usa Compose (hay que exportar `BUILDX_BUILDER`). Solo afecta a quien quiera una construcción fría.

## Cobertura, riesgos residuales y limpieza

- No repetido en la ronda 2: los casos de la ronda 1 que no dependen de los cambios (contenido de la imagen, usuario, red, puerto, caché de Rust, documentación salvo enlaces) se ejecutaron sobre el código anterior; la imagen se reconstruyó con todo `CACHED`, por lo que solo cambió lo que ya estaba construido.
- No probado: construcción en una máquina sin Rust, mise ni compilador de C (se acotó con el builder sin cachés y el contexto exportado de git; CONT-05); Docker en Linux o Windows, o con Compose antiguo (solo Docker Desktop en macOS arm64); puertos privilegiados con Docker fuera de Docker Desktop; carga y concurrencia; el comportamiento con `docker compose up` de Compose antiguo y la variable `HOST`.
- Riesgos residuales: el margen de 1 s del plazo de 2 s frente a los ~3 s de `docker stop` en este Docker, la contaminación de cachés compartidas (OBS-06) y la ausencia de CI para la guardia de versión.
- Limpieza (rondas 2 y 3): sin contenedores (`docker ps -a` vacío), `docker compose ps` vacío, builders `qa-cold`, `qa-cold2` y `qa-backend` eliminados y `desktop-linux` como builder actual, imágenes `qa-bad`, `qa-retry` y `qa-poison` eliminadas; solo quedan `boticario-backend` y `moby/buildkit`. No toqué la caché `boticario-data-cache` con pruebas destructivas (las alteraciones se hicieron en builders desechables con ids de montura propios) ni ejecuté `prune`. El repo no tiene cambios míos: todo lo alterado estaba en copias en el scratch. Puertos 8080 y 9090 libres.

## Cómo repetirlas

- Funcional: `docker compose up --build -d` y las peticiones `curl` de CONT-06 a CONT-08; `docker compose down` al terminar.
- Hash: `docker compose --progress=plain build --no-cache 2>&1 | grep 'hash:'`.
- Sin red: `docker run -d --name qa-sinred --network none boticario-backend` y `docker run --rm --network container:qa-sinred curlimages/curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/v1/sources`.
- Guardia: desde `backend/`, `mise exec -- cargo test -p catalog-core --test toolchain_pin`.
- Enlaces: el comprobador no se guardó en el repo; se escribió en el scratch de la sesión.
