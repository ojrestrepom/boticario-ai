//! Pruebas manuales sobre la base real construida desde la semilla (`data/build/catalog.db`).
//!
//! Están marcadas `#[ignore]` para que `cargo test` normal no dependa de ellas: se ejecutan con `cargo test -p catalog-api --locked -- --ignored`.
//! No fijan cuántos usos, grupos u objetivos tiene una planta: la semilla puede cambiar la curación.

use std::path::PathBuf;

use catalog_api::repository::SqliteCatalogRepository;
use catalog_core::domain::{ListQuery, Page, Plant, PlantId, PlantSummary};
use catalog_core::repository::CatalogRepository;

/// Raíz del repositorio: `CARGO_MANIFEST_DIR` es `backend/catalog-api`, así que está dos niveles arriba.
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn open_real() -> SqliteCatalogRepository {
    let path = repo_root().join("data/build/catalog.db");
    // Un test pedido a propósito con `--ignored` no debe pasar en silencio si falta la base.
    if !path.exists() {
        panic!(
            "falta data/build/catalog.db: ejecuta `catalog-ingest build` ({})",
            path.display()
        );
    }
    SqliteCatalogRepository::open(&path).unwrap()
}

fn plant(repo: &SqliteCatalogRepository, id: &str) -> Plant {
    repo.get_plant(&PlantId(id.to_string()))
        .unwrap()
        .unwrap_or_else(|| panic!("la planta {id} debería existir"))
}

fn search(repo: &SqliteCatalogRepository, q: &str) -> Page<PlantSummary> {
    repo.list_plants(&ListQuery {
        q: Some(q.to_string()),
        limit: 100,
        offset: 0,
    })
    .unwrap()
}

