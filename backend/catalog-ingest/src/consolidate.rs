//! Consolidador: une los registros de varias fuentes en un catálogo único con atribución.
//!
//! Todo ocurre en memoria. La salida es independiente del orden en que lleguen las fuentes: se procesan siempre por prioridad y todas las colecciones se guardan en `BTreeMap`/`BTreeSet`, que iteran ordenados por clave.

use std::collections::{BTreeMap, BTreeSet};

use catalog_core::domain::{
    Attributed, NameKind, Part, Plant, PlantId, PlantName, Reference, Source, SourceId, Use,
};
use catalog_core::normalize::{normalize_name, slug};

use crate::adapter::{PlantRecord, SourceRecords};
use crate::error::IngestError;

/// Idioma de los nombres científicos: el latín (`la`), porque la nomenclatura binomial es latina y no pertenece a ningún idioma moderno.
const SCIENTIFIC_LANGUAGE: &str = "la";

/// Lo que aporta una fuente a la consolidación.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceInput {
    /// Metadatos de la fuente.
    pub source: Source,
    /// Prioridad (1 = la más alta).
    pub priority: u32,
    /// Registros normalizados de la fuente.
    pub records: SourceRecords,
}

/// Planta consolidada y los identificadores que le da cada fuente.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConsolidatedPlant {
    /// Planta con su ID público y todos sus datos atribuidos.
    pub plant: Plant,
    /// Identificador de la planta en cada fuente que la aporta (tabla de enlace).
    pub source_plant_ids: BTreeMap<SourceId, String>,
}

/// Catálogo consolidado, listo para escribirse en la base neutral.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Catalog {
    /// Fuentes, ordenadas por id.
    pub sources: Vec<Source>,
    /// Plantas, ordenadas por ID público.
    pub plants: Vec<ConsolidatedPlant>,
    /// Referencias, ordenadas por id.
    pub references: Vec<Attributed<Reference>>,
}

/// Conjunto de fuentes que aportan un dato; el `BTreeSet` evita repetidas y las ordena por id.
type Contributors = BTreeSet<SourceId>;

/// Referencia acumulada: cita y quién la aporta.
struct RefAcc {
    citation: String,
    first_source: SourceId,
    sources: Contributors,
}

/// Planta acumulada mientras se recorren las fuentes.
#[derive(Default)]
struct PlantAcc {
    scientific_name: String,
    family: Option<(String, SourceId)>,
    // Clave de nombre: (rango del tipo, texto, idioma). `NameKind` no es `Ord`, por eso el rango.
    names: BTreeMap<(u8, String, String), Contributors>,
    parts: BTreeMap<String, Contributors>,
    // Clave de uso: (actividad, idioma, id de referencia).
    uses: BTreeMap<(String, String, String), Contributors>,
    source_plant_ids: BTreeMap<SourceId, String>,
}

fn kind_rank(kind: NameKind) -> u8 {
    match kind {
        NameKind::Scientific => 0,
        NameKind::Common => 1,
    }
}

fn kind_from_rank(rank: u8) -> NameKind {
    if rank == 0 {
        NameKind::Scientific
    } else {
        NameKind::Common
    }
}

/// Convierte un mapa dato -> fuentes en la lista atribuida (el orden lo da el mapa).
fn attributed<T>(value: T, sources: Contributors) -> Attributed<T> {
    Attributed {
        value,
        sources: sources.into_iter().collect(),
    }
}

