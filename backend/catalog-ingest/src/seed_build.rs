//! Construcción de `catalog.db` desde la semilla (`data/seed/`).
//!
//! Lee la semilla con [`load_seed`](crate::seed::load_seed), la mapea a las tablas del esquema neutral (las que lee la API y las del esquema v2) y escribe la base de forma atómica: primero en un archivo temporal junto al destino y, solo si todo salió bien, se renombra. No usa red, ni LLM, ni el marco de adaptadores.
//!
//! Cualquier inconsistencia de los datos aborta la construcción con un error que nombra la planta; la transacción se revierte y el temporal se borra, de modo que no queda una base parcial en el destino.

use std::collections::{BTreeMap, BTreeSet};
use std::ffi::OsString;
use std::fmt;
use std::path::{Path, PathBuf};

use catalog_core::normalize::{activity_base_key, activity_can_link_glossary, normalize_name};
use catalog_core::rows::{
    ActivityGlossaryRow, GoalRow, GoalSubareaRow, MetadataRow, NewPlantGoal, NewPlantName,
    NewPlantPart, NewPlantReviewFlag, NewPlantUse, NewPlantUseGroup, PlantAliasRow,
    PlantGoalRefRow, PlantImageRow, PlantNameSourceRow, PlantPartSourceRow, PlantProfileRefRow,
    PlantProfileRow, PlantRow, PlantSafetyRefRow, PlantSafetyRow, PlantSourceIdRow,
    PlantUseGroupRefRow, PlantUseSourceRow, ReferenceProvenanceRow, ReferenceSourceRow, SourceRow,
};
use catalog_core::schema::{
    activity_glossary, goal, goal_subarea, metadata, plant, plant_alias, plant_goal,
    plant_goal_ref, plant_image, plant_name, plant_name_source, plant_part, plant_part_source,
    plant_profile, plant_profile_ref, plant_review_flag, plant_safety, plant_safety_ref,
    plant_source_id, plant_use, plant_use_group, plant_use_group_ref, plant_use_source, reference,
    reference_source, source,
};
use catalog_core::version::{SCHEMA_VERSION, SCHEMA_VERSION_KEY, apply_schema};
use diesel::prelude::*;
use rusqlite::{Connection as Rusqlite, OpenFlags};
use sha2::{Digest, Sha256};

use crate::error::IngestError;
use crate::hash::content_hash;
use crate::seed::{
    Glossary, GoalCatalog, Manifest, PlantRecord, RefEntry, SafetyLevel, Seed, SeedError, load_seed,
};

/// Errores de la construcción desde la semilla. Todos nombran la planta implicada cuando la hay.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BuildError {
    /// La semilla no se pudo leer o no pasó la verificación (manifiesto, hash, tipos, objetivos).
    Seed(SeedError),
    /// Fallo de entrada/salida, del esquema o del cálculo del hash.
    Ingest(IngestError),
    /// Dos registros tienen el mismo `id`.
    DuplicateId {
        /// Identificador repetido.
        id: String,
    },
    /// Dos plantas distintas tienen el mismo nombre científico normalizado.
    DuplicateScientificName {
        /// Primera planta.
        first: String,
        /// Segunda planta.
        second: String,
        /// Nombre científico normalizado.
        name: String,
    },
    /// Un alias de una planta es igual al identificador de otra.
    AliasIsPlantId {
        /// Planta que declara el alias.
        plant: String,
        /// Alias.
        alias: String,
        /// Planta cuyo `id` es el alias.
        other: String,
    },
    /// Dos plantas declaran el mismo alias.
    DuplicateAlias {
        /// Alias repetido.
        alias: String,
        /// Primera planta.
        first: String,
        /// Segunda planta.
        second: String,
    },
    /// Un campo cita un ref que no existe en el diccionario `refs` del registro.
    UnknownRef {
        /// Planta del registro.
        plant: String,
        /// Campo que cita el ref.
        field: String,
        /// Ref citado.
        reference: String,
    },
    /// Un dato no cita ningún ref y por tanto no tiene dataset ni licencia.
    DataWithoutRefs {
        /// Planta del registro.
        plant: String,
        /// Campo sin refs.
        field: String,
    },
    /// Una entrada del diccionario `refs` no tiene dataset o licencia.
    RefWithoutProvenance {
        /// Planta del registro.
        plant: String,
        /// Ref afectado.
        reference: String,
        /// Campo vacío: `dataset` o `license`.
        field: &'static str,
    },
    /// El dataset de un ref no está declarado entre las fuentes del manifiesto.
    UnknownDataset {
        /// Planta del registro.
        plant: String,
        /// Ref afectado.
        reference: String,
        /// Dataset no declarado.
        dataset: String,
    },
    /// El mismo ref aparece con contenido distinto en dos registros.
    ReferenceConflict {
        /// Ref afectado.
        reference: String,
        /// Primera planta.
        first: String,
        /// Segunda planta.
        second: String,
    },
    /// La licencia de la imagen no es CC0, dominio público, CC BY ni CC BY-SA.
    UnsupportedImageLicense {
        /// Planta del registro.
        plant: String,
        /// Licencia rechazada.
        license: String,
    },
    /// Un objetivo o grupo de uso con revisión pendiente no tiene `reviewFlag`.
    PendingWithoutFlag {
        /// Planta del registro.
        plant: String,
        /// Elemento pendiente, por ejemplo `traditionalUses[2]` o `goals.relajacion-estres`.
        target: String,
    },
    /// Un grupo de uso repite la clave de una cita.
    DuplicateCitationKey {
        /// Planta del registro.
        plant: String,
        /// Grupo de uso, por ejemplo `traditionalUses[2]`.
        target: String,
        /// Clave repetida.
        key: String,
    },
    /// Una planta repite el mismo objetivo con la misma subárea y área.
    DuplicateGoal {
        /// Planta del registro.
        plant: String,
        /// Objetivo repetido.
        goal: String,
        /// Área repetida.
        area: String,
    },
    /// Una fila del glosario cita una fuente que no figura en el manifiesto.
    GlossarySourceUnknown {
        /// Clave de la fila del glosario.
        key: String,
        /// Fuente no declarada.
        source: String,
    },
    /// Fallo del almacenamiento SQLite; `plant` es la planta que se escribía, si se sabe.
    Storage {
        /// Planta que se escribía.
        plant: Option<String>,
        /// Mensaje del almacenamiento.
        message: String,
    },
}

