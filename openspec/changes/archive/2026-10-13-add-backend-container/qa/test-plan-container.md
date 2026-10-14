# Plan de pruebas: add-backend-container

Cambio: `openspec/changes/add-backend-container`. Requerimiento: spec delta `specs/backend-container/spec.md` (10 requisitos, 18 escenarios). Capability: `backend-container`.

Técnicas: un caso por escenario (caja negra sobre la imagen y compose), valores límite y clases de equivalencia para `PORT` y `RUST_LOG`, transición de estados para el ciclo de vida del contenedor (arrancar, atender, detener), pruebas negativas (insumo alterado, sin red, base ausente, puerto inválido) y charters exploratorios (apagado con conexiones abiertas, endurecimiento, plataforma amd64, contexto de construcción).

Las pruebas son independientes del informe del implementador (`verificacion-5.1-5.5.md`): todo se ejecutó de nuevo. Las construcciones destructivas (insumo alterado, cambios de código) se hicieron en una copia en el scratch del repo exportada con `git ls-files -co --exclude-standard`, con un builder desechable `qa-backend`, para no tocar el código ni las cachés del proyecto.

## Casos derivados de los escenarios

| ID | Requisito / escenario | Precondición | Pasos | Resultado esperado |
|---|---|---|---|---|
| CONT-01 | Imagen autocontenida / Servir sin red | Imagen `boticario-backend` construida | `docker run -d --network none boticario-backend`; desde un contenedor auxiliar en su espacio de red, `GET /v1/sources` | 200 con las fuentes del catálogo |
| CONT-02 | Imagen autocontenida / Contenido mínimo | Imagen construida | Listar `/app`; `find` de `raw.db`, `*.zip`, `cargo`, `rustc`, `*.rs`, `Cargo.toml`, `*.toml`, `catalog-ingest`; comprobar `/src`, `/data`, `/usr/local/cargo` | Solo existen `catalog-api` y `catalog.db`; no hay nada de lo demás |
| CONT-03 | Construcción reproducible / Hash igual al nativo | ZIP verificado (MD5 `45ae44a0...`) | `docker compose --progress=plain build --no-cache` y `grep hash:`; construcción nativa `catalog-ingest build` en un directorio de datos aparte | Ambos hashes iguales a `48d71b6b...5812d` |
| CONT-04 | Construcción reproducible / Insumo alterado | Copia en scratch, caché de datos vacía | Cambiar el MD5 declarado (`usda.rs`) y construir; repetir cambiando el tamaño declarado | La construcción falla en la etapa de catálogo y no se crea imagen |
| CONT-05 | Sin preparación previa / Máquina limpia | Builder desechable sin cachés | `BUILDX_BUILDER=qa-backend docker compose --progress=plain build` desde la raíz | Construcción con éxito; compila desde cero y descarga el ZIP |
| CONT-06 | Arranque / Salud y datos | Imagen construida | `docker compose up --build -d`; `GET http://localhost:8080/healthz` | 200 |
| CONT-07 | Arranque / Búsqueda real | Servicio arriba | `GET /v1/plants?q=lavand` y `GET /v1/sources` | 200 con plantas (lavandula-*) y la fuente `usda`; total del catálogo 2376 |
| CONT-08 | Configuración / Otro puerto | Puertos 8080 y 9090 libres | `PORT=9090 docker compose up -d`; `GET :9090/healthz`; `GET :8080/healthz` | 9090 responde 200; el 8080 del anfitrión no está publicado |
| CONT-09 | Configuración / Otro nivel de logs (escenario corregido en la ronda 2) | Imagen construida | Arrancar con `RUST_LOG=warn` y, por separado, con el valor por defecto; hacer una petición, detener y leer el log | Con `warn` el log no contiene «escuchando»; por defecto sí |
| CONT-10 | Configuración / filtros adicionales (ronda 1; el escenario original con `debug` ya no aplica) | Servicio arriba con `RUST_LOG=debug`, `error` y `trace` | Arrancar, hacer peticiones OK y de error, detener, leer el log | `debug` e `info` solo muestran INFO, `error` no muestra nada y `trace` añade TRAZAS de dependencias |
| CONT-11 | Sin privilegios / Usuario del proceso | Contenedor en ejecución | `docker top`, `/proc/1/status`, `docker image inspect` (`Config.User`); descriptor de `catalog.db` en `/proc/1/fdinfo` | UID distinto de 0; base abierta en solo lectura |
| CONT-12 | Apagado ordenado / Detener el contenedor | Contenedor en ejecución | `docker stop` (y `docker compose stop` con `up` en primer plano); `docker inspect` y `docker logs` | Salida 0, sin esperar al cierre forzado, log con «apagado completado» |
| CONT-26 | Apagado ordenado / Conexión colgada (escenario nuevo en `backend-container`) | Contenedor en ejecución con un cliente que mandó cabeceras incompletas y mantiene el socket | `docker stop` sin opciones; `docker inspect` y `docker logs`; repetir 3 veces | Salida 0 antes de que Docker fuerce el cierre (con `docker stop` sin opciones, ~3 s en Docker 29); el log tiene el aviso de apagado forzado y «apagado completado» |
| CONT-13 | Caché / Sin cambios | Imagen construida | Repetir `docker compose build` | Todos los pasos `CACHED`, sin `Compiling` ni descarga |
| CONT-14 | Caché / Cambio en Rust | Imagen construida | Modificar un archivo Rust (api, ingest y core) y reconstruir | Se recompila y no se descarga el ZIP |
| CONT-15 | Documentación / README solo con Docker | `README.md` | `grep` de instalación de Rust, mise o cargo; revisar la sección «Backend: catálogo y API» | Sin instrucciones de instalación; la sección cubre Docker, `docker compose up --build`, endpoints, variables, hash, reconstrucción y el enlace a `backend/README.md` |
| CONT-16 | Documentación / Flujo nativo completo | `backend/README.md` | Revisar secciones; comparar comandos y tabla con la sección antigua del README (HEAD); regenerar el OpenAPI y comparar | Prerrequisitos con mise, construcción, ejecución, OpenAPI, verificación y cambio de esquema; comandos conservados |
| CONT-17 | Documentación / Enlaces válidos | `README.md`, `backend/README.md`, `docs/**/*.md` | Comprobador propio de enlaces relativos y anclajes (con control negativo) | Todos los destinos existen |
| CONT-18 | Guardia / Versiones coinciden | `mise.toml` y `Dockerfile` alineados | `cargo test -p catalog-core --test toolchain_pin` | La prueba pasa |
| CONT-19 | Guardia / Versiones divergen | Igual | Cambiar `mise.toml` a 1.98.0 y ejecutar; restaurar; cambiar el `Dockerfile` a 1.98.0 y ejecutar; restaurar | La prueba falla indicando ambas versiones; archivos restaurados |

