//! Hash del contenido lógico de la base neutral.
//!
//! El archivo SQLite puede cambiar byte a byte sin que cambie su contenido (páginas libres, orden interno), así que no se hashea el archivo: se vuelcan las filas de cada tabla en un orden total y se hashea el volcado.
//!
//! Este módulo y `raw` son la única excepción al uso de Diesel (decisión 14 del diseño): el volcado recorre tablas y columnas que solo se conocen en tiempo de ejecución (se leen con `PRAGMA table_info`), así que usa SQL dinámico con `rusqlite`.

use std::path::Path;

use rusqlite::types::ValueRef;
use rusqlite::{Connection, OpenFlags};
use sha2::{Digest, Sha256};

use crate::error::IngestError;
use crate::raw::quote_ident;

/// Tablas del esquema neutral, en el orden fijo en que se vuelcan.
///
/// Un test comprueba que coincide con las tablas que crea `apply_schema`.
pub const NEUTRAL_TABLES: [&str; 24] = [
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

/// Calcula el SHA-256 (hexadecimal) del contenido lógico de la base `db`.
///
/// Los ids enteros autogenerados (`plant_name.id`, etc.) forman parte del contenido porque las tablas de atribución los referencian; son deterministas porque el catálogo se inserta en orden total.
pub fn content_hash(db: &Path) -> Result<String, IngestError> {
    if !db.exists() {
        return Err(IngestError::MissingDatabase {
            path: db.to_path_buf(),
        });
    }
    let conn = Connection::open_with_flags(db, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    let mut hasher = Sha256::new();
    for table in NEUTRAL_TABLES {
        dump_table(&conn, table, &mut hasher)?;
    }
    Ok(hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect())
}

/// Escribe un valor con su longitud por delante: así `("ab","c")` y `("a","bc")` no se confunden.
fn put_bytes(hasher: &mut Sha256, tag: u8, bytes: &[u8]) {
    hasher.update([tag]);
    hasher.update((bytes.len() as u64).to_le_bytes());
    hasher.update(bytes);
}

fn dump_table(conn: &Connection, table: &str, hasher: &mut Sha256) -> Result<(), IngestError> {
    let mut info = conn.prepare(&format!("PRAGMA table_info({})", quote_ident(table)))?;
    let columns: Vec<String> = info
        .query_map([], |row| row.get::<_, String>(1))?
        .collect::<Result<_, _>>()?;

    // Cabecera: nombre de la tabla y de sus columnas.
    put_bytes(hasher, b'T', table.as_bytes());
    for column in &columns {
        put_bytes(hasher, b'C', column.as_bytes());
    }

    let order = columns
        .iter()
        .map(|c| quote_ident(c))
        .collect::<Vec<_>>()
        .join(", ");
    let sql = format!("SELECT * FROM {} ORDER BY {order}", quote_ident(table));
    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query([])?;
    while let Some(row) = rows.next()? {
        hasher.update(b"R");
        for i in 0..columns.len() {
            // Cada valor lleva una etiqueta de tipo: `NULL`, `1` y `'1'` son datos distintos.
            match row.get_ref(i)? {
                ValueRef::Null => hasher.update(b"N"),
                ValueRef::Integer(v) => put_bytes(hasher, b'I', &v.to_le_bytes()),
                ValueRef::Real(v) => put_bytes(hasher, b'F', &v.to_le_bytes()),
                ValueRef::Text(t) => put_bytes(hasher, b'S', t),
                ValueRef::Blob(b) => put_bytes(hasher, b'B', b),
            }
        }
    }
    hasher.update(b"E");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{sample_catalog, sample_inputs};
    use crate::{consolidate::consolidate, write::write_catalog};
    use catalog_core::version::apply_schema;
    use diesel::{Connection as _, SqliteConnection};

    fn hash_of(catalog: &crate::consolidate::Catalog) -> String {
        let dir = tempfile::tempdir().unwrap();
        let out = dir.path().join("catalog.db");
        write_catalog(catalog, &out).unwrap();
        content_hash(&out).unwrap()
    }

    #[test]
    fn table_list_matches_schema() {
        // Se crea en un archivo temporal para poder abrirlo luego con rusqlite, que es lo que usa el volcado.
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("schema.db");
        apply_schema(&mut SqliteConnection::establish(path.to_str().unwrap()).unwrap()).unwrap();
        let conn = Connection::open(&path).unwrap();
        let mut stmt = conn
            .prepare(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
            )
            .unwrap();
        let mut tables: Vec<String> = stmt
            .query_map([], |r| r.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        tables.sort();
        let mut listed: Vec<String> = NEUTRAL_TABLES.iter().map(|t| t.to_string()).collect();
        listed.sort();
        assert_eq!(tables, listed);
    }

    #[test]
    fn same_catalog_in_two_paths_has_same_hash() {
        let catalog = sample_catalog();
        let hash = hash_of(&catalog);
        assert_eq!(hash.len(), 64);
        assert!(hash.chars().all(|c| c.is_ascii_hexdigit()));
        assert_eq!(hash, hash_of(&catalog));
    }

    #[test]
    fn changing_an_activity_changes_the_hash() {
        let mut inputs = sample_inputs();
        inputs[0].records.plants[0].uses[0].activity = "Sedativd".into();
        assert_ne!(
            hash_of(&consolidate(inputs).unwrap()),
            hash_of(&sample_catalog())
        );
    }

    #[test]
    fn changing_a_multivalued_spelling_changes_the_hash() {
        let mut inputs = sample_inputs();
        inputs[1].records.plants[0].scientific_name = "LAVANDULA  angustifoliA".into();
        assert_ne!(
            hash_of(&consolidate(inputs).unwrap()),
            hash_of(&sample_catalog())
        );
    }

    #[test]
    fn missing_database_is_reported() {
        let err = content_hash(Path::new("/no/existe/catalog.db")).unwrap_err();
        assert!(matches!(err, IngestError::MissingDatabase { .. }));
        let msg = err.to_string();
        assert!(msg.contains("catalog.db") && !msg.contains("descarga"));
    }
}
