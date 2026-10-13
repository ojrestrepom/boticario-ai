//! Errores de la ingesta.

use std::error::Error;
use std::fmt;
use std::path::PathBuf;

/// Errores que puede devolver la verificación del insumo, la importación cruda, la configuración y la consolidación.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IngestError {
    /// El insumo no existe: falta ejecutar el paso de descarga.
    MissingInput {
        /// Ruta donde se esperaba el insumo.
        path: PathBuf,
    },
    /// El tamaño del insumo no coincide con el declarado.
    SizeMismatch {
        /// Tamaño declarado, en bytes.
        expected: u64,
        /// Tamaño encontrado, en bytes.
        found: u64,
    },
    /// El checksum MD5 del insumo no coincide con el declarado.
    ChecksumMismatch {
        /// MD5 declarado (hexadecimal en minúsculas).
        expected: String,
        /// MD5 calculado (hexadecimal en minúsculas).
        found: String,
    },
    /// Fallo de entrada/salida. `path` es `None` cuando no se conoce el archivo.
    Io {
        /// Archivo implicado, si se conoce.
        path: Option<PathBuf>,
        /// Mensaje del sistema operativo.
        message: String,
    },
    /// El archivo ZIP es inválido o le falta una entrada pedida.
    InvalidZip {
        /// Descripción del problema.
        message: String,
    },
    /// Un CSV no se pudo decodificar o leer.
    InvalidCsv {
        /// Nombre de la entrada del ZIP.
        file: String,
        /// Fila de datos (1 = primera fila tras la cabecera), si aplica.
        row: Option<u64>,
        /// Descripción del problema.
        message: String,
    },
    /// La cabecera de un CSV falta, tiene una columna vacía o repite nombres.
    InvalidHeader {
        /// Nombre de la entrada del ZIP.
        file: String,
        /// Columna problemática, o vacío si falta la cabecera entera.
        column: String,
        /// Descripción del problema.
        message: String,
    },
    /// Fallo del almacenamiento SQLite, con un mensaje descriptivo.
    Storage(String),
    /// A una fuente le falta un metadato obligatorio (vacío o solo espacios).
    MissingMetadata {
        /// Identificador de la fuente (puede estar vacío si lo que falta es el propio id).
        source: String,
        /// Campo ausente: `id`, `name`, `version`, `license`, `citation`, `url` o `checksum`.
        field: &'static str,
    },
    /// El identificador de la fuente tiene caracteres fuera de `[a-z0-9_]`.
    InvalidSourceId {
        /// Identificador rechazado.
        id: String,
    },
    /// El archivo de configuración de fuentes es inválido.
    InvalidConfig {
        /// Archivo leído, si la configuración vino de uno.
        path: Option<PathBuf>,
        /// Descripción del problema.
        message: String,
    },
    /// La configuración pide una fuente para la que no hay adaptador registrado.
    UnknownSource {
        /// Identificador pedido.
        id: String,
    },
    /// Se registraron dos adaptadores con el mismo identificador de fuente.
    DuplicateAdapter {
        /// Identificador repetido.
        id: String,
    },
    /// Una fuente entregó dos plantas con la misma identidad canónica.
    DuplicateIdentity {
        /// Fuente que repite la identidad.
        source: String,
        /// Identidad canónica (nombre científico normalizado).
        identity: String,
        /// Identificador en la fuente del primer registro.
        first_source_plant_id: String,
        /// Identificador en la fuente del segundo registro.
        second_source_plant_id: String,
    },
    /// Dos identidades distintas producen el mismo slug (ID público).
    SlugCollision {
        /// Slug repetido.
        slug: String,
        /// Primera identidad canónica.
        first_identity: String,
        /// Segunda identidad canónica.
        second_identity: String,
    },
    /// Un uso apunta a una referencia que su propia fuente no entregó.
    UnresolvedReference {
        /// Fuente del uso.
        source: String,
        /// Planta de la fuente a la que pertenece el uso.
        source_plant_id: String,
        /// Referencia que no se encontró.
        reference_id: String,
    },
    /// Un mismo identificador de referencia tiene citas distintas.
    ConflictingReference {
        /// Identificador de la referencia.
        id: String,
        /// Fuente que la entregó primero.
        first_source: String,
        /// Fuente cuya cita difiere (puede ser la misma fuente).
        second_source: String,
    },
}