impl BuildError {
    /// Añade la planta a un fallo de almacenamiento que aún no la nombra.
    fn in_plant(self, plant: &str) -> Self {
        match self {
            Self::Storage {
                plant: None,
                message,
            } => Self::Storage {
                plant: Some(plant.to_string()),
                message,
            },
            other => other,
        }
    }
}

impl fmt::Display for BuildError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Seed(e) => write!(f, "{e}"),
            Self::Ingest(e) => write!(f, "{e}"),
            Self::DuplicateId { id } => {
                write!(f, "planta {id}: hay dos registros con el mismo id")
            }
            Self::DuplicateScientificName {
                first,
                second,
                name,
            } => write!(
                f,
                "las plantas {first} y {second} tienen el mismo nombre científico normalizado «{name}»"
            ),
            Self::AliasIsPlantId {
                plant,
                alias,
                other,
            } => write!(
                f,
                "planta {plant}: el alias «{alias}» es el id de la planta {other}"
            ),
            Self::DuplicateAlias {
                alias,
                first,
                second,
            } => write!(
                f,
                "las plantas {first} y {second} declaran el mismo alias «{alias}»"
            ),
            Self::UnknownRef {
                plant,
                field,
                reference,
            } => write!(
                f,
                "planta {plant}: {field} cita el ref «{reference}», que no está en el diccionario refs del registro"
            ),
            Self::DataWithoutRefs { plant, field } => write!(
                f,
                "planta {plant}: {field} no cita ningún ref, así que no tiene dataset ni licencia"
            ),
            Self::RefWithoutProvenance {
                plant,
                reference,
                field,
            } => write!(f, "planta {plant}: el ref «{reference}» no tiene {field}"),
            Self::UnknownDataset {
                plant,
                reference,
                dataset,
            } => write!(
                f,
                "planta {plant}: el ref «{reference}» es del dataset «{dataset}», que no figura entre las fuentes del manifiesto"
            ),
            Self::ReferenceConflict {
                reference,
                first,
                second,
            } => write!(
                f,
                "el ref «{reference}» tiene contenido distinto en las plantas {first} y {second}"
            ),
            Self::UnsupportedImageLicense { plant, license } => write!(
                f,
                "planta {plant}: licencia de imagen no admitida «{license}» (solo CC0, dominio público, CC BY y CC BY-SA)"
            ),
            Self::PendingWithoutFlag { plant, target } => write!(
                f,
                "planta {plant}: {target} está pendiente de revisión pero ningún reviewFlag lo señala"
            ),
            Self::DuplicateCitationKey { plant, target, key } => write!(
                f,
                "planta {plant}: {target} repite la clave de cita «{key}»"
            ),
            Self::DuplicateGoal { plant, goal, area } => write!(
                f,
                "planta {plant}: el objetivo «{goal}» está repetido con el área «{area}»"
            ),
            Self::GlossarySourceUnknown { key, source } => write!(
                f,
                "glosario: la fila «{key}» es de la fuente «{source}», que no figura entre las fuentes del manifiesto"
            ),
            Self::Storage { plant, message } => match plant {
                Some(plant) => write!(f, "planta {plant}: fallo al escribir la base: {message}"),
                None => write!(f, "fallo al escribir la base: {message}"),
            },
        }
    }
}

impl std::error::Error for BuildError {}

impl From<SeedError> for BuildError {
    fn from(err: SeedError) -> Self {
        Self::Seed(err)
    }
}

impl From<IngestError> for BuildError {
    fn from(err: IngestError) -> Self {
        Self::Ingest(err)
    }
}

impl From<diesel::result::Error> for BuildError {
    fn from(err: diesel::result::Error) -> Self {
        Self::Storage {
            plant: None,
            message: err.to_string(),
        }
    }
}

impl From<diesel::result::ConnectionError> for BuildError {
    fn from(err: diesel::result::ConnectionError) -> Self {
        Self::Storage {
            plant: None,
            message: err.to_string(),
        }
    }
}

impl From<catalog_core::version::SchemaError> for BuildError {
    fn from(err: catalog_core::version::SchemaError) -> Self {
        Self::Storage {
            plant: None,
            message: err.to_string(),
        }
    }
}

