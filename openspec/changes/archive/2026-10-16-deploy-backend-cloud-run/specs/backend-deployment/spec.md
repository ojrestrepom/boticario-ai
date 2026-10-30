# backend-deployment Specification

## Purpose
Define cómo se publica y se opera el backend en la nube: una imagen amd64 construida y etiquetada por CI, un despliegue continuo en Google Cloud Run con verificación posterior, una configuración de servicio de costo mínimo, una identidad de despliegue sin claves de larga duración y la documentación de preparación, operación, rollback y desmontaje.

## ADDED Requirements

### Requirement: Imagen amd64 publicada por CI y etiquetada por commit
El workflow de despliegue SHALL construir la imagen del backend para linux/amd64 en un runner de GitHub Actions y SHALL publicarla en un repositorio Docker de Artifact Registry de la región del servicio. La imagen SHALL llevar una etiqueta igual al SHA completo del commit y la etiqueta `latest`. El servicio SHALL desplegarse con la referencia por SHA, nunca con `latest`. El workflow SHALL NOT publicar la imagen en un registry público.

#### Scenario: Etiquetas de la imagen
- **WHEN** el workflow termina la publicación de un commit
- **THEN** el repositorio de Artifact Registry contiene la imagen con la etiqueta del SHA del commit y con `latest`, y ambas apuntan al mismo contenido

#### Scenario: Arquitectura de la imagen
- **WHEN** se inspecciona la imagen publicada
- **THEN** su plataforma es linux/amd64

#### Scenario: Despliegue por SHA
- **WHEN** el workflow despliega el servicio
- **THEN** la revisión creada referencia la imagen por la etiqueta del SHA del commit

#### Scenario: Repositorio privado
- **WHEN** se consulta el repositorio de Artifact Registry sin credenciales
- **THEN** la imagen no es accesible

### Requirement: Despliegue automático con verificación posterior
El workflow SHALL ejecutarse en cada `push` a `main` que modifique el backend (`backend/`, `data/migrations/`, `data/sources.toml`, `Dockerfile`, `.dockerignore` o el propio workflow) y bajo demanda con `workflow_dispatch`. SHALL NOT ejecutarse por cambios que solo afecten a la app, la documentación u OpenSpec. Los despliegues SHALL serializarse sin cancelar uno en curso. Tras desplegar, el workflow SHALL consultar `GET /health` y `GET /v1/plants/lavandula-angustifolia` sobre la URL del servicio y SHALL fallar si alguna no responde 200.

#### Scenario: Cambio del backend en main
- **WHEN** se hace `push` a `main` con un cambio bajo `backend/`
- **THEN** el workflow construye, publica y despliega, y el servicio sirve la nueva revisión

#### Scenario: Cambio ajeno al backend
- **WHEN** se hace `push` a `main` que solo modifica `app/`, `docs/` u `openspec/`
- **THEN** el workflow no se ejecuta

#### Scenario: Ejecución manual
- **WHEN** se lanza el workflow con `workflow_dispatch`
- **THEN** ejecuta el mismo camino de construcción, publicación, despliegue y verificación

#### Scenario: Despliegues concurrentes
- **WHEN** se encadenan dos ejecuciones del workflow
- **THEN** la segunda espera a que termine la primera y ninguna se cancela a medias

#### Scenario: Verificación posterior satisfactoria
- **WHEN** el servicio desplegado responde 200 en `/health` y en `/v1/plants/lavandula-angustifolia`
- **THEN** el job termina en éxito

#### Scenario: Verificación posterior fallida
- **WHEN** alguna de las dos consultas no responde 200 tras el despliegue
- **THEN** el job termina en fallo

### Requirement: Configuración del servicio en Cloud Run
El servicio `boticario-api` SHALL desplegarse en `northamerica-south1` con facturación por petición, escala a cero (`min-instances=0`), un máximo de 2 instancias, acceso público sin autenticación y la imagen escuchando en el puerto 8080 que Cloud Run inyecta por `PORT`. El servicio SHALL usar 1 vCPU y 256 MiB de memoria, una sonda de arranque HTTP a `/health` y una cuenta de servicio de ejecución dedicada. El servicio SHALL ser accesible por HTTPS en su URL `*.run.app` y SHALL servir la misma API que la imagen en local.

#### Scenario: Escala a cero y máximo de instancias
- **WHEN** se describe el servicio desplegado
- **THEN** `min-instances` es 0 y `max-instances` es 2

#### Scenario: Facturación por petición
- **WHEN** se describe el servicio desplegado
- **THEN** la CPU se asigna solo durante el procesamiento de peticiones

#### Scenario: Recursos del contenedor
- **WHEN** se describe el servicio desplegado
- **THEN** el contenedor tiene 1 vCPU y 256 MiB de memoria

#### Scenario: Sonda de arranque
- **WHEN** se describe el servicio desplegado
- **THEN** tiene una sonda de arranque HTTP a `/health` en el puerto 8080

#### Scenario: Ruta de salud alcanzable desde fuera
- **WHEN** se consulta `GET /health` por la URL pública `*.run.app`
- **THEN** la API responde 200

