//! Costura entre la lógica de la API y el almacenamiento.

use std::error::Error;
use std::fmt;

use crate::domain::{ListQuery, Page, Plant, PlantId, PlantSummary, Source};

/// Errores que puede devolver un repositorio.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RepositoryError {
    /// Fallo del almacenamiento subyacente, con un mensaje descriptivo.
    Storage(String),
    /// La base tiene una versión de esquema que este código no soporta.
    IncompatibleSchema {
        /// Versión encontrada en la base.
        found: u32,
        /// Versión que soporta este código.
        supported: u32,
    },
}

impl fmt::Display for RepositoryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Storage(msg) => write!(f, "fallo de almacenamiento: {msg}"),
            Self::IncompatibleSchema { found, supported } => write!(
                f,
                "esquema incompatible: la base es v{found} y se soporta v{supported}"
            ),
        }
    }
}

// Basta con marcar el tipo: `Error` exige `Debug + Display` y todo lo demás tiene implementación por defecto.
impl Error for RepositoryError {}

/// Acceso de solo lectura al catálogo.
///
/// Es síncrono a propósito: la API lo ejecuta con `spawn_blocking`. Exige `Send + Sync` para poder compartirse entre hilos (por ejemplo dentro de un `Arc`).
pub trait CatalogRepository: Send + Sync {
    /// Lista plantas filtradas por `query.q`, con orden total (nombre científico, luego id).
    fn list_plants(&self, query: &ListQuery) -> Result<Page<PlantSummary>, RepositoryError>;

    /// Devuelve el detalle de una planta, o `None` si no existe.
    fn get_plant(&self, id: &PlantId) -> Result<Option<Plant>, RepositoryError>;

    /// Lista las fuentes de datos del catálogo.
    fn list_sources(&self) -> Result<Vec<Source>, RepositoryError>;
}
