//! Adaptador de la fuente USDA (Dr. Duke's Phytochemical and Ethnobotanical Databases).
//!
//! Los valores de procedencia salen literalmente de `docs/data/usda-catalog.md`; si cambian allí, deben cambiar aquí.

use std::path::Path;

use catalog_core::domain::{Source, SourceId};

use crate::adapter::{InputDescriptor, SourceAdapter, SourceRecords};
use crate::error::IngestError;
use crate::raw::{RawFiles, RawImportSpec};

/// Identificador de la fuente (parte de los nombres de tabla cruda).
pub const SOURCE_ID: &str = "usda";
/// Nombre legible de la fuente.
pub const SOURCE_NAME: &str = "USDA Dr. Duke's Phytochemical and Ethnobotanical Databases";
/// Versión del dataset archivado.
pub const VERSION: &str = "1";
/// Licencia declarada por USDA.
pub const LICENSE: &str = "CC0";
/// Cita registrada por la API de Figshare para el artículo.
pub const CITATION: &str = "Duke, James A. (2016). Dr. Duke's Phytochemical and Ethnobotanical Databases. Ag Data Commons. Dataset. https://doi.org/10.15482/USDA.ADC/1239279";
/// URL del artículo del dataset en Ag Data Commons.
pub const ARTICLE_URL: &str = "https://agdatacommons.nal.usda.gov/articles/dataset/Dr_Duke_s_Phytochemical_and_Ethnobotanical_Databases/24660351";
/// Nombre del ZIP en la caché local.
pub const FILE_NAME: &str = "Duke-Source-CSV.zip";
/// URL de descarga del ZIP (Figshare redirige a un almacenamiento S3).
pub const DOWNLOAD_URL: &str = "https://ndownloader.figshare.com/files/43363335";
/// Tamaño del ZIP, en bytes.
pub const FILE_SIZE: u64 = 6_033_990;
/// MD5 del ZIP, en hexadecimal minúsculas.
pub const FILE_MD5: &str = "45ae44a0544586b8ac22a232beaac344";

/// Adaptador de USDA. No tiene estado: es un tipo unitario, solo agrupa el comportamiento.
pub struct UsdaAdapter;

impl SourceAdapter for UsdaAdapter {
    fn source(&self) -> Source {
        Source {
            id: SourceId(SOURCE_ID.to_string()),
            name: SOURCE_NAME.to_string(),
            version: VERSION.to_string(),
            license: LICENSE.to_string(),
            citation: CITATION.to_string(),
            url: ARTICLE_URL.to_string(),
            checksum: FILE_MD5.to_string(),
        }
    }

    fn input(&self) -> InputDescriptor {
        InputDescriptor {
            file_name: FILE_NAME.to_string(),
            download_url: DOWNLOAD_URL.to_string(),
            expected_size: FILE_SIZE,
            expected_md5: FILE_MD5.to_string(),
        }
    }

    fn raw_import(&self, archive: &Path) -> RawImportSpec {
        RawImportSpec {
            source_id: SOURCE_ID.to_string(),
            archive: archive.to_path_buf(),
            // La guía documenta que los CSV de este ZIP están en Windows-1252.
            encoding: encoding_rs::WINDOWS_1252,
            // Se importan todas las tablas, no solo las que usa la derivación.
            files: RawFiles::AllCsv,
        }
    }

    fn derive(&self, _raw: &rusqlite::Connection) -> Result<SourceRecords, IngestError> {
        // TEMPORAL: la derivación real llega en la tarea 5.3.
        Err(IngestError::Storage(
            "la derivación de USDA se implementa en la tarea 5.3".into(),
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::validate_source;

    #[test]
    fn metadata_is_complete() {
        assert_eq!(validate_source(&UsdaAdapter.source()), Ok(()));
        assert_eq!(UsdaAdapter.source().id.0, "usda");
    }

    #[test]
    fn input_matches_the_guide() {
        assert_eq!(
            UsdaAdapter.input(),
            InputDescriptor {
                file_name: "Duke-Source-CSV.zip".to_string(),
                download_url: "https://ndownloader.figshare.com/files/43363335".to_string(),
                expected_size: 6_033_990,
                expected_md5: "45ae44a0544586b8ac22a232beaac344".to_string(),
            }
        );
    }

    #[test]
    fn raw_import_reads_all_csv_as_windows_1252() {
        let spec = UsdaAdapter.raw_import(Path::new("x.zip"));
        assert_eq!(spec.source_id, "usda");
        assert_eq!(spec.encoding, encoding_rs::WINDOWS_1252);
        assert_eq!(spec.files, RawFiles::AllCsv);
    }
}