/// Consolida las fuentes en un catálogo.
///
/// Las plantas se unen por nombre científico normalizado. Los datos multivalor se suman conservando la fuente de cada uno; en los de valor único gana la fuente de mayor prioridad.
pub fn consolidate(mut inputs: Vec<SourceInput>) -> Result<Catalog, IngestError> {
    // Clave de orden total: prioridad y, a igualdad, id. Así el orden de entrada no importa.
    inputs.sort_by(|a, b| (a.priority, &a.source.id).cmp(&(b.priority, &b.source.id)));

    let references = collect_references(&inputs)?;

    let mut accs: BTreeMap<String, PlantAcc> = BTreeMap::new();
    for input in &inputs {
        let ref_ids: BTreeSet<&str> = input
            .records
            .references
            .iter()
            .map(|r| r.id.as_str())
            .collect();
        for record in &input.records.plants {
            add_plant(&mut accs, &input.source.id, record, &ref_ids)?;
        }
    }

    let plants = build_plants(accs, &references)?;

    let mut sources: Vec<Source> = inputs.into_iter().map(|i| i.source).collect();
    sources.sort_by(|a, b| a.id.cmp(&b.id));

    let references = references
        .into_iter()
        .map(|(id, acc)| {
            attributed(
                Reference {
                    id,
                    citation: acc.citation,
                },
                acc.sources,
            )
        })
        .collect();

    Ok(Catalog {
        sources,
        plants,
        references,
    })
}

/// Une las referencias de todas las fuentes por id; la misma cita se suma, una cita distinta es un error.
fn collect_references(inputs: &[SourceInput]) -> Result<BTreeMap<String, RefAcc>, IngestError> {
    let mut refs: BTreeMap<String, RefAcc> = BTreeMap::new();
    for input in inputs {
        let source = &input.source.id;
        for r in &input.records.references {
            match refs.get_mut(&r.id) {
                Some(acc) if acc.citation == r.citation => {
                    acc.sources.insert(source.clone());
                }
                Some(acc) => {
                    return Err(IngestError::ConflictingReference {
                        id: r.id.clone(),
                        first_source: acc.first_source.0.clone(),
                        second_source: source.0.clone(),
                    });
                }
                None => {
                    refs.insert(
                        r.id.clone(),
                        RefAcc {
                            citation: r.citation.clone(),
                            first_source: source.clone(),
                            sources: BTreeSet::from([source.clone()]),
                        },
                    );
                }
            }
        }
    }
    Ok(refs)
}

/// Suma una planta de una fuente a la acumulada con su misma identidad.
fn add_plant(
    accs: &mut BTreeMap<String, PlantAcc>,
    source: &SourceId,
    record: &PlantRecord,
    source_refs: &BTreeSet<&str>,
) -> Result<(), IngestError> {
    let identity = normalize_name(&record.scientific_name);
    // Una identidad sin letras ni dígitos ASCII daría un ID público vacío.
    if slug(&identity).is_empty() {
        return Err(IngestError::EmptyScientificName {
            source: source.0.clone(),
            source_plant_id: record.source_plant_id.clone(),
        });
    }
    let acc = accs.entry(identity.clone()).or_default();

    if let Some(first) = acc.source_plant_ids.get(source) {
        return Err(IngestError::DuplicateIdentity {
            source: source.0.clone(),
            identity,
            first_source_plant_id: first.clone(),
            second_source_plant_id: record.source_plant_id.clone(),
        });
    }
    acc.source_plant_ids
        .insert(source.clone(), record.source_plant_id.clone());

    // Las fuentes llegan por prioridad: el primer valor que aparece es el de mayor prioridad.
    let scientific = record.scientific_name.trim();
    if acc.scientific_name.is_empty() {
        acc.scientific_name = scientific.to_string();
    }
    if acc.family.is_none()
        && let Some(family) = record.family.as_deref().map(str::trim)
        && !family.is_empty()
    {
        acc.family = Some((family.to_string(), source.clone()));
    }

    let mut add_name = |kind: NameKind, text: &str, language: &str| {
        acc.names
            .entry((kind_rank(kind), text.to_string(), language.to_string()))
            .or_default()
            .insert(source.clone());
    };
    add_name(NameKind::Scientific, scientific, SCIENTIFIC_LANGUAGE);
    for name in &record.common_names {
        add_name(NameKind::Common, &name.text, &name.language);
    }

    for part in &record.parts {
        acc.parts
            .entry(part.clone())
            .or_default()
            .insert(source.clone());
    }

    for u in &record.uses {
        // La referencia debe existir en la misma fuente que el uso.
        if !source_refs.contains(u.reference_id.as_str()) {
            return Err(IngestError::UnresolvedReference {
                source: source.0.clone(),
                source_plant_id: record.source_plant_id.clone(),
                reference_id: u.reference_id.clone(),
            });
        }
        acc.uses
            .entry((
                u.activity.clone(),
                u.language.clone(),
                u.reference_id.clone(),
            ))
            .or_default()
            .insert(source.clone());
    }
    Ok(())
}

