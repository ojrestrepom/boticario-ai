//! Errores de la ingesta que no son propios de la lectura de la semilla.

use std::error::Error;
use std::fmt;
use std::path::PathBuf;

/// Errores de entrada/salida, de almacenamiento SQLite o de una base ausente.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IngestError {
    /// Fallo de entrada/salida. `path` es `None` cuando no se conoce el archivo.
    Io {
        /// Archivo implicado, si se conoce.
        path: Option<PathBuf>,
        /// Mensaje del sistema operativo.
        message: String,
    },
    /// Fallo del almacenamiento SQLite, con un mensaje descriptivo.
    Storage(String),
    /// No existe una base de datos que se debía leer (por ejemplo `catalog.db`).
    MissingDatabase {
        /// Ruta donde se esperaba la base.
        path: PathBuf,
    },
}

impl fmt::Display for IngestError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io {
                path: Some(path),
                message,
            } => write!(f, "error de E/S en {}: {message}", path.display()),
            Self::Io {
                path: None,
                message,
            } => write!(f, "error de E/S: {message}"),
            Self::Storage(msg) => write!(f, "fallo de almacenamiento: {msg}"),
            Self::MissingDatabase { path } => {
                write!(f, "no existe la base de datos {}", path.display())
            }
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

impl From<diesel::result::Error> for IngestError {
    fn from(err: diesel::result::Error) -> Self {
        Self::Storage(err.to_string())
    }
}

impl From<diesel::result::ConnectionError> for IngestError {
    fn from(err: diesel::result::ConnectionError) -> Self {
        Self::Storage(err.to_string())
    }
}

impl From<catalog_core::version::SchemaError> for IngestError {
    fn from(err: catalog_core::version::SchemaError) -> Self {
        Self::Storage(err.to_string())
    }
}