/// Resumen de una construcción: hash del contenido lógico y conteos de la base escrita.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SeedBuildReport {
    /// Hash (hexadecimal) del contenido lógico ordenado de la base.
    pub content_hash: String,
    /// Plantas.
    pub plants: u64,
    /// Nombres (`plant_name`).
    pub names: u64,
    /// Usos servidos por la API (`plant_use`).
    pub uses: u64,
    /// Grupos de uso (`plant_use_group`).
    pub use_groups: u64,
    /// Grupos de uso pendientes de revisión.
    pub pending_use_groups: u64,
    /// Citas sin resolver (`plant_use_group_ref` con `resolved` falso).
    pub unresolved_citations: u64,
    /// Objetivos de planta (`plant_goal`).
    pub plant_goals: u64,
    /// Objetivos de planta pendientes de revisión.
    pub pending_goals: u64,
    /// Filas de seguridad.
    pub safety: u64,
    /// Imágenes.
    pub images: u64,
    /// Referencias.
    pub references: u64,
    /// Fuentes.
    pub sources: u64,
    /// Alias.
    pub aliases: u64,
    /// Avisos de revisión.
    pub review_flags: u64,
    /// Filas del glosario de actividades (`activity_glossary`).
    pub glossary_terms: u64,
    /// Grupos de uso enlazados a un término del glosario.
    pub glossary_linked_groups: u64,
}

/// Lee la semilla de `seed_dir` (verificándola) y escribe la base en `out`.
pub fn build_from_dir(seed_dir: &Path, out: &Path) -> Result<SeedBuildReport, BuildError> {
    let seed = load_seed(seed_dir)?;
    build_seed(&seed, out)
}

/// Escribe en `out` la base construida desde una semilla ya leída, de forma atómica.
///
/// Si algo falla, `out` no se toca (si existía conserva su contenido) y no queda archivo temporal.
pub fn build_seed(seed: &Seed, out: &Path) -> Result<SeedBuildReport, BuildError> {
    let mut plants: Vec<&PlantRecord> = seed.plants.iter().collect();
    plants.sort_by(|a, b| a.id.cmp(&b.id));
    check_global(&plants)?;

    let io_error = |path: &Path, err: std::io::Error| {
        BuildError::Ingest(IngestError::Io {
            path: Some(path.to_path_buf()),
            message: err.to_string(),
        })
    };
    if let Some(parent) = out.parent().filter(|p| !p.as_os_str().is_empty()) {
        std::fs::create_dir_all(parent).map_err(|e| io_error(parent, e))?;
    }
    let tmp = temp_path(out);
    // Un temporal previo es resto de una ejecución interrumpida: se descarta.
    let _ = std::fs::remove_file(&tmp);

    let result = write_db(
        &seed.manifest,
        &seed.goals,
        seed.glossary.as_ref(),
        &plants,
        &tmp,
    )
    .and_then(|()| {
        let report = report_of(&tmp)?;
        std::fs::rename(&tmp, out).map_err(|e| io_error(out, e))?;
        Ok(report)
    });
    if result.is_err() {
        // Limpieza best-effort: el error original es el que importa.
        let _ = std::fs::remove_file(&tmp);
    }
    result
}

/// `<out>.tmp`, en la misma carpeta: el renombrado solo es atómico dentro del mismo sistema de archivos.
fn temp_path(out: &Path) -> PathBuf {
    let mut name: OsString = out.as_os_str().to_owned();
    name.push(".tmp");
    PathBuf::from(name)
}

/// Comprobaciones entre plantas: ids, nombres científicos y alias únicos.
fn check_global(plants: &[&PlantRecord]) -> Result<(), BuildError> {
    for pair in plants.windows(2) {
        if pair[0].id == pair[1].id {
            return Err(BuildError::DuplicateId {
                id: pair[0].id.clone(),
            });
        }
    }
    let mut names: BTreeMap<String, &str> = BTreeMap::new();
    for p in plants {
        let normalized = normalize_name(&p.scientific_name.name);
        if let Some(first) = names.insert(normalized.clone(), &p.id) {
            return Err(BuildError::DuplicateScientificName {
                first: first.to_string(),
                second: p.id.clone(),
                name: normalized,
            });
        }
    }
    let ids: BTreeSet<&str> = plants.iter().map(|p| p.id.as_str()).collect();
    let mut aliases: BTreeMap<&str, &str> = BTreeMap::new();
    for p in plants {
        for alias in &p.aliases {
            if alias != &p.id && ids.contains(alias.as_str()) {
                return Err(BuildError::AliasIsPlantId {
                    plant: p.id.clone(),
                    alias: alias.clone(),
                    other: alias.clone(),
                });
            }
            if let Some(first) = aliases.insert(alias, &p.id)
                && first != p.id
            {
                return Err(BuildError::DuplicateAlias {
                    alias: alias.clone(),
                    first: first.to_string(),
                    second: p.id.clone(),
                });
            }
        }
    }
    Ok(())
}

fn write_db(
    manifest: &Manifest,
    goals: &GoalCatalog,
    glossary: Option<&Glossary>,
    plants: &[&PlantRecord],
    path: &Path,
) -> Result<(), BuildError> {
    let url = path.to_str().ok_or_else(|| {
        BuildError::Ingest(IngestError::Io {
            path: Some(path.to_path_buf()),
            message: "la ruta no es UTF-8 válido".to_string(),
        })
    })?;
    let mut conn = SqliteConnection::establish(url)?;
    // Configuración de la conexión, fuera de la transacción (dentro, SQLite ignora este PRAGMA).
    diesel::sql_query("PRAGMA foreign_keys = ON").execute(&mut conn)?;
    apply_schema(&mut conn)?;
    conn.transaction::<(), BuildError, _>(|conn| {
        insert_all(conn, manifest, goals, glossary, plants)
    })
}

