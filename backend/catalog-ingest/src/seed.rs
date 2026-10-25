//! Lectura de la semilla del catálogo (`data/seed/`) con tipos estrictos y verificación del manifiesto.
//!
//! La semilla la produce la herramienta `tools/catalog-seed` y la sella con un `manifest.json` que declara el número de plantas y el `seedHash`. Este módulo no depende del marco de adaptadores: solo lee, valida la forma de cada registro (`deny_unknown_fields`, sin campos opcionales que el esquema no permita) y comprueba la integridad. El mapeo a las tablas es otro paso.

use std::collections::BTreeMap;
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Deserializer};
use serde_json::Value;
use sha2::{Digest, Sha256};

/// Versión del formato del manifiesto que este lector entiende.
pub const MANIFEST_FORMAT: u32 = 1;
/// Versión del registro que este lector entiende.
pub const RECORD_VERSION: u32 = 1;

/// Errores de lectura y verificación de la semilla.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SeedError {
    /// No hay semilla en el directorio indicado (falta el manifiesto).
    Missing {
        /// Directorio de la semilla.
        dir: PathBuf,
    },
    /// Fallo de entrada/salida.
    Io {
        /// Archivo implicado.
        path: PathBuf,
        /// Mensaje del sistema operativo.
        message: String,
    },
    /// Un archivo no es JSON válido o no cumple los tipos estrictos.
    Parse {
        /// Archivo implicado.
        file: PathBuf,
        /// Planta implicada, si el archivo es un registro.
        plant: Option<String>,
        /// Descripción del problema.
        message: String,
    },
    /// El nombre del archivo no coincide con el `id` del registro.
    FileNameMismatch {
        /// Archivo implicado.
        file: PathBuf,
        /// `id` declarado en el registro.
        id: String,
    },
    /// El número de plantas no coincide con el del manifiesto.
    CountMismatch {
        /// Número declarado en el manifiesto.
        expected: usize,
        /// Número de registros encontrados.
        found: usize,
    },
    /// Una versión de formato o de registro no es la que el lector entiende.
    UnsupportedVersion {
        /// Archivo implicado.
        file: PathBuf,
        /// Descripción del problema.
        message: String,
    },
    /// Un registro usa un objetivo o subárea que no existe en `goals.json`, o una subárea de otro objetivo.
    UnknownGoal {
        /// Archivo implicado.
        file: PathBuf,
        /// Planta implicada.
        plant: String,
        /// Descripción del problema, con el valor.
        message: String,
    },
    /// El `seedHash` recalculado no coincide con el del manifiesto.
    HashMismatch {
        /// Directorio de la semilla.
        dir: PathBuf,
        /// Hash declarado en el manifiesto.
        expected: String,
        /// Hash recalculado.
        found: String,
    },
}

impl fmt::Display for SeedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Missing { dir } => write!(
                f,
                "no existe la semilla del catálogo en {} (falta manifest.json); genérala con `python3 -I tools/catalog-seed/cli.py seal --seed {}` o restaura data/seed/ desde el repositorio",
                dir.display(),
                dir.display()
            ),
            Self::Io { path, message } => {
                write!(f, "no se pudo leer {}: {message}", path.display())
            }
            Self::Parse {
                file,
                plant,
                message,
            } => match plant {
                Some(plant) => write!(
                    f,
                    "registro inválido en {} (planta {plant}): {message}",
                    file.display()
                ),
                None => write!(
                    f,
                    "archivo de la semilla inválido {}: {message}",
                    file.display()
                ),
            },
            Self::FileNameMismatch { file, id } => write!(
                f,
                "el archivo {} no se llama como el id de su registro ({id})",
                file.display()
            ),
            Self::CountMismatch { expected, found } => write!(
                f,
                "el manifiesto declara {expected} plantas pero la semilla tiene {found}"
            ),
            Self::UnsupportedVersion { file, message } => {
                write!(f, "versión no soportada en {}: {message}", file.display())
            }
            Self::UnknownGoal {
                file,
                plant,
                message,
            } => write!(
                f,
                "objetivo inválido en {} (planta {plant}): {message}",
                file.display()
            ),
            Self::HashMismatch {
                dir,
                expected,
                found,
            } => write!(
                f,
                "la semilla {} fue alterada: el seedHash del manifiesto es {expected} pero el contenido da {found}; vuelve a sellarla con `python3 -I tools/catalog-seed/cli.py seal --seed {}` si el cambio es intencional",
                dir.display(),
                dir.display()
            ),
        }
    }
}

