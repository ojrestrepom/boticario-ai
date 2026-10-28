//! Implementación SQLite (con Diesel) del repositorio del catálogo.
//!
//! Lee únicamente el esquema neutral, siempre con el DSL de Diesel: aquí no hay SQL escrito a mano.
//! La base se abre en solo lectura y se comprueba su versión de esquema antes de servir nada.

use std::collections::{BTreeSet, HashMap, HashSet};
use std::error::Error;
use std::fmt;
use std::path::{Path, PathBuf};
use std::time::Duration;

use catalog_core::domain::{
    Credit, Goal, GoalPlant, GoalPlants, GoalPlantsOutcome, GoalSummary, IdName, Image, ListQuery,
    NameKind, Page, Part, Plant, PlantId, PlantName, PlantSummary, Reference, Safety, SafetyLevel,
    SubareaSummary, Use, UseGroup, UseGroupReference,
};
use catalog_core::normalize::{normalize_name, slug};
use catalog_core::repository::{CatalogRepository, RepositoryError};
use catalog_core::rows::{
    GoalRow, GoalSubareaRow, PlantGoalRefRow, PlantGoalRow, PlantImageRow, PlantNameRow,
    PlantPartRow, PlantProfileRow, PlantRow, PlantSafetyRefRow, PlantSafetyRow,
    PlantUseGroupRefRow, PlantUseGroupRow, PlantUseRow, ReferenceRow, SourceRow,
};
use catalog_core::schema::{
    goal, goal_subarea, metadata, plant, plant_alias, plant_goal, plant_goal_ref, plant_image,
    plant_name, plant_name_source, plant_part, plant_part_source, plant_profile, plant_profile_ref,
    plant_safety, plant_safety_ref, plant_use, plant_use_group, plant_use_group_ref,
    plant_use_source, reference, source,
};
use catalog_core::sqlite::{InvalidPath, read_only_url};
use catalog_core::version::{SCHEMA_VERSION, SCHEMA_VERSION_KEY};
use diesel::SqliteConnection;
use diesel::prelude::*;
use diesel::r2d2::{self, ConnectionManager, Pool, PooledConnection};

/// Conexiones simultáneas que mantiene el pool.
///
/// Cada petición bloqueante usa una conexión mientras dura su consulta; con un catálogo de lectura pequeño, cuatro sobran y acotan los descriptores de archivo abiertos.
pub const POOL_SIZE: u32 = 4;

/// Tiempo máximo que una petición espera una conexión libre del pool.
///
/// El valor por defecto de r2d2 (30 s) dejaría colgada una ráfaga que agote el pool; con 5 s falla limpio con un 500.
pub const POOL_CONNECTION_TIMEOUT: Duration = Duration::from_secs(5);

/// Fallo al abrir el repositorio.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OpenError {
    /// El archivo de la base no existe.
    Missing {
        /// Ruta que se intentó abrir.
        path: PathBuf,
    },
    /// La ruta no se puede convertir a URL de SQLite.
    InvalidPath(InvalidPath),
    /// La base existe pero falló el acceso o la comprobación de versión.
    Repository(RepositoryError),
}

// Se usa un enum propio en vez de reutilizar `RepositoryError`: "falta el archivo" es un problema de arranque con una pista accionable (qué comando ejecutar) que no tiene sentido durante una petición.
impl fmt::Display for OpenError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Missing { path } => write!(
                f,
                "no existe la base del catálogo en {}; constrúyela con `catalog-ingest build`",
                path.display()
            ),
            Self::InvalidPath(err) => err.fmt(f),
            Self::Repository(err) => err.fmt(f),
        }
    }
}

impl Error for OpenError {}

// `From` permite usar `?` y que Rust convierta el error de forma automática.
impl From<RepositoryError> for OpenError {
    fn from(err: RepositoryError) -> Self {
        Self::Repository(err)
    }
}

impl From<InvalidPath> for OpenError {
    fn from(err: InvalidPath) -> Self {
        Self::InvalidPath(err)
    }
}

/// Convierte cualquier error con `Display` (Diesel, r2d2) en un error de almacenamiento.
///
/// Es una función y no un `impl From<diesel::result::Error> for RepositoryError` por la regla de coherencia: solo se puede implementar un trait si el trait o el tipo son del crate actual, y aquí `From`, `diesel::result::Error` y `RepositoryError` son todos ajenos.
fn storage(err: impl fmt::Display) -> RepositoryError {
    RepositoryError::Storage(err.to_string())
}

/// Comprueba la versión de esquema guardada en `metadata`.
fn check_schema_version(conn: &mut SqliteConnection) -> Result<(), RepositoryError> {
    let stored: Option<String> = metadata::table
        .filter(metadata::key.eq(SCHEMA_VERSION_KEY))
        .select(metadata::value)
        .first(conn)
        .optional()
        .map_err(storage)?;
    let text =
        stored.ok_or_else(|| storage(format!("falta {SCHEMA_VERSION_KEY} en los metadatos")))?;
    let found: u32 = text
        .parse()
        .map_err(|_| storage(format!("{SCHEMA_VERSION_KEY} no es numérica: {text:?}")))?;
    if found != SCHEMA_VERSION {
        return Err(RepositoryError::IncompatibleSchema {
            found,
            supported: SCHEMA_VERSION,
        });
    }
    Ok(())
}

type SqlitePool = Pool<ConnectionManager<SqliteConnection>>;

/// Repositorio del catálogo sobre una base SQLite abierta en solo lectura.
pub struct SqliteCatalogRepository {
    pool: SqlitePool,
}

impl SqliteCatalogRepository {
    /// Abre la base en `path` en solo lectura y comprueba que su versión de esquema sea la soportada.
    pub fn open(path: &Path) -> Result<Self, OpenError> {
        if !path.exists() {
            return Err(OpenError::Missing {
                path: path.to_path_buf(),
            });
        }
        let url = read_only_url(path)?;
        // Una conexión directa, antes del pool: una base ilegible, un directorio o una versión incompatible fallan al instante y con el mensaje correcto, en vez de que el pool reintente la apertura hasta agotar su tiempo de espera.
        let mut probe = SqliteConnection::establish(&url).map_err(|err| {
            storage(format!(
                "no se pudo abrir la base del catálogo en {}: {err}",
                path.display()
            ))
        })?;
        check_schema_version(&mut probe).map_err(|err| match err {
            RepositoryError::Storage(msg) => {
                storage(format!("base del catálogo en {}: {msg}", path.display()))
            }
            other => other,
        })?;
        drop(probe);
        let pool = Pool::builder()
            .max_size(POOL_SIZE)
            .connection_timeout(POOL_CONNECTION_TIMEOUT)
            // Sin conexiones ansiosas: ya se comprobó que la base abre, y las conexiones se crean al primer uso.
            // `NopErrorHandler` evita que r2d2 registre cada intento fallido: el error ya llega a quien llama.
            .error_handler(Box::new(r2d2::NopErrorHandler))
            .build_unchecked(ConnectionManager::<SqliteConnection>::new(url));
        Ok(Self { pool })
    }

    fn conn(
        &self,
    ) -> Result<PooledConnection<ConnectionManager<SqliteConnection>>, RepositoryError> {
        self.pool.get().map_err(storage)
    }
}

/// Convierte el texto de `plant_name.kind` en [`NameKind`].
fn parse_kind(kind: &str) -> Result<NameKind, RepositoryError> {
    match kind {
        "scientific" => Ok(NameKind::Scientific),
        "common" => Ok(NameKind::Common),
        other => Err(storage(format!("tipo de nombre desconocido: {other:?}"))),
    }
}

fn to_plant_name(row: &PlantNameRow) -> Result<PlantName, RepositoryError> {
    Ok(PlantName {
        text: row.text.clone(),
        kind: parse_kind(&row.kind)?,
        language: row.language.clone(),
    })
}

/// Patrón `LIKE` de "contiene" para un texto ya normalizado, con `%`, `_` y `\` escapados con `\`.
fn contains_pattern(normalized: &str) -> String {
    let mut pattern = String::from("%");
    for c in normalized.chars() {
        if matches!(c, '%' | '_' | '\\') {
            pattern.push('\\');
        }
        pattern.push(c);
    }
    pattern.push('%');
    pattern
}

impl CatalogRepository for SqliteCatalogRepository {
    /// Precondición: `query.limit` y `query.offset` ya están validados (rangos incluidos) por quien llama; aquí se usan tal cual.
    fn list_plants(&self, query: &ListQuery) -> Result<Page<PlantSummary>, RepositoryError> {
        let mut conn = self.conn()?;
        let conn = &mut *conn;

        // Un `q` vacío o solo con espacios se normaliza a "" y no filtra.
        let normalized = query.q.as_deref().map(normalize_name).unwrap_or_default();
        let pattern = (!normalized.is_empty()).then(|| contains_pattern(&normalized));
        // Para los alias (identificadores anteriores) la consulta se reduce con `slug`: los caracteres que no son letras ni dígitos pasan a un guion, como en el alias. Un `slug` vacío (por ejemplo `%`) no busca en alias.
        let alias_pattern = Some(slug(&normalized))
            .filter(|s| !s.is_empty())
            .map(|s| contains_pattern(&s));

        // Ids de las plantas con algún nombre (científico o común) que contiene el texto.
        // `escape('\\')` declara `\` como carácter de escape: sin él, `%` y `_` del usuario actuarían como comodines.
        let matching_ids = |pattern: &str| {
            plant_name::table
                .filter(plant_name::normalized.like(pattern.to_owned()).escape('\\'))
                .select(plant_name::plant_id)
        };
        // Ids de las plantas con algún alias que contiene el texto reducido. El alias solo sirve para encontrar la planta: nunca se devuelve como nombre.
        let matching_alias_ids = |pattern: &str| {
            plant_alias::table
                .filter(plant_alias::alias.like(pattern.to_owned()).escape('\\'))
                .select(plant_alias::plant_id)
        };

        // `into_boxed` permite añadir el filtro solo si hay búsqueda.
        // Una sola cláusula `IN (nombres) OR IN (alias)` por planta: cada planta cuenta una vez en la lista y en el total.
        let mut count_query = plant::table.into_boxed();
        let mut page_query = plant::table.into_boxed();
        if let Some(pattern) = &pattern {
            if let Some(alias_pattern) = &alias_pattern {
                count_query = count_query.filter(
                    plant::id
                        .eq_any(matching_ids(pattern))
                        .or(plant::id.eq_any(matching_alias_ids(alias_pattern))),
                );
                page_query = page_query.filter(
                    plant::id
                        .eq_any(matching_ids(pattern))
                        .or(plant::id.eq_any(matching_alias_ids(alias_pattern))),
                );
            } else {
                count_query = count_query.filter(plant::id.eq_any(matching_ids(pattern)));
                page_query = page_query.filter(plant::id.eq_any(matching_ids(pattern)));
            }
        }

        let total: i64 = count_query.count().get_result(conn).map_err(storage)?;
        let plants: Vec<PlantRow> = page_query
            .order_by((plant::scientific_name.asc(), plant::id.asc()))
            .limit(i64::from(query.limit))
            .offset(i64::from(query.offset))
            .select(PlantRow::as_select())
            .load(conn)
            .map_err(storage)?;

        // Una sola consulta para los nombres comunes de toda la página.
        let ids: Vec<&str> = plants.iter().map(|p| p.id.as_str()).collect();
        let name_rows: Vec<PlantNameRow> = if ids.is_empty() {
            Vec::new()
        } else {
            plant_name::table
                .filter(plant_name::kind.eq("common"))
                .filter(plant_name::plant_id.eq_any(&ids))
                .order_by((
                    plant_name::text.asc(),
                    plant_name::language.asc(),
                    plant_name::id.asc(),
                ))
                .select(PlantNameRow::as_select())
                .load(conn)
                .map_err(storage)?
        };
        let mut commons: HashMap<&str, Vec<PlantName>> = HashMap::new();
        for row in &name_rows {
            commons
                .entry(row.plant_id.as_str())
                .or_default()
                .push(to_plant_name(row)?);
        }

        // Una sola consulta para los nombres para mostrar de toda la página (D12: sin N+1 por planta).
        let display_rows: Vec<(String, Option<String>)> = if ids.is_empty() {
            Vec::new()
        } else {
            plant_profile::table
                .filter(plant_profile::plant_id.eq_any(&ids))
                .select((plant_profile::plant_id, plant_profile::display_name))
                .load(conn)
                .map_err(storage)?
        };
        let mut display_names: HashMap<String, String> = display_rows
            .into_iter()
            .filter_map(|(id, name)| name.map(|name| (id, name)))
            .collect();

        let items = plants
            .iter()
            .map(|p| {
                let display_name = display_names
                    .remove(&p.id)
                    .unwrap_or_else(|| p.scientific_name.clone());
                let mut common_names = commons.remove(p.id.as_str()).unwrap_or_default();
                sort_common_names(&mut common_names, &display_name);
                PlantSummary {
                    id: PlantId(p.id.clone()),
                    scientific_name: p.scientific_name.clone(),
                    display_name,
                    common_names,
                    family: p.family.clone(),
                }
            })
            .collect();
        Ok(Page {
            items,
            total: u64::try_from(total).map_err(storage)?,
        })
    }