fn insert_all(
    conn: &mut SqliteConnection,
    manifest: &Manifest,
    goals: &GoalCatalog,
    glossary: Option<&Glossary>,
    plants: &[&PlantRecord],
) -> Result<(), BuildError> {
    diesel::insert_into(metadata::table)
        .values(MetadataRow {
            key: SCHEMA_VERSION_KEY.to_string(),
            value: SCHEMA_VERSION.to_string(),
        })
        .execute(conn)?;

    let mut datasets: BTreeSet<&str> = BTreeSet::new();
    for s in &manifest.sources {
        datasets.insert(s.id.as_str());
        diesel::insert_into(source::table)
            .values(SourceRow {
                id: s.id.clone(),
                name: s.name.clone(),
                version: s.version.clone(),
                license: s.license.clone(),
                citation: s.attribution.clone(),
                url: s.url.clone(),
                checksum: source_checksum(&s.files),
                license_url: s.license_url.clone(),
            })
            .execute(conn)?;
    }

    for g in &goals.goals {
        diesel::insert_into(goal::table)
            .values(GoalRow {
                id: g.id.clone(),
                label: g.label.clone(),
                position: to_i32(g.position as usize),
            })
            .execute(conn)?;
    }
    for s in &goals.subareas {
        diesel::insert_into(goal_subarea::table)
            .values(GoalSubareaRow {
                id: s.id.clone(),
                goal_id: s.goal_id.clone(),
                label: s.label.clone(),
                position: to_i32(s.position as usize),
            })
            .execute(conn)?;
    }

    let glossary_keys = insert_glossary(conn, glossary, &datasets)?;

    insert_references(conn, plants, &datasets)?;

    for record in plants {
        insert_plant(conn, record, &glossary_keys).map_err(|e| e.in_plant(&record.id))?;
    }
    Ok(())
}

/// Escribe `activity_glossary` y devuelve sus claves, para enlazar los grupos de uso.
///
/// Cada fila debe citar una fuente del manifiesto. Sin glosario, la tabla queda vacía.
fn insert_glossary(
    conn: &mut SqliteConnection,
    glossary: Option<&Glossary>,
    datasets: &BTreeSet<&str>,
) -> Result<BTreeSet<String>, BuildError> {
    let mut keys = BTreeSet::new();
    let Some(glossary) = glossary else {
        return Ok(keys);
    };
    for row in &glossary.rows {
        if !datasets.contains(row.source_id.as_str()) {
            return Err(BuildError::GlossarySourceUnknown {
                key: row.key.clone(),
                source: row.source_id.clone(),
            });
        }
        // La fecha (AAAA-MM-DD) es el prefijo de la hora ISO 8601 de la revisión.
        let revision_date: String = row.revision_timestamp.chars().take(10).collect();
        diesel::insert_into(activity_glossary::table)
            .values(ActivityGlossaryRow {
                key: row.key.clone(),
                term: row.term.clone(),
                text: row.text.clone(),
                entry_url: row.entry_url.clone(),
                revision_date,
                source_id: row.source_id.clone(),
                source_name: row.source_name.clone(),
                adapted: row.adapted,
            })
            .execute(conn)?;
        keys.insert(row.key.clone());
    }
    Ok(keys)
}

/// Clave del término del glosario que explica una actividad, si la hay.
///
/// Es la forma base de la actividad cuando existe en el glosario; la fórmula de enfermedad grave nunca se enlaza.
pub fn glossary_key_for<'a>(activity: &str, keys: &'a BTreeSet<String>) -> Option<&'a str> {
    if !activity_can_link_glossary(activity) {
        return None;
    }
    keys.get(&activity_base_key(activity)).map(String::as_str)
}

fn to_i32(n: usize) -> i32 {
    i32::try_from(n).unwrap_or(i32::MAX)
}

/// Checksum de una fuente: vacío sin archivos, `<algoritmo>:<valor>` con uno, y un sha256 de la lista ordenada con varios.
fn source_checksum(files: &[crate::seed::ManifestFile]) -> String {
    match files {
        [] => String::new(),
        [one] => format!("{}:{}", one.checksum.algorithm, one.checksum.value),
        many => {
            let mut lines: Vec<String> = many
                .iter()
                .map(|f| {
                    format!(
                        "{}\t{}:{}",
                        f.filename, f.checksum.algorithm, f.checksum.value
                    )
                })
                .collect();
            lines.sort();
            let mut hasher = Sha256::new();
            hasher.update(lines.join("\n").as_bytes());
            let digest: String = hasher
                .finalize()
                .iter()
                .map(|b| format!("{b:02x}"))
                .collect();
            format!("sha256:{digest}")
        }
    }
}

/// Escribe `reference` y `reference_source` con los refs de todos los registros.
///
/// Un ref repetido debe tener el mismo contenido en todos los registros; dataset y licencia son obligatorios y el dataset debe estar en el manifiesto.
fn insert_references(
    conn: &mut SqliteConnection,
    plants: &[&PlantRecord],
    datasets: &BTreeSet<&str>,
) -> Result<(), BuildError> {
    let mut all: BTreeMap<&str, (&RefEntry, &str)> = BTreeMap::new();
    for p in plants {
        for (key, entry) in &p.refs {
            for (field, value) in [("dataset", &entry.dataset), ("license", &entry.license)] {
                if value.trim().is_empty() {
                    return Err(BuildError::RefWithoutProvenance {
                        plant: p.id.clone(),
                        reference: key.clone(),
                        field,
                    });
                }
            }
            if !datasets.contains(entry.dataset.as_str()) {
                return Err(BuildError::UnknownDataset {
                    plant: p.id.clone(),
                    reference: key.clone(),
                    dataset: entry.dataset.clone(),
                });
            }
            match all.get(key.as_str()) {
                Some((first_entry, first_plant)) if *first_entry != entry => {
                    return Err(BuildError::ReferenceConflict {
                        reference: key.clone(),
                        first: (*first_plant).to_string(),
                        second: p.id.clone(),
                    });
                }
                Some(_) => {}
                None => {
                    all.insert(key, (entry, &p.id));
                }
            }
        }
    }
    for (key, (entry, _)) in all {
        diesel::insert_into(reference::table)
            .values(ReferenceProvenanceRow {
                id: key.to_string(),
                citation: entry.label.clone(),
                dataset: Some(entry.dataset.clone()),
                license: Some(entry.license.clone()),
                url: entry.url.clone(),
            })
            .execute(conn)?;
        diesel::insert_into(reference_source::table)
            .values(ReferenceSourceRow {
                reference_id: key.to_string(),
                source_id: entry.dataset.clone(),
            })
            .execute(conn)?;
    }
    Ok(())
}

