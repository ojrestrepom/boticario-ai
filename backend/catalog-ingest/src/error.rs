//! Errores de la ingesta.

use std::error::Error;
use std::fmt;
use std::path::PathBuf;

/// Errores que puede devolver la verificación del insumo o la importación cruda.
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
