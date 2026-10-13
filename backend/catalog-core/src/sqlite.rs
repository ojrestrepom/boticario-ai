//! Ayudas para abrir bases SQLite que comparten la ingesta y la API.

use std::error::Error;
use std::fmt;
use std::path::{Path, PathBuf};

/// La ruta de la base no se puede expresar como URL de SQLite porque no es UTF-8 válido.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InvalidPath {
    /// Ruta rechazada.
    pub path: PathBuf,
}

impl fmt::Display for InvalidPath {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "la ruta {} no es UTF-8 válido", self.path.display())
    }
}

impl Error for InvalidPath {}

/// URL de SQLite para abrir `path` en solo lectura: `file:<ruta>?mode=ro`.
///
/// Diesel abre las conexiones con soporte de URI, y `mode=ro` hace que SQLite rechace cualquier escritura. En una URI, `%`, `?` y `#` tienen significado propio, así que se escapan en la ruta.
pub fn read_only_url(path: &Path) -> Result<String, InvalidPath> {
    let text = path.to_str().ok_or_else(|| InvalidPath {
        path: path.to_path_buf(),
    })?;
    let escaped = text
        .replace('%', "%25")
        .replace('?', "%3F")
        .replace('#', "%23");
    Ok(format!("file:{escaped}?mode=ro"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn read_only_url_escapes_uri_characters() {
        assert_eq!(
            read_only_url(Path::new("a#b?c%d/raw.db")).unwrap(),
            "file:a%23b%3Fc%25d/raw.db?mode=ro"
        );
    }
}
