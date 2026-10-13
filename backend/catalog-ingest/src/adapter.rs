//! Contrato de adaptador de fuente.
//!
//! Un adaptador es lo único que conoce un dataset concreto. Hace dos cosas: dice cómo importar su crudo y deriva, desde las tablas crudas, registros normalizados con un formato común. Lo demás (consolidar, escribir la base neutral) no sabe de qué dataset vienen.

use std::path::Path;

use catalog_core::domain::Source;

use crate::error::IngestError;
use crate::raw::RawImportSpec;

/// Insumo que hay que descargar y verificar antes de importarlo.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InputDescriptor {
    /// Nombre del archivo en la caché local.
    pub file_name: String,
    /// URL de descarga.
    pub download_url: String,
    /// Tamaño esperado, en bytes.
    pub expected_size: u64,
    /// MD5 esperado (hexadecimal en minúsculas).
    pub expected_md5: String,
}

/// Nombre de una planta tal como lo entrega una fuente.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NameRecord {
    /// Texto del nombre.
    pub text: String,
    /// Código de idioma, por ejemplo `en`.
    pub language: String,
}

/// Uso de una planta; la referencia se indica por id y se resuelve al consolidar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UseRecord {
    /// Actividad o propiedad atribuida.
    pub activity: String,
    /// Idioma de la etiqueta de actividad.
    pub language: String,
    /// Id de una [`ReferenceRecord`] de la misma fuente.
    pub reference_id: String,
}

/// Referencia bibliográfica de una fuente.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReferenceRecord {
    /// Identificador de la referencia.
    pub id: String,
    /// Cita completa.
    pub citation: String,
}

/// Planta normalizada, sin identidad pública todavía.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlantRecord {
    /// Identificador de la planta dentro de la fuente (va a la tabla de enlace).
    pub source_plant_id: String,
    /// Nombre científico.
    pub scientific_name: String,
    /// Familia, si la fuente la conoce.
    pub family: Option<String>,
    /// Nombres comunes.
    pub common_names: Vec<NameRecord>,
    /// Etiquetas de las partes de la planta.
    pub parts: Vec<String>,
    /// Usos de la planta.
    pub uses: Vec<UseRecord>,
}

/// Todo lo que una fuente aporta, ya normalizado.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct SourceRecords {
    /// Plantas de la fuente.
    pub plants: Vec<PlantRecord>,
    /// Referencias de la fuente.
    pub references: Vec<ReferenceRecord>,
}

/// Contrato que implementa cada fuente de datos.
///
/// No exige `Send + Sync`: la construcción es secuencial y de un solo hilo. Si algún día se paraleliza, bastará con añadir esos límites aquí (`trait SourceAdapter: Send + Sync`).
pub trait SourceAdapter {
    /// Metadatos de la fuente.
    fn source(&self) -> Source;
    /// Insumo que hay que descargar y verificar.
    fn input(&self) -> InputDescriptor;
    /// Cómo importar el crudo; recibe la ruta del archivo ya verificado.
    fn raw_import(&self, archive: &Path) -> RawImportSpec;
    /// Deriva registros normalizados leyendo solo las tablas crudas de su fuente.
    fn derive(&self, raw: &rusqlite::Connection) -> Result<SourceRecords, IngestError>;
}

/// Comprueba que la fuente declara todos sus metadatos y que su id es seguro para nombres de tabla.
///
/// El id forma parte de los nombres `raw_<fuente>_<tabla>`, por eso se restringe a `[a-z0-9_]`.
pub fn validate_source(source: &Source) -> Result<(), IngestError> {
    let id = source.id.0.as_str();
    let missing = |field| IngestError::MissingMetadata {
        source: id.to_string(),
        field,
    };
    if id.trim().is_empty() {
        return Err(missing("id"));
    }
    if !id
        .chars()
        .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_')
    {
        return Err(IngestError::InvalidSourceId { id: id.to_string() });
    }
    let fields = [
        ("name", &source.name),
        ("version", &source.version),
        ("license", &source.license),
        ("citation", &source.citation),
        ("url", &source.url),
        ("checksum", &source.checksum),
    ];
    for (field, value) in fields {
        if value.trim().is_empty() {
            return Err(missing(field));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{FixtureAdapter, alpha_records, fixture_source};

    #[test]
    fn conforming_adapter_passes_validation() {
        let adapter = FixtureAdapter::new("alpha", alpha_records());
        assert_eq!(validate_source(&adapter.source()), Ok(()));
        assert_eq!(adapter.input().file_name, "alpha.zip");
        let spec = adapter.raw_import(Path::new("x.zip"));
        assert_eq!(spec.source_id, "alpha");
    }

    #[test]
    fn empty_license_names_source_and_field() {
        let mut source = fixture_source("alpha");
        source.license = "   ".to_string();
        let err = validate_source(&source).unwrap_err();
        assert_eq!(
            err,
            IngestError::MissingMetadata {
                source: "alpha".to_string(),
                field: "license"
            }
        );
        let msg = err.to_string();
        assert!(msg.contains("alpha") && msg.contains("license"));
    }

    #[test]
    fn each_field_is_required() {
        for field in ["name", "version", "license", "citation", "url", "checksum"] {
            let mut source = fixture_source("alpha");
            match field {
                "name" => source.name.clear(),
                "version" => source.version.clear(),
                "license" => source.license.clear(),
                "citation" => source.citation.clear(),
                "url" => source.url.clear(),
                _ => source.checksum.clear(),
            }
            match validate_source(&source) {
                Err(IngestError::MissingMetadata { field: f, .. }) => assert_eq!(f, field),
                other => panic!("campo {field}: {other:?}"),
            }
        }
    }

    #[test]
    fn invalid_ids_are_rejected() {
        for id in ["Alpha", "al-pha", "al pha", "alfa\u{f1}"] {
            assert_eq!(
                validate_source(&fixture_source(id)),
                Err(IngestError::InvalidSourceId { id: id.to_string() }),
                "id {id:?}"
            );
        }
        assert!(matches!(
            validate_source(&fixture_source("")),
            Err(IngestError::MissingMetadata { field: "id", .. })
        ));
        assert_eq!(validate_source(&fixture_source("a_1")), Ok(()));
    }
}