#### Scenario: Acceso público por HTTPS
- **WHEN** se consulta `GET /v1/plants?q=lavandula` por HTTPS en la URL del servicio sin credenciales
- **THEN** la API responde 200 con la lista de plantas

#### Scenario: Error del contrato
- **WHEN** se consulta `GET /v1/plants/no-existe` en la URL del servicio
- **THEN** la API responde 404 con `application/problem+json`

#### Scenario: Primera petición tras inactividad
- **WHEN** no hay tráfico durante al menos 15 minutos y llega una petición
- **THEN** el servicio arranca una instancia, responde 200 y el tiempo de arranque en frío queda medido en el informe de QA

### Requirement: Identidad de despliegue sin claves de larga duración
El workflow SHALL autenticarse en Google Cloud mediante Workload Identity Federation con el token OIDC de GitHub Actions, y SHALL NOT usar claves JSON de cuentas de servicio ni guardarlas en el repositorio o en los secretos de GitHub. La cuenta de servicio de despliegue SHALL tener solo permisos para administrar Cloud Run, escribir en el repositorio de Artifact Registry y actuar como la cuenta de ejecución. La cuenta de servicio de ejecución SHALL NOT tener roles. El proveedor de identidad SHALL estar restringido por condición de atributo al repositorio del proyecto.

#### Scenario: Sin claves almacenadas
- **WHEN** se revisan el repositorio, sus secretos y el workflow
- **THEN** no hay claves JSON de cuentas de servicio y la autenticación usa Workload Identity Federation

#### Scenario: Permisos mínimos de despliegue
- **WHEN** se listan los roles de la cuenta de servicio de despliegue
- **THEN** solo incluye administración de Cloud Run, escritura en Artifact Registry y `iam.serviceAccountUser` sobre la cuenta de ejecución

#### Scenario: Cuenta de ejecución sin roles
- **WHEN** se listan los roles de la cuenta de servicio de ejecución en el proyecto
- **THEN** no tiene ninguno

#### Scenario: Proveedor restringido al repositorio
- **WHEN** se describe el proveedor de Workload Identity Federation
- **THEN** su condición de atributo acepta únicamente `assertion.repository == 'sebastianrodriguez1115/boticario-ai'`

#### Scenario: Acciones fijadas
- **WHEN** se revisa el workflow
- **THEN** cada acción de terceros está fijada por SHA con un comentario de versión y los permisos del job se limitan a `contents: read` e `id-token: write`

### Requirement: Observabilidad y control de costo
El servicio SHALL escribir sus logs en Cloud Logging y SHALL ser consultable su historial de revisiones. El proyecto SHALL tener una alerta de presupuesto del equivalente a 1 USD en la moneda de la cuenta de facturación. El repositorio de Artifact Registry SHALL tener una política de limpieza que conserve solo las últimas versiones de la imagen. El máximo de instancias SHALL acotar el gasto del servicio.

#### Scenario: Logs del servicio
- **WHEN** el servicio atiende una petición
- **THEN** los logs del servicio en Cloud Logging contienen la salida de la API y los logs de petición de Cloud Run

#### Scenario: Alerta de presupuesto
- **WHEN** se listan los presupuestos de la cuenta de facturación
- **THEN** existe uno del equivalente a 1 USD en la moneda de la cuenta de facturación con umbrales de alerta por correo

#### Scenario: Limpieza de imágenes
- **WHEN** se describe el repositorio de Artifact Registry
- **THEN** tiene una política de limpieza activa que conserva solo las últimas versiones

#### Scenario: Consumo dentro de la capa gratuita
- **WHEN** se lee el consumo del servicio tras la QA
- **THEN** las peticiones, los vCPU-s y los GiB-s quedan dentro de la capa gratuita

### Requirement: Documentación de preparación, operación, rollback y desmontaje
El repositorio SHALL documentar en `docs/deploy/cloud-run.md` la preparación única en GCP con comandos reproducibles (proyecto, facturación, APIs, repositorio de imágenes, cuentas de servicio, Workload Identity Federation, permisos, política de limpieza y alerta de presupuesto), los secretos y variables de GitHub que necesita el workflow, el despliegue manual, la consulta de logs, el rollback a la revisión anterior y el desmontaje completo para volver a costo cero. El `README.md` SHALL enlazar a ese documento y SHALL actualizar la sección de despliegue en amd64.

#### Scenario: Preparación documentada
- **WHEN** un desarrollador consulta `docs/deploy/cloud-run.md` con una cuenta de Google nueva
- **THEN** encuentra los comandos, en orden, para dejar listo el proyecto y los secretos y variables de GitHub

#### Scenario: Rollback documentado
- **WHEN** una revisión desplegada falla
- **THEN** el documento indica cómo dirigir el tráfico a la revisión anterior sin reconstruir la imagen

#### Scenario: Desmontaje documentado
- **WHEN** el desarrollador quiere dejar de pagar y de exponer el servicio
- **THEN** el documento indica cómo eliminar el servicio, el repositorio de imágenes, las cuentas de servicio y la configuración de identidad, o el proyecto entero

#### Scenario: README enlaza
- **WHEN** se consulta el `README.md`
- **THEN** enlaza a `docs/deploy/cloud-run.md` y «Despliegue en amd64» describe la construcción y el despliegue por CI