/// Resolución de refs de un registro: comprueba que existan y devuelve sus datasets.
struct Refs<'a> {
    record: &'a PlantRecord,
}

impl Refs<'_> {
    fn entry(&self, field: &str, key: &str) -> Result<&RefEntry, BuildError> {
        self.record
            .refs
            .get(key)
            .ok_or_else(|| BuildError::UnknownRef {
                plant: self.record.id.clone(),
                field: field.to_string(),
                reference: key.to_string(),
            })
    }

    /// Datasets de `refs`; falla si no hay ninguno o alguno no está en el diccionario.
    fn datasets(&self, field: &str, refs: &[String]) -> Result<BTreeSet<String>, BuildError> {
        if refs.is_empty() {
            return Err(BuildError::DataWithoutRefs {
                plant: self.record.id.clone(),
                field: field.to_string(),
            });
        }
        refs.iter()
            .map(|r| self.entry(field, r).map(|e| e.dataset.clone()))
            .collect()
    }

    /// Refs sin repetir, en el orden dado, comprobando que existan.
    fn unique(&self, field: &str, refs: &[String]) -> Result<Vec<String>, BuildError> {
        self.datasets(field, refs)?;
        let mut out: Vec<String> = Vec::new();
        for r in refs {
            if !out.contains(r) {
                out.push(r.clone());
            }
        }
        Ok(out)
    }
}

/// Nombre pendiente de escribir, con los datasets que lo aportan (los repetidos se fusionan).
struct PendingName {
    text: String,
    kind: &'static str,
    language: String,
    datasets: BTreeSet<String>,
}

fn add_name(
    names: &mut Vec<PendingName>,
    text: &str,
    kind: &'static str,
    language: &str,
    datasets: BTreeSet<String>,
) {
    if let Some(existing) = names
        .iter_mut()
        .find(|n| n.text == text && n.kind == kind && n.language == language)
    {
        existing.datasets.extend(datasets);
    } else {
        names.push(PendingName {
            text: text.to_string(),
            kind,
            language: language.to_string(),
            datasets,
        });
    }
}

