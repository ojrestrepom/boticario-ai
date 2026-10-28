//! La búsqueda por objetivo (cambio `enable-goal-search`) no añade tablas ni migraciones: la API abre una base construida desde la semilla de fixture con la versión de esquema vigente y las tablas de objetivos que dejó `consolidate-catalog-seed`.
//!
//! Complementa `fixture_end_to_end.rs` (servicio HTTP sobre la misma base) y `plain_logs.rs` (arranque del binario sobre la base de fixture).

use std::collections::BTreeSet;
use std::path::Path;

use catalog_api::repository::SqliteCatalogRepository;
use catalog_core::domain::ListQuery;
use catalog_core::repository::CatalogRepository;
use catalog_core::schema::{goal, goal_subarea, metadata, plant_goal};
use catalog_core::version::{SCHEMA_VERSION, SCHEMA_VERSION_KEY, apply_schema};
use catalog_ingest::seed_build::build_from_dir;
use diesel::prelude::*;
use diesel::sql_types::Text;
use diesel::{SqliteConnection, sql_query};

#[derive(QueryableByName)]
struct TableName {
    #[diesel(sql_type = Text)]
    name: String,
}

fn table_names(conn: &mut SqliteConnection) -> BTreeSet<String> {
    sql_query("SELECT name FROM sqlite_master WHERE type = 'table'")
        .load::<TableName>(conn)
        .unwrap()
        .into_iter()
        .map(|t| t.name)
        .collect()
}

#[test]
fn api_opens_a_fixture_seed_database_at_schema_v2_without_own_tables() {
    // Este cambio no sube la versión del esquema ni añade migraciones: si cambia, hay que revisarlo.
    assert_eq!(SCHEMA_VERSION, 2);

    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("build").join("catalog.db");
    let seed = Path::new(env!("CARGO_MANIFEST_DIR")).join("../catalog-ingest/tests/fixtures/seed");
    build_from_dir(&seed, &out).unwrap();

    // La API la abre (comprueba la versión del esquema) y la sirve.
    let repo = SqliteCatalogRepository::open(&out).unwrap();
    let page = repo
        .list_plants(&ListQuery {
            q: None,
            limit: 20,
            offset: 0,
        })
        .unwrap();
    assert_eq!(page.total, 3);

    let mut conn = SqliteConnection::establish(out.to_str().unwrap()).unwrap();

    // La versión guardada es la soportada.
    let stored: String = metadata::table
        .filter(metadata::key.eq(SCHEMA_VERSION_KEY))
        .select(metadata::value)
        .first(&mut conn)
        .unwrap();
    assert_eq!(stored, SCHEMA_VERSION.to_string());

    // La base construida solo tiene las tablas del esquema neutral: la construcción no crea tablas propias de la búsqueda.
    let mut reference = SqliteConnection::establish(":memory:").unwrap();
    apply_schema(&mut reference).unwrap();
    assert_eq!(table_names(&mut conn), table_names(&mut reference));

    // Las tablas de objetivos existen con las columnas que lee la búsqueda y traen los datos de la semilla.
    let goals: i64 = goal::table.count().get_result(&mut conn).unwrap();
    let subareas: i64 = goal_subarea::table.count().get_result(&mut conn).unwrap();
    assert_eq!((goals, subareas), (6, 6));
    let rows: Vec<(String, String, Option<String>, bool)> = plant_goal::table
        .select((
            plant_goal::plant_id,
            plant_goal::goal_id,
            plant_goal::subarea_id,
            plant_goal::pending_review,
        ))
        .order_by(plant_goal::id.asc())
        .load(&mut conn)
        .unwrap();
    assert!(!rows.is_empty());
    assert!(
        rows.iter()
            .any(|(plant, goal, subarea, _)| plant == "calendula-officinalis"
                && goal == "otros-objetivos"
                && subarea.as_deref() == Some("boca-y-garganta"))
    );
}
