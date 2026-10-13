//! Adaptador de la fuente USDA (Dr. Duke's Phytochemical and Ethnobotanical Databases).
//!
//! Los valores de procedencia salen literalmente de `docs/data/usda-catalog.md`; si cambian allí, deben cambiar aquí.

use std::collections::{BTreeSet, HashMap, HashSet};
use std::path::Path;

use catalog_core::domain::{Source, SourceId};
use diesel::prelude::*;

use crate::adapter::{
    InputDescriptor, NameRecord, PlantRecord, ReferenceRecord, SourceAdapter, SourceRecords,
    UseRecord,
};
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

/// Tablas crudas de USDA que lee la derivación, declaradas a mano para Diesel.
///
/// Son un **subconjunto** de lo que crea `import_raw`: cada tabla real tiene todas las columnas del CSV (todas `TEXT`) y una columna `_row` con el número de fila; aquí solo se declaran las que se usan.
/// `#[sql_name]` enlaza el nombre Rust (minúsculas, como pide el estilo) con el nombre real de la tabla o columna en SQL.
mod raw_tables {
    diesel::table! {
        #[sql_name = "raw_usda_fnftax"]
        fnftax (_row) {
            _row -> Integer,
            #[sql_name = "FNFNUM"]
            fnfnum -> Text,
            #[sql_name = "TAXON"]
            taxon -> Text,
            #[sql_name = "GENUS"]
            genus -> Text,
            #[sql_name = "SPECIES"]
            species -> Text,
            #[sql_name = "FAMILY"]
            family -> Text,
        }
    }

    diesel::table! {
        #[sql_name = "raw_usda_farmacy_new"]
        farmacy_new (_row) {
            _row -> Integer,
            #[sql_name = "FNFNUM"]
            fnfnum -> Text,
            #[sql_name = "PPCO"]
            ppco -> Text,
        }
    }

    diesel::table! {
        #[sql_name = "raw_usda_parts"]
        parts (_row) {
            _row -> Integer,
            #[sql_name = "PPCO"]
            ppco -> Text,
            #[sql_name = "PPNA"]
            ppna -> Text,
        }
    }

    diesel::table! {
        #[sql_name = "raw_usda_ethnobot"]
        ethnobot (_row) {
            _row -> Integer,
            #[sql_name = "GENUS"]
            genus -> Text,
            #[sql_name = "SPECIES"]
            species -> Text,
            #[sql_name = "TAXON"]
            taxon -> Text,
            #[sql_name = "ACTIVITY"]
            activity -> Text,
            #[sql_name = "REFERENCE"]
            reference -> Text,
        }
    }

    diesel::table! {
        #[sql_name = "raw_usda_references"]
        references (_row) {
            _row -> Integer,
            #[sql_name = "REFERENCE"]
            reference -> Text,
            #[sql_name = "LONGREF"]
            longref -> Text,
        }
    }

    diesel::table! {
        #[sql_name = "raw_usda_common_names"]
        common_names (_row) {
            _row -> Integer,
            #[sql_name = "CNNAM"]
            cnnam -> Text,
            #[sql_name = "FNFNUM"]
            fnfnum -> Text,
        }
    }
}

/// Idioma de las etiquetas de actividad: el dataset está en inglés.
const ACTIVITY_LANGUAGE: &str = "en";
/// Idioma de un nombre común sin etiqueta de idioma entre paréntesis.
const NAME_LANGUAGE: &str = "en";
/// Idioma indeterminado: nombres con etiqueta entre paréntesis, que `COMMON_NAMES` no declara en una columna.
const UNDETERMINED_LANGUAGE: &str = "und";

/// Cifras de la derivación que no caben en [`SourceRecords`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct DeriveStats {
    /// Filas de `ETHNOBOT` elegibles (taxón exacto y referencia resoluble), antes de fundir las repetidas.
    pub eligible_use_rows: usize,
}

/// Idioma de un nombre común.
///
/// `COMMON_NAMES` no tiene columna de idioma. Regla: un nombre que termina en una etiqueta entre paréntesis (`Rumberry (Eng.)`) es `und` (indeterminado), porque la etiqueta puede ser de otro idioma o de origen; cualquier otro es `en`.
/// El texto nunca se modifica: la etiqueta se conserva.
fn name_language(text: &str) -> &'static str {
    if text.ends_with(')') && text.contains('(') {
        UNDETERMINED_LANGUAGE
    } else {
        NAME_LANGUAGE
    }
}

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

    fn derive(&self, raw: &mut diesel::SqliteConnection) -> Result<SourceRecords, IngestError> {
        derive_with_stats(raw).map(|(records, _stats)| records)
    }
}

