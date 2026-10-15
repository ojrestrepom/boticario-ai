//! Compara las cinco plantas del fixture `tests/fixtures/plant_catalog.json` con la base construida.
//!
//! Está marcado `#[ignore]` porque necesita `data/build/catalog.db`, que no está en el árbol de tests (resultado de `build`, con el ZIP de USDA descargado). El fixture JSON sí vive dentro del crate. Un test normal debe pasar sin red y sin `data/`. Ejecútalo con `cargo test -p catalog-ingest --test asset_crosscheck -- --ignored --nocapture`.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

use catalog_core::schema::{plant_part, plant_source_id, plant_use, reference};
use diesel::prelude::*;
use serde_json::Value;

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn text(value: &Value) -> String {
    value.as_str().expect("se esperaba un texto").to_string()
}

#[test]
#[ignore = "necesita data/build/catalog.db"]
fn asset_plants_match_the_built_catalog() {
    let db = repo_root().join("data/build/catalog.db");
    assert!(db.exists(), "falta {}: ejecuta `build` antes", db.display());
    let mut conn = SqliteConnection::establish(&format!("file:{}?mode=ro", db.display())).unwrap();

    let fixture = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/plant_catalog.json");
    let asset: Value = serde_json::from_str(&std::fs::read_to_string(fixture).unwrap()).unwrap();
    // Citas del asset por id de referencia.
    let asset_citations: std::collections::BTreeMap<String, String> = asset["references"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| (text(&r["id"]), text(&r["citation"])))
        .collect();

    let plants = asset["plants"].as_array().unwrap();
    assert_eq!(plants.len(), 5);
    for asset_plant in plants {
        let usda_id = asset_plant["usdaPlantId"].as_i64().unwrap().to_string();
        let name = text(&asset_plant["sourceScientificName"]);

        let plant_id: String = plant_source_id::table
            .filter(plant_source_id::source_id.eq("usda"))
            .filter(plant_source_id::source_plant_id.eq(&usda_id))
            .select(plant_source_id::plant_id)
            .first(&mut conn)
            .unwrap_or_else(|e| panic!("{name} ({usda_id}) no está en el catálogo: {e}"));

        // Partes: conjunto de etiquetas.
        let expected_parts: BTreeSet<String> = asset_plant["parts"]
            .as_array()
            .unwrap()
            .iter()
            .map(|p| text(&p["name"]))
            .collect();
        let parts: BTreeSet<String> = plant_part::table
            .filter(plant_part::plant_id.eq(&plant_id))
            .select(plant_part::label)
            .load::<String>(&mut conn)
            .unwrap()
            .into_iter()
            .collect();
        assert_eq!(parts, expected_parts, "partes de {name}");

        // Usos: conjunto de (actividad, id de referencia).
        let mut expected_uses = BTreeSet::new();
        for u in asset_plant["traditionalUses"].as_array().unwrap() {
            for r in u["referenceIds"].as_array().unwrap() {
                expected_uses.insert((text(&u["activity"]), text(r)));
            }
        }
        let uses: BTreeSet<(String, String)> = plant_use::table
            .filter(plant_use::plant_id.eq(&plant_id))
            .select((plant_use::activity, plant_use::reference_id))
            .load::<(String, String)>(&mut conn)
            .unwrap()
            .into_iter()
            .collect();
        assert_eq!(uses, expected_uses, "usos de {name}");

        // Citas de las referencias usadas.
        for (_, ref_id) in &expected_uses {
            let citation: String = reference::table
                .find(ref_id)
                .select(reference::citation)
                .first(&mut conn)
                .unwrap();
            assert_eq!(&citation, &asset_citations[ref_id], "cita {ref_id}");
        }
        println!(
            "{name} ({usda_id}): {} partes, {} usos distintos",
            parts.len(),
            uses.len()
        );
    }
    // Manzanilla (605) y Menta (619) no tienen usos.
    for usda_id in ["605", "619"] {
        let id: String = plant_source_id::table
            .filter(plant_source_id::source_plant_id.eq(usda_id))
            .select(plant_source_id::plant_id)
            .first(&mut conn)
            .unwrap();
        let n: i64 = plant_use::table
            .filter(plant_use::plant_id.eq(&id))
            .count()
            .get_result(&mut conn)
            .unwrap();
        assert_eq!(n, 0, "usos de {usda_id}");
    }
}