impl std::error::Error for SeedError {}

/// Campo que debe estar presente pero admite `null` (el esquema lo exige en `required`).
fn nullable<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer)
}

/// Fuente declarada en el manifiesto.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestSource {
    /// Atribución.
    pub attribution: String,
    /// Archivos de la fuente.
    pub files: Vec<ManifestFile>,
    /// Identificador del dataset.
    pub id: String,
    /// Licencia.
    pub license: String,
    /// Nombre legible de la fuente.
    pub name: String,
    /// Página del dataset.
    pub url: String,
    /// Versión de la fuente.
    pub version: String,
}

/// Archivo de una fuente del manifiesto.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestFile {
    /// Checksum del archivo.
    pub checksum: ManifestChecksum,
    /// Nombre del archivo.
    pub filename: String,
    /// Tamaño en bytes.
    pub size: u64,
}

/// Checksum de un archivo de fuente.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestChecksum {
    /// Algoritmo (`md5` o `sha256`).
    pub algorithm: String,
    /// Valor en hexadecimal.
    pub value: String,
}

/// Manifiesto de la semilla (`manifest.json`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Manifest {
    /// Versión del formato del manifiesto.
    pub format_version: u32,
    /// Fuentes declaradas.
    pub sources: Vec<ManifestSource>,
    /// Versión del prompt con que se generaron los registros.
    pub prompt_version: u32,
    /// Versión del registro.
    pub record_version: u32,
    /// Modelos usados.
    pub models: Vec<String>,
    /// Número de plantas.
    pub plant_count: usize,
    /// Número de plantas por código de aviso de revisión.
    pub review_flags: BTreeMap<String, u32>,
    /// Hash de integridad de la semilla (`sha256:<hex>`).
    pub seed_hash: String,
}

/// Objetivo del catálogo de objetivos.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GoalEntry {
    /// Identificador.
    pub id: String,
    /// Etiqueta visible.
    pub label: String,
    /// Posición de orden.
    pub position: u32,
}

/// Subárea del catálogo de objetivos.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct SubareaEntry {
    /// Identificador.
    pub id: String,
    /// Objetivo al que pertenece.
    pub goal_id: String,
    /// Etiqueta visible.
    pub label: String,
    /// Posición de orden.
    pub position: u32,
}

/// Catálogo de objetivos (`goals.json`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GoalCatalog {
    /// Objetivos.
    pub goals: Vec<GoalEntry>,
    /// Subáreas.
    pub subareas: Vec<SubareaEntry>,
}