fn ids(page: &Page<PlantSummary>) -> Vec<&str> {
    page.items.iter().map(|p| p.id.0.as_str()).collect()
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn lavender_is_found_and_has_the_consolidated_content() {
    let repo = open_real();

    let page = search(&repo, "lavand");
    assert!(
        ids(&page).contains(&"lavandula-angustifolia"),
        "{:?}",
        ids(&page)
    );

    let lavender = plant(&repo, "lavandula-angustifolia");
    // No se fija cuántos: la semilla puede cambiar la curación.
    assert!(!lavender.uses.is_empty(), "la lavanda debe tener usos");
    assert!(!lavender.parts.is_empty(), "la lavanda debe tener partes");
    // El nombre para mostrar es el de la semilla y va primero entre los nombres comunes.
    assert_eq!(lavender.display_name, "Lavanda");
    let first_common = lavender
        .names
        .iter()
        .find(|n| n.kind == catalog_core::domain::NameKind::Common)
        .map(|n| n.text.as_str());
    assert_eq!(first_common, Some("Lavanda"));
    assert!(
        !lavender.use_groups.is_empty(),
        "la lavanda debe tener grupos de uso"
    );
    for group in &lavender.use_groups {
        assert!(group.count > 0 && !group.references.is_empty(), "{group:?}");
    }
    assert!(lavender.description.is_some() && lavender.origin.is_some());
    assert_eq!(lavender.oil_type.as_deref(), Some("Esencial"));
    assert!(
        !lavender.credits.is_empty(),
        "la lavanda debe tener créditos"
    );
    // Créditos por nombre, sin repetir, con licencia y atribución; el de Wikipedia (descripción) lleva la URL de su licencia y un artículo.
    let names: Vec<&str> = lavender.credits.iter().map(|c| c.name.as_str()).collect();
    let mut sorted = names.clone();
    sorted.sort();
    sorted.dedup();
    assert_eq!(names, sorted);
    let wiki = lavender
        .credits
        .iter()
        .find(|c| c.license == "CC BY-SA 4.0")
        .expect("la descripción de la lavanda resume Wikipedia");
    assert_eq!(
        wiki.license_url.as_deref(),
        Some("https://creativecommons.org/licenses/by-sa/4.0/")
    );
    assert!(
        wiki.url
            .as_deref()
            .is_some_and(|u| u.contains("/wiki/Lavandula_angustifolia")),
        "{wiki:?}"
    );
    // Los objetivos son coherentes: nombre, área, tipo de respaldo y al menos una referencia, y ninguno está pendiente.
    assert!(
        !lavender.goals.is_empty(),
        "la lavanda debe tener objetivos de la EMA"
    );
    for goal in &lavender.goals {
        assert!(
            !goal.name.is_empty()
                && !goal.area.is_empty()
                && !goal.evidence.is_empty()
                && !goal.references.is_empty(),
            "{goal:?}"
        );
        assert_eq!(
            goal.subarea.is_some(),
            goal.id == "otros-objetivos",
            "{goal:?}"
        );
    }
    assert!(lavender.safety.is_some());
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn pending_goal_of_st_johns_wort_is_not_served() {
    let repo = open_real();
    let hypericum = plant(&repo, "hypericum-perforatum");
    assert!(
        hypericum.goals.iter().all(|g| g.id != "relajacion-estres"),
        "{:?}",
        hypericum.goals.iter().map(|g| &g.id).collect::<Vec<_>>()
    );
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn eucalyptus_has_safety_without_level() {
    let repo = open_real();
    let safety = plant(&repo, "eucalyptus-globulus").safety.unwrap();
    assert_eq!(safety.level, None);
    assert!(!safety.text.is_empty() && !safety.references.is_empty());
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn a_known_alias_resolves_to_the_canonical_plant() {
    let repo = open_real();
    let by_alias = plant(&repo, "rosmarinus-officinalis");
    assert_eq!(by_alias.id.0, "salvia-rosmarinus");
    assert_eq!(by_alias, plant(&repo, "salvia-rosmarinus"));
    assert_eq!(
        repo.get_plant(&PlantId("no-existe-esta-planta".to_string()))
            .unwrap(),
        None
    );
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn search_finds_previous_identifiers_without_duplicates() {
    let repo = open_real();
    // Alias que no es nombre de ninguna planta.
    assert_eq!(
        ids(&search(&repo, "matricaria recutita")),
        ["matricaria-chamomilla"]
    );
    // Nombre sinónimo y alias a la vez: cada planta aparece y cuenta una sola vez.
    let rosemary = search(&repo, "rosmarinus officinalis");
    let found = ids(&rosemary);
    assert!(found.contains(&"salvia-rosmarinus"), "{found:?}");
    let mut unique = found.clone();
    unique.sort_unstable();
    unique.dedup();
    assert_eq!(unique.len(), found.len(), "{found:?}");
    assert_eq!(rosemary.total as usize, found.len());
    // Límite conocido de la subcadena: «mentha piperita» no es subcadena de ningún nombre ni alias.
    let none = search(&repo, "mentha piperita");
    assert_eq!((none.items.len(), none.total), (0, 0));
    assert_eq!(
        ids(&search(&repo, "mentha x piperita")),
        ["mentha-x-piperita"]
    );
}

/// Mide los 357 nombres anteriores que la QA del cambio 1 (API-04) no encontraba: con la búsqueda por alias deben encontrar su planta nueva.
#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn the_357_previous_names_find_their_new_plant() {
    let repo = open_real();
    let tsv = repo_root().join(
        "openspec/changes/archive/2026-10-26-consolidate-catalog-seed/qa/evidence/api/API-04-old-names-not-found.tsv",
    );
    let text = std::fs::read_to_string(&tsv).unwrap_or_else(|e| panic!("{}: {e}", tsv.display()));
    let mut total = 0;
    let mut recovered = 0;
    let mut missing = Vec::new();
    for line in text.lines().skip(1).filter(|l| !l.trim().is_empty()) {
        let cols: Vec<&str> = line.split('\t').collect();
        let (name, new_id) = (cols[1], cols[2]);
        total += 1;
        let page = search(&repo, name);
        if ids(&page).contains(&new_id) {
            recovered += 1;
        } else {
            missing.push(format!("{name} -> {new_id}"));
        }
    }
    println!("nombres anteriores recuperados: {recovered} de {total}");
    assert_eq!(total, 357);
    assert!(
        missing.is_empty(),
        "{recovered} de {total}; faltan {missing:#?}"
    );
}