## Casos exploratorios

| ID | Charter | Pasos | Resultado esperado |
|---|---|---|---|
| CONT-20 | `.dockerignore` protege la caché | En la copia: tocar `README.md`, `compose.yaml`, `openspec/`, `docs/` y `app/` y reconstruir | Todas las capas siguen en caché |
| CONT-21 | El contexto sale solo de git | Exportar los archivos versionables (sin `data/.cache`, `data/build` ni `target`) y construir con el builder que ya tiene la construcción limpia | Mismo contexto: todo en caché y mismo resultado |
| CONT-22 | Configuración de entorno hostil | `HOST=127.0.0.1` en el anfitrión; `PORT` vacío; `PORT=80`; `PORT=abc`; `PORT=70000` | `HOST` no afecta; vacío usa 8080; 80 funciona sin root; los inválidos fallan sin dejar contenedor |
| CONT-23 | Endurecimiento | `docker run --read-only --cap-drop ALL --security-opt no-new-privileges` | La API sirve con normalidad |
| CONT-24 | Arranque defectuoso | `CATALOG_DB=/nope.db`; `PORT=abc` en el contenedor | Salida 1 y 2 con mensaje claro |
| CONT-25 | Apagado con conexión keep-alive inactiva | Abrir una conexión keep-alive, `docker stop` | Salida 0 en menos de 10 s |
| CONT-27 | Plataforma amd64 | `docker build --platform linux/amd64` (comando del README) y arranque | Construye, mismo hash, sirve |
| CONT-28 | Comandos del README | `docker compose --progress=plain build 2>&1 \| grep 'hash:'` con caché (sin línea) y `build --no-cache` (con línea) | Coincide con lo documentado |
| CONT-29 | Regresión del workspace | `cargo test --locked --workspace` | Todo en verde con la nueva dev-dependency |
| CONT-30 | Insumo con caché de datos previa (ronda 1) | Caché con ZIP válido y MD5 declarado distinto | Informe del comportamiento; resuelto por CONT-35 |