/// Nombre científico o sinónimo.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Name {
    /// Nombre.
    pub name: String,
    /// Autores (puede ser nulo).
    #[serde(deserialize_with = "nullable")]
    pub authors: Option<String>,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Valor con referencias (familia, origen, descripción, parte usada).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ValueRefs {
    /// Valor.
    pub value: String,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Nombre para mostrar.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DisplayName {
    /// Nombre.
    pub value: String,
    /// Idioma.
    pub language: String,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Nombre común.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommonName {
    /// Texto.
    pub text: String,
    /// Idioma.
    pub language: String,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Tipo de aceite (siempre `Esencial`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Oil {
    /// Tipo de aceite.
    #[serde(rename = "type")]
    pub kind: String,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Cita de un grupo de uso tradicional.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Citation {
    /// Clave de la cita en el insumo.
    pub key: String,
    /// Referencia resuelta, o nulo si la cita no se resolvió.
    #[serde(rename = "ref", deserialize_with = "nullable")]
    pub reference: Option<String>,
    /// Texto de la cita.
    pub text: String,
}

/// Grupo de uso tradicional.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct TraditionalUse {
    /// Actividad.
    pub activity: String,
    /// Fuente de la actividad.
    pub activity_source: String,
    /// Número de registros que respaldan el grupo.
    pub n: u32,
    /// Países.
    pub countries: Vec<String>,
    /// Referencias.
    pub refs: Vec<String>,
    /// Citas.
    pub citations: Vec<Citation>,
    /// Pendiente de revisión.
    pub pending_review: bool,
}

/// Asignación de un área de uso a un objetivo.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct GoalAssignment {
    /// Identificador del objetivo (validado contra `goals.json`).
    pub goal: String,
    /// Identificador de la subárea (nula salvo en «otros objetivos»; validado contra `goals.json`).
    #[serde(deserialize_with = "nullable")]
    pub subarea: Option<String>,
    /// Área de uso de origen.
    pub area: String,
    /// Evidencia.
    pub evidence: String,
    /// Pendiente de revisión.
    pub pending_review: bool,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Nivel de seguridad.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SafetyLevel {
    /// Alto.
    Alto,
    /// Medio.
    Medio,
    /// Bajo.
    Bajo,
}

/// Seguridad de la planta.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Safety {
    /// Nivel (nulo si el texto es solo una advertencia sin nivel).
    #[serde(deserialize_with = "nullable")]
    pub level: Option<SafetyLevel>,
    /// Texto.
    pub text: String,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Imagen de la planta.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Image {
    /// URL de la imagen.
    pub url: String,
    /// URL de la página de origen.
    pub page_url: String,
    /// Autor (puede ser nulo).
    #[serde(deserialize_with = "nullable")]
    pub author: Option<String>,
    /// Licencia.
    pub license: String,
    /// URL de la licencia (puede ser nula).
    #[serde(deserialize_with = "nullable")]
    pub license_url: Option<String>,
    /// Si la licencia exige atribución.
    pub attribution_required: bool,
    /// Referencias.
    pub refs: Vec<String>,
}

/// Fuente de un registro.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RecordSource {
    /// Dataset.
    pub dataset: String,
    /// Licencia.
    pub license: String,
}

/// Entrada del diccionario de referencias de un registro.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RefEntry {
    /// Dataset de origen.
    pub dataset: String,
    /// Etiqueta.
    pub label: String,
    /// Licencia.
    pub license: String,
    /// URL, si existe.
    #[serde(default)]
    pub url: Option<String>,
}

/// Aviso de revisión.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ReviewFlag {
    /// Código.
    pub code: String,
    /// Elemento al que se refiere.
    pub target: String,
    /// Mensaje.
    pub message: String,
}

/// Registro consolidado de una planta (`plants/<id>.json`).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct PlantRecord {
    /// Identificador de la planta.
    pub id: String,
    /// Versión del registro.
    pub record_version: u32,
    /// Hash del paquete de insumo.
    pub bundle_hash: String,
    /// Versión del prompt.
    pub prompt_version: u32,
    /// Modelo.
    pub model: String,
    /// Alias del identificador.
    pub aliases: Vec<String>,
    /// Nombre científico.
    pub scientific_name: Name,
    /// Sinónimos.
    pub synonyms: Vec<Name>,
    /// Familia.
    #[serde(deserialize_with = "nullable")]
    pub family: Option<ValueRefs>,
    /// Nombre para mostrar.
    #[serde(deserialize_with = "nullable")]
    pub display_name: Option<DisplayName>,
    /// Nombres comunes.
    pub common_names: Vec<CommonName>,
    /// Origen.
    #[serde(deserialize_with = "nullable")]
    pub origin: Option<ValueRefs>,
    /// Descripción.
    #[serde(deserialize_with = "nullable")]
    pub description: Option<ValueRefs>,
    /// Partes usadas.
    pub parts_used: Vec<ValueRefs>,
    /// Aceite.
    #[serde(deserialize_with = "nullable")]
    pub oil: Option<Oil>,
    /// Usos tradicionales.
    pub traditional_uses: Vec<TraditionalUse>,
    /// Objetivos.
    pub goals: Vec<GoalAssignment>,
    /// Seguridad.
    #[serde(deserialize_with = "nullable")]
    pub safety: Option<Safety>,
    /// Imagen.
    #[serde(deserialize_with = "nullable")]
    pub image: Option<Image>,
    /// Fuentes.
    pub sources: Vec<RecordSource>,
    /// Diccionario de referencias.
    pub refs: BTreeMap<String, RefEntry>,
    /// Avisos de revisión.
    pub review_flags: Vec<ReviewFlag>,
}

