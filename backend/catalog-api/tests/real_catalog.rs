//! Prueba manual sobre la base real construida por la ingesta (`data/build/catalog.db`).
//!
//! Está marcada `#[ignore]` para que `cargo test` normal no dependa de ella: se ejecuta con `cargo test -- --ignored`.

use std::path::PathBuf;

use catalog_api::repository::SqliteCatalogRepository;
use catalog_core::domain::{ListQuery, PlantId};
use catalog_core::repository::CatalogRepository;

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn lavender_is_found_in_the_real_catalog() {
    // `CARGO_MANIFEST_DIR` es `backend/catalog-api`: la raíz del repo está dos niveles arriba.
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../data/build/catalog.db");
    if !path.exists() {
        eprintln!(
            "se omite: no existe {}; constrúyela con `catalog-ingest build`",
            path.display()
        );
        return;
    }
    let repo = SqliteCatalogRepository::open(&path).unwrap();

    let page = repo
        .list_plants(&ListQuery {
            q: Some("lavand".to_string()),
            ..ListQuery::default()
        })
        .unwrap();
    assert!(
        page.items
            .iter()
            .any(|p| p.id.0 == "lavandula-angustifolia"),
        "{:?}",
        page.items.iter().map(|p| &p.id.0).collect::<Vec<_>>()
    );

    let plant = repo
        .get_plant(&PlantId("lavandula-angustifolia".to_string()))
        .unwrap()
        .unwrap();
    assert_eq!(plant.uses.len(), 10);
    assert_eq!(plant.parts.len(), 4);
}
