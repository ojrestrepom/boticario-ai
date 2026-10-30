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
        .find(|c| c.name == "Wikipedia en español")
        .expect("la descripción de la lavanda resume Wikipedia");
    assert_eq!(wiki.license, "CC BY-SA 4.0");
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

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn common_names_are_alphabetical_and_spanish_goes_first_on_a_display_name_tie() {
    let repo = open_real();
    for id in ["acorus-calamus", "aleurites-moluccanus"] {
        let plant = plant(&repo, id);
        let rest: Vec<&str> = plant
            .names
            .iter()
            .filter(|n| {
                n.kind == catalog_core::domain::NameKind::Common && n.text != plant.display_name
            })
            .map(|n| n.text.as_str())
            .collect();
        let mut sorted = rest.clone();
        sorted.sort_by_cached_key(|t| catalog_core::normalize::normalize_name(t));
        assert_eq!(rest, sorted, "{id}");
    }
    // Todas las plantas tipo «Sisal»: el `displayName` aparece en `en` y en `es` y el `es` va delante.
    let page = repo
        .list_plants(&ListQuery {
            q: None,
            limit: 5000,
            offset: 0,
        })
        .unwrap();
    let mut ties = 0;
    for p in &page.items {
        let langs: Vec<&str> = p
            .common_names
            .iter()
            .filter(|n| n.text == p.display_name)
            .map(|n| n.language.as_str())
            .collect();
        if langs.contains(&"en") && langs.contains(&"es") {
            ties += 1;
            assert_eq!(p.common_names[0].language, "es", "{}", p.id.0);
        }
    }
    println!("plantas con empate en/es: {ties}");
    assert!(ties > 0);
}

