//! Versión del esquema neutral y aplicación de sus migraciones embebidas.

use std::error::Error;
use std::fmt;

use diesel::SqliteConnection;
use diesel::migration::MigrationSource;
use diesel::sqlite::Sqlite;
use diesel_migrations::{EmbeddedMigrations, embed_migrations};

/// Versión del esquema; súbela cuando las migraciones de `data/migrations/` cambien de forma incompatible.
pub const SCHEMA_VERSION: u32 = 2;

/// Clave de la tabla `metadata` donde se guarda la versión del esquema.
pub const SCHEMA_VERSION_KEY: &str = "schema_version";

/// Migraciones de `data/migrations/`, incluidas en el binario en tiempo de compilación.
///
/// La ruta es relativa al directorio del crate (`backend/catalog-core/`), por eso sube dos niveles hasta la raíz del repositorio.
pub const MIGRATIONS: EmbeddedMigrations = embed_migrations!("../../data/migrations");

/// Fallo al aplicar el esquema a una base.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SchemaError {
    /// Descripción del problema, tal como la reporta Diesel.
    pub message: String,
}

impl fmt::Display for SchemaError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "no se pudo aplicar el esquema: {}", self.message)
    }
}

impl Error for SchemaError {}

/// Aplica el esquema neutral a una base nueva y vacía.
///
/// Ejecuta el `up.sql` de cada migración embebida, en orden, pero sin pasar por el arnés de Diesel (`run_pending_migrations`): el arnés crea además la tabla `__diesel_schema_migrations` para llevar la cuenta de lo aplicado, y aquí no hace falta ni conviene.
/// La base no evoluciona, se regenera entera en cada construcción, así que no hay nada que registrar y el archivo resultante contiene solo las tablas del esquema neutral.
pub fn apply_schema(conn: &mut SqliteConnection) -> Result<(), SchemaError> {
    let wrap = |e: Box<dyn Error + Send + Sync>| SchemaError {
        message: e.to_string(),
    };
    let mut migrations = MigrationSource::<Sqlite>::migrations(&MIGRATIONS).map_err(wrap)?;
    // Los nombres empiezan por la fecha, así que el orden alfabético es el cronológico.
    migrations.sort_by_key(|m| m.name().to_string());
    for migration in migrations {
        migration.run(conn).map_err(wrap)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use diesel::Connection;
    use rusqlite::Connection as Rusqlite;

    /// El `up.sql` de cada migración, leído en tiempo de compilación para buscar en él.
    const UP_SQL: [&str; 2] = [
        include_str!("../../../data/migrations/2026-10-12-000000_catalog_v1/up.sql"),
        include_str!("../../../data/migrations/2026-10-26-000000_catalog_v2/up.sql"),
    ];

    fn schema_in_memory() -> SqliteConnection {
        let mut conn = SqliteConnection::establish(":memory:").unwrap();
        apply_schema(&mut conn).unwrap();
        conn
    }

    #[test]
    fn schema_loads_and_stores_version() {
        use crate::schema::metadata::dsl::*;
        use diesel::prelude::*;

        let mut conn = schema_in_memory();
        diesel::insert_into(metadata)
            .values((
                key.eq(SCHEMA_VERSION_KEY),
                value.eq(SCHEMA_VERSION.to_string()),
            ))
            .execute(&mut conn)
            .unwrap();
        let stored: String = metadata
            .filter(key.eq(SCHEMA_VERSION_KEY))
            .select(value)
            .first(&mut conn)
            .unwrap();
        assert_eq!(stored.parse::<u32>().unwrap(), SCHEMA_VERSION);
    }

    #[test]
    fn schema_creates_exactly_the_expected_tables() {
        // Se escribe la base en un archivo para abrirla también con rusqlite e inspeccionar `sqlite_master`.
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("schema.db");
        {
            let mut conn = SqliteConnection::establish(path.to_str().unwrap()).unwrap();
            apply_schema(&mut conn).unwrap();
        }
        let conn = Rusqlite::open(&path).unwrap();
        let mut stmt = conn
            .prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
            .unwrap();
        let tables: Vec<String> = stmt
            .query_map([], |row| row.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();

        let mut expected = vec![
            "metadata",
            "source",
            "plant",
            "plant_source_id",
            "plant_name",
            "plant_part",
            "reference",
            "plant_use",
            "plant_name_source",
            "plant_part_source",
            "plant_use_source",
            "reference_source",
            "plant_profile",
            "plant_profile_ref",
            "plant_use_group",
            "plant_use_group_ref",
            "goal",
            "goal_subarea",
            "plant_goal",
            "plant_goal_ref",
            "plant_safety",
            "plant_safety_ref",
            "plant_image",
            "plant_alias",
            "plant_review_flag",
        ];
        expected.sort();
        assert_eq!(tables, expected);
    }

    #[test]
    fn v2_tables_accept_the_new_shapes_and_reject_inconsistent_rows() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("v2.db");
        {
            let mut conn = SqliteConnection::establish(path.to_str().unwrap()).unwrap();
            apply_schema(&mut conn).unwrap();
        }
        let conn = Rusqlite::open(&path).unwrap();
        conn.pragma_update(None, "foreign_keys", true).unwrap();
        conn.execute_batch(
            "INSERT INTO plant VALUES ('p', 'P p', 'p p', NULL, NULL);
             INSERT INTO reference VALUES ('d:1', 'cita', 'd', 'lic', NULL);
             INSERT INTO goal VALUES ('g', 'G', 1), ('h', 'H', 2);
             INSERT INTO goal_subarea VALUES ('s', 'h', 'S', 1);
             INSERT INTO plant_use_group VALUES (1, 'p', 1, 'a', 'a', 1, '[]', 1);
             INSERT INTO plant_use_group_ref VALUES (1, 'k', 1, 'k (sin resolver)', 0, NULL);
             INSERT INTO plant_use_group_ref VALUES (1, 'j', 2, 'cita', 1, 'd:1');
             INSERT INTO plant_goal VALUES (1, 'p', 'g', NULL, 1, 'area', 'ev', 0);
             INSERT INTO plant_profile_ref VALUES ('p', 'description', 'd:1');
             INSERT INTO plant_safety VALUES ('p', NULL, 'precaución');
             INSERT INTO plant_image VALUES ('p', 'u', 'pu', NULL, 'CC0', NULL, 0);",
        )
        .unwrap();
        for bad in [
            // Cita resuelta sin referencia.
            "INSERT INTO plant_use_group_ref VALUES (1, 'x', 3, 't', 1, NULL)",
            // Cita sin resolver con referencia.
            "INSERT INTO plant_use_group_ref VALUES (1, 'x', 3, 't', 0, 'd:1')",
            // Subárea de otro objetivo.
            "INSERT INTO plant_goal VALUES (2, 'p', 'g', 's', 2, 'area', 'ev', 0)",
            // Objetivo repetido para la misma planta, subárea y área.
            "INSERT INTO plant_goal VALUES (2, 'p', 'g', NULL, 2, 'area', 'ev', 0)",
            // Campo del perfil fuera de la lista cerrada.
            "INSERT INTO plant_profile_ref VALUES ('p', 'otro', 'd:1')",
            // Referencia del perfil que no existe.
            "INSERT INTO plant_profile_ref VALUES ('p', 'origin', 'd:2')",
            // Nivel de seguridad fuera de la lista.
            "INSERT INTO plant_safety VALUES ('q', 'extremo', 't')",
        ] {
            assert!(conn.execute(bad, []).is_err(), "debería fallar: {bad}");
        }
    }

    #[test]
    fn schema_has_no_dataset_terms() {
        let sql = UP_SQL.join("\n").to_lowercase();
        // Los términos se arman con `concat!` para que este archivo tampoco los contenga literalmente: el test de independencia de la API busca esos nombres en todo el código de `catalog-core`.
        for term in [
            concat!("us", "da"),
            concat!("fnf", "num"),
            concat!("fnf", "tax"),
            concat!("ethno", "bot"),
            concat!("far", "macy"),
            concat!("pp", "co"),
            concat!("pp", "na"),
            "taxon",
            concat!("long", "ref"),
            concat!("du", "ke"),
        ] {
            assert!(!sql.contains(term), "el esquema contiene {term:?}");
        }
    }
}