/// Semilla leída y verificada, lista para el mapeo a las tablas.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Seed {
    /// Manifiesto.
    pub manifest: Manifest,
    /// Catálogo de objetivos.
    pub goals: GoalCatalog,
    /// Registros ordenados por `id`.
    pub plants: Vec<PlantRecord>,
}

fn io_error(path: &Path, err: &std::io::Error) -> SeedError {
    SeedError::Io {
        path: path.to_path_buf(),
        message: err.to_string(),
    }
}

fn read_json(path: &Path) -> Result<Value, SeedError> {
    let text = fs::read_to_string(path).map_err(|e| io_error(path, &e))?;
    serde_json::from_str(&text).map_err(|e| SeedError::Parse {
        file: path.to_path_buf(),
        plant: None,
        message: e.to_string(),
    })
}

/// JSON canónico idéntico al de la herramienta (`json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`).
///
/// Las claves se ordenan por punto de código (equivale al orden por bytes UTF-8), las cadenas se escapan como en Python con `ensure_ascii=False` y solo se admiten enteros (la semilla no tiene decimales).
fn canonical_json(value: &Value, out: &mut String) -> Result<(), String> {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Value::Number(n) if n.is_f64() => {
            return Err(format!("número no entero en la semilla: {n}"));
        }
        Value::Number(n) => out.push_str(&n.to_string()),
        Value::String(s) => out.push_str(&serde_json::to_string(s).map_err(|e| e.to_string())?),
        Value::Array(items) => {
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                canonical_json(item, out)?;
            }
            out.push(']');
        }
        Value::Object(map) => {
            let mut entries: Vec<(&String, &Value)> = map.iter().collect();
            entries.sort_by(|a, b| a.0.cmp(b.0));
            out.push('{');
            for (i, (key, item)) in entries.into_iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push_str(&serde_json::to_string(key).map_err(|e| e.to_string())?);
                out.push(':');
                canonical_json(item, out)?;
            }
            out.push('}');
        }
    }
    Ok(())
}

fn canonical(value: &Value, file: &Path, plant: Option<&str>) -> Result<String, SeedError> {
    let mut out = String::new();
    canonical_json(value, &mut out).map_err(|message| SeedError::Parse {
        file: file.to_path_buf(),
        plant: plant.map(str::to_owned),
        message,
    })?;
    Ok(out)
}