    fn get_plant(&self, id: &PlantId) -> Result<Option<Plant>, RepositoryError> {
        let mut conn = self.conn()?;
        let conn = &mut *conn;

        // Primero el identificador de planta; solo si no existe se busca un alias (un identificador de planta siempre gana).
        let row: Option<PlantRow> = plant::table
            .find(&id.0)
            .select(PlantRow::as_select())
            .first(conn)
            .optional()
            .map_err(storage)?;
        let row = match row {
            Some(row) => row,
            None => {
                let canonical: Option<String> = plant_alias::table
                    .find(&id.0)
                    .select(plant_alias::plant_id)
                    .first(conn)
                    .optional()
                    .map_err(storage)?;
                let Some(canonical) = canonical else {
                    return Ok(None);
                };
                plant::table
                    .find(&canonical)
                    .select(PlantRow::as_select())
                    .first(conn)
                    .optional()
                    .map_err(storage)?
                    .ok_or_else(|| {
                        storage(format!("alias {:?} apunta a una planta inexistente", id.0))
                    })?
            }
        };
        // De aquí en adelante todo se carga por el identificador canónico, sea cual sea el que se pidió.
        let id = &PlantId(row.id.clone());

        let profile: Option<PlantProfileRow> = plant_profile::table
            .find(&id.0)
            .select(PlantProfileRow::as_select())
            .first(conn)
            .optional()
            .map_err(storage)?;
        // Defensa: sin perfil, o con el nombre nulo, el nombre para mostrar es el científico.
        let display_name = profile
            .as_ref()
            .and_then(|p| p.display_name.clone())
            .unwrap_or_else(|| row.scientific_name.clone());
        let names = load_names(conn, &id.0, &display_name)?;
        // Los sinónimos son los demás nombres científicos; los nombres ya vienen ordenados por texto.
        let mut synonyms: Vec<String> = Vec::new();
        for name in &names {
            if name.kind == NameKind::Scientific
                && name.text != row.scientific_name
                && !synonyms.contains(&name.text)
            {
                synonyms.push(name.text.clone());
            }
        }
        let (origin, description, oil_type) = match profile {
            Some(p) => (p.origin, p.description, p.oil_type),
            None => (None, None, None),
        };

        Ok(Some(Plant {
            id: PlantId(row.id),
            scientific_name: row.scientific_name,
            family: row.family,
            names,
            parts: load_parts(conn, &id.0)?,
            uses: load_uses(conn, &id.0)?,
            display_name,
            synonyms,
            description,
            origin,
            oil_type,
            use_groups: load_use_groups(conn, &id.0)?,
            goals: load_goals(conn, &id.0)?,
            safety: load_safety(conn, &id.0)?,
            image: load_image(conn, &id.0)?,
            credits: load_credits(conn, &id.0)?,
        }))
    }

    fn list_goals(&self) -> Result<Vec<GoalSummary>, RepositoryError> {
        let mut conn = self.conn()?;
        let conn = &mut *conn;

        let goals: Vec<GoalRow> = goal::table
            .order_by((goal::position.asc(), goal::id.asc()))
            .select(GoalRow::as_select())
            .load(conn)
            .map_err(storage)?;
        let subareas: Vec<GoalSubareaRow> = goal_subarea::table
            .order_by((goal_subarea::position.asc(), goal_subarea::id.asc()))
            .select(GoalSubareaRow::as_select())
            .load(conn)
            .map_err(storage)?;
        // Solo las filas visibles cuentan: las pendientes de revisión no existen para la búsqueda.
        let links: Vec<(String, Option<String>, String)> = plant_goal::table
            .filter(plant_goal::pending_review.eq(false))
            .select((
                plant_goal::goal_id,
                plant_goal::subarea_id,
                plant_goal::plant_id,
            ))
            .load(conn)
            .map_err(storage)?;

        // Plantas distintas por objetivo y por subárea: una planta en dos subáreas cuenta una vez en el objetivo.
        let mut by_goal: HashMap<&str, HashSet<&str>> = HashMap::new();
        let mut by_subarea: HashMap<&str, HashSet<&str>> = HashMap::new();
        for (goal_id, subarea_id, plant_id) in &links {
            by_goal.entry(goal_id).or_default().insert(plant_id);
            if let Some(subarea_id) = subarea_id {
                by_subarea.entry(subarea_id).or_default().insert(plant_id);
            }
        }
        let count = |set: Option<&HashSet<&str>>| set.map_or(0, HashSet::len) as u64;

        Ok(goals
            .into_iter()
            .map(|g| {
                let subareas = subareas
                    .iter()
                    .filter(|s| s.goal_id == g.id)
                    .map(|s| SubareaSummary {
                        id: s.id.clone(),
                        name: s.label.clone(),
                        plant_count: count(by_subarea.get(s.id.as_str())),
                    })
                    // Las subáreas sin plantas visibles se omiten.
                    .filter(|s| s.plant_count > 0)
                    .collect();
                GoalSummary {
                    plant_count: count(by_goal.get(g.id.as_str())),
                    id: g.id,
                    name: g.label,
                    subareas,
                }
            })
            .collect())
    }

    /// Precondición: `limit` y `offset` ya están validados por quien llama.
    fn list_goal_plants(
        &self,
        goal_id: &str,
        subarea_id: Option<&str>,
        limit: u32,
        offset: u32,
    ) -> Result<GoalPlantsOutcome, RepositoryError> {
        let mut conn = self.conn()?;
        let conn = &mut *conn;

        let Some(goal_row) = goal::table
            .find(goal_id)
            .select(GoalRow::as_select())
            .first(conn)
            .optional()
            .map_err(storage)?
        else {
            return Ok(GoalPlantsOutcome::UnknownGoal);
        };
        // Una subárea pedida debe ser de este objetivo; si el objetivo no tiene ninguna, cualquier valor es ajeno.
        let subarea = match subarea_id {
            None => None,
            Some(id) => {
                let row: Option<GoalSubareaRow> = goal_subarea::table
                    .find(id)
                    .filter(goal_subarea::goal_id.eq(goal_id))
                    .select(GoalSubareaRow::as_select())
                    .first(conn)
                    .optional()
                    .map_err(storage)?;
                match row {
                    Some(row) => Some(IdName {
                        id: row.id,
                        name: row.label,
                    }),
                    None => return Ok(GoalPlantsOutcome::UnknownSubarea),
                }
            }
        };

        let mut links = plant_goal::table
            .filter(plant_goal::goal_id.eq(goal_id))
            .filter(plant_goal::pending_review.eq(false))
            .into_boxed();
        if let Some(subarea) = &subarea {
            links = links.filter(plant_goal::subarea_id.eq(subarea.id.clone()));
        }
        let link_rows: Vec<(String, String)> = links
            .order_by((plant_goal::position.asc(), plant_goal::id.asc()))
            .select((plant_goal::plant_id, plant_goal::area))
            .load(conn)
            .map_err(storage)?;
        // Áreas por planta, sin repetir y en el orden del registro (una planta puede estar en varias subáreas).
        let mut areas: HashMap<String, Vec<String>> = HashMap::new();
        for (plant_id, area) in link_rows {
            let list = areas.entry(plant_id).or_default();
            if !list.contains(&area) {
                list.push(area);
            }
        }

        let ids: Vec<&str> = areas.keys().map(String::as_str).collect();
        let plants: Vec<PlantRow> = if ids.is_empty() {
            Vec::new()
        } else {
            plant::table
                .filter(plant::id.eq_any(&ids))
                .select(PlantRow::as_select())
                .load(conn)
                .map_err(storage)?
        };
        let mut display_names = display_names_of(conn, &ids)?;

        // Orden total en Rust: `plant_profile.display_name` no tiene columna normalizada. Con unas 135 plantas por objetivo basta ordenar en memoria.
        let mut keyed: Vec<(PlantRow, String, (String, String, String))> = plants
            .into_iter()
            .map(|p| {
                let display_name = display_names
                    .remove(&p.id)
                    .unwrap_or_else(|| p.scientific_name.clone());
                let key = (
                    normalize_name(&display_name),
                    normalize_name(&p.scientific_name),
                    p.id.clone(),
                );
                (p, display_name, key)
            })
            .collect();
        keyed.sort_by(|a, b| a.2.cmp(&b.2));

        let total = keyed.len() as u64;
        let page: Vec<(PlantRow, String)> = keyed
            .into_iter()
            .skip(offset as usize)
            .take(limit as usize)
            .map(|(p, display_name, _)| (p, display_name))
            .collect();

        // Consultas por lote solo para la página: nombres comunes, precauciones e imágenes.
        let page_ids: Vec<&str> = page.iter().map(|(p, _)| p.id.as_str()).collect();
        let mut commons = common_names_of(conn, &page_ids)?;
        let safety = safety_levels_of(conn, &page_ids)?;
        let mut images = images_of(conn, &page_ids)?;

        let items = page
            .into_iter()
            .map(|(p, display_name)| {
                let mut common_names = commons.remove(&p.id).unwrap_or_default();
                sort_common_names(&mut common_names, &display_name);
                let level = safety.get(&p.id);
                GoalPlant {
                    areas: areas.remove(&p.id).unwrap_or_default(),
                    safety_level: level.copied().flatten(),
                    has_safety: level.is_some(),
                    image: images.remove(&p.id),
                    id: PlantId(p.id),
                    scientific_name: p.scientific_name,
                    display_name,
                    common_names,
                    family: p.family,
                }
            })
            .collect();

        Ok(GoalPlantsOutcome::Found(GoalPlants {
            goal: IdName {
                id: goal_row.id,
                name: goal_row.label,
            },
            subarea,
            page: Page { items, total },
        }))
    }
}

/// Nombres para mostrar de un conjunto de plantas; las que no tienen perfil o lo tienen nulo no aparecen.
fn display_names_of(
    conn: &mut SqliteConnection,
    ids: &[&str],
) -> Result<HashMap<String, String>, RepositoryError> {
    if ids.is_empty() {
        return Ok(HashMap::new());
    }
    let rows: Vec<(String, Option<String>)> = plant_profile::table
        .filter(plant_profile::plant_id.eq_any(ids))
        .select((plant_profile::plant_id, plant_profile::display_name))
        .load(conn)
        .map_err(storage)?;
    Ok(rows
        .into_iter()
        .filter_map(|(id, name)| name.map(|name| (id, name)))
        .collect())
}

