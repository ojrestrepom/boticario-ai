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

    fn derive(&self, _raw: &rusqlite::Connection) -> Result<SourceRecords, IngestError> {
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

    fn table(&self, file: &str) -> String {
        crate::raw::raw_table_name(&self.source.id.0, file)
    }
}

/// Lee una tabla cruda en el orden original del CSV (`_row`), convirtiendo cada fila con `map`.
fn read_table<T>(
    conn: &rusqlite::Connection,
    table: &str,
    columns: &str,
    map: impl Fn(&rusqlite::Row<'_>) -> rusqlite::Result<T>,
) -> Result<Vec<T>, IngestError> {
    // Si la tabla no existe, `prepare` falla con "no such table: <tabla>" y `From` lo convierte en `IngestError::Storage`.
    let mut stmt = conn.prepare(&format!("SELECT {columns} FROM {table} ORDER BY _row"))?;
    let rows = stmt.query_map([], map)?.collect::<Result<Vec<_>, _>>()?;
    Ok(rows)
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
            files: RawFiles::Only(FIXTURE_FILES.iter().map(|f| f.to_string()).collect()),
        }
    }

    fn derive(&self, raw: &rusqlite::Connection) -> Result<SourceRecords, IngestError> {
        let mut plants: Vec<PlantRecord> = read_table(
            raw,
            &self.table("plants.csv"),
            "id, scientific_name, family",
            |r| {
                let family: String = r.get(2)?;
                Ok(PlantRecord {
                    family: (!family.trim().is_empty()).then_some(family),
                    ..plant(&r.get::<_, String>(0)?, &r.get::<_, String>(1)?)
                })
            },
        )?;
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

        for (plant_id, text, language) in read_table(
            raw,
            &self.table("names.csv"),
            "plant_id, text, language",
            |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, String>(2)?,
                ))
            },
        )? {
            plants[owner("names.csv", &plant_id)?]
                .common_names
                .push(name(&text, &language));
        }
        for (plant_id, label) in
            read_table(raw, &self.table("parts.csv"), "plant_id, label", |r| {
                Ok((r.get::<_, String>(0)?, r.get::<_, String>(1)?))
            })?
        {
            plants[owner("parts.csv", &plant_id)?].parts.push(label);
        }
        for (plant_id, activity, language, reference_id) in read_table(
            raw,
            &self.table("uses.csv"),
            "plant_id, activity, language, reference_id",
            |r| {
                Ok((
                    r.get::<_, String>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, String>(2)?,
                    r.get::<_, String>(3)?,
                ))
            },
        )? {
            plants[owner("uses.csv", &plant_id)?].uses.push(use_rec(
                &activity,
                &language,
                &reference_id,
            ));
        }
        let references = read_table(raw, &self.table("references.csv"), "id, citation", |r| {
            Ok(reference(&r.get::<_, String>(0)?, &r.get::<_, String>(1)?))
        })?;
        Ok(SourceRecords { plants, references })
    }
}
