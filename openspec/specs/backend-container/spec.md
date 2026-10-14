# backend-container Specification

## Purpose
Define la imagen de contenedor del backend: un artefacto autocontenido con la API y el catálogo ya construido, que se construye y arranca con Docker sin instalar Rust, mise ni descargar datos a mano, y que sirve de base para un despliegue posterior.

## Requirements

### Requirement: Imagen autocontenida
La imagen SHALL contener la API y el catálogo ya construido, y SHALL servir sin acceso a la red. La imagen final SHALL NOT incluir la base cruda, el ZIP del dataset, el toolchain de Rust ni el código fuente.

#### Scenario: Servir sin red
- **WHEN** se ejecuta el contenedor sin acceso a la red y se consulta `GET /v1/sources`
- **THEN** la API responde 200 con las fuentes del catálogo

#### Scenario: Contenido mínimo
- **WHEN** se inspecciona el sistema de archivos de la imagen final
- **THEN** no existe la base cruda, el ZIP, `cargo`, `rustc` ni el código fuente, y sí existen el binario de la API y la base del catálogo

### Requirement: Construcción reproducible del catálogo
El catálogo SHALL construirse al construir la imagen, no al arrancar el contenedor, y la construcción SHALL imprimir el hash de contenido del catálogo. Ese hash SHALL ser igual al de una construcción nativa a partir del mismo insumo verificado.

#### Scenario: Hash igual al nativo
- **WHEN** se construye la imagen y se compara el hash impreso en el log de construcción con el de una construcción nativa del mismo insumo
- **THEN** ambos hashes son idénticos

#### Scenario: Insumo alterado
- **WHEN** el ZIP descargado durante la construcción no coincide con el tamaño y el MD5 declarados
- **THEN** la construcción de la imagen falla y no produce imagen

### Requirement: Construcción sin preparación previa
`docker compose build` SHALL construir la imagen en una máquina que solo tiene Docker con Compose y acceso a la red, sin Rust, mise, un compilador de C ni descargas manuales previas.

#### Scenario: Máquina limpia
- **WHEN** un compañero con solo Docker ejecuta `docker compose build` desde la raíz del repo
- **THEN** la imagen se construye con éxito

### Requirement: Arranque con un solo comando
`docker compose up` SHALL arrancar la API publicando el puerto 8080 del anfitrión por defecto, con datos reales del catálogo.

#### Scenario: Salud y datos
- **WHEN** se ejecuta `docker compose up` y se consulta `http://localhost:8080/healthz`
- **THEN** la respuesta es 200

#### Scenario: Búsqueda real
- **WHEN** se consulta `/v1/plants?q=lavand` y `/v1/sources`
- **THEN** ambas responden 200 y devuelven plantas y fuentes del catálogo real

### Requirement: Configuración por entorno
El puerto publicado y el puerto de escucha SHALL poder cambiarse con la variable `PORT`, y el nivel de logs con `RUST_LOG`. La dirección de escucha SHALL ser siempre `0.0.0.0` dentro del contenedor y SHALL NOT depender de la configuración del usuario.

#### Scenario: Otro puerto
- **WHEN** se ejecuta `PORT=9090 docker compose up` y se consulta `http://localhost:9090/healthz`
- **THEN** la respuesta es 200 y el puerto 8080 del anfitrión no está publicado

#### Scenario: Otro nivel de logs
- **WHEN** se ejecuta el contenedor con `RUST_LOG=warn` y, por separado, con el valor por defecto
- **THEN** con `warn` el log no contiene la línea INFO de arranque («escuchando») y con el valor por defecto sí la contiene

### Requirement: Ejecución sin privilegios
El proceso de la API SHALL ejecutarse con un usuario sin privilegios, nunca como root, y SHALL abrir la base del catálogo en solo lectura.

#### Scenario: Usuario del proceso
- **WHEN** se consulta el usuario del proceso dentro del contenedor en ejecución
- **THEN** no es root

### Requirement: Apagado ordenado
Al recibir la señal de terminación, el contenedor SHALL terminar de forma ordenada, con código de salida 0 y un registro de que el apagado se completó. El apagado SHALL esperar a las peticiones en curso como máximo el plazo de gracia, que es menor que el plazo por defecto de `docker stop` (unos 3 s en Docker 29), y SHALL terminar con código 0 aunque queden conexiones abiertas.

#### Scenario: Detener el contenedor
- **WHEN** se ejecuta `docker stop` sobre el contenedor en ejecución
- **THEN** el contenedor termina con código 0, sin esperar al cierre forzado, y su log contiene «apagado completado»

#### Scenario: Conexión colgada
- **WHEN** un cliente mantiene una conexión abierta con cabeceras incompletas y se ejecuta `docker stop`
- **THEN** el contenedor termina con código 0 antes de que Docker fuerce el cierre, con `docker stop` sin opciones, y el log contiene el aviso de apagado forzado y «apagado completado»

### Requirement: Reconstrucción incremental con caché
Las reconstrucciones SHALL reutilizar la caché de construcción. Sin cambios, la reconstrucción SHALL reutilizar todas las capas. Con un cambio en un archivo Rust, SHALL recompilar sin volver a descargar el ZIP del dataset.

#### Scenario: Sin cambios
- **WHEN** se vuelve a construir la imagen sin modificar el repo
- **THEN** la construcción termina reutilizando la caché y no ejecuta de nuevo la compilación ni la descarga

#### Scenario: Cambio en Rust
- **WHEN** se modifica un archivo Rust y se vuelve a construir la imagen
- **THEN** se recompila el código y no se descarga de nuevo el ZIP

#### Scenario: Insumo cacheado inválido
- **WHEN** el ZIP guardado en la caché de construcción no pasa la verificación
- **THEN** la construcción lo descarta, lo descarga de nuevo y continúa

### Requirement: Documentación sin setup manual
El README de la raíz SHALL describir cómo arrancar el backend usando solo Docker y SHALL NOT incluir instrucciones para instalar Rust, mise ni cargo, aunque SHALL poder enlazar a `backend/README.md` para quien modifique el código. El flujo de desarrollo nativo SHALL conservarse completo en `backend/README.md`, y los enlaces del README y de `docs/` SHALL seguir siendo válidos.

#### Scenario: README solo con Docker
- **WHEN** se busca en el README instrucciones de instalación de Rust, mise o cargo
- **THEN** no hay ninguna, y la sección del backend indica Docker, `docker compose up --build`, endpoints, variables configurables, cómo ver el hash del catálogo, cómo reconstruir y, como máximo, un enlace a `backend/README.md`

#### Scenario: Flujo nativo completo
- **WHEN** se revisa `backend/README.md`
- **THEN** incluye prerrequisitos con mise, construcción del catálogo, ejecución de la API, regeneración del OpenAPI, verificación y cambio de esquema

#### Scenario: Enlaces válidos
- **WHEN** se comprueban los enlaces relativos y los anclajes del README y de `docs/`
- **THEN** todos apuntan a destinos existentes

### Requirement: Guardia de versión del toolchain
Una prueba automatizada SHALL fallar cuando la versión de Rust de la imagen base de compilación no coincida con la fijada para el desarrollo local, para que ambas no diverjan.

#### Scenario: Versiones coinciden
- **WHEN** se ejecuta la prueba con la versión de la imagen igual a la fijada localmente
- **THEN** la prueba pasa

#### Scenario: Versiones divergen
- **WHEN** se altera una de las dos versiones y se ejecuta la prueba
- **THEN** la prueba falla indicando ambas versiones
