//! Utilidades compartidas por los tests (no se compila fuera de `cargo test`).

use std::io::Write;
use std::path::PathBuf;

use zip::write::SimpleFileOptions;

/// Crea un ZIP en `dir` con las entradas `(nombre, contenido)`, codificando cada contenido en Windows-1252.
pub fn build_zip(dir: &tempfile::TempDir, entries: &[(&str, &str)]) -> PathBuf {
    let path = dir.path().join("fixture.zip");
    let mut writer = zip::ZipWriter::new(std::fs::File::create(&path).unwrap());
    // `Stored` evita depender de la compresión: el fixture solo necesita ser un ZIP válido.
    let options = SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored);
    for (name, content) in entries {
        let (bytes, _, unmappable) = encoding_rs::WINDOWS_1252.encode(content);
        assert!(
            !unmappable,
            "el fixture usa un carácter fuera de Windows-1252"
        );
        writer.start_file(*name, options).unwrap();
        writer.write_all(&bytes).unwrap();
    }
    writer.finish().unwrap();
    path
}

use std::path::Path;

use catalog_core::domain::{Source, SourceId};

use crate::adapter::{
    InputDescriptor, NameRecord, PlantRecord, ReferenceRecord, SourceAdapter, SourceRecords,
    UseRecord,
};
use crate::error::IngestError;
use crate::raw::{RawFiles, RawImportSpec};

/// Fuente de fixture con todos los metadatos completos.
pub fn fixture_source(id: &str) -> Source {
    Source {
        id: SourceId(id.to_string()),
        name: format!("Fuente {id}"),
        version: "1".to_string(),
        license: "CC0".to_string(),
        citation: format!("Cita de {id}"),
        url: format!("https://example.test/{id}"),
        checksum: "d41d8cd98f00b204e9800998ecf8427e".to_string(),
    }
}

/// Atajo para construir un [`NameRecord`].
pub fn name(text: &str, language: &str) -> NameRecord {
    NameRecord {
        text: text.to_string(),
        language: language.to_string(),
    }
}

/// Atajo para construir un [`UseRecord`].
pub fn use_rec(activity: &str, language: &str, reference_id: &str) -> UseRecord {
    UseRecord {
        activity: activity.to_string(),
        language: language.to_string(),
        reference_id: reference_id.to_string(),
    }
}

/// Atajo para construir un [`ReferenceRecord`].
pub fn reference(id: &str, citation: &str) -> ReferenceRecord {
    ReferenceRecord {
        id: id.to_string(),
        citation: citation.to_string(),
    }
}

/// Planta vacía con identificador y nombre científico.
pub fn plant(source_plant_id: &str, scientific_name: &str) -> PlantRecord {
    PlantRecord {
        source_plant_id: source_plant_id.to_string(),
        scientific_name: scientific_name.to_string(),
        family: None,
        common_names: vec![],
        parts: vec![],
        uses: vec![],
    }
}

/// Registros de `alpha`: lavanda con familia `Lamiaceae`.
pub fn alpha_records() -> SourceRecords {
    SourceRecords {
        plants: vec![PlantRecord {
            family: Some("Lamiaceae".to_string()),
            common_names: vec![name("lavender", "en"), name("English lavender", "en")],
            parts: vec!["Flower".to_string(), "Leaf".to_string()],
            uses: vec![
                use_rec("Sedative", "en", "r1"),
                use_rec("Antiseptic", "en", "r2"),
            ],
            ..plant("A1", "Lavandula angustifolia")
        }],
        references: vec![reference("r1", "Cita uno"), reference("r2", "Cita dos")],
    }
}

/// Registros de `beta`: misma lavanda (otra ortografía), otra familia, y una planta propia.
pub fn beta_records() -> SourceRecords {
    SourceRecords {
        plants: vec![
            PlantRecord {
                family: Some("Labiatae".to_string()),
                common_names: vec![name("lavender", "en"), name("lavanda", "es")],
                parts: vec!["Flower".to_string(), "Root".to_string()],
                uses: vec![
                    use_rec("Sedative", "en", "r1"),
                    use_rec("Insecticide", "en", "r3"),
                ],
                ..plant("B7", "LAVANDULA  angustifolia")
            },
            PlantRecord {
                family: Some("Asteraceae".to_string()),
                common_names: vec![name("chamomile", "en")],
                parts: vec!["Flower".to_string()],
                uses: vec![use_rec("Calmative", "en", "r1")],
                ..plant("B8", "Matricaria chamomilla")
            },
        ],
        references: vec![reference("r1", "Cita uno"), reference("r3", "Cita tres")],
    }
}

/// Adaptador de fixture: entrega siempre los registros con los que se construyó.
pub struct FixtureAdapter {
    pub source: Source,
    pub records: SourceRecords,
}

impl FixtureAdapter {
    pub fn new(id: &str, records: SourceRecords) -> Self {
        Self {
            source: fixture_source(id),
            records,
        }
    }
}

impl SourceAdapter for FixtureAdapter {
    fn source(&self) -> Source {
        self.source.clone()
    }

    fn input(&self) -> InputDescriptor {
        InputDescriptor {
            file_name: format!("{}.zip", self.source.id.0),
            download_url: self.source.url.clone(),
            expected_size: 0,
            expected_md5: self.source.checksum.clone(),
        }
    }

    fn raw_import(&self, archive: &Path) -> RawImportSpec {
        RawImportSpec {
            source_id: self.source.id.0.clone(),
            archive: archive.to_path_buf(),
            encoding: encoding_rs::WINDOWS_1252,
            files: RawFiles::AllCsv,
        }
    }

    fn derive(&self, _raw: &rusqlite::Connection) -> Result<SourceRecords, IngestError> {
        Ok(self.records.clone())
    }
}
