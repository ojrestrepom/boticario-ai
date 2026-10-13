//! Comprueba la construcción real (`data/build/`) contra los valores de referencia del análisis previo.
//!
//! Está marcado `#[ignore]` porque necesita `data/build/raw.db` y `data/build/catalog.db`, que existen solo tras ejecutar `build`. Ejecútalo con `cargo test -p catalog-ingest --test real_build -- --ignored --nocapture`.

use std::path::{Path, PathBuf};

use catalog_core::schema::{plant, plant_name, plant_part, plant_use, reference};
use catalog_ingest::usda::derive_with_stats;
use diesel::prelude::*;

fn build_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../data/build")
}

fn open_read_only(db: &Path) -> SqliteConnection {
    assert!(db.exists(), "falta {}: ejecuta `build` antes", db.display());
    SqliteConnection::establish(&format!("file:{}?mode=ro", db.display())).unwrap()
}

#[test]
#[ignore = "necesita data/build/ construido con `build`"]
fn real_catalog_matches_reference_values() {
    let mut catalog = open_read_only(&build_dir().join("catalog.db"));

    let plants: i64 = plant::table.count().get_result(&mut catalog).unwrap();
    let with_uses = plant_use::table
        .select(plant_use::plant_id)
        .distinct()
        .load::<String>(&mut catalog)
        .unwrap()
        .len();
    let uses: i64 = plant_use::table.count().get_result(&mut catalog).unwrap();
    let references: i64 = reference::table.count().get_result(&mut catalog).unwrap();
    let common: i64 = plant_name::table
        .filter(plant_name::kind.eq("common"))
        .count()
        .get_result(&mut catalog)
        .unwrap();
    let scientific: i64 = plant_name::table
        .filter(plant_name::kind.eq("scientific"))
        .count()
        .get_result(&mut catalog)
        .unwrap();
    let families: i64 = plant::table
        .filter(plant::family.is_not_null())
        .count()
        .get_result(&mut catalog)
        .unwrap();
    let parts: i64 = plant_part::table.count().get_result(&mut catalog).unwrap();

    let mut raw = open_read_only(&build_dir().join("raw.db"));
    let (_records, stats) = derive_with_stats(&mut raw).unwrap();

    println!(
        "plantas={plants} con_usos={with_uses} usos={uses} filas_elegibles={} referencias={references} comunes={common} cientificos={scientific} familias={families} partes={parts}",
        stats.eligible_use_rows
    );
    assert_eq!(plants, 2_376);
    assert_eq!(with_uses, 1_180);
    assert_eq!(uses, 18_931);
    assert_eq!(stats.eligible_use_rows, 19_446);
    assert_eq!(references, 32);
    assert_eq!(common, 2_920);
    assert_eq!(scientific, 2_376);
    assert_eq!(families, 2_342);
}
