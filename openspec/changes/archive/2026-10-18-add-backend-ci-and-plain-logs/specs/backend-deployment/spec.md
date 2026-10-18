## MODIFIED Requirements

### Requirement: Despliegue automático con verificación posterior
El workflow SHALL ejecutarse en cada `push` a `main` que modifique el backend (`backend/`, `data/migrations/`, `data/sources.toml`, `Dockerfile`, `.dockerignore`, `mise.toml` o el propio workflow) y bajo demanda con `workflow_dispatch`. SHALL NOT ejecutarse por cambios que solo afecten a la app, la documentación u OpenSpec. Antes de construir la imagen, el workflow SHALL ejecutar las verificaciones del backend definidas por la capability `backend-ci`, y SHALL construir, publicar y desplegar solo si pasan. Si fallan, SHALL NOT publicar ninguna imagen ni crear ninguna revisión. Los despliegues SHALL serializarse sin cancelar uno en curso. Tras desplegar, el workflow SHALL consultar `GET /health` y `GET /v1/plants/lavandula-angustifolia` sobre la URL del servicio y SHALL fallar si alguna no responde 200.

#### Scenario: Cambio del backend en main
- **WHEN** se hace `push` a `main` con un cambio bajo `backend/` y las verificaciones pasan
- **THEN** el workflow construye, publica y despliega, y el servicio sirve la nueva revisión

#### Scenario: Cambio ajeno al backend
- **WHEN** se hace `push` a `main` que solo modifica `app/`, `docs/` u `openspec/`
- **THEN** el workflow no se ejecuta

#### Scenario: Cambio del toolchain
- **WHEN** se hace `push` a `main` que solo modifica `mise.toml`
- **THEN** el workflow se ejecuta, y la guarda de versión de las verificaciones falla si el `Dockerfile` no coincide

#### Scenario: Verificaciones fallidas
- **WHEN** el formato, el lint o alguna prueba del backend falla en una ejecución del workflow
- **THEN** el workflow termina en fallo sin construir la imagen, sin publicarla en Artifact Registry y sin crear una revisión en Cloud Run, y el servicio sigue sirviendo la revisión anterior

#### Scenario: Ejecución manual
- **WHEN** se lanza el workflow con `workflow_dispatch`
- **THEN** ejecuta el mismo camino de verificaciones, construcción, publicación, despliegue y verificación posterior

#### Scenario: Despliegues concurrentes
- **WHEN** se encadenan dos ejecuciones del workflow
- **THEN** la segunda espera a que termine la primera y ninguna se cancela a medias

#### Scenario: Verificación posterior satisfactoria
- **WHEN** el servicio desplegado responde 200 en `/health` y en `/v1/plants/lavandula-angustifolia`
- **THEN** el job termina en éxito

#### Scenario: Verificación posterior fallida
- **WHEN** alguna de las dos consultas no responde 200 tras el despliegue
- **THEN** el job termina en fallo