fn insert_plant(
    conn: &mut SqliteConnection,
    rec: &PlantRecord,
    glossary_keys: &BTreeSet<String>,
) -> Result<(), BuildError> {
    let id = rec.id.as_str();
    let refs = Refs { record: rec };

    // Planta y familia (atribuida al dataset del primer ref del nombre científico).
    let sci_datasets = refs.datasets("scientificName", &rec.scientific_name.refs)?;
    let first_sci_ref = &rec.scientific_name.refs[0];
    let family_source_id = refs.entry("scientificName", first_sci_ref)?.dataset.clone();
    if let Some(family) = &rec.family {
        refs.datasets("family", &family.refs)?;
    }
    diesel::insert_into(plant::table)
        .values(PlantRow {
            id: id.to_string(),
            scientific_name: rec.scientific_name.name.clone(),
            scientific_name_normalized: normalize_name(&rec.scientific_name.name),
            family: rec.family.as_ref().map(|f| f.value.clone()),
            family_source_id: rec.family.as_ref().map(|_| family_source_id),
        })
        .execute(conn)?;
    // Identificador de cada fuente que respalda el nombre científico, como dato de procedencia.
    let mut seen_sources: BTreeSet<String> = BTreeSet::new();
    for key in &rec.scientific_name.refs {
        let dataset = refs.entry("scientificName", key)?.dataset.clone();
        if seen_sources.insert(dataset.clone()) {
            let source_plant_id = key.split_once(':').map_or(key.as_str(), |(_, rest)| rest);
            diesel::insert_into(plant_source_id::table)
                .values(PlantSourceIdRow {
                    plant_id: id.to_string(),
                    source_id: dataset,
                    source_plant_id: source_plant_id.to_string(),
                })
                .execute(conn)?;
        }
    }

    // Perfil.
    if let Some(origin) = &rec.origin {
        refs.datasets("origin", &origin.refs)?;
    }
    if let Some(description) = &rec.description {
        refs.datasets("description", &description.refs)?;
    }
    if let Some(oil) = &rec.oil {
        refs.datasets("oil", &oil.refs)?;
    }
    diesel::insert_into(plant_profile::table)
        .values(PlantProfileRow {
            plant_id: id.to_string(),
            display_name: rec.display_name.as_ref().map(|d| d.value.clone()),
            authors: rec.scientific_name.authors.clone(),
            origin: rec.origin.as_ref().map(|o| o.value.clone()),
            description: rec.description.as_ref().map(|d| d.value.clone()),
            oil_type: rec.oil.as_ref().map(|o| o.kind.clone()),
            record_version: to_i32(rec.record_version as usize),
            bundle_hash: rec.bundle_hash.clone(),
            prompt_version: to_i32(rec.prompt_version as usize),
        })
        .execute(conn)?;

    // Referencias de cada campo del perfil (lista cerrada de `field`).
    let mut profile_refs: Vec<(&str, Vec<String>)> = vec![(
        "scientificName",
        refs.unique("scientificName", &rec.scientific_name.refs)?,
    )];
    if let Some(v) = &rec.family {
        profile_refs.push(("family", refs.unique("family", &v.refs)?));
    }
    if let Some(v) = &rec.display_name {
        profile_refs.push(("displayName", refs.unique("displayName", &v.refs)?));
    }
    if let Some(v) = &rec.origin {
        profile_refs.push(("origin", refs.unique("origin", &v.refs)?));
    }
    if let Some(v) = &rec.description {
        profile_refs.push(("description", refs.unique("description", &v.refs)?));
    }
    if let Some(v) = &rec.oil {
        profile_refs.push(("oil", refs.unique("oil", &v.refs)?));
    }
    if !rec.parts_used.is_empty() {
        let mut all: Vec<String> = Vec::new();
        for (i, part) in rec.parts_used.iter().enumerate() {
            for r in refs.unique(&format!("partsUsed[{i}]"), &part.refs)? {
                if !all.contains(&r) {
                    all.push(r);
                }
            }
        }
        profile_refs.push(("partsUsed", all));
    }
    for (field, list) in profile_refs {
        for reference_id in list {
            diesel::insert_into(plant_profile_ref::table)
                .values(PlantProfileRefRow {
                    plant_id: id.to_string(),
                    field: field.to_string(),
                    reference_id,
                })
                .execute(conn)?;
        }
    }

    // Nombres: científico y sinónimos en `la`, nombre para mostrar y nombres comunes.
    let mut names: Vec<PendingName> = Vec::new();
    add_name(
        &mut names,
        &rec.scientific_name.name,
        "scientific",
        "la",
        sci_datasets,
    );
    for (i, syn) in rec.synonyms.iter().enumerate() {
        let datasets = refs.datasets(&format!("synonyms[{i}]"), &syn.refs)?;
        add_name(&mut names, &syn.name, "scientific", "la", datasets);
    }
    if let Some(display) = &rec.display_name {
        let datasets = refs.datasets("displayName", &display.refs)?;
        // Un `displayName` en latín es el nombre científico (planta sin nombre común): queda en el perfil, no como nombre común.
        if display.language != "la" {
            add_name(
                &mut names,
                &display.value,
                "common",
                &display.language,
                datasets,
            );
        }
    }
    for (i, common) in rec.common_names.iter().enumerate() {
        let datasets = refs.datasets(&format!("commonNames[{i}]"), &common.refs)?;
        // Un nombre en latín no es un nombre común.
        if common.language != "la" {
            add_name(
                &mut names,
                &common.text,
                "common",
                &common.language,
                datasets,
            );
        }
    }
    for name in &names {
        let normalized = normalize_name(&name.text);
        let name_id: i32 = diesel::insert_into(plant_name::table)
            .values(NewPlantName {
                plant_id: id,
                text: &name.text,
                kind: name.kind,
                language: &name.language,
                normalized: &normalized,
            })
            .returning(plant_name::id)
            .get_result(conn)?;
        for dataset in &name.datasets {
            diesel::insert_into(plant_name_source::table)
                .values(PlantNameSourceRow {
                    plant_name_id: name_id,
                    source_id: dataset.clone(),
                })
                .execute(conn)?;
        }
    }

    // Partes.
    let mut parts: Vec<(String, BTreeSet<String>)> = Vec::new();
    for (i, part) in rec.parts_used.iter().enumerate() {
        let datasets = refs.datasets(&format!("partsUsed[{i}]"), &part.refs)?;
        match parts.iter_mut().find(|(label, _)| label == &part.value) {
            Some((_, existing)) => existing.extend(datasets),
            None => parts.push((part.value.clone(), datasets)),
        }
    }
    for (label, datasets) in &parts {
        let part_id: i32 = diesel::insert_into(plant_part::table)
            .values(NewPlantPart {
                plant_id: id,
                label,
            })
            .returning(plant_part::id)
            .get_result(conn)?;
        for dataset in datasets {
            diesel::insert_into(plant_part_source::table)
                .values(PlantPartSourceRow {
                    plant_part_id: part_id,
                    source_id: dataset.clone(),
                })
                .execute(conn)?;
        }
    }

    let flag_targets: BTreeSet<&str> = rec.review_flags.iter().map(|f| f.target.as_str()).collect();
    insert_uses(conn, rec, &refs, &flag_targets, glossary_keys)?;
    insert_goals(conn, rec, &refs, &flag_targets)?;

    // Seguridad (sin fila si el registro no trae `safety`).
    if let Some(safety) = &rec.safety {
        let unique = refs.unique("safety", &safety.refs)?;
        diesel::insert_into(plant_safety::table)
            .values(PlantSafetyRow {
                plant_id: id.to_string(),
                level: safety.level.map(|l| {
                    match l {
                        SafetyLevel::Alto => "alto",
                        SafetyLevel::Medio => "medio",
                        SafetyLevel::Bajo => "bajo",
                    }
                    .to_string()
                }),
                text: safety.text.clone(),
            })
            .execute(conn)?;
        for r in unique {
            diesel::insert_into(plant_safety_ref::table)
                .values(PlantSafetyRefRow {
                    plant_id: id.to_string(),
                    reference_id: r,
                })
                .execute(conn)?;
        }
    }

    // Imagen.
    if let Some(image) = &rec.image {
        if !image_license_allowed(&image.license) {
            return Err(BuildError::UnsupportedImageLicense {
                plant: id.to_string(),
                license: image.license.clone(),
            });
        }
        refs.datasets("image", &image.refs)?;
        diesel::insert_into(plant_image::table)
            .values(PlantImageRow {
                plant_id: id.to_string(),
                url: image.url.clone(),
                page_url: image.page_url.clone(),
                author: image.author.clone(),
                license: image.license.clone(),
                license_url: image.license_url.clone(),
                attribution_required: image.attribution_required,
            })
            .execute(conn)?;
    }

    // Alias y avisos de revisión.
    for alias in &rec.aliases {
        diesel::insert_into(plant_alias::table)
            .values(PlantAliasRow {
                alias: alias.clone(),
                plant_id: id.to_string(),
            })
            .execute(conn)?;
    }
    for flag in &rec.review_flags {
        diesel::insert_into(plant_review_flag::table)
            .values(NewPlantReviewFlag {
                plant_id: id,
                code: &flag.code,
                target: &flag.target,
                message: &flag.message,
            })
            .execute(conn)?;
    }
    Ok(())
}

