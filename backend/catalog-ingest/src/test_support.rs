//! Utilidades compartidas por los tests (solo se compila con `cargo test` o con la feature `test-fixtures`).

#![allow(missing_docs)]

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
use crate::consolidate::SourceInput;
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

/// Adaptador de fixture que entrega registros ya hechos, sin leer el crudo (para tests que no necesitan SQLite).
pub struct StaticAdapter {
    pub source: Source,
    pub records: SourceRecords,
}

impl StaticAdapter {
    pub fn new(id: &str, records: SourceRecords) -> Self {
        Self {
            source: fixture_source(id),
            records,
        }
    }
}

impl SourceAdapter for StaticAdapter {
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

    fn derive(&self, _raw: &mut diesel::SqliteConnection) -> Result<SourceRecords, IngestError> {
        Ok(self.records.clone())
    }
}

/// Las dos fuentes de ejemplo (`alpha` prioridad 1, `beta` prioridad 2) como entrada del consolidador.
pub fn sample_inputs() -> Vec<SourceInput> {
    vec![
        SourceInput {
            source: fixture_source("alpha"),
            priority: 1,
            records: alpha_records(),
        },
        SourceInput {
            source: fixture_source("beta"),
            priority: 2,
            records: beta_records(),
        },
    ]
}

/// Catálogo consolidado a partir de [`sample_inputs`].
pub fn sample_catalog() -> crate::consolidate::Catalog {
    crate::consolidate::consolidate(sample_inputs()).unwrap()
}

/// Contenido de los CSV (con cabecera) que lee [`FixtureAdapter`].
#[derive(Debug, Clone)]
pub struct FixtureCsv {
    /// `plants.csv`: `id,scientific_name,family`.
    pub plants: String,
    /// `names.csv`: `plant_id,text,language`.
    pub names: String,
    /// `parts.csv`: `plant_id,label`.
    pub parts: String,
    /// `uses.csv`: `plant_id,activity,language,reference_id`.
    pub uses: String,
    /// `references.csv`: `id,citation`.
    pub references: String,
}