/// Todas las plantas de un objetivo o subárea, recorriendo las páginas de 100.
fn all_goal_plants(
    repo: &SqliteCatalogRepository,
    goal: &str,
    subarea: Option<&str>,
) -> Vec<catalog_core::domain::GoalPlant> {
    use catalog_core::domain::GoalPlantsOutcome;
    let mut items = Vec::new();
    loop {
        let GoalPlantsOutcome::Found(found) = repo
            .list_goal_plants(goal, subarea, 100, items.len() as u32)
            .unwrap()
        else {
            panic!("{goal}/{subarea:?} debería existir");
        };
        let total = found.page.total as usize;
        let empty = found.page.items.is_empty();
        items.extend(found.page.items);
        if items.len() >= total || empty {
            assert_eq!(items.len(), total, "{goal}/{subarea:?}");
            return items;
        }
    }
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn every_goal_returns_plants_and_hides_toxic_and_pending_ones() {
    use diesel::prelude::*;

    let repo = open_real();
    // Plantas que la semilla excluye por toxicidad y filas de `plant_goal` pendientes de revisión, leídas de la base.
    let mut conn = diesel::SqliteConnection::establish(
        repo_root().join("data/build/catalog.db").to_str().unwrap(),
    )
    .unwrap();
    let toxic: Vec<String> = catalog_core::schema::plant_review_flag::table
        .filter(
            catalog_core::schema::plant_review_flag::code.eq("objetivos-omitidos-por-toxicidad"),
        )
        .select(catalog_core::schema::plant_review_flag::plant_id)
        .load(&mut conn)
        .unwrap();
    assert!(!toxic.is_empty());
    let pending: Vec<(String, String)> = catalog_core::schema::plant_goal::table
        .filter(catalog_core::schema::plant_goal::pending_review.eq(true))
        .select((
            catalog_core::schema::plant_goal::goal_id,
            catalog_core::schema::plant_goal::plant_id,
        ))
        .load(&mut conn)
        .unwrap();
    assert!(!pending.is_empty());

    let forbidden = [
        "dosis",
        " mg",
        "mg/",
        "eficaz",
        "eficacia",
        "cura ",
        "curar",
        "garantiza",
    ];
    let goals = repo.list_goals().unwrap();
    assert_eq!(goals.len(), 6);
    for goal in &goals {
        let plants = all_goal_plants(&repo, &goal.id, None);
        assert!(!plants.is_empty(), "{} no tiene plantas", goal.id);
        assert_eq!(plants.len() as u64, goal.plant_count, "{}", goal.id);
        println!(
            "objetivo {}: {} plantas, {} subáreas",
            goal.id,
            goal.plant_count,
            goal.subareas.len()
        );
        for plant in &plants {
            assert!(!toxic.contains(&plant.id.0), "{}: {}", goal.id, plant.id.0);
            assert!(
                !pending.contains(&(goal.id.clone(), plant.id.0.clone())),
                "{}: {} está pendiente de revisión",
                goal.id,
                plant.id.0
            );
            assert!(!plant.areas.is_empty(), "{}: {}", goal.id, plant.id.0);
            for area in &plant.areas {
                let lower = area.to_lowercase();
                assert!(
                    forbidden.iter().all(|w| !lower.contains(w)),
                    "{}: {area}",
                    plant.id.0
                );
            }
        }
        for subarea in &goal.subareas {
            let in_subarea = all_goal_plants(&repo, &goal.id, Some(&subarea.id));
            assert_eq!(
                in_subarea.len() as u64,
                subarea.plant_count,
                "{}",
                subarea.id
            );
            println!("  subárea {}: {} plantas", subarea.id, subarea.plant_count);
        }
    }
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn st_johns_wort_is_not_in_stress_but_its_detail_is_served() {
    let repo = open_real();
    let stress = all_goal_plants(&repo, "relajacion-estres", None);
    assert!(stress.iter().all(|p| p.id.0 != "hypericum-perforatum"));
    let hypericum = plant(&repo, "hypericum-perforatum");
    assert_eq!(hypericum.id.0, "hypericum-perforatum");
    // Sigue en el listado de plantas.
    assert!(ids(&search(&repo, "hypericum perforatum")).contains(&"hypericum-perforatum"));
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn real_goal_results_are_totally_ordered_and_union_counts_once() {
    let repo = open_real();
    let other = all_goal_plants(&repo, "otros-objetivos", None);
    let mut seen: Vec<&str> = other.iter().map(|p| p.id.0.as_str()).collect();
    let before = seen.len();
    seen.sort_unstable();
    seen.dedup();
    assert_eq!(seen.len(), before, "la unión repite plantas");
    for goal in repo.list_goals().unwrap() {
        let plants = all_goal_plants(&repo, &goal.id, None);
        let keys: Vec<(String, String, String)> = plants
            .iter()
            .map(|p| {
                (
                    catalog_core::normalize::normalize_name(&p.display_name),
                    catalog_core::normalize::normalize_name(&p.scientific_name),
                    p.id.0.clone(),
                )
            })
            .collect();
        let mut sorted = keys.clone();
        sorted.sort();
        assert_eq!(keys, sorted, "{}", goal.id);
    }
}

#[test]
#[ignore = "necesita data/build/catalog.db (se genera con `catalog-ingest build`)"]
fn real_glossary_explains_terms_and_credits_their_sources() {
    let repo = open_real();
    let mut explained = 0usize;
    let mut with_wiktionary = 0usize;
    let mut diuretic_checked = false;
    let mut serious_checked = false;
    let mut no_term_checked = false;
    let mut qualified_checked = false;
    let page = repo
        .list_plants(&ListQuery {
            q: None,
            limit: 100,
            offset: 0,
        })
        .unwrap();
    let mut all: Vec<PlantId> = page.items.iter().map(|p| p.id.clone()).collect();
    let mut offset = 100;
    while all.len() < page.total as usize {
        let next = repo
            .list_plants(&ListQuery {
                q: None,
                limit: 100,
                offset,
            })
            .unwrap();
        all.extend(next.items.iter().map(|p| p.id.clone()));
        offset += 100;
    }
    for id in &all {
        let plant = plant(&repo, &id.0);
        let mut served_sources: std::collections::BTreeSet<&str> = Default::default();
        for group in &plant.use_groups {
            if let Some(g) = &group.glossary {
                explained += 1;
                served_sources.insert(g.source_name.as_str());
                assert!(g.url.starts_with("https://") && !g.text.is_empty(), "{g:?}");
                assert!(
                    !group
                        .activity
                        .starts_with("Uso tradicional, sin eficacia demostrada: "),
                    "{group:?}"
                );
                if group.activity == "Diurético" {
                    assert_eq!(g.term, "Diurético");
                    assert_eq!(g.source_name, "Wikcionario");
                    assert!(!g.adapted);
                    assert_eq!(
                        g.text,
                        "Que aumenta o facilita la producción y excreción de orina."
                    );
                    diuretic_checked = true;
                }
                if group.activity.starts_with("Antídoto (") && !qualified_checked {
                    assert_eq!(g.term, "Antídoto");
                    qualified_checked = true;
                }
            } else if group.activity == "Fiebre" && !no_term_checked {
                no_term_checked = true;
            } else if group
                .activity
                .starts_with("Uso tradicional, sin eficacia demostrada: ")
            {
                serious_checked = true;
            }
        }
        // Los créditos del glosario salen solo de explicaciones servidas, y Wikipedia no se repite.
        let has_wiktionary = plant
            .credits
            .iter()
            .any(|c| c.name == "Wikcionario en español");
        assert_eq!(
            has_wiktionary,
            served_sources.contains("Wikcionario"),
            "{}: {:?}",
            plant.id.0,
            plant.credits.iter().map(|c| &c.name).collect::<Vec<_>>()
        );
        if has_wiktionary {
            with_wiktionary += 1;
        }
        if served_sources.contains("Wikipedia") {
            assert_eq!(
                plant
                    .credits
                    .iter()
                    .filter(|c| c.name == "Wikipedia en español")
                    .count(),
                1,
                "{}",
                plant.id.0
            );
        }
        let names: Vec<&str> = plant.credits.iter().map(|c| c.name.as_str()).collect();
        let mut unique = names.clone();
        unique.sort();
        unique.dedup();
        assert_eq!(names.len(), unique.len(), "{}: {names:?}", plant.id.0);
    }
    println!(
        "grupos con explicación={explained} plantas con crédito de Wikcionario={with_wiktionary}"
    );
    assert!(diuretic_checked && no_term_checked && serious_checked && qualified_checked);
    assert!(explained > 0 && with_wiktionary > 0);
    // La lavanda ya trae explicaciones servidas.
    let lavender = plant(&repo, "lavandula-angustifolia");
    assert!(lavender.use_groups.iter().any(|g| g.glossary.is_some()));
}