/// Grupos de uso, sus citas y los usos de la API (uno por referencia resuelta de cada grupo servido).
fn insert_uses(
    conn: &mut SqliteConnection,
    rec: &PlantRecord,
    refs: &Refs<'_>,
    flag_targets: &BTreeSet<&str>,
    glossary_keys: &BTreeSet<String>,
) -> Result<(), BuildError> {
    let id = rec.id.as_str();
    // (actividad, referencia) -> datasets; la API tiene una fila por par, aunque dos grupos lo repitan.
    let mut uses: Vec<(String, String, BTreeSet<String>)> = Vec::new();
    for (i, group) in rec.traditional_uses.iter().enumerate() {
        let target = format!("traditionalUses[{i}]");
        let group_datasets = refs.datasets(&format!("{target}.refs"), &group.refs)?;
        if group.pending_review && !flag_targets.contains(target.as_str()) {
            return Err(BuildError::PendingWithoutFlag {
                plant: id.to_string(),
                target,
            });
        }
        let countries =
            serde_json::to_string(&group.countries).map_err(|e| BuildError::Storage {
                plant: Some(id.to_string()),
                message: e.to_string(),
            })?;
        let group_id: i32 = diesel::insert_into(plant_use_group::table)
            .values(NewPlantUseGroup {
                plant_id: id,
                position: to_i32(i),
                activity: &group.activity,
                activity_source: &group.activity_source,
                n: to_i32(group.n as usize),
                countries: &countries,
                pending_review: group.pending_review,
                glossary_key: glossary_key_for(&group.activity, glossary_keys),
            })
            .returning(plant_use_group::id)
            .get_result(conn)?;

        let mut keys: BTreeSet<&str> = BTreeSet::new();
        for (j, citation) in group.citations.iter().enumerate() {
            if !keys.insert(citation.key.as_str()) {
                return Err(BuildError::DuplicateCitationKey {
                    plant: id.to_string(),
                    target,
                    key: citation.key.clone(),
                });
            }
            let reference_id = match &citation.reference {
                Some(r) => {
                    refs.entry(&format!("{target}.citations[{j}].ref"), r)?;
                    Some(r.clone())
                }
                None => None,
            };
            diesel::insert_into(plant_use_group_ref::table)
                .values(PlantUseGroupRefRow {
                    use_group_id: group_id,
                    key: citation.key.clone(),
                    position: to_i32(j),
                    text: citation.text.clone(),
                    resolved: reference_id.is_some(),
                    reference_id: reference_id.clone(),
                })
                .execute(conn)?;
            // Un grupo pendiente no genera usos de la API; una cita sin resolver tampoco.
            if group.pending_review {
                continue;
            }
            if let Some(r) = reference_id {
                let mut datasets = group_datasets.clone();
                datasets.insert(refs.entry("citation", &r)?.dataset.clone());
                match uses
                    .iter_mut()
                    .find(|(activity, rf, _)| activity == &group.activity && rf == &r)
                {
                    Some((_, _, existing)) => existing.extend(datasets),
                    None => uses.push((group.activity.clone(), r, datasets)),
                }
            }
        }
    }
    for (activity, reference_id, datasets) in &uses {
        let use_id: i32 = diesel::insert_into(plant_use::table)
            .values(NewPlantUse {
                plant_id: id,
                activity,
                language: "es",
                reference_id,
            })
            .returning(plant_use::id)
            .get_result(conn)?;
        for dataset in datasets {
            diesel::insert_into(plant_use_source::table)
                .values(PlantUseSourceRow {
                    plant_use_id: use_id,
                    source_id: dataset.clone(),
                })
                .execute(conn)?;
        }
    }
    Ok(())
}

/// Objetivos de la planta con sus referencias.
fn insert_goals(
    conn: &mut SqliteConnection,
    rec: &PlantRecord,
    refs: &Refs<'_>,
    flag_targets: &BTreeSet<&str>,
) -> Result<(), BuildError> {
    let id = rec.id.as_str();
    let mut seen: BTreeSet<(&str, &str, &str)> = BTreeSet::new();
    for (i, g) in rec.goals.iter().enumerate() {
        let unique = refs.unique(&format!("goals[{i}].refs"), &g.refs)?;
        let sub = g.subarea.as_deref();
        if !seen.insert((g.goal.as_str(), sub.unwrap_or(""), g.area.as_str())) {
            return Err(BuildError::DuplicateGoal {
                plant: id.to_string(),
                goal: g.goal.clone(),
                area: g.area.clone(),
            });
        }
        if g.pending_review {
            let mut targets = vec![format!("goals.{}", g.goal), format!("goals[{i}]")];
            if let Some(sub) = sub {
                targets.push(format!("goals.{}.{sub}", g.goal));
            }
            if !targets.iter().any(|t| flag_targets.contains(t.as_str())) {
                return Err(BuildError::PendingWithoutFlag {
                    plant: id.to_string(),
                    target: targets.swap_remove(0),
                });
            }
        }
        let goal_row_id: i32 = diesel::insert_into(plant_goal::table)
            .values(NewPlantGoal {
                plant_id: id,
                goal_id: &g.goal,
                subarea_id: sub,
                position: to_i32(i),
                area: &g.area,
                evidence: &g.evidence,
                pending_review: g.pending_review,
            })
            .returning(plant_goal::id)
            .get_result(conn)?;
        for r in unique {
            diesel::insert_into(plant_goal_ref::table)
                .values(PlantGoalRefRow {
                    plant_goal_id: goal_row_id,
                    reference_id: r,
                })
                .execute(conn)?;
        }
    }
    Ok(())
}