/// Nombres comunes de un conjunto de plantas, en una sola consulta; sin ordenar entre sí (lo hace `sort_common_names`).
fn common_names_of(
    conn: &mut SqliteConnection,
    ids: &[&str],
) -> Result<HashMap<String, Vec<PlantName>>, RepositoryError> {
    let mut out: HashMap<String, Vec<PlantName>> = HashMap::new();
    if ids.is_empty() {
        return Ok(out);
    }
    let rows: Vec<PlantNameRow> = plant_name::table
        .filter(plant_name::kind.eq("common"))
        .filter(plant_name::plant_id.eq_any(ids))
        .order_by((
            plant_name::text.asc(),
            plant_name::language.asc(),
            plant_name::id.asc(),
        ))
        .select(PlantNameRow::as_select())
        .load(conn)
        .map_err(storage)?;
    for row in &rows {
        out.entry(row.plant_id.clone())
            .or_default()
            .push(to_plant_name(row)?);
    }
    Ok(out)
}

/// Nivel de precaución de las plantas que tienen una fila de seguridad: `Some(None)` es una precaución sin nivel, y las plantas sin fila no aparecen.
fn safety_levels_of(
    conn: &mut SqliteConnection,
    ids: &[&str],
) -> Result<HashMap<String, Option<SafetyLevel>>, RepositoryError> {
    if ids.is_empty() {
        return Ok(HashMap::new());
    }
    let rows: Vec<(String, Option<String>)> = plant_safety::table
        .filter(plant_safety::plant_id.eq_any(ids))
        .select((plant_safety::plant_id, plant_safety::level))
        .load(conn)
        .map_err(storage)?;
    rows.into_iter()
        .map(|(id, level)| {
            let level =
                match level.as_deref() {
                    None => None,
                    Some(text) => Some(SafetyLevel::parse(text).ok_or_else(|| {
                        storage(format!("nivel de seguridad desconocido: {text:?}"))
                    })?),
                };
            Ok((id, level))
        })
        .collect()
}

/// Imágenes de un conjunto de plantas, las mismas que sirve el detalle.
fn images_of(
    conn: &mut SqliteConnection,
    ids: &[&str],
) -> Result<HashMap<String, Image>, RepositoryError> {
    if ids.is_empty() {
        return Ok(HashMap::new());
    }
    let rows: Vec<PlantImageRow> = plant_image::table
        .filter(plant_image::plant_id.eq_any(ids))
        .select(PlantImageRow::as_select())
        .load(conn)
        .map_err(storage)?;
    Ok(rows
        .into_iter()
        .map(|r| {
            (
                r.plant_id,
                Image {
                    url: r.url,
                    page_url: r.page_url,
                    author: r.author,
                    license: r.license,
                    license_url: r.license_url,
                    attribution_required: r.attribution_required,
                },
            )
        })
        .collect())
}

/// Ordena los nombres comunes: primero los que coinciden con el nombre para mostrar (el de idioma `es` antes que los demás), y luego el resto por texto normalizado (sin mayúsculas ni acentos), texto original e idioma, de modo que el orden es total y estable.
fn sort_common_names(names: &mut [PlantName], display_name: &str) {
    names.sort_by_cached_key(|n| {
        let is_display = n.text == display_name;
        (
            !is_display,
            is_display && n.language != "es",
            normalize_name(&n.text),
            n.text.clone(),
            n.language.clone(),
        )
    });
}

/// Nombres de la planta: científicos primero y luego los comunes, con el nombre para mostrar a la cabeza de estos si es uno de ellos; el resto, por texto e idioma.
fn load_names(
    conn: &mut SqliteConnection,
    plant_id: &str,
    display_name: &str,
) -> Result<Vec<PlantName>, RepositoryError> {
    let rows: Vec<PlantNameRow> = plant_name::table
        .filter(plant_name::plant_id.eq(plant_id))
        .select(PlantNameRow::as_select())
        .load(conn)
        .map_err(storage)?;
    let names = rows
        .iter()
        .map(to_plant_name)
        .collect::<Result<Vec<_>, RepositoryError>>()?;
    // `NameKind` no implementa `Ord`, así que se separa por un rango explícito: científico antes que común.
    // Los científicos conservan su orden por texto e idioma; los comunes siguen `sort_common_names`.
    let (mut commons, mut names): (Vec<PlantName>, Vec<PlantName>) =
        names.into_iter().partition(|n| n.kind == NameKind::Common);
    names.sort_by(|a, b| (&a.text, &a.language).cmp(&(&b.text, &b.language)));
    sort_common_names(&mut commons, display_name);
    names.extend(commons);
    Ok(names)
}

/// Partes de la planta, ordenadas por etiqueta.
fn load_parts(conn: &mut SqliteConnection, plant_id: &str) -> Result<Vec<Part>, RepositoryError> {
    let rows: Vec<PlantPartRow> = plant_part::table
        .filter(plant_part::plant_id.eq(plant_id))
        .order_by(plant_part::label.asc())
        .select(PlantPartRow::as_select())
        .load(conn)
        .map_err(storage)?;
    Ok(rows.into_iter().map(|r| Part { label: r.label }).collect())
}

/// Usos de la planta con su referencia, ordenados por actividad, idioma y referencia.
fn load_uses(conn: &mut SqliteConnection, plant_id: &str) -> Result<Vec<Use>, RepositoryError> {
    let rows: Vec<PlantUseRow> = plant_use::table
        .filter(plant_use::plant_id.eq(plant_id))
        .order_by((
            plant_use::activity.asc(),
            plant_use::language.asc(),
            plant_use::reference_id.asc(),
        ))
        .select(PlantUseRow::as_select())
        .load(conn)
        .map_err(storage)?;
    let ref_ids: Vec<&str> = rows.iter().map(|r| r.reference_id.as_str()).collect();
    let references: HashMap<String, String> = reference::table
        .filter(reference::id.eq_any(&ref_ids))
        .select(ReferenceRow::as_select())
        .load(conn)
        .map_err(storage)?
        .into_iter()
        .map(|r| (r.id, r.citation))
        .collect();
    rows.into_iter()
        .map(|r| {
            let citation = references
                .get(&r.reference_id)
                .ok_or_else(|| storage(format!("referencia inexistente: {}", r.reference_id)))?
                .clone();
            Ok(Use {
                activity: r.activity,
                language: r.language,
                reference: Reference {
                    id: r.reference_id,
                    citation,
                },
            })
        })
        .collect()
}

/// Citas (etiquetas de `reference.citation`) de las referencias dadas, por identificador.
fn load_reference_labels(
    conn: &mut SqliteConnection,
    ids: &[&str],
) -> Result<HashMap<String, String>, RepositoryError> {
    if ids.is_empty() {
        return Ok(HashMap::new());
    }
    Ok(reference::table
        .filter(reference::id.eq_any(ids))
        .select(ReferenceRow::as_select())
        .load(conn)
        .map_err(storage)?
        .into_iter()
        .map(|r| (r.id, r.citation))
        .collect())
}

/// Grupos de uso tradicional servidos de la planta, con todas sus citas, por número de registros descendente y actividad.
///
/// La `citation` de cada referencia es el texto completo (`plant_use_group_ref.text`), no la etiqueta de `reference.citation`.
/// Los grupos sin ninguna cita resuelta (`pending_review`) no se sirven.
fn load_use_groups(
    conn: &mut SqliteConnection,
    plant_id: &str,
) -> Result<Vec<UseGroup>, RepositoryError> {
    let groups: Vec<PlantUseGroupRow> = plant_use_group::table
        .filter(plant_use_group::plant_id.eq(plant_id))
        .filter(plant_use_group::pending_review.eq(false))
        .select(PlantUseGroupRow::as_select())
        .load(conn)
        .map_err(storage)?;
    if groups.is_empty() {
        return Ok(Vec::new());
    }
    let group_ids: Vec<i32> = groups.iter().map(|g| g.id).collect();
    let ref_rows: Vec<PlantUseGroupRefRow> = plant_use_group_ref::table
        .filter(plant_use_group_ref::use_group_id.eq_any(&group_ids))
        .order_by((
            plant_use_group_ref::use_group_id.asc(),
            plant_use_group_ref::position.asc(),
            plant_use_group_ref::key.asc(),
        ))
        .select(PlantUseGroupRefRow::as_select())
        .load(conn)
        .map_err(storage)?;
    let mut refs: HashMap<i32, Vec<UseGroupReference>> = HashMap::new();
    for r in ref_rows {
        refs.entry(r.use_group_id)
            .or_default()
            .push(UseGroupReference {
                id: r.reference_id,
                citation: r.text,
            });
    }

    let mut out = groups
        .into_iter()
        .map(|g| {
            let countries: Vec<String> = serde_json::from_str(&g.countries).map_err(|err| {
                storage(format!(
                    "países del grupo de uso {} no son JSON: {err}",
                    g.id
                ))
            })?;
            let count = u32::try_from(g.n)
                .map_err(|_| storage(format!("n inválido en el grupo de uso {}: {}", g.id, g.n)))?;
            Ok((
                g.id,
                UseGroup {
                    activity: g.activity,
                    activity_source: g.activity_source,
                    count,
                    countries,
                    references: refs.remove(&g.id).unwrap_or_default(),
                },
            ))
        })
        .collect::<Result<Vec<_>, RepositoryError>>()?;
    out.sort_by(|(ia, a), (ib, b)| {
        b.count
            .cmp(&a.count)
            .then_with(|| normalize_name(&a.activity).cmp(&normalize_name(&b.activity)))
            .then_with(|| a.activity.cmp(&b.activity))
            .then_with(|| ia.cmp(ib))
    });
    Ok(out.into_iter().map(|(_, g)| g).collect())
}

/// Objetivos servidos de la planta, por nombre (y luego subárea, área e id).
///
/// Los marcados como pendientes de revisión (`plant_goal.pending_review`) no se sirven.
fn load_goals(conn: &mut SqliteConnection, plant_id: &str) -> Result<Vec<Goal>, RepositoryError> {
    let rows: Vec<PlantGoalRow> = plant_goal::table
        .filter(plant_goal::plant_id.eq(plant_id))
        .filter(plant_goal::pending_review.eq(false))
        .select(PlantGoalRow::as_select())
        .load(conn)
        .map_err(storage)?;
    if rows.is_empty() {
        return Ok(Vec::new());
    }
    let goal_ids: Vec<&str> = rows.iter().map(|r| r.goal_id.as_str()).collect();
    let goal_labels: HashMap<String, String> = goal::table
        .filter(goal::id.eq_any(&goal_ids))
        .select(GoalRow::as_select())
        .load(conn)
        .map_err(storage)?
        .into_iter()
        .map(|g| (g.id, g.label))
        .collect();
    let subarea_ids: Vec<&str> = rows
        .iter()
        .filter_map(|r| r.subarea_id.as_deref())
        .collect();
    let subarea_labels: HashMap<String, String> = if subarea_ids.is_empty() {
        HashMap::new()
    } else {
        goal_subarea::table
            .filter(goal_subarea::id.eq_any(&subarea_ids))
            .select(GoalSubareaRow::as_select())
            .load(conn)
            .map_err(storage)?
            .into_iter()
            .map(|s| (s.id, s.label))
            .collect()
    };
    let plant_goal_ids: Vec<i32> = rows.iter().map(|r| r.id).collect();
    let ref_rows: Vec<PlantGoalRefRow> = plant_goal_ref::table
        .filter(plant_goal_ref::plant_goal_id.eq_any(&plant_goal_ids))
        .order_by((
            plant_goal_ref::plant_goal_id.asc(),
            plant_goal_ref::reference_id.asc(),
        ))
        .select(PlantGoalRefRow::as_select())
        .load(conn)
        .map_err(storage)?;
    let ref_id_list: Vec<&str> = ref_rows.iter().map(|r| r.reference_id.as_str()).collect();
    let labels = load_reference_labels(conn, &ref_id_list)?;
    let mut refs: HashMap<i32, Vec<Reference>> = HashMap::new();
    for r in ref_rows {
        let citation = labels
            .get(&r.reference_id)
            .ok_or_else(|| storage(format!("referencia inexistente: {}", r.reference_id)))?
            .clone();
        refs.entry(r.plant_goal_id).or_default().push(Reference {
            id: r.reference_id,
            citation,
        });
    }

    let mut out = rows
        .into_iter()
        .map(|r| {
            let name = goal_labels
                .get(&r.goal_id)
                .ok_or_else(|| storage(format!("objetivo inexistente: {}", r.goal_id)))?
                .clone();
            let subarea = match &r.subarea_id {
                None => None,
                Some(sid) => Some(
                    subarea_labels
                        .get(sid)
                        .ok_or_else(|| storage(format!("subárea inexistente: {sid}")))?
                        .clone(),
                ),
            };
            Ok((
                r.id,
                Goal {
                    id: r.goal_id,
                    name,
                    subarea,
                    area: r.area,
                    evidence: r.evidence,
                    references: refs.remove(&r.id).unwrap_or_default(),
                },
            ))
        })
        .collect::<Result<Vec<_>, RepositoryError>>()?;
    out.sort_by(|(ia, a), (ib, b)| {
        (&a.name, &a.subarea, &a.area, ia).cmp(&(&b.name, &b.subarea, &b.area, ib))
    });
    Ok(out.into_iter().map(|(_, g)| g).collect())
}

