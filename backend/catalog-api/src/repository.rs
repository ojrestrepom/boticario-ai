//! Implementación SQLite (con Diesel) del repositorio del catálogo.
//!
//! Lee únicamente el esquema neutral, siempre con el DSL de Diesel: aquí no hay SQL escrito a mano.
//! La base se abre en solo lectura y se comprueba su versión de esquema antes de servir nada.

use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::path::{Path, PathBuf};
use std::time::Duration;

use catalog_core::domain::{
    ListQuery, NameKind, Page, Part, Plant, PlantId, PlantName, PlantSummary, Reference, Use,
};
use catalog_core::normalize::normalize_name;
use catalog_core::repository::{CatalogRepository, RepositoryError};
use catalog_core::rows::{PlantNameRow, PlantPartRow, PlantRow, PlantUseRow, ReferenceRow};
use catalog_core::schema::{metadata, plant, plant_name, plant_part, plant_use, reference};
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

        // Ids de las plantas con algún nombre (científico o común) que contiene el texto.
        // `escape('\\')` declara `\` como carácter de escape: sin él, `%` y `_` del usuario actuarían como comodines.
        let matching_ids = |pattern: &str| {
            plant_name::table
                .filter(plant_name::normalized.like(pattern.to_owned()).escape('\\'))
                .select(plant_name::plant_id)
        };

        // `into_boxed` permite añadir el filtro solo si hay búsqueda.
        let mut count_query = plant::table.into_boxed();
        let mut page_query = plant::table.into_boxed();
        if let Some(pattern) = &pattern {
            count_query = count_query.filter(plant::id.eq_any(matching_ids(pattern)));
            page_query = page_query.filter(plant::id.eq_any(matching_ids(pattern)));
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

        let items = plants
            .iter()
            .map(|p| PlantSummary {
                id: PlantId(p.id.clone()),
                scientific_name: p.scientific_name.clone(),
                common_names: commons.remove(p.id.as_str()).unwrap_or_default(),
                family: p.family.clone(),
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

        let Some(row) = plant::table
            .find(&id.0)
            .select(PlantRow::as_select())
            .first(conn)
            .optional()
            .map_err(storage)?
        else {
            return Ok(None);
        };

        Ok(Some(Plant {
            id: PlantId(row.id),
            scientific_name: row.scientific_name,
            family: row.family,
            names: load_names(conn, &id.0)?,
            parts: load_parts(conn, &id.0)?,
            uses: load_uses(conn, &id.0)?,
        }))
    }
}

/// Nombres de la planta: científicos primero, luego por texto e idioma.
fn load_names(
    conn: &mut SqliteConnection,
    plant_id: &str,
) -> Result<Vec<PlantName>, RepositoryError> {
    let rows: Vec<PlantNameRow> = plant_name::table
        .filter(plant_name::plant_id.eq(plant_id))
        .select(PlantNameRow::as_select())
        .load(conn)
        .map_err(storage)?;
    let mut names = rows
        .iter()
        .map(to_plant_name)
        .collect::<Result<Vec<_>, RepositoryError>>()?;
    // `NameKind` no implementa `Ord`, así que se ordena por un rango explícito: científico antes que común.
    names.sort_by(|a, b| {
        let rank = |n: &PlantName| u8::from(n.kind == NameKind::Common);
        (rank(a), &a.text, &a.language).cmp(&(rank(b), &b.text, &b.language))
    });
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
                supported: 1
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
        let mut v: Vec<String> = (1..=25).map(|n| format!("fillerus-{n:02}")).collect();
        v.extend(
            [
                "lavandula-angustifolia",
                "lavandula-latifolia",
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
        assert_eq!(page.total, 31);
        assert_eq!(ids(&page), expected_order());
    }

    #[test]
    fn pages_are_consecutive_and_total_is_independent() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let mut seen = Vec::new();
        for offset in (0..31).step_by(7) {
            let page = repo.list_plants(&query(None, 7, offset)).unwrap();
            assert_eq!(page.total, 31);
            seen.extend(page.items.into_iter().map(|p| p.id.0));
        }
        assert_eq!(seen, expected_order());
    }

    #[test]
    fn default_limit_is_twenty_and_offset_past_total_is_empty() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        let page = repo.list_plants(&ListQuery::default()).unwrap();
        assert_eq!((page.items.len(), page.total), (20, 31));
        let past = repo.list_plants(&query(None, 20, 500)).unwrap();
        assert_eq!((past.items.len(), past.total), (0, 31));
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
                common_names: vec![
                    name("Espliego", "es"),
                    name("Lavanda", "es"),
                    name("Lavender", "en")
                ],
                family: Some("Lamiaceae".to_string()),
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
                ("Espliego", NameKind::Common, "es"),
                ("Lavanda", NameKind::Common, "es"),
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

    #[test]
    fn unknown_plant_is_none() {
        let fixture = Fixture::standard();
        let repo = fixture.repo();
        assert_eq!(repo.get_plant(&pid("does-not-exist")).unwrap(), None);
    }
}