/// Licencias de imagen admitidas: CC0, dominio público, CC BY y CC BY-SA, en cualquier versión; se rechazan NC y ND.
///
/// Es la misma regla que aplica el validador de las herramientas de la semilla.
pub fn image_license_allowed(license: &str) -> bool {
    let lower = license.trim().to_lowercase();
    if lower == "public domain"
        || lower == "dominio público"
        || lower == "dominio publico"
        || lower.starts_with("cc0")
        || lower == "pd"
        || lower.starts_with("pd ")
        || lower.starts_with("pd-")
    {
        return true;
    }
    let tokens: Vec<&str> = lower.split([' ', '-']).filter(|t| !t.is_empty()).collect();
    if tokens.len() < 2 || tokens[0] != "cc" || tokens[1] != "by" {
        return false;
    }
    if tokens.iter().any(|t| *t == "nc" || *t == "nd") {
        return false;
    }
    let mut rest = &tokens[2..];
    if rest.first() == Some(&"sa") {
        rest = &rest[1..];
    }
    let is_version = |t: &str| {
        let mut parts = t.split('.');
        matches!(
            (parts.next(), parts.next(), parts.next()),
            (Some(a), Some(b), None)
                if !a.is_empty()
                    && !b.is_empty()
                    && a.chars().all(|c| c.is_ascii_digit())
                    && b.chars().all(|c| c.is_ascii_digit())
        )
    };
    if rest.first().is_some_and(|t| is_version(t)) {
        rest = &rest[1..];
    }
    // Un sufijo de jurisdicción opcional (por ejemplo «au»).
    match rest {
        [] => true,
        [word] => word.chars().all(char::is_alphabetic),
        _ => false,
    }
}

/// Conteos de la base escrita, leídos con `rusqlite` (independiente de Diesel) y su hash lógico.
fn report_of(db: &Path) -> Result<SeedBuildReport, BuildError> {
    let hash = content_hash(db)?;
    let conn = Rusqlite::open_with_flags(db, OpenFlags::SQLITE_OPEN_READ_ONLY)
        .map_err(IngestError::from)?;
    let count = |sql: &str| -> Result<u64, BuildError> {
        conn.query_row(sql, [], |r| r.get::<_, i64>(0))
            .map(|n| u64::try_from(n).unwrap_or(0))
            .map_err(|e| BuildError::Ingest(IngestError::from(e)))
    };
    Ok(SeedBuildReport {
        content_hash: hash,
        plants: count("SELECT COUNT(*) FROM plant")?,
        names: count("SELECT COUNT(*) FROM plant_name")?,
        uses: count("SELECT COUNT(*) FROM plant_use")?,
        use_groups: count("SELECT COUNT(*) FROM plant_use_group")?,
        pending_use_groups: count("SELECT COUNT(*) FROM plant_use_group WHERE pending_review = 1")?,
        unresolved_citations: count("SELECT COUNT(*) FROM plant_use_group_ref WHERE resolved = 0")?,
        plant_goals: count("SELECT COUNT(*) FROM plant_goal")?,
        pending_goals: count("SELECT COUNT(*) FROM plant_goal WHERE pending_review = 1")?,
        safety: count("SELECT COUNT(*) FROM plant_safety")?,
        images: count("SELECT COUNT(*) FROM plant_image")?,
        references: count("SELECT COUNT(*) FROM reference")?,
        sources: count("SELECT COUNT(*) FROM source")?,
        aliases: count("SELECT COUNT(*) FROM plant_alias")?,
        review_flags: count("SELECT COUNT(*) FROM plant_review_flag")?,
        glossary_terms: count("SELECT COUNT(*) FROM activity_glossary")?,
        glossary_linked_groups: count(
            "SELECT COUNT(*) FROM plant_use_group WHERE glossary_key IS NOT NULL",
        )?,
    })
}

#[cfg(test)]
mod tests {
    use super::image_license_allowed;

    #[test]
    fn accepts_cc0_public_domain_cc_by_and_cc_by_sa_in_any_version() {
        for ok in [
            "CC0",
            "CC0 1.0",
            "Public domain",
            "Dominio público",
            "CC BY 2.0",
            "CC BY 2.5",
            "CC BY 3.0 au",
            "CC BY-SA 3.0",
            "CC BY-SA 4.0",
            "cc-by-sa-2.5",
            "CC BY 4.0",
        ] {
            assert!(image_license_allowed(ok), "{ok}");
        }
    }

    #[test]
    fn rejects_other_licenses() {
        for bad in [
            "",
            "CC BY-NC 4.0",
            "CC BY-ND 2.0",
            "CC BY-NC-SA 3.0",
            "All rights reserved",
            "GFDL",
            "CC BY 4.0 extra words",
            "CC SA 4.0",
        ] {
            assert!(!image_license_allowed(bad), "{bad}");
        }
    }
}