/// Convierte los acumuladores en plantas con ID público, detectando colisiones de slug.
fn build_plants(
    accs: BTreeMap<String, PlantAcc>,
    references: &BTreeMap<String, RefAcc>,
) -> Result<Vec<ConsolidatedPlant>, IngestError> {
    let mut slugs: BTreeMap<String, String> = BTreeMap::new();
    let mut plants = Vec::new();
    for (identity, acc) in accs {
        let id = slug(&identity);
        if let Some(first) = slugs.get(&id) {
            return Err(IngestError::SlugCollision {
                slug: id,
                first_identity: first.clone(),
                second_identity: identity,
            });
        }
        slugs.insert(id.clone(), identity);

        let names = acc
            .names
            .into_iter()
            .map(|((rank, text, language), sources)| {
                let name = PlantName {
                    text,
                    kind: kind_from_rank(rank),
                    language,
                };
                attributed(name, sources)
            })
            .collect();
        let parts = acc
            .parts
            .into_iter()
            .map(|(label, sources)| attributed(Part { label }, sources))
            .collect();
        let uses = acc
            .uses
            .into_iter()
            .map(|((activity, language, reference_id), sources)| {
                // `add_plant` ya garantizó que la referencia existe; la cita es única por id.
                let citation = references[&reference_id].citation.clone();
                let reference = Reference {
                    id: reference_id,
                    citation,
                };
                attributed(
                    Use {
                        activity,
                        language,
                        reference,
                    },
                    sources,
                )
            })
            .collect();
        let family = acc.family.map(|(value, source)| Attributed {
            value,
            sources: vec![source],
        });

        plants.push(ConsolidatedPlant {
            plant: Plant {
                id: PlantId(id),
                scientific_name: acc.scientific_name,
                family,
                names,
                parts,
                uses,
            },
            source_plant_ids: acc.source_plant_ids,
        });
    }
    // Los slugs no colisionan, pero su orden puede diferir del de las identidades: se reordena por ID.
    plants.sort_by(|a, b| a.plant.id.cmp(&b.plant.id));
    Ok(plants)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{
        alpha_records, beta_records, fixture_source, plant, reference, use_rec,
    };

    fn input(id: &str, priority: u32, records: SourceRecords) -> SourceInput {
        SourceInput {
            source: fixture_source(id),
            priority,
            records,
        }
    }

    fn two_sources() -> Vec<SourceInput> {
        vec![
            input("alpha", 1, alpha_records()),
            input("beta", 2, beta_records()),
        ]
    }

    fn sid(id: &str) -> SourceId {
        SourceId(id.to_string())
    }

    fn find_plant<'a>(catalog: &'a Catalog, id: &str) -> &'a ConsolidatedPlant {
        catalog.plants.iter().find(|p| p.plant.id.0 == id).unwrap()
    }

    #[test]
    fn merges_shared_plant_with_attribution() {
        let catalog = consolidate(two_sources()).unwrap();
        assert_eq!(catalog.plants.len(), 2);
        let lavender = find_plant(&catalog, "lavandula-angustifolia");
        let plant = &lavender.plant;
        assert_eq!(plant.scientific_name, "Lavandula angustifolia");
        let family = plant.family.as_ref().unwrap();
        assert_eq!(family.value, "Lamiaceae");
        assert_eq!(family.sources, [sid("alpha")]);
        assert_eq!(lavender.source_plant_ids[&sid("alpha")], "A1");
        assert_eq!(lavender.source_plant_ids[&sid("beta")], "B7");

        let sources_of = |text: &str, language: &str| {
            plant
                .names
                .iter()
                .find(|n| n.value.text == text && n.value.language == language)
                .unwrap_or_else(|| panic!("falta el nombre {text}"))
                .sources
                .clone()
        };
        assert_eq!(sources_of("lavender", "en"), [sid("alpha"), sid("beta")]);
        assert_eq!(sources_of("English lavender", "en"), [sid("alpha")]);
        assert_eq!(sources_of("lavanda", "es"), [sid("beta")]);
        // Cada fuente aporta su ortografía del nombre científico, en latín.
        assert_eq!(sources_of("Lavandula angustifolia", "la"), [sid("alpha")]);
        assert_eq!(sources_of("LAVANDULA  angustifolia", "la"), [sid("beta")]);
        assert_eq!(plant.names.len(), 5);

        let parts: Vec<_> = plant
            .parts
            .iter()
            .map(|p| (p.value.label.as_str(), p.sources.len()))
            .collect();
        assert_eq!(parts, [("Flower", 2), ("Leaf", 1), ("Root", 1)]);

        let uses: Vec<_> = plant
            .uses
            .iter()
            .map(|u| {
                (
                    u.value.activity.as_str(),
                    u.value.reference.id.as_str(),
                    u.sources.len(),
                )
            })
            .collect();
        assert_eq!(
            uses,
            [
                ("Antiseptic", "r2", 1),
                ("Insecticide", "r3", 1),
                ("Sedative", "r1", 2)
            ]
        );
        assert_eq!(plant.uses[2].value.reference.citation, "Cita uno");

        let refs: Vec<_> = catalog
            .references
            .iter()
            .map(|r| (r.value.id.as_str(), r.sources.len()))
            .collect();
        assert_eq!(refs, [("r1", 2), ("r2", 1), ("r3", 1)]);
    }

    #[test]
    fn single_source_plant_keeps_its_attribution() {
        let catalog = consolidate(two_sources()).unwrap();
        let chamomile = find_plant(&catalog, "matricaria-chamomilla");
        let plant = &chamomile.plant;
        assert_eq!(plant.family.as_ref().unwrap().sources, [sid("beta")]);
        assert!(plant.names.iter().all(|n| n.sources == [sid("beta")]));
        assert!(plant.parts.iter().all(|p| p.sources == [sid("beta")]));
        assert!(plant.uses.iter().all(|u| u.sources == [sid("beta")]));
        assert_eq!(chamomile.source_plant_ids.len(), 1);
    }

    #[test]
    fn lower_priority_fills_missing_family() {
        let mut inputs = two_sources();
        inputs[0].records.plants[0].family = None;
        let catalog = consolidate(inputs).unwrap();
        let family = find_plant(&catalog, "lavandula-angustifolia")
            .plant
            .family
            .clone()
            .unwrap();
        assert_eq!(family.value, "Labiatae");
        assert_eq!(family.sources, [sid("beta")]);
    }

    #[test]
    fn no_family_is_none() {
        let inputs = vec![input(
            "alpha",
            1,
            SourceRecords {
                plants: vec![plant("A1", "Aloe vera")],
                references: vec![],
            },
        )];
        let catalog = consolidate(inputs).unwrap();
        assert_eq!(catalog.plants[0].plant.family, None);
    }

    #[test]
    fn input_order_does_not_matter() {
        let forward = consolidate(two_sources()).unwrap();
        let mut reversed = two_sources();
        reversed.reverse();
        assert_eq!(consolidate(reversed).unwrap(), forward);
        let ids: Vec<_> = forward.sources.iter().map(|s| s.id.0.as_str()).collect();
        assert_eq!(ids, ["alpha", "beta"]);
    }

    #[test]
    fn priority_decides_not_input_position() {
        let mut inputs = two_sources();
        inputs[0].priority = 2;
        inputs[1].priority = 1;
        let catalog = consolidate(inputs).unwrap();
        let p = &find_plant(&catalog, "lavandula-angustifolia").plant;
        assert_eq!(p.family.as_ref().unwrap().value, "Labiatae");
        assert_eq!(p.scientific_name, "LAVANDULA  angustifolia");
    }

    #[test]
    fn duplicate_identity_within_source_names_both_records() {
        let mut inputs = two_sources();
        inputs[0]
            .records
            .plants
            .push(plant("A2", "  lavandula   ANGUSTIFOLIA"));
        let err = consolidate(inputs).unwrap_err();
        assert_eq!(
            err,
            IngestError::DuplicateIdentity {
                source: "alpha".to_string(),
                identity: "lavandula angustifolia".to_string(),
                first_source_plant_id: "A1".to_string(),
                second_source_plant_id: "A2".to_string(),
            }
        );
        let msg = err.to_string();
        assert!(msg.contains("alpha") && msg.contains("A1") && msg.contains("A2"));
    }

    #[test]
    fn slugs_are_stable_across_runs() {
        let first = consolidate(two_sources()).unwrap();
        let second = consolidate(two_sources()).unwrap();
        let ids = |c: &Catalog| -> Vec<String> {
            c.plants.iter().map(|p| p.plant.id.0.clone()).collect()
        };
        assert_eq!(ids(&first), ids(&second));
        assert_eq!(
            ids(&first),
            ["lavandula-angustifolia", "matricaria-chamomilla"]
        );
    }

    #[test]
    fn slug_collision_names_both_identities() {
        let inputs = vec![input(
            "alpha",
            1,
            SourceRecords {
                plants: vec![
                    plant("A1", "Mentha x piperita"),
                    plant("A2", "Mentha-x piperita"),
                ],
                references: vec![],
            },
        )];
        let err = consolidate(inputs).unwrap_err();
        assert_eq!(
            err,
            IngestError::SlugCollision {
                slug: "mentha-x-piperita".to_string(),
                first_identity: "mentha x piperita".to_string(),
                second_identity: "mentha-x piperita".to_string(),
            }
        );
    }

    #[test]
    fn unresolved_reference_is_reported() {
        let mut inputs = two_sources();
        // `r3` existe en beta, pero no en alpha: cada uso se resuelve en su propia fuente.
        inputs[0].records.plants[0]
            .uses
            .push(use_rec("Tonic", "en", "r3"));
        let err = consolidate(inputs).unwrap_err();
        assert_eq!(
            err,
            IngestError::UnresolvedReference {
                source: "alpha".to_string(),
                source_plant_id: "A1".to_string(),
                reference_id: "r3".to_string(),
            }
        );
    }

    #[test]
    fn conflicting_reference_is_reported() {
        let mut inputs = two_sources();
        inputs[1].records.references[0] = reference("r1", "Otra cita");
        let err = consolidate(inputs).unwrap_err();
        assert_eq!(
            err,
            IngestError::ConflictingReference {
                id: "r1".to_string(),
                first_source: "alpha".to_string(),
                second_source: "beta".to_string(),
            }
        );
    }

    #[test]
    fn display_of_new_errors_names_the_culprits() {
        let dup = IngestError::DuplicateIdentity {
            source: "alpha".to_string(),
            identity: "aloe vera".to_string(),
            first_source_plant_id: "A1".to_string(),
            second_source_plant_id: "A2".to_string(),
        };
        assert_eq!(
            dup.to_string(),
            "la fuente \"alpha\" repite la identidad \"aloe vera\": registros \"A1\" y \"A2\""
        );
        let unknown = IngestError::UnknownSource {
            id: "gamma".to_string(),
        };
        assert!(unknown.to_string().contains("\"gamma\""));
    }

    #[test]
    fn empty_scientific_name_is_rejected() {
        for name in ["", "   ", "!!!"] {
            let inputs = vec![input(
                "alpha",
                1,
                SourceRecords {
                    plants: vec![plant("A9", name)],
                    references: vec![],
                },
            )];
            assert_eq!(
                consolidate(inputs).unwrap_err(),
                IngestError::EmptyScientificName {
                    source: "alpha".to_string(),
                    source_plant_id: "A9".to_string(),
                },
                "nombre {name:?}"
            );
        }
    }
}