impl fmt::Display for IngestError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingInput { path } => write!(
                f,
                "no existe el insumo {}: ejecuta primero el paso de descarga",
                path.display()
            ),
            Self::SizeMismatch { expected, found } => write!(
                f,
                "tamaño distinto del declarado: se esperaban {expected} bytes y hay {found}"
            ),
            Self::ChecksumMismatch { expected, found } => write!(
                f,
                "checksum MD5 distinto del declarado: se esperaba {expected} y se obtuvo {found}"
            ),
            Self::Io {
                path: Some(path),
                message,
            } => write!(f, "error de E/S en {}: {message}", path.display()),
            Self::Io {
                path: None,
                message,
            } => write!(f, "error de E/S: {message}"),
            Self::InvalidZip { message } => write!(f, "ZIP inválido: {message}"),
            Self::InvalidCsv {
                file,
                row: Some(row),
                message,
            } => write!(f, "CSV inválido en {file}, fila {row}: {message}"),
            Self::InvalidCsv {
                file,
                row: None,
                message,
            } => write!(f, "CSV inválido en {file}: {message}"),
            Self::InvalidHeader {
                file,
                column,
                message,
            } => write!(
                f,
                "cabecera inválida en {file} (columna \"{column}\"): {message}"
            ),
            Self::Storage(msg) => write!(f, "fallo de almacenamiento: {msg}"),
            Self::MissingMetadata { source, field } => write!(
                f,
                "la fuente \"{source}\" no declara el metadato obligatorio `{field}`"
            ),
            Self::InvalidSourceId { id } => write!(
                f,
                "identificador de fuente inválido \"{id}\": solo se admiten [a-z0-9_]"
            ),
            Self::InvalidConfig {
                path: Some(path),
                message,
            } => write!(
                f,
                "configuración de fuentes inválida en {}: {message}",
                path.display()
            ),
            Self::InvalidConfig {
                path: None,
                message,
            } => write!(f, "configuración de fuentes inválida: {message}"),
            Self::UnknownSource { id } => write!(
                f,
                "la configuración activa la fuente \"{id}\" pero no hay adaptador registrado para ella"
            ),
            Self::DuplicateAdapter { id } => {
                write!(f, "ya hay un adaptador registrado para la fuente \"{id}\"")
            }
            Self::DuplicateIdentity {
                source,
                identity,
                first_source_plant_id,
                second_source_plant_id,
            } => write!(
                f,
                "la fuente \"{source}\" repite la identidad \"{identity}\": registros \"{first_source_plant_id}\" y \"{second_source_plant_id}\""
            ),
            Self::SlugCollision {
                slug,
                first_identity,
                second_identity,
            } => write!(
                f,
                "colisión de slug \"{slug}\" entre las identidades \"{first_identity}\" y \"{second_identity}\""
            ),
            Self::UnresolvedReference {
                source,
                source_plant_id,
                reference_id,
            } => write!(
                f,
                "la planta \"{source_plant_id}\" de la fuente \"{source}\" usa la referencia \"{reference_id}\", que esa fuente no entregó"
            ),
            Self::ConflictingReference {
                id,
                first_source,
                second_source,
            } => write!(
                f,
                "la referencia \"{id}\" tiene citas distintas en las fuentes \"{first_source}\" y \"{second_source}\""
            ),
        }
    }
}

impl Error for IngestError {}

// Las conversiones `From` permiten usar `?` directamente: el compilador llama a `from` por nosotros.
impl From<std::io::Error> for IngestError {
    fn from(err: std::io::Error) -> Self {
        Self::Io {
            path: None,
            message: err.to_string(),
        }
    }
}

impl From<rusqlite::Error> for IngestError {
    fn from(err: rusqlite::Error) -> Self {
        Self::Storage(err.to_string())
    }
}

impl From<zip::result::ZipError> for IngestError {
    fn from(err: zip::result::ZipError) -> Self {
        Self::InvalidZip {
            message: err.to_string(),
        }
    }
}
