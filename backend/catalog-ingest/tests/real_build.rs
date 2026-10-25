//! Comprueba la construcción real (`data/build/catalog.db`) contra la semilla de `data/seed/`.
//!
//! Está marcado `#[ignore]` porque necesita `data/build/catalog.db`, que existe solo tras ejecutar `build`. Ejecútalo con `cargo test -p catalog-ingest --test real_build -- --ignored --nocapture`.
//!
//! No fija conteos de la curación (usos o partes de una planta): comprueba que la base refleja la semilla y que la lavanda existe con usos y partes.

use std::path::{Path, PathBuf};

use catalog_core::schema::{plant, plant_name, plant_part, plant_use, reference};
use catalog_ingest::seed::load_seed;
use diesel::prelude::*;

fn data_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../data")
}

fn open_read_only(db: &Path) -> SqliteConnection {
    assert!(db.exists(), "falta {}: ejecuta `build` antes", db.display());
    SqliteConnection::establish(&format!("file:{}?mode=ro", db.display())).unwrap()
}

#[test]
#[ignore = "necesita data/build/catalog.db construido con `build`"]
fn real_catalog_reflects_the_seed() {
    let seed = load_seed(&data_dir().join("seed")).unwrap();
    let mut catalog = open_read_only(&data_dir().join("build/catalog.db"));

    let plants: i64 = plant::table.count().get_result(&mut catalog).unwrap();
    let scientific: i64 = plant_name::table
        .filter(plant_name::kind.eq("scientific"))
        .count()
        .get_result(&mut catalog)
        .unwrap();
    let references: i64 = reference::table.count().get_result(&mut catalog).unwrap();
    println!(
        "plantas={plants} cientificos={scientific} referencias={references} semilla={}",
        seed.plants.len()
    );
    assert_eq!(plants as usize, seed.plants.len());
    assert!(
        scientific >= plants,
        "cada planta tiene su nombre científico"
    );
    assert!(references > 0);

    // Toda planta de la semilla está en la base con su id.
    let mut ids: Vec<String> = plant::table.select(plant::id).load(&mut catalog).unwrap();
    ids.sort();
    let mut expected: Vec<String> = seed.plants.iter().map(|p| p.id.clone()).collect();
    expected.sort();
    assert_eq!(ids, expected);

    // La lavanda existe, con usos y partes (sin fijar cuántos).
    let lavender = "lavandula-angustifolia";
    let uses: i64 = plant_use::table
        .filter(plant_use::plant_id.eq(lavender))
        .count()
        .get_result(&mut catalog)
        .unwrap();
    let parts: i64 = plant_part::table
        .filter(plant_part::plant_id.eq(lavender))
        .count()
        .get_result(&mut catalog)
        .unwrap();
    assert!(uses > 0, "la lavanda debe tener usos");
    assert!(parts > 0, "la lavanda debe tener partes");
}