/// Selector de identidad: `GENUS`, `SPECIES` y `TAXON` exactos (tras recortar espacios exteriores).
type Identity = (String, String, String);

/// Como [`SourceAdapter::derive`], pero devuelve además las cifras de [`DeriveStats`].
///
/// Cada tabla se lee **una sola vez** y el cruce se hace en memoria con mapas: preguntar a SQLite por cada una de las 2.376 plantas recorrería ~80.000 filas de `ETHNOBOT` cada vez.
pub fn derive_with_stats(
    raw: &mut diesel::SqliteConnection,
) -> Result<(SourceRecords, DeriveStats), IngestError> {
    use raw_tables::{common_names, ethnobot, farmacy_new, fnftax, parts, references};

    // Error de una fila de `table` cuyo `FNFNUM` no existe en `FNFTAX`.
    let orphan = |table: &str, fnfnum: &str| IngestError::OrphanRow {
        source: SOURCE_ID.to_string(),
        table: table.to_string(),
        source_plant_id: fnfnum.to_string(),
    };

    // Identidad: una planta por fila de `FNFTAX`, en el orden del CSV.
    let mut plants: Vec<PlantRecord> = Vec::new();
    let mut by_fnfnum: HashMap<String, usize> = HashMap::new();
    let mut by_identity: HashMap<Identity, usize> = HashMap::new();
    let rows = fnftax::table
        .order(fnftax::_row)
        .select((
            fnftax::fnfnum,
            fnftax::taxon,
            fnftax::genus,
            fnftax::species,
            fnftax::family,
        ))
        .load::<(String, String, String, String, String)>(raw)?;
    for (fnfnum, taxon, genus, species, family) in rows {
        let (fnfnum, taxon, family) = (fnfnum.trim(), taxon.trim(), family.trim());
        let index = plants.len();
        // Un `FNFNUM` repetido dejaría a la segunda planta sin nombres ni partes: se rechaza.
        if by_fnfnum.insert(fnfnum.to_string(), index).is_some() {
            return Err(IngestError::DuplicateSourcePlantId {
                source: SOURCE_ID.to_string(),
                source_plant_id: fnfnum.to_string(),
            });
        }
        by_identity
            .entry((
                genus.trim().to_string(),
                species.trim().to_string(),
                taxon.to_string(),
            ))
            .or_insert(index);
        plants.push(PlantRecord {
            source_plant_id: fnfnum.to_string(),
            scientific_name: taxon.to_string(),
            family: (!family.is_empty()).then(|| family.to_string()),
            common_names: Vec::new(),
            parts: Vec::new(),
            uses: Vec::new(),
        });
    }

    // Nombres comunes por `FNFNUM`.
    let rows = common_names::table
        .order(common_names::_row)
        .select((common_names::fnfnum, common_names::cnnam))
        .load::<(String, String)>(raw)?;
    for (fnfnum, name) in rows {
        let (name, fnfnum) = (name.trim(), fnfnum.trim());
        // Una fila que apunta a una planta inexistente es un dato inconsistente, aunque su nombre esté vacío.
        let &index = by_fnfnum
            .get(fnfnum)
            .ok_or_else(|| orphan("COMMON_NAMES", fnfnum))?;
        if !name.is_empty() {
            plants[index].common_names.push(NameRecord {
                text: name.to_string(),
                language: name_language(name).to_string(),
            });
        }
    }

    // Partes: código -> etiqueta, y luego pares (`FNFNUM`, `PPCO`) distintos de `FARMACY_NEW`.
    let mut part_labels: HashMap<String, String> = HashMap::new();
    let rows = parts::table
        .select((parts::ppco, parts::ppna))
        .load::<(String, String)>(raw)?;
    for (code, label) in rows {
        let (code, label) = (code.trim().to_string(), label.trim().to_string());
        if let Some(previous) = part_labels.insert(code.clone(), label.clone())
            && previous != label
        {
            return Err(IngestError::Storage(format!(
                "el código de parte \"{code}\" aparece en PARTS con etiquetas distintas (\"{previous}\" y \"{label}\")"
            )));
        }
    }
    let rows = farmacy_new::table
        .order(farmacy_new::_row)
        .select((farmacy_new::fnfnum, farmacy_new::ppco))
        .load::<(String, String)>(raw)?;
    let mut seen_pairs: HashSet<(usize, String)> = HashSet::new();
    for (fnfnum, code) in rows {
        let code = code.trim();
        let &index = by_fnfnum
            .get(fnfnum.trim())
            .ok_or_else(|| orphan("FARMACY_NEW", fnfnum.trim()))?;
        if code.is_empty() {
            continue;
        }
        if !seen_pairs.insert((index, code.to_string())) {
            continue;
        }
        let label = part_labels.get(code).ok_or_else(|| {
            IngestError::Storage(format!(
                "el código de parte \"{code}\" (FARMACY_NEW, FNFNUM {}) no existe en PARTS",
                fnfnum.trim()
            ))
        })?;
        plants[index].parts.push(label.clone());
    }

    // Referencias: solo resuelve una clave con exactamente una fila y `LONGREF` no vacío.
    let rows = references::table
        .select((references::reference, references::longref))
        .load::<(String, String)>(raw)?;
    let mut by_key: HashMap<String, Vec<String>> = HashMap::new();
    for (key, longref) in rows {
        by_key
            .entry(key.trim().to_string())
            .or_default()
            .push(longref.trim().to_string());
    }
    let resolve = |key: &str| -> Option<&str> {
        match by_key.get(key)?.as_slice() {
            [only] if !only.is_empty() => Some(only.as_str()),
            _ => None,
        }
    };

    // Usos: filas cuyo (`GENUS`, `SPECIES`, `TAXON`) cruza exactamente y cuya referencia resuelve.
    let rows = ethnobot::table
        .order(ethnobot::_row)
        .select((
            ethnobot::genus,
            ethnobot::species,
            ethnobot::taxon,
            ethnobot::activity,
            ethnobot::reference,
        ))
        .load::<(String, String, String, String, String)>(raw)?;
    let mut stats = DeriveStats::default();
    let mut used_references: BTreeSet<String> = BTreeSet::new();
    for (genus, species, taxon, activity, reference) in rows {
        let identity = (
            genus.trim().to_string(),
            species.trim().to_string(),
            taxon.trim().to_string(),
        );
        let (activity, reference) = (activity.trim(), reference.trim());
        let Some(&index) = by_identity.get(&identity) else {
            continue;
        };
        if activity.is_empty() || reference.is_empty() || resolve(reference).is_none() {
            continue;
        }
        stats.eligible_use_rows += 1;
        used_references.insert(reference.to_string());
        plants[index].uses.push(UseRecord {
            activity: activity.to_string(),
            language: ACTIVITY_LANGUAGE.to_string(),
            reference_id: reference.to_string(),
        });
    }

    // Solo se entregan las referencias que algún uso elegible cita.
    let references = used_references
        .into_iter()
        .filter_map(|id| {
            let citation = resolve(&id)?.to_string();
            Some(ReferenceRecord { id, citation })
        })
        .collect();

    Ok((SourceRecords { plants, references }, stats))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::validate_source;
    use crate::raw::import_raw;
    use crate::test_support::build_zip;
    use diesel::Connection;

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

    /// CSV mínimos con solo las columnas que lee la derivación.
    struct Csv {
        fnftax: &'static str,
        farmacy_new: &'static str,
        parts: &'static str,
        ethnobot: &'static str,
        references: &'static str,
        common_names: &'static str,
    }

    impl Csv {
        const FNFTAX_HEADER: &'static str = "FNFNUM,TAXON,GENUS,SPECIES,FAMILY\n";
        const FARMACY_HEADER: &'static str = "FNFNUM,PPCO\n";
        const PARTS_HEADER: &'static str = "PPCO,PPNA\n";
        const ETHNO_HEADER: &'static str = "ETHNO,GENUS,SPECIES,TAXON,ACTIVITY,REFERENCE\n";
        const REFS_HEADER: &'static str = "REFERENCE,LONGREF\n";
        const NAMES_HEADER: &'static str = "CNNAM,FNFNUM\n";
    }

    /// Importa los CSV con `import_raw`, abre `raw.db` con Diesel y deriva.
    fn derive_from(csv: &Csv) -> Result<(SourceRecords, DeriveStats), IngestError> {
        let dir = tempfile::tempdir().unwrap();
        let tables = [
            ("FNFTAX.csv", [Csv::FNFTAX_HEADER, csv.fnftax]),
            ("FARMACY_NEW.csv", [Csv::FARMACY_HEADER, csv.farmacy_new]),
            ("PARTS.csv", [Csv::PARTS_HEADER, csv.parts]),
            ("ETHNOBOT.csv", [Csv::ETHNO_HEADER, csv.ethnobot]),
            ("REFERENCES.csv", [Csv::REFS_HEADER, csv.references]),
            ("COMMON_NAMES.csv", [Csv::NAMES_HEADER, csv.common_names]),
        ];
        let contents: Vec<(&str, String)> = tables
            .iter()
            .map(|(name, [header, rows])| (*name, format!("{header}{rows}")))
            .collect();
        let entries: Vec<(&str, &str)> = contents.iter().map(|(n, c)| (*n, c.as_str())).collect();
        let zip = build_zip(&dir, &entries);
        let raw_db = dir.path().join("raw.db");
        import_raw(&UsdaAdapter.raw_import(&zip), &raw_db).unwrap();
        let mut conn = SqliteConnection::establish(raw_db.to_str().unwrap()).unwrap();
        derive_with_stats(&mut conn)
    }

    const TAX: &str = "544,Lavandula angustifolia,Lavandula,angustifolia,Lamiaceae\n\
                       605,Matricaria recutita,Matricaria,recutita,\n\
                       157,Beta vulgaris subsp. subsp. vulgaris,Beta,vulgaris,Amaranthaceae\n";

    fn base() -> Csv {
        Csv {
            fnftax: TAX,
            farmacy_new: "",
            parts: "",
            ethnobot: "",
            references: "",
            common_names: "",
        }
    }

    fn plant_of<'a>(records: &'a SourceRecords, id: &str) -> &'a PlantRecord {
        records
            .plants
            .iter()
            .find(|p| p.source_plant_id == id)
            .unwrap()
    }

    #[test]
    fn identity_family_and_literal_taxon() {
        let (records, _) = derive_from(&base()).unwrap();
        assert_eq!(records.plants.len(), 3);
        let lavender = plant_of(&records, "544");
        assert_eq!(lavender.scientific_name, "Lavandula angustifolia");
        assert_eq!(lavender.family.as_deref(), Some("Lamiaceae"));
        // Familia vacía -> None; sin usos ni nombres ni partes.
        let chamomile = plant_of(&records, "605");
        assert_eq!(chamomile.family, None);
        assert!(chamomile.uses.is_empty() && chamomile.parts.is_empty());
        // El `subsp.` repetido de la fuente se conserva.
        assert_eq!(
            plant_of(&records, "157").scientific_name,
            "Beta vulgaris subsp. subsp. vulgaris"
        );
        assert!(records.references.is_empty());
    }

    #[test]
    fn eligible_and_excluded_uses() {
        let csv = Csv {
            ethnobot: "1,Lavandula,angustifolia,Lavandula angustifolia, Carminative ,Steinmetz\n\
                       2,Lavandula,angustifolia,Lavandula angustifolia,Sedative,Missing\n\
                       3,Lavandula,angustifolia,Lavandula angustifolia,Antiseptic,\n\
                       4,Lavandula,angustifolia,Lavandula angustifolia,Tonic,Dup\n\
                       5,Lavandula,angustifolia,Lavandula angustifolia var. x,Wrong taxon,Steinmetz\n\
                       6,Lavandula,angustifolia,Lavandula angustifolia,Empty longref,Blank\n\
                       7,Lavandula,angustifolia,Lavandula angustifolia,Carminative,Steinmetz\n\
                       8,Otra,planta,Otra planta,Unknown plant,Steinmetz\n",
            references: "Steinmetz,Steinmetz 1954\nDup,Primera\nDup,Segunda\nBlank,\nUnused,Nunca citada\n",
            ..base()
        };
        let (records, stats) = derive_from(&csv).unwrap();
        let uses = &plant_of(&records, "544").uses;
        // Elegibles: filas 1 y 7 (la actividad se recorta; la repetida se entrega y la funde el consolidador).
        assert_eq!(uses.len(), 2);
        assert!(uses.iter().all(|u| u.activity == "Carminative"));
        assert!(
            uses.iter()
                .all(|u| u.language == "en" && u.reference_id == "Steinmetz")
        );
        assert_eq!(stats.eligible_use_rows, 2);
        // Solo la referencia citada por un uso elegible.
        assert_eq!(
            records.references,
            vec![ReferenceRecord {
                id: "Steinmetz".to_string(),
                citation: "Steinmetz 1954".to_string()
            }]
        );
        assert!(plant_of(&records, "605").uses.is_empty());
    }

    #[test]
    fn common_names_get_language_by_label() {
        let csv = Csv {
            common_names: "English Lavender,544\n\
                           Rumberry (Eng.),544\n\
                           Fieberstrauch (Ger.),605\n\
                           Blue (Bay) Gum,157\n",
            ..base()
        };
        let (records, _) = derive_from(&csv).unwrap();
        let names = |id: &str| -> Vec<(String, String)> {
            plant_of(&records, id)
                .common_names
                .iter()
                .map(|n| (n.text.clone(), n.language.clone()))
                .collect()
        };
        assert_eq!(
            names("544"),
            vec![
                ("English Lavender".to_string(), "en".to_string()),
                ("Rumberry (Eng.)".to_string(), "und".to_string()),
            ]
        );
        assert_eq!(
            names("605"),
            vec![("Fieberstrauch (Ger.)".to_string(), "und".to_string())]
        );
        // Un paréntesis que no cierra el texto no es una etiqueta final.
        assert_eq!(
            names("157"),
            vec![("Blue (Bay) Gum".to_string(), "en".to_string())]
        );
        // Nunca se inventan nombres en español.
        assert!(
            records
                .plants
                .iter()
                .flat_map(|p| &p.common_names)
                .all(|n| n.language != "es")
        );
    }

    #[test]
    fn parts_are_deduplicated_and_empty_codes_ignored() {
        let csv = Csv {
            farmacy_new: "544,FL\n544,FL\n544,LF\n544,\n605,FL\n",
            parts: "FL,Flower\nLF,Leaf\n",
            ..base()
        };
        let (records, _) = derive_from(&csv).unwrap();
        assert_eq!(plant_of(&records, "544").parts, vec!["Flower", "Leaf"]);
        assert_eq!(plant_of(&records, "605").parts, vec!["Flower"]);
    }

    #[test]
    fn unresolved_part_code_is_an_error_naming_it() {
        let csv = Csv {
            farmacy_new: "544,ZZ\n",
            parts: "FL,Flower\n",
            ..base()
        };
        let err = derive_from(&csv).unwrap_err();
        assert!(err.to_string().contains("ZZ"), "{err}");
    }

    #[test]
    fn orphan_common_name_is_an_error_naming_table_and_fnfnum() {
        let csv = Csv {
            common_names: "English Lavender,544\nIgnored,999\n",
            ..base()
        };
        let err = derive_from(&csv).unwrap_err();
        assert!(
            matches!(&err, IngestError::OrphanRow { table, source_plant_id, .. }
                if table == "COMMON_NAMES" && source_plant_id == "999"),
            "{err}"
        );
        assert!(err.to_string().contains("999"), "{err}");
    }

    #[test]
    fn orphan_part_is_an_error_naming_table_and_fnfnum() {
        let csv = Csv {
            farmacy_new: "544,FL\n999,FL\n",
            parts: "FL,Flower\n",
            ..base()
        };
        let err = derive_from(&csv).unwrap_err();
        assert!(
            matches!(&err, IngestError::OrphanRow { table, source_plant_id, .. }
                if table == "FARMACY_NEW" && source_plant_id == "999"),
            "{err}"
        );
    }

    #[test]
    fn repeated_fnfnum_in_fnftax_is_an_error() {
        let csv = Csv {
            fnftax: "544,Lavandula angustifolia,Lavandula,angustifolia,Lamiaceae\n\
                     544,Matricaria recutita,Matricaria,recutita,\n",
            ..base()
        };
        let err = derive_from(&csv).unwrap_err();
        assert!(
            matches!(&err, IngestError::DuplicateSourcePlantId { source_plant_id, .. }
                if source_plant_id == "544"),
            "{err}"
        );
    }

    #[test]
    fn sensitive_activity_label_is_kept_verbatim() {
        let csv = Csv {
            ethnobot: "1,Lavandula,angustifolia,Lavandula angustifolia,Poison,Steinmetz\n",
            references: "Steinmetz,Steinmetz 1954\n",
            ..base()
        };
        let (records, _) = derive_from(&csv).unwrap();
        let lavender = plant_of(&records, "544");
        // La etiqueta llega tal cual: ni se omite ni se reetiqueta.
        assert_eq!(
            lavender.uses,
            vec![UseRecord {
                activity: "Poison".to_string(),
                language: "en".to_string(),
                reference_id: "Steinmetz".to_string(),
            }]
        );
        // Ninguna otra planta ni nombre ni parte aparece por inferencia.
        assert!(
            records
                .plants
                .iter()
                .all(|p| p.source_plant_id == "544" || p.uses.is_empty())
        );
        assert!(
            records
                .plants
                .iter()
                .all(|p| p.common_names.is_empty() && p.parts.is_empty())
        );
        assert_eq!(records.references.len(), 1);
    }

    #[test]
    fn missing_raw_table_is_reported() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("empty.db");
        let mut conn = SqliteConnection::establish(path.to_str().unwrap()).unwrap();
        let err = derive_with_stats(&mut conn).unwrap_err();
        assert!(err.to_string().contains("raw_usda_"), "{err}");
    }
}