## Casos añadidos en la ronda 2

Cambios que los motivan: el escenario «Otro nivel de logs» se reformuló; `catalog-api` ahora limita a 5 s el drenaje del apagado (`SHUTDOWN_GRACE`) y hay un delta nuevo `specs/catalog-api/spec.md`; el `Dockerfile` reintenta la descarga con la caché vacía; y se añadieron los escenarios «Conexión colgada» e «Insumo cacheado inválido» a `backend-container`.

| ID | Requisito / escenario | Precondición | Pasos | Resultado esperado |
|---|---|---|---|---|
| CONT-31 | `catalog-api` / Conexión colgada, aislada del temporizador de Docker | Contenedor con una conexión de cabeceras incompletas | `docker kill -s TERM` y sondeo del estado; leer el log | Termina al agotarse los 5 s con código 0; el log tiene `WARN ... se fuerza el apagado` y `INFO ... apagado completado` |
| CONT-32 | `backend-container` / Conexión colgada con plazo explícito | Igual | `docker stop -t 10` y, en el scratch, un compose con `stop_grace_period: 10s` | Salida 0 con las dos líneas de log |
| CONT-33 | `catalog-api` / Conexiones inactivas | Contenedor sin peticiones en curso; y una conexión keep-alive inactiva | `docker stop`; `cargo test -p catalog-api --test shutdown` | Termina de inmediato con 0 y «apagado completado»; las dos pruebas pasan |
| CONT-34 | `catalog-api` / Conexión colgada (prueba automatizada) | Código del repo | `cargo test -p catalog-api --test shutdown`, `cargo test --workspace` | `incomplete_request_forces_shutdown_after_grace` y el resto pasan |
| CONT-35 | Caché / Insumo cacheado inválido | Builder desechable; copia en el scratch con id de montura propio (`qa-retry-data-cache`) | Construir con un `Dockerfile.poison` que deja un ZIP corrupto en la caché; construir con el `Dockerfile` real | La construcción rechaza el ZIP, vacía la caché, lo descarga de nuevo y termina con el hash esperado |
| CONT-36 | Caché / Insumo cacheado inválido, caché sana | Tras CONT-35 | Cambiar el binario de ingesta y reconstruir | No hay reintento; dice «ya estaba y está verificado» |
| CONT-37 | Construcción reproducible / Insumo alterado con el reintento | Copia con MD5 declarado `000...0`, con y sin caché previa | Construir | Un solo reintento y fallo con código 1 sin crear imagen (no hay bucle) |
| CONT-38 | Sin preparación previa / Máquina limpia con el `Dockerfile` nuevo | Builder desechable sin cachés | `BUILDX_BUILDER=qa-cold docker compose --progress=plain build` | Éxito, descarga, hash esperado |
| CONT-39 | Regresión | Estado actual del repo | `docker compose build` con caché; comprobador de enlaces; `toolchain_pin` dentro del workspace | 10 pasos `CACHED`; 0 enlaces rotos; todo en verde |

Ronda 3: se repitieron CONT-12, CONT-26, CONT-31, CONT-32, CONT-33 y CONT-34 con `SHUTDOWN_GRACE` de 2 s; el plan no cambia (CONT-26 se ejecutó además con `docker compose stop` y `down`).
