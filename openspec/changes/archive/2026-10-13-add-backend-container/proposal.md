# Proposal

## Why

Hoy arrancar el backend exige instalar Rust con mise, un compilador de C, descargar el dataset y construir el catálogo a mano antes de ejecutar la API. Eso es fricción para cualquier compañero y no es un artefacto desplegable. Este cambio empaqueta la API y el catálogo ya construido en una imagen de contenedor autocontenida, de modo que arrancar el backend sea un solo comando y la misma imagen sirva después para un despliegue.

## What Changes

- Añadir un `Dockerfile` en la raíz del repo, multietapa: una etapa compila `catalog-ingest` y `catalog-api` con la misma versión de Rust que `mise.toml`, otra construye el catálogo ejecutando `download` y `build` dentro de la construcción de la imagen e imprime su hash, y la imagen final solo lleva el binario de la API y `catalog.db`, con un usuario sin privilegios.
- Añadir un `.dockerignore` que deja fuera del contexto de construcción lo que no participa en el backend (`app/`, `.git/`, `docs/`, `openspec/`, salidas locales de compilación y de datos, y carpetas de herramientas de agentes).
- Añadir un `compose.yaml` en la raíz con un servicio `api` que construye la imagen y publica el puerto 8080, de modo que `docker compose up --build` sea todo lo que hace un compañero. `PORT` y `RUST_LOG` se pueden sobrescribir por entorno.
- Usar cachés de BuildKit para el registro de cargo, el directorio `target` y el ZIP descargado, de forma que una reconstrucción sin cambios sea inmediata, un cambio en Rust recompile de forma incremental y el ZIP no se descargue otra vez.
- Añadir un test de guardia que falla si la versión de Rust de la imagen base del `Dockerfile` no coincide con la de `mise.toml`.
- Reescribir la sección «Backend: catálogo y API» del `README.md` de la raíz para que solo requiera Docker, con un enlace de una línea a `backend/README.md` para quien vaya a desarrollar el backend. El flujo nativo (mise, cargo, diesel, tests, regeneración del OpenAPI, cambio de esquema) se mueve completo a un `backend/README.md` nuevo, pensado para quien quiera hacer el setup con mise y modificar el código Rust. Se actualizan el árbol de estructura del repo y el párrafo de CI, y los enlaces de `docs/` siguen siendo válidos, con las referencias a comandos nativos redirigidas a `backend/README.md`. `AGENTS.md` no cambia.
- Hacer el apagado de `catalog-api` con tiempo máximo (surgido de la QA): al recibir SIGTERM o Ctrl-C la API deja de aceptar conexiones, espera a las peticiones en curso como máximo 2 s (`SHUTDOWN_GRACE`) y termina con código 0, registrando un aviso de apagado forzado si se agotó el plazo y siempre «apagado completado». Así una conexión colgada no hace que Docker tenga que enviar SIGKILL con el plazo por defecto de `docker stop`.
- Hacer que el `Dockerfile` reintente la descarga del dataset una vez, tras vaciar la caché del ZIP, si el ZIP cacheado no pasa la verificación (observación de la QA), para que un cambio del MD5 o del tamaño declarados no bloquee la construcción.
- Sin cambios en la ingesta, en la app Flutter ni en la spec `catalog-ingest`. El único cambio de código es el apagado con tiempo máximo en `catalog-api`. `mise.toml` se conserva para el desarrollo local.

## Capabilities

### New Capabilities
- `backend-container`: imagen de contenedor autocontenida del backend (API y catálogo construido), construcción reproducible, arranque con un solo comando, configuración por entorno, ejecución sin privilegios, apagado ordenado, reconstrucción incremental con caché, documentación sin setup manual y guardia de versión del toolchain.

### Modified Capabilities
- `catalog-api`: se añade el requisito «Apagado ordenado con tiempo máximo». No se modifican los requisitos existentes. La imagen empaqueta el resto del comportamiento de `catalog-api` y de `catalog-ingest` sin alterarlo.

## Impact

- Repositorio: archivos nuevos `Dockerfile`, `.dockerignore` y `compose.yaml` en la raíz; un test de guardia de versión en el workspace de `backend/`; un `backend/README.md` nuevo con el flujo nativo; y cambios en el `README.md` de la raíz y en las referencias de `docs/`. `app/`, el código de la ingesta, `data/` y `AGENTS.md` no cambian.
- Código: `catalog-api` añade el apagado con tiempo máximo (constante `SHUTDOWN_GRACE` en `startup.rs`, función `serve` probada con tests de conexión inactiva y colgada) y activa en `tokio` las features que ese apagado necesita. `backend/Cargo.toml` y `Cargo.lock` cambian en consecuencia.
- Herramientas: el equipo necesita Docker (Desktop o compatible) con BuildKit y Compose; ya no necesita Rust, mise ni un compilador de C para solo ejecutar el backend.
- Datos: el catálogo se descarga y construye al construir la imagen, no al arrancar el contenedor ni se versiona en git. La construcción es la única que usa la red; el contenedor no la necesita para servir.
- Plataforma: la imagen se construye nativa (arm64 en los Mac del equipo); `--platform linux/amd64` queda documentado como opción.
- Fuera de alcance: despliegue en una plataforma concreta (la nube), CI para el backend, TLS, autenticación e integración de la app Flutter con la API.
