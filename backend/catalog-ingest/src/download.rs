//! Descarga explícita del insumo de una fuente a la caché local.
//!
//! Es un paso aparte de la construcción: construir nunca toca la red.

use std::fs::{self, File};
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::time::Duration;

use crate::adapter::SourceAdapter;
use crate::error::IngestError;
use crate::input::{InputSpec, verify_input};

/// Tiempo máximo de toda la descarga (conexión, redirecciones y cuerpo).
///
/// Sin él, un servidor que no responde dejaría la CLI colgada indefinidamente. Diez minutos sobran para el insumo conocido (decenas de MB) incluso con una conexión lenta.
const DOWNLOAD_TIMEOUT: Duration = Duration::from_secs(600);

/// Qué pasó con el insumo.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DownloadOutcome {
    /// Ya estaba en la caché y pasó la verificación; no se tocó la red.
    AlreadyPresent(PathBuf),
    /// Se descargó y verificó ahora.
    Downloaded(PathBuf),
}

/// Deja el insumo del adaptador en `cache_dir`, verificado por tamaño y MD5.
///
/// Un archivo existente que no pasa la verificación **no se borra**: es del usuario, y se le pide que lo elimine él.
pub fn download_input(
    adapter: &dyn SourceAdapter,
    cache_dir: &Path,
) -> Result<DownloadOutcome, IngestError> {
    let input = adapter.input();
    let target = cache_dir.join(&input.file_name);
    let verify = |path: &Path| -> Result<(), IngestError> {
        verify_input(&InputSpec {
            path,
            expected_size: input.expected_size,
            expected_md5: &input.expected_md5,
        })
    };

    if target.exists() {
        return match verify(&target) {
            Ok(()) => Ok(DownloadOutcome::AlreadyPresent(target)),
            Err(err) => Err(IngestError::Download {
                url: input.download_url.clone(),
                message: format!(
                    "{} ya existe pero no es íntegro ({err}); bórralo y vuelve a ejecutar la descarga",
                    target.display()
                ),
            }),
        };
    }

    fs::create_dir_all(cache_dir).map_err(|e| IngestError::Io {
        path: Some(cache_dir.to_path_buf()),
        message: e.to_string(),
    })?;

    // Se descarga a un archivo temporal para que un corte a medias nunca parezca un insumo válido.
    let part = cache_dir.join(format!("{}.part", input.file_name));
    let result =
        fetch_to(&input.download_url, &part, input.expected_size).and_then(|()| verify(&part));
    match result {
        Ok(()) => {
            fs::rename(&part, &target).map_err(|e| IngestError::Io {
                path: Some(target.clone()),
                message: e.to_string(),
            })?;
            Ok(DownloadOutcome::Downloaded(target))
        }
        Err(err) => {
            // Si el borrado falla no hay nada más que hacer; el error original es el importante.
            let _ = fs::remove_file(&part);
            Err(err)
        }
    }
}

/// Descarga `url` a `dest` copiando el cuerpo por bloques (no se carga entero en memoria).
///
/// Se lee como máximo `expected_size + 1` bytes: un cuerpo mayor de lo esperado llega con un byte de más y la verificación posterior falla por tamaño, en lugar de llenar el disco.
fn fetch_to(url: &str, dest: &Path, expected_size: u64) -> Result<(), IngestError> {
    let download_error = |message: String| IngestError::Download {
        url: url.to_string(),
        message,
    };
    // `ureq` sigue las redirecciones por defecto (Figshare redirige a S3).
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(DOWNLOAD_TIMEOUT))
        .build()
        .into();
    let response = agent
        .get(url)
        .call()
        .map_err(|e| download_error(e.to_string()))?;
    let mut reader = response
        .into_body()
        .into_reader()
        .take(expected_size.saturating_add(1));
    let mut file = File::create(dest).map_err(|e| IngestError::Io {
        path: Some(dest.to_path_buf()),
        message: e.to_string(),
    })?;
    io::copy(&mut reader, &mut file).map_err(|e| download_error(e.to_string()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{StaticAdapter, alpha_records};

    // `StaticAdapter` espera 0 bytes y el MD5 del vacío: un archivo vacío es íntegro y uno con contenido no.
    fn adapter() -> StaticAdapter {
        StaticAdapter::new("alpha", alpha_records())
    }

    #[test]
    fn intact_file_is_already_present() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("alpha.zip");
        fs::write(&path, b"").unwrap();
        let outcome = download_input(&adapter(), dir.path()).unwrap();
        assert_eq!(outcome, DownloadOutcome::AlreadyPresent(path));
    }

    #[test]
    fn corrupt_file_is_reported_and_kept() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("alpha.zip");
        fs::write(&path, b"corrupto").unwrap();
        let err = download_input(&adapter(), dir.path()).unwrap_err();
        assert!(matches!(err, IngestError::Download { .. }));
        assert!(err.to_string().contains("bórralo"));
        assert_eq!(fs::read(&path).unwrap(), b"corrupto");
    }
}