impl FixtureCsv {
    /// Entradas `(nombre de archivo, contenido)` listas para [`build_zip`].
    pub fn entries(&self) -> [(&'static str, &str); 5] {
        [
            ("plants.csv", &self.plants),
            ("names.csv", &self.names),
            ("parts.csv", &self.parts),
            ("uses.csv", &self.uses),
            ("references.csv", &self.references),
        ]
    }

    /// CSV de ejemplo equivalentes a [`alpha_records`].
    pub fn alpha() -> Self {
        Self {
            plants: "id,scientific_name,family\nA1,Lavandula angustifolia,Lamiaceae\n".into(),
            names: "plant_id,text,language\nA1,lavender,en\nA1,English lavender,en\n".into(),
            parts: "plant_id,label\nA1,Flower\nA1,Leaf\n".into(),
            uses:
                "plant_id,activity,language,reference_id\nA1,Sedative,en,r1\nA1,Antiseptic,en,r2\n"
                    .into(),
            references: "id,citation\nr1,Cita uno\nr2,Cita dos\n".into(),
        }
    }

    /// CSV de ejemplo equivalentes a [`beta_records`].
    pub fn beta() -> Self {
        Self {
            plants: "id,scientific_name,family\nB7,LAVANDULA  angustifolia,Labiatae\nB8,Matricaria chamomilla,Asteraceae\n".into(),
            names: "plant_id,text,language\nB7,lavender,en\nB7,lavanda,es\nB8,chamomile,en\n".into(),
            parts: "plant_id,label\nB7,Flower\nB7,Root\nB8,Flower\n".into(),
            uses: "plant_id,activity,language,reference_id\nB7,Sedative,en,r1\nB7,Insecticide,en,r3\nB8,Calmative,en,r1\n".into(),
            references: "id,citation\nr1,Cita uno\nr3,Cita tres\n".into(),
        }
    }
}

/// Adaptador de fixture "real": importa cinco CSV sencillos y los deriva leyendo las tablas crudas.
///
/// Sirve de "segundo dataset que no es USDA": no tiene nada específico de ninguna fuente real.
pub struct FixtureAdapter {
    source: Source,
}

const FIXTURE_FILES: [&str; 5] = [
    "plants.csv",
    "names.csv",
    "parts.csv",
    "uses.csv",
    "references.csv",
];

impl FixtureAdapter {
    /// Crea el adaptador de la fuente `id`.
    pub fn new(id: &str) -> Self {
        Self {
            source: fixture_source(id),
        }
    }
}

/// Declara, para una fuente de fixture, las tablas crudas que lee (`table!` de Diesel) y la función que las deriva.
///
/// `table!` necesita el nombre SQL como literal, y las tablas crudas se llaman `raw_<fuente>_<archivo>`; por eso la macro recibe un módulo y los cinco nombres completos. Cada módulo declara solo un subconjunto de columnas: las que lee la derivación.
macro_rules! fixture_source_tables {
    ($module:ident, $plants:literal, $names:literal, $parts:literal, $uses:literal, $refs:literal) => {
        mod $module {
            use super::*;
            use diesel::prelude::*;

            diesel::table! {
                #[sql_name = $plants]
                plants (_row) {
                    _row -> Integer,
                    id -> Text,
                    scientific_name -> Text,
                    family -> Text,
                }
            }
            diesel::table! {
                #[sql_name = $names]
                names (_row) {
                    _row -> Integer,
                    plant_id -> Text,
                    text -> Text,
                    language -> Text,
                }
            }
            diesel::table! {
                #[sql_name = $parts]
                parts (_row) {
                    _row -> Integer,
                    plant_id -> Text,
                    label -> Text,
                }
            }
            diesel::table! {
                #[sql_name = $uses]
                uses (_row) {
                    _row -> Integer,
                    plant_id -> Text,
                    activity -> Text,
                    language -> Text,
                    reference_id -> Text,
                }
            }
            diesel::table! {
                #[sql_name = $refs]
                refs (_row) {
                    _row -> Integer,
                    id -> Text,
                    citation -> Text,
                }
            }

            pub fn derive(raw: &mut SqliteConnection) -> Result<SourceRecords, IngestError> {
                let mut plants: Vec<PlantRecord> = plants::table
                    .order(plants::_row)
                    .select((plants::id, plants::scientific_name, plants::family))
                    .load::<(String, String, String)>(raw)?
                    .into_iter()
                    .map(|(id, name, family)| PlantRecord {
                        family: (!family.trim().is_empty()).then_some(family),
                        ..plant(&id, &name)
                    })
                    .collect();
                // Índice id de la fuente -> posición en `plants`, para repartir las filas hijas.
                let index: std::collections::HashMap<String, usize> = plants
                    .iter()
                    .enumerate()
                    .map(|(i, p)| (p.source_plant_id.clone(), i))
                    .collect();
                let owner = |file: &str, plant_id: &str| -> Result<usize, IngestError> {
                    index.get(plant_id).copied().ok_or(IngestError::InvalidCsv {
                        file: file.to_string(),
                        row: None,
                        message: format!("planta desconocida `{plant_id}`"),
                    })
                };

                for (plant_id, text, language) in names::table
                    .order(names::_row)
                    .select((names::plant_id, names::text, names::language))
                    .load::<(String, String, String)>(raw)?
                {
                    plants[owner("names.csv", &plant_id)?]
                        .common_names
                        .push(name(&text, &language));
                }
                for (plant_id, label) in parts::table
                    .order(parts::_row)
                    .select((parts::plant_id, parts::label))
                    .load::<(String, String)>(raw)?
                {
                    plants[owner("parts.csv", &plant_id)?].parts.push(label);
                }
                for (plant_id, activity, language, reference_id) in uses::table
                    .order(uses::_row)
                    .select((
                        uses::plant_id,
                        uses::activity,
                        uses::language,
                        uses::reference_id,
                    ))
                    .load::<(String, String, String, String)>(raw)?
                {
                    plants[owner("uses.csv", &plant_id)?].uses.push(use_rec(
                        &activity,
                        &language,
                        &reference_id,
                    ));
                }
                let references = refs::table
                    .order(refs::_row)
                    .select((refs::id, refs::citation))
                    .load::<(String, String)>(raw)?
                    .into_iter()
                    .map(|(id, citation)| reference(&id, &citation))
                    .collect();
                Ok(SourceRecords { plants, references })
            }
        }
    };
}

fixture_source_tables!(
    alpha_tables,
    "raw_alpha_plants",
    "raw_alpha_names",
    "raw_alpha_parts",
    "raw_alpha_uses",
    "raw_alpha_references"
);
fixture_source_tables!(
    beta_tables,
    "raw_beta_plants",
    "raw_beta_names",
    "raw_beta_parts",
    "raw_beta_uses",
    "raw_beta_references"
);

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
            files: RawFiles::Only(FIXTURE_FILES.iter().map(|f| f.to_string()).collect()),
        }
    }

    fn derive(&self, raw: &mut diesel::SqliteConnection) -> Result<SourceRecords, IngestError> {
        // Las tablas crudas llevan el id de la fuente en el nombre, así que cada fuente de fixture tiene su módulo.
        match self.source.id.0.as_str() {
            "alpha" => alpha_tables::derive(raw),
            "beta" => beta_tables::derive(raw),
            other => Err(IngestError::UnknownSource {
                id: other.to_string(),
            }),
        }
    }
}