/// Lee la semilla de `dir` (con `manifest.json`, `goals.json` y `plants/*.json`) y verifica su integridad.
///
/// Comprueba que cada archivo se llame como el `id` de su registro, que el número de plantas coincida con el manifiesto y que el `seedHash` recalculado sea el del manifiesto. Los errores identifican el archivo y la planta.
pub fn load_seed(dir: &Path) -> Result<Seed, SeedError> {
    let manifest_path = dir.join("manifest.json");
    if !manifest_path.is_file() {
        return Err(SeedError::Missing {
            dir: dir.to_path_buf(),
        });
    }
    let manifest: Manifest =
        serde_json::from_value(read_json(&manifest_path)?).map_err(|e| SeedError::Parse {
            file: manifest_path.clone(),
            plant: None,
            message: e.to_string(),
        })?;
    if manifest.format_version != MANIFEST_FORMAT {
        return Err(SeedError::UnsupportedVersion {
            file: manifest_path,
            message: format!(
                "formatVersion {} (se espera {MANIFEST_FORMAT})",
                manifest.format_version
            ),
        });
    }

    let goals_path = dir.join("goals.json");
    if !goals_path.is_file() {
        return Err(SeedError::Missing {
            dir: dir.to_path_buf(),
        });
    }
    let goals_value = read_json(&goals_path)?;
    let goals: GoalCatalog =
        serde_json::from_value(goals_value.clone()).map_err(|e| SeedError::Parse {
            file: goals_path.clone(),
            plant: None,
            message: e.to_string(),
        })?;

    let plants_dir = dir.join("plants");
    let mut files: Vec<PathBuf> = fs::read_dir(&plants_dir)
        .map_err(|e| io_error(&plants_dir, &e))?
        .map(|entry| {
            entry
                .map(|e| e.path())
                .map_err(|e| io_error(&plants_dir, &e))
        })
        .collect::<Result<_, _>>()?;
    files.retain(|p| p.extension().is_some_and(|ext| ext == "json"));
    files.sort();

    let mut records: Vec<(PlantRecord, String)> = Vec::with_capacity(files.len());
    for file in &files {
        let value = read_json(file)?;
        let plant = value.get("id").and_then(Value::as_str).map(str::to_owned);
        let record: PlantRecord =
            serde_json::from_value(value.clone()).map_err(|e| SeedError::Parse {
                file: file.clone(),
                plant: plant.clone(),
                message: e.to_string(),
            })?;
        if file.file_stem().and_then(|s| s.to_str()) != Some(record.id.as_str()) {
            return Err(SeedError::FileNameMismatch {
                file: file.clone(),
                id: record.id,
            });
        }
        if record.record_version != RECORD_VERSION {
            return Err(SeedError::UnsupportedVersion {
                file: file.clone(),
                message: format!(
                    "planta {}: recordVersion {} (se espera {RECORD_VERSION})",
                    record.id, record.record_version
                ),
            });
        }
        check_goals(&record, &goals, file)?;
        let canon = canonical(&value, file, plant.as_deref())?;
        records.push((record, canon));
    }
    if records.len() != manifest.plant_count {
        return Err(SeedError::CountMismatch {
            expected: manifest.plant_count,
            found: records.len(),
        });
    }
    records.sort_by(|a, b| a.0.id.cmp(&b.0.id));

    let mut hasher = Sha256::new();
    for (record, canon) in &records {
        hasher.update(format!("plant\n{}\n{canon}\n", record.id).as_bytes());
    }
    hasher.update(format!("goals\n{}\n", canonical(&goals_value, &goals_path, None)?).as_bytes());
    let found = format!("sha256:{}", hex(&hasher.finalize()));
    if found != manifest.seed_hash {
        return Err(SeedError::HashMismatch {
            dir: dir.to_path_buf(),
            expected: manifest.seed_hash,
            found,
        });
    }

    Ok(Seed {
        manifest,
        goals,
        plants: records.into_iter().map(|(r, _)| r).collect(),
    })
}

fn check_goals(record: &PlantRecord, catalog: &GoalCatalog, file: &Path) -> Result<(), SeedError> {
    let fail = |message: String| SeedError::UnknownGoal {
        file: file.to_path_buf(),
        plant: record.id.clone(),
        message,
    };
    for assignment in &record.goals {
        if !catalog.goals.iter().any(|g| g.id == assignment.goal) {
            return Err(fail(format!("objetivo desconocido «{}»", assignment.goal)));
        }
        if let Some(sub) = &assignment.subarea {
            match catalog.subareas.iter().find(|s| &s.id == sub) {
                None => return Err(fail(format!("subárea desconocida «{sub}»"))),
                Some(s) if s.goal_id != assignment.goal => {
                    return Err(fail(format!(
                        "la subárea «{sub}» pertenece a «{}», no a «{}»",
                        s.goal_id, assignment.goal
                    )));
                }
                Some(_) => {}
            }
        }
    }
    Ok(())
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
