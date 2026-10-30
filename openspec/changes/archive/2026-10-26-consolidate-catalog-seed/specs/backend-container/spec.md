# Spec Delta

## ADDED Requirements

### Requirement: Reconstrucción incremental de la semilla y la API
Las reconstrucciones SHALL reutilizar la caché de construcción. Sin cambios, la reconstrucción SHALL reutilizar todas las capas. Con un cambio en un archivo Rust, SHALL recompilar sin descargar datos. Con un cambio en la semilla, SHALL reconstruir el catálogo sin recompilar el código de la API.

#### Scenario: Sin cambios
- **WHEN** se vuelve a construir la imagen sin modificar el repo
- **THEN** la construcción termina reutilizando la caché y no ejecuta de nuevo la compilación ni la construcción del catálogo

#### Scenario: Cambio en Rust
- **WHEN** se modifica un archivo Rust y se vuelve a construir la imagen
- **THEN** se recompila el código y no se descarga ningún dato

#### Scenario: Cambio en la semilla
- **WHEN** se modifica un registro de la semilla, con su manifiesto actualizado, y se vuelve a construir la imagen
- **THEN** se reconstruye el catálogo y no se recompila el binario de la API

## MODIFIED Requirements

### Requirement: Imagen autocontenida
La imagen SHALL contener la API y el catálogo ya construido, y SHALL servir sin acceso a la red. La imagen final SHALL NOT incluir la semilla, las herramientas de generación, el toolchain de Rust ni el código fuente, y SHALL NOT incluir ningún token de API: los tokens llegan siempre por el entorno en tiempo de ejecución.

#### Scenario: Servir sin red
- **WHEN** se ejecuta el contenedor sin acceso a la red y con `API_TOKENS` definido, y se consulta `GET /v1/plants/lavandula-angustifolia` con un token válido
- **THEN** la API responde 200 con el detalle de la planta

#### Scenario: Contenido mínimo
- **WHEN** se inspecciona el sistema de archivos de la imagen final
- **THEN** no existe `data/seed/`, `cargo`, `rustc` ni el código fuente, y sí existen el binario de la API y la base del catálogo

#### Scenario: Sin tokens en la imagen
- **WHEN** se inspeccionan las capas y la configuración de la imagen
- **THEN** no contienen ningún valor de `API_TOKENS` y la variable no tiene valor por defecto

### Requirement: Construcción reproducible del catálogo
El catálogo SHALL construirse al construir la imagen, no al arrancar el contenedor, a partir de la semilla del repositorio y sin descargar ningún dato, y la construcción SHALL imprimir el hash de contenido del catálogo. Ese hash SHALL ser igual al de una construcción nativa a partir de la misma semilla.

#### Scenario: Hash igual al nativo
- **WHEN** se construye la imagen y se compara el hash impreso en el log de construcción con el de una construcción nativa de la misma semilla
- **THEN** ambos hashes son idénticos

#### Scenario: Insumo alterado
- **WHEN** un registro de la semilla no coincide con el hash de su manifiesto
- **THEN** la construcción de la imagen falla y no produce imagen

#### Scenario: Sin descargas de datos
- **WHEN** se construye la imagen con la caché de Docker vacía
- **THEN** la etapa del catálogo no realiza ninguna conexión de red para obtener datos

### Requirement: Construcción sin preparación previa
`docker compose build` SHALL construir la imagen en una máquina que solo tiene Docker con Compose y acceso a la red para obtener las imágenes base y los crates de Rust, sin Rust, mise, un compilador de C ni descargas manuales previas de datos.

#### Scenario: Máquina limpia
- **WHEN** un compañero con solo Docker ejecuta `docker compose build` desde la raíz del repo
- **THEN** la imagen se construye con éxito

## REMOVED Requirements

### Requirement: Reconstrucción incremental con caché
**Reason**: Su caché de construcción guardaba el ZIP de USDA descargado y lo revalidaba por tamaño y MD5; la construcción ya no descarga datos y el ZIP desaparece. La reconstrucción incremental se reexpresa en «Reconstrucción incremental de la semilla y la API».
**Migration**: Véase «Reconstrucción incremental de la semilla y la API».