/// Precauciones de la planta, o `None` si no hay ninguna fila (sin dato, no "segura").
fn load_safety(
    conn: &mut SqliteConnection,
    plant_id: &str,
) -> Result<Option<Safety>, RepositoryError> {
    let Some(row) = plant_safety::table
        .find(plant_id)
        .select(PlantSafetyRow::as_select())
        .first(conn)
        .optional()
        .map_err(storage)?
    else {
        return Ok(None);
    };
    let level = match row.level.as_deref() {
        None => None,
        Some(text) => Some(
            SafetyLevel::parse(text)
                .ok_or_else(|| storage(format!("nivel de seguridad desconocido: {text:?}")))?,
        ),
    };
    let ref_rows: Vec<PlantSafetyRefRow> = plant_safety_ref::table
        .filter(plant_safety_ref::plant_id.eq(plant_id))
        .order_by(plant_safety_ref::reference_id.asc())
        .select(PlantSafetyRefRow::as_select())
        .load(conn)
        .map_err(storage)?;
    let ref_id_list: Vec<&str> = ref_rows.iter().map(|r| r.reference_id.as_str()).collect();
    let labels = load_reference_labels(conn, &ref_id_list)?;
    let references = ref_rows
        .into_iter()
        .map(|r| {
            let citation = labels
                .get(&r.reference_id)
                .ok_or_else(|| storage(format!("referencia inexistente: {}", r.reference_id)))?
                .clone();
            Ok(Reference {
                id: r.reference_id,
                citation,
            })
        })
        .collect::<Result<Vec<_>, RepositoryError>>()?;
    Ok(Some(Safety {
        level,
        text: row.text,
        references,
    }))
}

/// Datos de la imagen de la planta. Solo lee el registro: la API nunca descarga la imagen.
fn load_image(
    conn: &mut SqliteConnection,
    plant_id: &str,
) -> Result<Option<Image>, RepositoryError> {
    Ok(plant_image::table
        .find(plant_id)
        .select(PlantImageRow::as_select())
        .first(conn)
        .optional()
        .map_err(storage)?
        .map(|r| Image {
            url: r.url,
            page_url: r.page_url,
            author: r.author,
            license: r.license,
            license_url: r.license_url,
            attribution_required: r.attribution_required,
        }))
}

