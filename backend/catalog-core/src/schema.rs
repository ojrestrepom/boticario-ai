//! Esquema SQL neutral embebido y su versión.

/// Versión del esquema; súbela cuando `data/schema.sql` cambie de forma incompatible.
pub const SCHEMA_VERSION: u32 = 1;

/// Clave de la tabla `metadata` donde se guarda la versión del esquema.
pub const SCHEMA_VERSION_KEY: &str = "schema_version";

/// Contenido de `data/schema.sql`, incluido en el binario en tiempo de compilación.
///
/// La ruta de `include_str!` es relativa a este archivo (`backend/catalog-core/src/`), por eso sube tres niveles hasta la raíz del repositorio.
pub const SCHEMA_SQL: &str = include_str!("../../../data/schema.sql");

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    fn load() -> Connection {
        let conn = Connection::open_in_memory().unwrap();
        conn.execute_batch(SCHEMA_SQL).unwrap();
        conn
    }

    #[test]
    fn schema_loads_and_stores_version() {
        let conn = load();
        conn.execute(
            "INSERT INTO metadata (key, value) VALUES (?1, ?2)",
            (SCHEMA_VERSION_KEY, SCHEMA_VERSION.to_string()),
        )
        .unwrap();
        let value: String = conn
            .query_row(
                "SELECT value FROM metadata WHERE key = ?1",
                [SCHEMA_VERSION_KEY],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(value.parse::<u32>().unwrap(), SCHEMA_VERSION);
    }

    #[test]
    fn schema_creates_expected_tables() {
        let conn = load();
        let expected = [
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
        ];
        for table in expected {
            let n: i64 = conn
                .query_row(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?1",
                    [table],
                    |row| row.get(0),
                )
                .unwrap();
            assert_eq!(n, 1, "falta la tabla {table}");
        }
    }

    #[test]
    fn schema_has_no_dataset_terms() {
        let sql = SCHEMA_SQL.to_lowercase();
        for term in [
            "usda", "fnfnum", "fnftax", "ethnobot", "farmacy", "ppco", "ppna", "taxon", "longref",
            "duke",
        ] {
            assert!(!sql.contains(term), "el esquema contiene {term:?}");
        }
    }
}
