//! Verificación del insumo descargado (tamaño y MD5) antes de leerlo.

use std::fs::File;
use std::io::{ErrorKind, Read};
use std::path::Path;

use md5::{Digest, Md5};

use crate::error::IngestError;

/// Insumo y valores que debe cumplir, declarados por el adaptador.
///
/// El lifetime `'a` dice que la estructura solo *presta* la ruta y el checksum: no los copia, y por eso no puede vivir más que los datos prestados.
#[derive(Debug, Clone, Copy)]
pub struct InputSpec<'a> {
    /// Ruta del archivo descargado.
    pub path: &'a Path,
    /// Tamaño esperado, en bytes.
    pub expected_size: u64,
    /// MD5 esperado en hexadecimal (se acepta en mayúsculas o minúsculas).
    pub expected_md5: &'a str,
}

/// Comprueba existencia, tamaño y MD5 del insumo, en ese orden.
///
/// El tamaño se mira antes que el MD5 porque es barato y evita leer un archivo enorme que ya sabemos incorrecto.
pub fn verify_input(spec: &InputSpec<'_>) -> Result<(), IngestError> {
    let io_error = |err: std::io::Error| IngestError::Io {
        path: Some(spec.path.to_path_buf()),
        message: err.to_string(),
    };

    let metadata = match std::fs::metadata(spec.path) {
        Ok(metadata) => metadata,
        Err(err) if err.kind() == ErrorKind::NotFound => {
            return Err(IngestError::MissingInput {
                path: spec.path.to_path_buf(),
            });
        }
        Err(err) => return Err(io_error(err)),
    };

    if metadata.len() != spec.expected_size {
        return Err(IngestError::SizeMismatch {
            expected: spec.expected_size,
            found: metadata.len(),
        });
    }

    // Se lee por bloques para no cargar el archivo completo en memoria.
    let mut file = File::open(spec.path).map_err(io_error)?;
    let mut hasher = Md5::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let n = file.read(&mut buffer).map_err(io_error)?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }
    // El resumen son 16 bytes; cada uno se escribe como dos dígitos hexadecimales en minúsculas.
    let found: String = hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect();

    let expected = spec.expected_md5.to_ascii_lowercase();
    if found != expected {
        return Err(IngestError::ChecksumMismatch { expected, found });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // MD5 de "hello world\n".
    const CONTENT: &[u8] = b"hello world\n";
    const MD5: &str = "6f5902ac237024bdd0c176cb93063dc4";

    fn fixture(content: &[u8]) -> (tempfile::TempDir, std::path::PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("input.zip");
        std::fs::write(&path, content).unwrap();
        (dir, path)
    }

    #[test]
    fn intact_file_passes() {
        let (_dir, path) = fixture(CONTENT);
        let spec = InputSpec {
            path: &path,
            expected_size: CONTENT.len() as u64,
            expected_md5: MD5,
        };
        assert_eq!(verify_input(&spec), Ok(()));
    }

    #[test]
    fn uppercase_expected_md5_is_accepted() {
        let (_dir, path) = fixture(CONTENT);
        let upper = MD5.to_ascii_uppercase();
        let spec = InputSpec {
            path: &path,
            expected_size: CONTENT.len() as u64,
            expected_md5: &upper,
        };
        assert_eq!(verify_input(&spec), Ok(()));
    }

    #[test]
    fn altered_byte_fails_checksum() {
        let (_dir, path) = fixture(b"hello_world\n");
        let spec = InputSpec {
            path: &path,
            expected_size: CONTENT.len() as u64,
            expected_md5: MD5,
        };
        assert!(matches!(
            verify_input(&spec),
            Err(IngestError::ChecksumMismatch { .. })
        ));
    }

    #[test]
    fn different_size_fails() {
        let (_dir, path) = fixture(CONTENT);
        let spec = InputSpec {
            path: &path,
            expected_size: 99,
            expected_md5: MD5,
        };
        let err = verify_input(&spec).unwrap_err();
        assert_eq!(
            err,
            IngestError::SizeMismatch {
                expected: 99,
                found: CONTENT.len() as u64
            }
        );
        assert_eq!(
            err.to_string(),
            "tamaño distinto del declarado: se esperaban 99 bytes y hay 12"
        );
    }

    #[test]
    fn missing_file_mentions_download_step() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("absent.zip");
        let spec = InputSpec {
            path: &path,
            expected_size: 1,
            expected_md5: MD5,
        };
        let err = verify_input(&spec).unwrap_err();
        assert!(matches!(err, IngestError::MissingInput { .. }));
        let text = err.to_string();
        assert!(text.contains("absent.zip"));
        assert!(text.contains("paso de descarga"));
    }
}