/// Créditos de la planta: los datasets que respaldan sus datos, sin repeticiones y ordenados por nombre.
///
/// Es la unión de las fuentes de sus nombres, partes, usos y familia, y de los datasets de las referencias que respaldan el perfil, los objetivos servidos, las precauciones y los grupos de uso servidos.
/// No indica qué dato viene de cada uno. Nombre, licencia, URL de licencia y atribución salen de la fuente (`source`), no de la referencia.
/// Si una referencia de la descripción trae su propia URL (el artículo resumido), esa es la `url` del crédito de su dataset.
fn load_credits(
    conn: &mut SqliteConnection,
    plant_id: &str,
) -> Result<Vec<Credit>, RepositoryError> {
    let mut source_ids: BTreeSet<String> = BTreeSet::new();

    // Tablas de atribución de nombres, partes y usos.
    source_ids.extend(
        plant_name_source::table
            .filter(
                plant_name_source::plant_name_id.eq_any(
                    plant_name::table
                        .filter(plant_name::plant_id.eq(plant_id))
                        .select(plant_name::id),
                ),
            )
            .select(plant_name_source::source_id)
            .distinct()
            .load::<String>(conn)
            .map_err(storage)?,
    );
    source_ids.extend(
        plant_part_source::table
            .filter(
                plant_part_source::plant_part_id.eq_any(
                    plant_part::table
                        .filter(plant_part::plant_id.eq(plant_id))
                        .select(plant_part::id),
                ),
            )
            .select(plant_part_source::source_id)
            .distinct()
            .load::<String>(conn)
            .map_err(storage)?,
    );
    source_ids.extend(
        plant_use_source::table
            .filter(
                plant_use_source::plant_use_id.eq_any(
                    plant_use::table
                        .filter(plant_use::plant_id.eq(plant_id))
                        .select(plant_use::id),
                ),
            )
            .select(plant_use_source::source_id)
            .distinct()
            .load::<String>(conn)
            .map_err(storage)?,
    );
    let family_source: Option<Option<String>> = plant::table
        .find(plant_id)
        .select(plant::family_source_id)
        .first(conn)
        .optional()
        .map_err(storage)?;
    source_ids.extend(family_source.flatten());

    // Datasets de las referencias de lo que se sirve: perfil, objetivos, precauciones y grupos de uso.
    // Los objetivos y grupos pendientes de revisión no se sirven, así que tampoco acreditan.
    let datasets = [
        reference::table
            .filter(
                reference::id.eq_any(
                    plant_profile_ref::table
                        .filter(plant_profile_ref::plant_id.eq(plant_id))
                        .select(plant_profile_ref::reference_id),
                ),
            )
            .select(reference::dataset)
            .distinct()
            .load::<Option<String>>(conn)
            .map_err(storage)?,
        reference::table
            .filter(
                reference::id.eq_any(
                    plant_goal_ref::table
                        .filter(
                            plant_goal_ref::plant_goal_id.eq_any(
                                plant_goal::table
                                    .filter(plant_goal::plant_id.eq(plant_id))
                                    .filter(plant_goal::pending_review.eq(false))
                                    .select(plant_goal::id),
                            ),
                        )
                        .select(plant_goal_ref::reference_id),
                ),
            )
            .select(reference::dataset)
            .distinct()
            .load::<Option<String>>(conn)
            .map_err(storage)?,
        reference::table
            .filter(
                reference::id.eq_any(
                    plant_safety_ref::table
                        .filter(plant_safety_ref::plant_id.eq(plant_id))
                        .select(plant_safety_ref::reference_id),
                ),
            )
            .select(reference::dataset)
            .distinct()
            .load::<Option<String>>(conn)
            .map_err(storage)?,
        reference::table
            .filter(
                reference::id.nullable().eq_any(
                    plant_use_group_ref::table
                        .filter(
                            plant_use_group_ref::use_group_id.eq_any(
                                plant_use_group::table
                                    .filter(plant_use_group::plant_id.eq(plant_id))
                                    .filter(plant_use_group::pending_review.eq(false))
                                    .select(plant_use_group::id),
                            ),
                        )
                        .select(plant_use_group_ref::reference_id),
                ),
            )
            .select(reference::dataset)
            .distinct()
            .load::<Option<String>>(conn)
            .map_err(storage)?,
    ];
    source_ids.extend(datasets.into_iter().flatten().flatten());

    if source_ids.is_empty() {
        return Ok(Vec::new());
    }

    // Si la descripción resume un artículo, el crédito de su dataset enlaza a ese artículo y no al sitio.
    let description_refs: Vec<(Option<String>, Option<String>)> = reference::table
        .filter(
            reference::id.eq_any(
                plant_profile_ref::table
                    .filter(plant_profile_ref::plant_id.eq(plant_id))
                    .filter(plant_profile_ref::field.eq("description"))
                    .select(plant_profile_ref::reference_id),
            ),
        )
        .order_by(reference::id.asc())
        .select((reference::dataset, reference::url))
        .load(conn)
        .map_err(storage)?;
    let mut article_urls: HashMap<String, String> = HashMap::new();
    for (dataset, url) in description_refs {
        if let (Some(dataset), Some(url)) = (dataset, url) {
            article_urls.entry(dataset).or_insert(url);
        }
    }

    let ids: Vec<&str> = source_ids.iter().map(String::as_str).collect();
    let sources: Vec<SourceRow> = source::table
        .filter(source::id.eq_any(&ids))
        .select(SourceRow::as_select())
        .load(conn)
        .map_err(storage)?;
    let mut credits: Vec<(String, Credit)> = sources
        .into_iter()
        .map(|s| {
            let url = article_urls.remove(&s.id).unwrap_or(s.url);
            (
                s.id,
                Credit {
                    name: s.name,
                    license: s.license,
                    license_url: s.license_url,
                    attribution: s.citation,
                    url: Some(url),
                },
            )
        })
        .collect();
    credits.sort_by(|(ia, a), (ib, b)| (&a.name, ia).cmp(&(&b.name, ib)));
    Ok(credits.into_iter().map(|(_, c)| c).collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::Fixture;
    use catalog_core::normalize::NORMALIZATION_CASES;
    use catalog_core::rows::MetadataRow;

    fn query(q: Option<&str>, limit: u32, offset: u32) -> ListQuery {
        ListQuery {
            q: q.map(str::to_string),
            limit,
            offset,
        }
    }

    fn ids(page: &Page<PlantSummary>) -> Vec<&str> {
        page.items.iter().map(|p| p.id.0.as_str()).collect()
    }

    fn pid(id: &str) -> PlantId {
        PlantId(id.to_string())
    }

    // ---- 6.1 apertura ----

    #[test]
    fn opens_valid_database() {
        let fixture = Fixture::standard();
        assert!(SqliteCatalogRepository::open(&fixture.path).is_ok());
    }

    #[test]
    fn incompatible_version_is_rejected() {
        let fixture = Fixture::with_version(Some("99"));
        let err = SqliteCatalogRepository::open(&fixture.path).err().unwrap();
        assert_eq!(
            err,
            OpenError::Repository(RepositoryError::IncompatibleSchema {
                found: 99,
                supported: SCHEMA_VERSION
            })
        );
    }

    #[test]
    fn missing_or_non_numeric_version_is_a_storage_error() {
        for version in [None, Some("abc")] {
            let fixture = Fixture::with_version(version);
            let err = SqliteCatalogRepository::open(&fixture.path).err().unwrap();
            assert!(
                matches!(err, OpenError::Repository(RepositoryError::Storage(_))),
                "{err:?}"
            );
        }
    }

    #[test]
    fn unreadable_database_fails_fast_naming_the_path() {
        let dir = tempfile::tempdir().unwrap();
        let garbage = dir.path().join("basura.db");
        std::fs::write(&garbage, b"x\n").unwrap();
        for path in [garbage, dir.path().to_path_buf()] {
            let started = std::time::Instant::now();
            let err = SqliteCatalogRepository::open(&path).err().unwrap();
            assert!(started.elapsed() < Duration::from_secs(2), "{err}");
            assert!(
                matches!(err, OpenError::Repository(RepositoryError::Storage(_))),
                "{err:?}"
            );
            assert!(err.to_string().contains(path.to_str().unwrap()), "{err}");
        }
    }

    #[test]
    fn missing_database_names_path_and_build_command() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("nope.db");
        let err = SqliteCatalogRepository::open(&path).err().unwrap();
        let text = err.to_string();
        assert!(text.contains(path.to_str().unwrap()), "{text}");
        assert!(text.contains("build"), "{text}");
        // Abrir no debe crear el archivo.
        assert!(!path.exists());
    }

    #[test]
    fn pooled_connections_cannot_write() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let mut conn = repo.conn().unwrap();
        let err = diesel::insert_into(metadata::table)
            .values(MetadataRow {
                key: "x".to_string(),
                value: "y".to_string(),
            })
            .execute(&mut *conn)
            .unwrap_err();
        assert!(err.to_string().contains("readonly"), "{err}");
    }

    // ---- 6.2 listado ----

    fn expected_order() -> Vec<String> {
        let mut v: Vec<String> = [
            "abutilon-theophrasti",
            "conium-maculatum",
            "eucalyptus-globulus",
        ]
        .map(String::from)
        .to_vec();
        v.extend((1..=25).map(|n| format!("fillerus-{n:02}")));
        v.extend(
            [
                "lavandula-angustifolia",
                "lavandula-latifolia",
                "matricaria-chamomilla",
                "mentha-x-piperita",
                "twin-a",
                "twin-b",
                "zea-mays",
            ]
            .map(String::from),
        );
        v
    }

    #[test]
    fn lists_in_total_order_with_id_tiebreak() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo.list_plants(&query(None, 100, 0)).unwrap();
        assert_eq!(page.total, 35);
        assert_eq!(ids(&page), expected_order());
    }

    #[test]
    fn pages_are_consecutive_and_total_is_independent() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let mut seen = Vec::new();
        for offset in (0..35).step_by(7) {
            let page = repo.list_plants(&query(None, 7, offset)).unwrap();
            assert_eq!(page.total, 35);
            seen.extend(page.items.into_iter().map(|p| p.id.0));
        }
        assert_eq!(seen, expected_order());
    }

    #[test]
    fn default_limit_is_twenty_and_offset_past_total_is_empty() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo.list_plants(&ListQuery::default()).unwrap();
        assert_eq!((page.items.len(), page.total), (20, 35));
        let past = repo.list_plants(&query(None, 20, 500)).unwrap();
        assert_eq!((past.items.len(), past.total), (0, 35));
    }

    #[test]
    fn items_carry_common_names_and_family() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo
            .list_plants(&query(Some("lavandula angustifolia"), 20, 0))
            .unwrap();
        let name = |text: &str, language: &str| PlantName {
            text: text.to_string(),
            kind: NameKind::Common,
            language: language.to_string(),
        };
        assert_eq!(
            page.items,
            vec![PlantSummary {
                id: pid("lavandula-angustifolia"),
                scientific_name: "Lavandula angustifolia".to_string(),
                // «Lavanda» es el nombre para mostrar y va primero aunque «Espliego» sea anterior por texto.
                common_names: vec![
                    name("Lavanda", "es"),
                    name("Espliego", "es"),
                    name("Lavender", "en")
                ],
                family: Some("Lamiaceae".to_string()),
                display_name: "Lavanda".to_string(),
            }]
        );
        // Sin familia es `None`, y el nombre científico no cuenta como nombre común.
        let mentha = repo.list_plants(&query(Some("mentha"), 20, 0)).unwrap();
        assert_eq!(mentha.items[0].family, None);
        assert_eq!(mentha.items[0].common_names.len(), 2);
    }

    #[test]
    fn searches_scientific_and_common_names() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let sci = repo.list_plants(&query(Some("lavandula"), 20, 0)).unwrap();
        assert_eq!(ids(&sci), ["lavandula-angustifolia", "lavandula-latifolia"]);
        assert_eq!(sci.total, 2);
        let common = repo.list_plants(&query(Some("espliego"), 20, 0)).unwrap();
        assert_eq!(ids(&common), ["lavandula-angustifolia"]);
        // Subcadena en medio del nombre.
        let inner = repo.list_plants(&query(Some("pike lav"), 20, 0)).unwrap();
        assert_eq!(ids(&inner), ["lavandula-latifolia"]);
        let none = repo.list_plants(&query(Some("zzz"), 20, 0)).unwrap();
        assert_eq!((none.items.len(), none.total), (0, 0));
    }

    #[test]
    fn search_total_ignores_the_page() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo.list_plants(&query(Some("filler"), 5, 10)).unwrap();
        assert_eq!((page.items.len(), page.total), (5, 25));
    }

    #[test]
    fn search_ignores_case_accents_and_spaces() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for q in ["ÑANDÚ", "  nandu   cafe ", "Café"] {
            let page = repo.list_plants(&query(Some(q), 20, 0)).unwrap();
            assert_eq!(ids(&page), ["mentha-x-piperita"], "q = {q:?}");
        }
    }

    #[test]
    fn search_treats_hybrid_sign_and_plain_x_alike() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for q in ["mentha x piperita", "Mentha × piperita", "mentha×piperita"] {
            let page = repo.list_plants(&query(Some(q), 20, 0)).unwrap();
            assert_eq!(ids(&page), ["mentha-x-piperita"], "q = {q:?}");
        }
    }

    #[test]
    fn shared_normalization_cases_match_their_normalized_form() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for (input, expected) in NORMALIZATION_CASES {
            let raw = repo.list_plants(&query(Some(input), 100, 0)).unwrap();
            let normalized = repo.list_plants(&query(Some(expected), 100, 0)).unwrap();
            assert_eq!(raw, normalized, "caso {input:?}");
        }
    }

    #[test]
    fn empty_or_blank_query_means_no_filter() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let all = repo.list_plants(&query(None, 100, 0)).unwrap();
        for q in ["", "   ", "\t\n"] {
            assert_eq!(repo.list_plants(&query(Some(q), 100, 0)).unwrap(), all);
        }
    }

    #[test]
    fn pattern_characters_are_literal() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for q in ["%", "_", "100%", "corn_m"] {
            let page = repo.list_plants(&query(Some(q), 100, 0)).unwrap();
            assert_eq!(ids(&page), ["zea-mays"], "q = {q:?}");
        }
        // `%` y `_` no actúan como comodines dentro de un texto.
        for q in ["lav%ula", "lav_ndula", "c_rn"] {
            assert_eq!(repo.list_plants(&query(Some(q), 100, 0)).unwrap().total, 0);
        }
        // La barra invertida (el carácter de escape) también es literal.
        assert_eq!(
            repo.list_plants(&query(Some("\\"), 100, 0)).unwrap().total,
            0
        );
    }

    // ---- 6.3 detalle ----

    #[test]
    fn detail_includes_names_parts_and_uses() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(plant.scientific_name, "Lavandula angustifolia");
        assert_eq!(plant.family, Some("Lamiaceae".to_string()));
        let names: Vec<(&str, NameKind, &str)> = plant
            .names
            .iter()
            .map(|n| (n.text.as_str(), n.kind, n.language.as_str()))
            .collect();
        assert_eq!(
            names,
            [
                ("Lavandula angustifolia", NameKind::Scientific, "la"),
                ("Lavandula vera", NameKind::Scientific, "la"),
                ("Lavanda", NameKind::Common, "es"),
                ("Espliego", NameKind::Common, "es"),
                ("Lavender", NameKind::Common, "en"),
            ]
        );
        let parts: Vec<&str> = plant.parts.iter().map(|p| p.label.as_str()).collect();
        assert_eq!(parts, ["Flower", "Leaf"]);

        assert_eq!(
            plant.uses,
            vec![
                Use {
                    activity: "Antiseptic".to_string(),
                    language: "en".to_string(),
                    reference: Reference {
                        id: "ref-1".to_string(),
                        citation: "Smith 1990".to_string()
                    }
                },
                Use {
                    activity: "Sedative".to_string(),
                    language: "en".to_string(),
                    reference: Reference {
                        id: "ref-2".to_string(),
                        citation: "Jones 2001".to_string()
                    }
                },
            ]
        );
    }

    #[test]
    fn detail_without_uses_or_family() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let latifolia = repo
            .get_plant(&pid("lavandula-latifolia"))
            .unwrap()
            .unwrap();
        assert!(latifolia.uses.is_empty() && latifolia.parts.is_empty());
        let mentha = repo.get_plant(&pid("mentha-x-piperita")).unwrap().unwrap();
        assert_eq!(mentha.family, None);
    }

    // ---- 2.1 nombre para mostrar ----

    fn summary_of(repo: &SqliteCatalogRepository, q: &str) -> PlantSummary {
        let mut page = repo.list_plants(&query(Some(q), 20, 0)).unwrap();
        assert_eq!(page.items.len(), 1, "q = {q:?}");
        page.items.remove(0)
    }

    fn texts(names: &[PlantName]) -> Vec<&str> {
        names.iter().map(|n| n.text.as_str()).collect()
    }

    #[test]
    fn list_item_display_name_is_first_of_the_common_names() {
        // Escenarios «Nombre para mostrar en el listado» y «Nombre para mostrar primero».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let lavender = summary_of(&repo, "lavandula angustifolia");
        assert_eq!(lavender.display_name, "Lavanda");
        assert_eq!(
            texts(&lavender.common_names),
            ["Lavanda", "Espliego", "Lavender"]
        );
        // Con otro nombre para mostrar que sí es común, ese pasa a ser el primero.
        assert_eq!(summary_of(&repo, "conium").display_name, "Cicuta");
    }

    #[test]
    fn detail_display_name_goes_first_among_common_names_after_the_scientific_ones() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(plant.display_name, "Lavanda");
        let kinds: Vec<NameKind> = plant.names.iter().map(|n| n.kind).collect();
        assert_eq!(
            kinds,
            [
                NameKind::Scientific,
                NameKind::Scientific,
                NameKind::Common,
                NameKind::Common,
                NameKind::Common
            ]
        );
        assert_eq!(
            texts(&plant.names[2..]),
            ["Lavanda", "Espliego", "Lavender"]
        );
    }

    fn language_of<'a>(names: &'a [PlantName], text: &str) -> Vec<&'a str> {
        names
            .iter()
            .filter(|n| n.text == text)
            .map(|n| n.language.as_str())
            .collect()
    }

    #[test]
    fn common_names_sort_ignoring_case_and_accents_after_the_display_name() {
        // Escenario «Nombre para mostrar primero» con «Árnica»: el orden binario daría «Espliego» antes.
        let fixture = Fixture::standard();
        fixture.insert_name("lavandula-angustifolia", "Árnica", "common", "es");
        let repo = fixture.repo();
        let lavender = summary_of(&repo, "lavandula angustifolia");
        assert_eq!(
            texts(&lavender.common_names),
            ["Lavanda", "Árnica", "Espliego", "Lavender"]
        );
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(
            texts(&plant.names[2..]),
            ["Lavanda", "Árnica", "Espliego", "Lavender"]
        );
    }

    #[test]
    fn common_names_mix_upper_and_lower_case_and_start_with_accented_letters() {
        let fixture = Fixture::standard();
        for text in ["cálamo acuático", "Ácoro", "Zarza", "bálsamo", "Cálamo"] {
            fixture.insert_name("lavandula-angustifolia", text, "common", "es");
        }
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(
            texts(&plant.names[2..]),
            [
                "Lavanda",
                "Ácoro",
                "bálsamo",
                "Cálamo",
                "cálamo acuático",
                "Espliego",
                "Lavender",
                "Zarza"
            ]
        );
    }

    #[test]
    fn spanish_name_goes_first_when_english_and_spanish_equal_the_display_name() {
        // Caso «Sisal»: el mismo texto en `en` y en `es`; el `es` va primero, también si el `en` se insertó antes.
        let fixture = Fixture::standard();
        fixture.insert_name("lavandula-angustifolia", "Lavanda", "common", "en");
        let repo = fixture.repo();
        let summary = summary_of(&repo, "lavandula angustifolia");
        assert_eq!(summary.display_name, "Lavanda");
        assert_eq!(language_of(&summary.common_names, "Lavanda"), ["es", "en"]);
        assert_eq!(summary.common_names[0].language, "es");
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(plant.names[2].language, "es");
        assert_eq!(language_of(&plant.names, "Lavanda"), ["es", "en"]);
    }

    #[test]
    fn use_groups_with_equal_count_sort_activities_ignoring_accents() {
        let fixture = Fixture::standard();
        fixture.insert_use_group("lavandula-angustifolia", "Zumbido", 91, 5);
        fixture.insert_use_group("lavandula-angustifolia", "Úlcera", 92, 5);
        fixture.insert_use_group("lavandula-angustifolia", "alivio", 93, 5);
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        let activities: Vec<&str> = plant
            .use_groups
            .iter()
            .map(|g| g.activity.as_str())
            .collect();
        assert_eq!(
            activities,
            ["Sedante", "alivio", "Úlcera", "Zumbido", "Antiséptico"]
        );
    }

    #[test]
    fn plant_without_common_names_displays_its_scientific_name() {
        // Escenario «Sin nombre común» (`twin-a` no tiene perfil ni nombres comunes).
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo.list_plants(&query(Some("twin plant"), 20, 0)).unwrap();
        assert_eq!(ids(&page), ["twin-a", "twin-b"]);
        for item in &page.items {
            assert_eq!(item.display_name, "Twin plant");
            assert!(item.common_names.is_empty());
        }
        let plant = repo.get_plant(&pid("twin-a")).unwrap().unwrap();
        assert_eq!(plant.display_name, "Twin plant");
        assert!(plant.names.iter().all(|n| n.kind == NameKind::Scientific));
    }

    #[test]
    fn plant_without_profile_falls_back_to_the_scientific_name() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        assert_eq!(
            summary_of(&repo, "lavandula latifolia").display_name,
            "Lavandula latifolia"
        );
        let plant = repo
            .get_plant(&pid("lavandula-latifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(plant.display_name, "Lavandula latifolia");
        // Sin perfil, el único nombre común no se destaca ni se convierte en el nombre para mostrar.
        assert_eq!(
            texts(&plant.names),
            ["Lavandula latifolia", "Spike lavender"]
        );
    }

    #[test]
    fn only_other_language_names_keep_the_scientific_display_name() {
        // Escenarios «Solo nombres en otros idiomas» y «Varios nombres en otros idiomas».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let item = summary_of(&repo, "abutilon");
        assert_eq!(item.display_name, "Abutilon theophrasti");
        // Ordenados por texto e idioma, sin ninguno destacado: «Butterprint» antes que «Velvetleaf».
        assert_eq!(texts(&item.common_names), ["Butterprint", "Velvetleaf"]);
        let plant = repo
            .get_plant(&pid("abutilon-theophrasti"))
            .unwrap()
            .unwrap();
        assert_eq!(plant.display_name, "Abutilon theophrasti");
        assert_eq!(
            texts(&plant.names),
            ["Abutilon theophrasti", "Butterprint", "Velvetleaf"]
        );
    }

    #[test]
    fn display_name_is_loaded_for_the_whole_page_without_changing_the_order() {
        // El orden del listado sigue siendo por nombre científico e id, y cada elemento lleva su nombre.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo.list_plants(&query(None, 100, 0)).unwrap();
        assert_eq!(ids(&page), expected_order());
        let display: HashMap<&str, &str> = page
            .items
            .iter()
            .map(|p| (p.id.0.as_str(), p.display_name.as_str()))
            .collect();
        assert_eq!(display["lavandula-angustifolia"], "Lavanda");
        assert_eq!(display["eucalyptus-globulus"], "Eucalipto");
        assert_eq!(display["zea-mays"], "Zea mays");
        assert_eq!(display["fillerus-01"], "Fillerus 01");
    }

    // ---- 3.1 contenido consolidado ----

    #[test]
    fn complete_plant_has_profile_synonyms_and_oil() {
        // Escenario «Planta con todos los campos».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(plant.synonyms, ["Lavandula vera"]);
        assert_eq!(
            plant.description.as_deref(),
            Some("Arbusto aromático de flores violetas.")
        );
        assert_eq!(plant.origin.as_deref(), Some("Sureste de Europa."));
        assert_eq!(plant.oil_type.as_deref(), Some("Esencial"));
        assert_eq!(plant.use_groups.len(), 2);
        assert_eq!(plant.goals.len(), 2);
        assert!(plant.safety.is_some() && plant.image.is_some());
    }

    #[test]
    fn plants_without_consolidated_data_have_null_or_empty_fields() {
        // Escenario «Planta con campos vacíos»: una planta sin perfil y otra con perfil de campos nulos.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for id in ["lavandula-latifolia", "abutilon-theophrasti"] {
            let plant = repo.get_plant(&pid(id)).unwrap().unwrap();
            assert!(plant.synonyms.is_empty(), "{id}");
            assert_eq!(
                (&plant.description, &plant.origin, &plant.oil_type),
                (&None, &None, &None),
                "{id}"
            );
            assert!(
                plant.use_groups.is_empty() && plant.goals.is_empty(),
                "{id}"
            );
            assert_eq!((&plant.safety, &plant.image), (&None, &None), "{id}");
        }
    }

    // ---- 3.2 grupos de uso y objetivos ----

    #[test]
    fn use_groups_are_ordered_by_count_with_countries() {
        // Escenario «Grupos de uso»: 12 registros de 3 países y otro de 2; por texto «Antiséptico» iría antes.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        let groups: Vec<(&str, u32)> = plant
            .use_groups
            .iter()
            .map(|g| (g.activity.as_str(), g.count))
            .collect();
        assert_eq!(groups, [("Sedante", 12), ("Antiséptico", 2)]);
        assert_eq!(plant.use_groups[0].activity_source, "Sedative");
        assert_eq!(
            plant.use_groups[0].countries,
            ["Turquía", "Francia", "Otros lugares"]
        );
    }

    #[test]
    fn use_group_citation_is_the_full_text_and_not_the_label() {
        // Escenario «Cita completa en los grupos de uso» y compatibilidad de `uses`.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        let antiseptic = &plant.use_groups[1];
        assert_eq!(
            antiseptic.references,
            [UseGroupReference {
                id: Some("ref-1".to_string()),
                citation: "Smith, J. 1990. Registros de plantas. Publicado por el autor, Lisboa."
                    .to_string(),
            }]
        );
        // `uses[].reference.citation` sigue siendo la etiqueta de la referencia.
        let use_citation = plant
            .uses
            .iter()
            .find(|u| u.reference.id == "ref-1")
            .map(|u| u.reference.citation.as_str());
        assert_eq!(use_citation, Some("Smith 1990"));
    }

    #[test]
    fn use_group_with_an_unresolved_citation_keeps_both_references() {
        // Escenario «Grupo de uso con una cita sin resolver».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        let sedative = &plant.use_groups[0];
        assert_eq!(sedative.references.len(), 2);
        assert!(sedative.references[0].is_resolved());
        assert_eq!(
            sedative.references[0].citation,
            "Jones, A. 2001. Plantas medicinales. Editorial Ejemplo, Madrid."
        );
        assert_eq!(
            sedative.references[1],
            UseGroupReference {
                id: None,
                citation: "Woi.6 (sin resolver)".to_string()
            }
        );
        assert!(!sedative.references[1].is_resolved());
    }

    #[test]
    fn pending_use_groups_are_not_served_and_uses_has_one_row_per_resolved_reference() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert!(
            plant
                .use_groups
                .iter()
                .all(|g| g.activity != "Actividad pendiente")
        );
        let resolved: usize = plant
            .use_groups
            .iter()
            .flat_map(|g| &g.references)
            .filter(|r| r.is_resolved())
            .count();
        assert_eq!(plant.uses.len(), resolved);
    }

    #[test]
    fn goals_carry_names_subarea_area_evidence_and_reference_labels() {
        // Escenarios «Objetivo de la EMA» y «Subárea de otros objetivos»; el objetivo pendiente no se sirve.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(
            plant.goals,
            vec![
                Goal {
                    id: "cuidado-de-la-piel".to_string(),
                    name: "Cuidado de la piel".to_string(),
                    subarea: None,
                    area: "Piel irritada".to_string(),
                    evidence: "La agencia tiene una monografía en esta área.".to_string(),
                    references: vec![Reference {
                        id: "ref-ema-skin".to_string(),
                        citation: "Monografía sobre la piel".to_string()
                    }],
                },
                Goal {
                    id: "otros-objetivos".to_string(),
                    name: "Otros objetivos".to_string(),
                    subarea: Some("Digestión".to_string()),
                    area: "Digestión lenta".to_string(),
                    evidence: "La agencia tiene una entrada de lista en esta área.".to_string(),
                    references: vec![
                        Reference {
                            id: "ref-1".to_string(),
                            citation: "Smith 1990".to_string()
                        },
                        Reference {
                            id: "ref-ema-skin".to_string(),
                            citation: "Monografía sobre la piel".to_string()
                        },
                    ],
                },
            ]
        );
    }

    // ---- 3.3 seguridad e imagen ----

    #[test]
    fn safety_has_level_text_and_references() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let safety = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap()
            .safety
            .unwrap();
        assert_eq!(safety.level, Some(SafetyLevel::Medium));
        assert_eq!(safety.text, "Evitar durante el embarazo.");
        let ids: Vec<&str> = safety.references.iter().map(|r| r.id.as_str()).collect();
        assert_eq!(ids, ["ref-1", "ref-ema-safety"]);
        let toxic = repo.get_plant(&pid("conium-maculatum")).unwrap().unwrap();
        assert_eq!(toxic.safety.unwrap().level, Some(SafetyLevel::High));
    }

    #[test]
    fn safety_without_data_is_none() {
        // Escenario «Seguridad sin datos».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo.get_plant(&pid("zea-mays")).unwrap().unwrap();
        assert_eq!(plant.safety, None);
    }

    #[test]
    fn safety_without_level_keeps_text_and_references() {
        // Escenario «Seguridad sin nivel».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let safety = repo
            .get_plant(&pid("eucalyptus-globulus"))
            .unwrap()
            .unwrap()
            .safety
            .unwrap();
        assert_eq!(safety.level, None);
        assert_eq!(safety.text, "Contraindicado en niños pequeños.");
        assert_eq!(safety.references.len(), 1);
    }

    #[test]
    fn image_carries_its_license_and_missing_optionals_are_none() {
        // Escenarios «Imagen con licencia» y «Sin imagen».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let image = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap()
            .image
            .unwrap();
        assert_eq!(
            image.url,
            "https://imagenes.invalid/lavandula-angustifolia.jpg"
        );
        assert_eq!(
            image.page_url,
            "https://commons.wikimedia.org/wiki/File:lavandula-angustifolia.jpg"
        );
        assert_eq!(image.author.as_deref(), Some("Autora Ejemplo"));
        assert_eq!(image.license, "CC BY-SA 4.0");
        assert_eq!(
            image.license_url.as_deref(),
            Some("https://creativecommons.org/licenses/by-sa/4.0/")
        );
        assert!(image.attribution_required);
        let bare = repo
            .get_plant(&pid("conium-maculatum"))
            .unwrap()
            .unwrap()
            .image
            .unwrap();
        assert_eq!((bare.author, bare.license_url), (None, None));
        assert!(!bare.attribution_required);
        let none = repo
            .get_plant(&pid("lavandula-latifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(none.image, None);
    }

    #[test]
    fn unknown_plant_is_none() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        assert_eq!(repo.get_plant(&pid("does-not-exist")).unwrap(), None);
    }
    // ---- 3.4 créditos ----

    fn credit_names(plant: &Plant) -> Vec<&str> {
        plant.credits.iter().map(|c| c.name.as_str()).collect()
    }

    fn credit<'a>(plant: &'a Plant, name: &str) -> &'a Credit {
        plant
            .credits
            .iter()
            .find(|c| c.name == name)
            .unwrap_or_else(|| panic!("falta el crédito {name:?}: {:?}", credit_names(plant)))
    }

    #[test]
    fn credits_are_the_union_of_the_datasets_of_a_plant_with_several_sources() {
        // Escenario «Créditos de una planta con varias fuentes»: orden por nombre y sin indicar campos.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(
            credit_names(&plant),
            [
                "Agencia reguladora",
                "Enciclopedia libre",
                "Fuente a",
                "Fuente b"
            ]
        );
        // Nombre, licencia y atribución salen de la fuente, no de la referencia (cuya licencia es otra).
        let wiki = credit(&plant, "Enciclopedia libre");
        assert_eq!(wiki.license, "CC BY-SA 4.0");
        assert_eq!(wiki.attribution, "Cita de wiki");
    }

    #[test]
    fn credit_license_url_comes_from_the_source() {
        // Escenario «URL de licencia por fuente».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(
            credit(&plant, "Enciclopedia libre").license_url.as_deref(),
            Some("https://creativecommons.org/licenses/by-sa/4.0/")
        );
        assert_eq!(credit(&plant, "Agencia reguladora").license_url, None);
        assert_eq!(credit(&plant, "Fuente a").license_url, None);
    }

    #[test]
    fn credits_have_no_repeated_datasets() {
        // Escenario «Sin repeticiones»: la fuente `a` respalda nombres, partes, usos, familia y referencias, y sale una vez.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for id in ["lavandula-angustifolia", "conium-maculatum"] {
            let plant = repo.get_plant(&pid(id)).unwrap().unwrap();
            let names = credit_names(&plant);
            let unique: BTreeSet<&str> = names.iter().copied().collect();
            assert_eq!(names.len(), unique.len(), "{id}: {names:?}");
        }
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(
            plant
                .credits
                .iter()
                .filter(|c| c.name == "Fuente a")
                .count(),
            1
        );
    }

    #[test]
    fn credits_link_the_wikipedia_style_article_of_the_description() {
        // Escenario «Descripción derivada de Wikipedia»: el enlace del crédito es el del artículo, no el del sitio.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        let wiki = credit(&plant, "Enciclopedia libre");
        assert_eq!(
            wiki.url.as_deref(),
            Some("https://es.example.test/wiki/Lavandula_angustifolia")
        );
        // Una fuente sin artículo enlaza a su página.
        assert_eq!(
            credit(&plant, "Fuente a").url.as_deref(),
            Some("https://example.test/a")
        );
    }

    #[test]
    fn credits_come_from_served_content_only() {
        // El objetivo pendiente no se sirve, así que su referencia no acredita su fuente.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert!(!credit_names(&plant).contains(&"Fuente pendiente"));
        // La tóxica solo tiene fuente `a` y la de las precauciones.
        let toxic = repo.get_plant(&pid("conium-maculatum")).unwrap().unwrap();
        assert_eq!(credit_names(&toxic), ["Agencia reguladora", "Fuente a"]);
    }

    #[test]
    fn plant_without_any_dataset_has_no_credits() {
        // Escenario «Planta sin créditos».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let plant = repo
            .get_plant(&pid("matricaria-chamomilla"))
            .unwrap()
            .unwrap();
        assert!(plant.credits.is_empty());
    }

    // ---- 3.5 contenido pendiente de revisión ----

    #[test]
    fn a_review_flag_without_pending_review_omits_nothing() {
        // Los flags no condicionan nada por sí solos: ni uno con el código del objetivo condicionado.
        let fixture = Fixture::standard();
        let before = fixture
            .repo()
            .get_plant(&pid("conium-maculatum"))
            .unwrap()
            .unwrap();
        for code in [
            "objetivos-omitidos-por-toxicidad",
            "interacciones-graves-estres",
            "cita-sin-resolver",
            "inventado",
        ] {
            fixture.insert_review_flag("lavandula-angustifolia", code, "goals");
            fixture.insert_review_flag("conium-maculatum", code, "goals");
        }
        let repo = fixture.repo();
        let lavender = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        // Siguen los dos objetivos no pendientes y los dos grupos servidos, con la cita sin resolver.
        let goal_ids: Vec<&str> = lavender.goals.iter().map(|g| g.id.as_str()).collect();
        assert_eq!(goal_ids, ["cuidado-de-la-piel", "otros-objetivos"]);
        assert_eq!(lavender.use_groups.len(), 2);
        assert_eq!(lavender.use_groups[0].references.len(), 2);
        let after = repo.get_plant(&pid("conium-maculatum")).unwrap().unwrap();
        assert_eq!(before, after);
    }

    #[test]
    fn only_pending_review_omits_goals_and_groups() {
        // Escenarios «Objetivo condicionado» y «Grupo sin ninguna cita resuelta»: la omisión depende solo de `pending_review`.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let lavender = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert!(lavender.goals.iter().all(|g| g.id != "relajacion-estres"));
        assert!(
            lavender
                .use_groups
                .iter()
                .all(|g| g.activity != "Actividad pendiente")
        );
        // El resto del detalle se sirve igual.
        assert_eq!(lavender.display_name, "Lavanda");
        assert!(lavender.safety.is_some() && lavender.image.is_some());
    }

    // ---- 4.1 identificadores anteriores ----

    #[test]
    fn an_alias_resolves_to_the_canonical_plant() {
        // Escenario «Alias de un renombre» (capa de repositorio): el detalle es el de la planta canónica.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let canonical = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        let by_alias = repo.get_plant(&pid("lavandula-vera")).unwrap().unwrap();
        assert_eq!(by_alias.id, pid("lavandula-angustifolia"));
        assert_eq!(by_alias, canonical);
        // Un identificador que no es de planta ni alias no existe.
        assert_eq!(repo.get_plant(&pid("lavandula-nada")).unwrap(), None);
    }

    #[test]
    fn a_plant_id_wins_over_an_equal_alias() {
        let fixture = Fixture::standard();
        fixture.insert_alias("zea-mays", "abutilon-theophrasti");
        let repo = fixture.repo();
        let plant = repo.get_plant(&pid("zea-mays")).unwrap().unwrap();
        assert_eq!(plant.id, pid("zea-mays"));
    }

    // ---- 4.3 búsqueda por identificador anterior ----

    #[test]
    fn search_finds_a_plant_by_its_previous_identifier() {
        // Escenario «Búsqueda por identificador anterior»: el alias `matricaria-recutita` no es nombre de ninguna planta.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo
            .list_plants(&query(Some("matricaria recutita"), 20, 0))
            .unwrap();
        assert_eq!(ids(&page), ["matricaria-chamomilla"]);
        assert_eq!(page.total, 1);
        // Otras formas de escribir la misma consulta dan lo mismo.
        for q in ["Matricaria  Recutita", "  MATRICARIA-RECUTITA ", "recutita"] {
            let again = repo.list_plants(&query(Some(q), 20, 0)).unwrap();
            assert_eq!(again, page, "q = {q:?}");
        }
    }

    #[test]
    fn the_alias_is_never_returned_as_a_name() {
        // Escenario «Alias que no es nombre».
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let item = summary_of(&repo, "matricaria recutita");
        assert_eq!(item.scientific_name, "Matricaria chamomilla");
        assert_eq!(item.display_name, "Matricaria chamomilla");
        assert!(item.common_names.is_empty());
        let plant = repo
            .get_plant(&pid("matricaria-chamomilla"))
            .unwrap()
            .unwrap();
        let everything = format!("{item:?} {plant:?}").to_lowercase();
        assert!(!everything.contains("recutita"), "{everything}");
    }

    #[test]
    fn a_plant_matching_by_name_and_by_alias_is_listed_and_counted_once() {
        // Escenario «Alias sin duplicar resultados»: `Lavandula vera` es sinónimo y `lavandula-vera` es alias de la misma planta.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for q in ["lavandula vera", "vera", "lavandula-vera"] {
            let page = repo.list_plants(&query(Some(q), 20, 0)).unwrap();
            assert_eq!(ids(&page), ["lavandula-angustifolia"], "q = {q:?}");
            assert_eq!(page.total, 1, "q = {q:?}");
        }
        // Una consulta que coincide por nombres con dos plantas y por alias con una de ellas sigue contando dos.
        let both = repo.list_plants(&query(Some("lavandula"), 20, 0)).unwrap();
        assert_eq!(
            ids(&both),
            ["lavandula-angustifolia", "lavandula-latifolia"]
        );
        assert_eq!(both.total, 2);
    }

    #[test]
    fn alias_search_compares_the_query_reduced_to_a_slug() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        // La puntuación de la consulta es un espacio al compararla con el alias.
        let page = repo
            .list_plants(&query(
                Some("Mentha x piperita subsp. nothosubsp. piperita"),
                20,
                0,
            ))
            .unwrap();
        assert_eq!(ids(&page), ["mentha-x-piperita"]);
        assert_eq!(page.total, 1);
        // Sin la `x` la consulta no es subcadena de ningún nombre ni alias: es el límite conocido de la búsqueda por subcadena.
        let none = repo
            .list_plants(&query(Some("mentha piperita"), 20, 0))
            .unwrap();
        assert_eq!((none.items.len(), none.total), (0, 0));
        let with_x = repo
            .list_plants(&query(Some("mentha x piperita"), 20, 0))
            .unwrap();
        assert_eq!(ids(&with_x), ["mentha-x-piperita"]);
    }

    #[test]
    fn a_query_without_letters_or_digits_does_not_search_aliases() {
        // Escenario «Consulta sin letras ni dígitos»: todos los alias llevan guiones, y `-` no debe coincidir con ellos.
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        for q in ["-", " - ", "--", "%", "_"] {
            let page = repo.list_plants(&query(Some(q), 100, 0)).unwrap();
            let by_names_only: Vec<&str> = if matches!(q, "%" | "_") {
                vec!["zea-mays"]
            } else {
                Vec::new()
            };
            assert_eq!(ids(&page), by_names_only, "q = {q:?}");
            assert_eq!(page.total, by_names_only.len() as u64, "q = {q:?}");
        }
    }

    #[test]
    fn alias_matches_keep_the_total_order_and_consistent_pages() {
        let fixture = Fixture::standard();
        fixture.insert_alias("lavandula-spica", "twin-b");
        fixture.insert_alias("lavandula-stoechas", "twin-a");
        let repo = fixture.repo();
        // Coinciden por nombre (las dos lavandas) y por alias (las gemelas, de igual nombre científico): orden por nombre científico y luego id.
        let all = repo.list_plants(&query(Some("lavandula"), 20, 0)).unwrap();
        assert_eq!(
            ids(&all),
            [
                "lavandula-angustifolia",
                "lavandula-latifolia",
                "twin-a",
                "twin-b"
            ]
        );
        assert_eq!(all.total, 4);
        let mut seen = Vec::new();
        for offset in 0..4 {
            let page = repo
                .list_plants(&query(Some("lavandula"), 1, offset))
                .unwrap();
            assert_eq!(page.total, 4);
            seen.extend(page.items.into_iter().map(|p| p.id.0));
        }
        assert_eq!(
            seen,
            [
                "lavandula-angustifolia",
                "lavandula-latifolia",
                "twin-a",
                "twin-b"
            ]
        );
    }

    // ---- búsqueda por objetivo ----

    fn goal_repo() -> (Fixture, SqliteCatalogRepository) {
        let fixture = Fixture::with_goal_search();
        let repo = fixture.repo();
        (fixture, repo)
    }

    fn goal_plants(
        repo: &SqliteCatalogRepository,
        goal: &str,
        subarea: Option<&str>,
        limit: u32,
        offset: u32,
    ) -> GoalPlants {
        match repo.list_goal_plants(goal, subarea, limit, offset).unwrap() {
            GoalPlantsOutcome::Found(found) => found,
            other => panic!("{goal}/{subarea:?}: {other:?}"),
        }
    }

    fn goal_ids(found: &GoalPlants) -> Vec<&str> {
        found.page.items.iter().map(|p| p.id.0.as_str()).collect()
    }

    fn goal_plant<'a>(found: &'a GoalPlants, id: &str) -> &'a GoalPlant {
        found
            .page
            .items
            .iter()
            .find(|p| p.id.0 == id)
            .unwrap_or_else(|| panic!("{id} no está en {:?}", goal_ids(found)))
    }

    #[test]
    fn goals_come_in_catalog_order_with_visible_counts_and_subareas() {
        // Escenarios «Lista de objetivos», «Objetivo con subáreas», «Subárea sin plantas» y «Objetivo sin plantas».
        let (_fixture, repo) = goal_repo();
        let goals = repo.list_goals().unwrap();
        let summary: Vec<(&str, u64)> = goals
            .iter()
            .map(|g| (g.id.as_str(), g.plant_count))
            .collect();
        assert_eq!(
            summary,
            [
                ("cuidado-de-la-piel", 2),
                ("otros-objetivos", 2),
                ("relajacion-estres", 1),
                ("mejorar-el-sueno", 7),
                ("cansancio-y-fatiga", 0),
            ]
        );
        assert_eq!(goals[3].name, "Mejorar el sueño");
        // `mentha-x-piperita` está en dos subáreas pero cuenta una vez en el objetivo; la subárea sin plantas se omite.
        let other = &goals[1];
        let subareas: Vec<(&str, &str, u64)> = other
            .subareas
            .iter()
            .map(|s| (s.id.as_str(), s.name.as_str(), s.plant_count))
            .collect();
        assert_eq!(
            subareas,
            [
                ("digestion", "Digestión", 2),
                ("vias-urinarias", "Vías urinarias", 1)
            ]
        );
        assert!(goals[0].subareas.is_empty() && goals[4].subareas.is_empty());
    }

    #[test]
    fn counts_match_the_totals_of_the_results() {
        // Escenario «Coherencia con los resultados».
        let (_fixture, repo) = goal_repo();
        for goal in repo.list_goals().unwrap() {
            let found = goal_plants(&repo, &goal.id, None, 100, 0);
            assert_eq!(found.page.total, goal.plant_count, "{}", goal.id);
            assert_eq!(
                found.page.items.len() as u64,
                goal.plant_count,
                "{}",
                goal.id
            );
            for subarea in &goal.subareas {
                let found = goal_plants(&repo, &goal.id, Some(&subarea.id), 100, 0);
                assert_eq!(found.page.total, subarea.plant_count, "{}", subarea.id);
            }
        }
    }

    #[test]
    fn goal_results_carry_the_goal_and_no_subarea_without_a_filter() {
        // Escenario «Plantas de un objetivo».
        let (_fixture, repo) = goal_repo();
        let found = goal_plants(&repo, "mejorar-el-sueno", None, 20, 0);
        assert_eq!(
            found.goal,
            IdName {
                id: "mejorar-el-sueno".into(),
                name: "Mejorar el sueño".into()
            }
        );
        assert_eq!(found.subarea, None);
        assert_eq!(found.page.total, 7);
        let arnica = goal_plant(&found, "arnica-montana");
        assert_eq!(arnica.display_name, "Árnica");
        assert_eq!(arnica.areas, ["Trastornos del sueño"]);
    }

    #[test]
    fn a_subarea_filters_plants_and_areas() {
        // Escenario «Subárea».
        let (_fixture, repo) = goal_repo();
        let found = goal_plants(&repo, "otros-objetivos", Some("digestion"), 20, 0);
        assert_eq!(
            found.subarea,
            Some(IdName {
                id: "digestion".into(),
                name: "Digestión".into()
            })
        );
        assert_eq!(
            goal_ids(&found),
            ["lavandula-angustifolia", "mentha-x-piperita"]
        );
        assert_eq!(goal_plant(&found, "mentha-x-piperita").areas, ["Gases"]);
        let urinary = goal_plants(&repo, "otros-objetivos", Some("vias-urinarias"), 20, 0);
        assert_eq!(goal_ids(&urinary), ["mentha-x-piperita"]);
        assert_eq!(goal_plant(&urinary, "mentha-x-piperita").areas, ["Vejiga"]);
    }

    #[test]
    fn the_union_of_subareas_lists_a_plant_once_with_all_its_areas() {
        // Escenario «Unión sin subárea».
        let (_fixture, repo) = goal_repo();
        let found = goal_plants(&repo, "otros-objetivos", None, 20, 0);
        assert_eq!(
            goal_ids(&found),
            ["lavandula-angustifolia", "mentha-x-piperita"]
        );
        assert_eq!(found.page.total, 2);
        assert_eq!(
            goal_plant(&found, "mentha-x-piperita").areas,
            ["Gases", "Vejiga"]
        );
    }

    #[test]
    fn a_plant_in_two_goals_has_only_the_areas_of_each() {
        // Escenario «Planta en dos objetivos».
        let (_fixture, repo) = goal_repo();
        let skin = goal_plants(&repo, "cuidado-de-la-piel", None, 20, 0);
        let sleep = goal_plants(&repo, "mejorar-el-sueno", None, 20, 0);
        assert_eq!(goal_plant(&skin, "arnica-montana").areas, ["Heridas leves"]);
        assert_eq!(
            goal_plant(&sleep, "arnica-montana").areas,
            ["Trastornos del sueño"]
        );
    }

    #[test]
    fn unknown_goal_and_foreign_subareas_are_told_apart() {
        // Escenarios «Objetivo desconocido» y «Subárea ajena» (a nivel de repositorio).
        let (_fixture, repo) = goal_repo();
        assert_eq!(
            repo.list_goal_plants("no-existe", None, 20, 0).unwrap(),
            GoalPlantsOutcome::UnknownGoal
        );
        // Un `subarea` válido de otro objetivo, uno inexistente, uno vacío y uno enviado a un objetivo sin subáreas.
        for (goal, subarea) in [
            ("mejorar-el-sueno", "digestion"),
            ("otros-objetivos", "inexistente"),
            ("otros-objetivos", ""),
            ("cuidado-de-la-piel", "digestion"),
        ] {
            assert_eq!(
                repo.list_goal_plants(goal, Some(subarea), 20, 0).unwrap(),
                GoalPlantsOutcome::UnknownSubarea,
                "{goal}/{subarea}"
            );
        }
        // Una subárea sin plantas existe: devuelve una lista vacía.
        let empty = goal_plants(&repo, "otros-objetivos", Some("molestias-oculares"), 20, 0);
        assert_eq!((empty.page.items.len(), empty.page.total), (0, 0));
    }

    #[test]
    fn a_goal_without_visible_plants_is_an_empty_page() {
        // Escenario «Objetivo sin plantas».
        let (_fixture, repo) = goal_repo();
        let found = goal_plants(&repo, "cansancio-y-fatiga", None, 20, 0);
        assert!(found.page.items.is_empty());
        assert_eq!(found.page.total, 0);
        assert_eq!(found.goal.id, "cansancio-y-fatiga");
    }

    #[test]
    fn plants_without_goals_never_appear() {
        // Escenario «Planta sin objetivos»: `conium-maculatum` es la tóxica sin objetivos.
        let (_fixture, repo) = goal_repo();
        for goal in repo.list_goals().unwrap() {
            let found = goal_plants(&repo, &goal.id, None, 100, 0);
            assert!(
                !goal_ids(&found).contains(&"conium-maculatum"),
                "{}",
                goal.id
            );
        }
    }

    #[test]
    fn a_goal_pending_review_hides_the_plant_there_only() {
        // Escenarios «Planta condicionada por revisión» y «Flag sin marca de revisión del objetivo».
        let (_fixture, repo) = goal_repo();
        let stress = goal_plants(&repo, "relajacion-estres", None, 100, 0);
        assert_eq!(goal_ids(&stress), ["zea-mays"]);
        assert_eq!(stress.page.total, 1);
        // El eucalipto sigue visible en el sueño, donde no está pendiente.
        let sleep = goal_plants(&repo, "mejorar-el-sueno", None, 100, 0);
        assert!(goal_ids(&sleep).contains(&"eucalyptus-globulus"));
        // La planta sigue existiendo por el detalle.
        assert!(
            repo.get_plant(&pid("eucalyptus-globulus"))
                .unwrap()
                .is_some()
        );
        // `mentha-x-piperita` tiene una marca de revisión de identidad, pero ningún objetivo pendiente: aparece.
        let other = goal_plants(&repo, "otros-objetivos", None, 100, 0);
        assert!(goal_ids(&other).contains(&"mentha-x-piperita"));
        // `zea-mays` tiene una marca de revisión sin datos de seguridad, sin `pending_review`: aparece.
        assert!(goal_ids(&stress).contains(&"zea-mays"));
    }

    #[test]
    fn plants_are_ordered_by_display_name_ignoring_case_and_accents() {
        // Escenarios «Orden por nombre para mostrar» y «Orden sin distinguir acentos ni mayúsculas».
        let (_fixture, repo) = goal_repo();
        let found = goal_plants(&repo, "mejorar-el-sueno", None, 100, 0);
        // «abedul», el científico «Abutilon theophrasti», «Árnica», «Eucalipto», las dos «Twin plant» empatadas (por identificador) y «Zarzaparrilla».
        assert_eq!(
            goal_ids(&found),
            [
                "betula-pendula",
                "abutilon-theophrasti",
                "arnica-montana",
                "eucalyptus-globulus",
                "twin-a",
                "twin-b",
                "smilax-aspera"
            ]
        );
        let names: Vec<&str> = found
            .page
            .items
            .iter()
            .map(|p| p.display_name.as_str())
            .collect();
        assert_eq!(names[..3], ["abedul", "Abutilon theophrasti", "Árnica"]);
    }

    #[test]
    fn pages_do_not_repeat_plants_and_total_is_independent() {
        // Escenarios «Páginas sin repetición» y «Desplazamiento más allá del total».
        let (_fixture, repo) = goal_repo();
        let all: Vec<String> = goal_ids(&goal_plants(&repo, "mejorar-el-sueno", None, 100, 0))
            .into_iter()
            .map(str::to_string)
            .collect();
        let mut walked: Vec<String> = Vec::new();
        for offset in (0..10).step_by(3) {
            let page = goal_plants(&repo, "mejorar-el-sueno", None, 3, offset);
            assert_eq!(page.page.total, 7);
            walked.extend(goal_ids(&page).into_iter().map(str::to_string));
        }
        assert_eq!(walked, all);
        let past = goal_plants(&repo, "mejorar-el-sueno", None, 3, 500);
        assert!(past.page.items.is_empty());
        assert_eq!(past.page.total, 7);
    }

    #[test]
    fn cards_carry_safety_level_flag_and_image() {
        // Escenarios «Precauciones sin nivel» y «Datos ausentes».
        let (_fixture, repo) = goal_repo();
        let skin = goal_plants(&repo, "cuidado-de-la-piel", None, 100, 0);
        let lavender = goal_plant(&skin, "lavandula-angustifolia");
        assert_eq!(lavender.safety_level, Some(SafetyLevel::Medium));
        assert!(lavender.has_safety);
        // La imagen es la misma del detalle.
        let detail = repo
            .get_plant(&pid("lavandula-angustifolia"))
            .unwrap()
            .unwrap();
        assert_eq!(lavender.image, detail.image);
        assert!(lavender.image.is_some());
        assert_eq!(lavender.family.as_deref(), Some("Lamiaceae"));
        assert_eq!(
            lavender
                .common_names
                .iter()
                .map(|n| n.text.as_str())
                .collect::<Vec<_>>(),
            ["Lavanda", "Espliego", "Lavender"]
        );

        let sleep = goal_plants(&repo, "mejorar-el-sueno", None, 100, 0);
        // Precauciones sin nivel: nivel nulo y `hasSafety` verdadero.
        let eucalyptus = goal_plant(&sleep, "eucalyptus-globulus");
        assert_eq!(
            (eucalyptus.safety_level, eucalyptus.has_safety),
            (None, true)
        );
        // Sin imagen ni seguridad.
        let stress = goal_plants(&repo, "relajacion-estres", None, 100, 0);
        let corn = goal_plant(&stress, "zea-mays");
        assert_eq!(
            (corn.safety_level, corn.has_safety, corn.image.as_ref()),
            (None, false, None)
        );
    }

    #[test]
    fn a_scientific_display_name_keeps_foreign_common_names() {
        // Un `displayName` científico con nombres comunes en otro idioma.
        let (_fixture, repo) = goal_repo();
        let found = goal_plants(&repo, "mejorar-el-sueno", None, 100, 0);
        let velvet = goal_plant(&found, "abutilon-theophrasti");
        assert_eq!(velvet.display_name, "Abutilon theophrasti");
        assert_eq!(
            velvet
                .common_names
                .iter()
                .map(|n| (n.text.as_str(), n.language.as_str()))
                .collect::<Vec<_>>(),
            [("Butterprint", "en"), ("Velvetleaf", "en")]
        );
    }
}
