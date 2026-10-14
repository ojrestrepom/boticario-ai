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
- Sin cambios en el código de la API ni de la ingesta, en la app Flutter ni en las specs `catalog-api` y `catalog-ingest`. `mise.toml` se conserva para el desarrollo local.

## Capabilities

### New Capabilities
- `backend-container`: imagen de contenedor autocontenida del backend (API y catálogo construido), construcción reproducible, arranque con un solo comando, configuración por entorno, ejecución sin privilegios, apagado ordenado, reconstrucción incremental con caché, documentación sin setup manual y guardia de versión del toolchain.

### Modified Capabilities
Ninguna. La imagen empaqueta el comportamiento existente de `catalog-api` y `catalog-ingest` sin alterar sus requisitos.

## Impact

- Repositorio: archivos nuevos `Dockerfile`, `.dockerignore` y `compose.yaml` en la raíz; un test de guardia de versión en el workspace de `backend/`; un `backend/README.md` nuevo con el flujo nativo; y cambios en el `README.md` de la raíz y en las referencias de `docs/`. `app/`, el código de la API y de la ingesta, `data/` y `AGENTS.md` no cambian.
- Herramientas: el equipo necesita Docker (Desktop o compatible) con BuildKit y Compose; ya no necesita Rust, mise ni un compilador de C para solo ejecutar el backend.
- Datos: el catálogo se descarga y construye al construir la imagen, no al arrancar el contenedor ni se versiona en git. La construcción es la única que usa la red; el contenedor no la necesita para servir.
- Plataforma: la imagen se construye nativa (arm64 en los Mac del equipo); `--platform linux/amd64` queda documentado como opción.
- Fuera de alcance: despliegue en una plataforma concreta (la nube), CI para el backend, TLS, autenticación e integración de la app Flutter con la API.
