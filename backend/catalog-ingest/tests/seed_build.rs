//! Pruebas de la construcción de `catalog.db` desde la semilla de fixtures (`tests/fixtures/seed/`).
//!
//! Las alteraciones de datos se hacen sobre la semilla ya leída (en memoria), para no tener que volver a sellar el manifiesto; los errores que detecta la lectura (objetivo desconocido, nivel de seguridad inválido) se prueban de punta a punta sobre una copia del directorio.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use catalog_ingest::hash::content_hash;
use catalog_ingest::seed::{Seed, load_seed};
use catalog_ingest::seed_build::{BuildError, build_from_dir, build_seed};
use rusqlite::{Connection, OpenFlags};

fn fixture() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/seed")
}

fn copy_dir(from: &Path, to: &Path) {
    fs::create_dir_all(to).unwrap();
    for entry in fs::read_dir(from).unwrap() {
        let entry = entry.unwrap();
        let target = to.join(entry.file_name());
        if entry.path().is_dir() {
            copy_dir(&entry.path(), &target);
        } else {
            fs::copy(entry.path(), target).unwrap();
        }
    }
}

fn seed() -> Seed {
    load_seed(&fixture()).unwrap()
}

fn plant<'a>(seed: &'a mut Seed, id: &str) -> &'a mut catalog_ingest::seed::PlantRecord {
    seed.plants.iter_mut().find(|p| p.id == id).unwrap()
}

/// Construye la base y la abre en solo lectura con `rusqlite`.
fn built(seed: &Seed) -> (tempfile::TempDir, PathBuf, Connection) {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("build/catalog.db");
    build_seed(seed, &out).unwrap();
    let conn = Connection::open_with_flags(&out, OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
    (dir, out, conn)
}

fn count(conn: &Connection, sql: &str) -> i64 {
    conn.query_row(sql, [], |r| r.get(0)).unwrap()
}

fn strings(conn: &Connection, sql: &str) -> Vec<String> {
    let mut stmt = conn.prepare(sql).unwrap();
    stmt.query_map([], |r| r.get::<_, String>(0))
        .unwrap()
        .map(Result::unwrap)
        .collect()
}

/// La construcción falla con un error que nombra la planta y no deja ni base ni temporal.
fn assert_fails_naming(seed: &Seed, plant: &str, extra: &str) -> BuildError {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("catalog.db");
    let err = build_seed(seed, &out).unwrap_err();
    let msg = err.to_string();
    assert!(msg.contains(plant), "no nombra la planta {plant}: {msg}");
    assert!(msg.contains(extra), "no contiene «{extra}»: {msg}");
    assert!(!out.exists(), "quedó una base en el destino");
    assert!(
        !dir.path().join("catalog.db.tmp").exists(),
        "quedó el temporal"
    );
    err
}

// ---- Tarea 7.3: mapeo ----

#[test]
fn builds_without_network_and_maps_the_api_tables() {
    let seed = seed();
    let (_dir, _out, conn) = built(&seed);
    assert_eq!(count(&conn, "SELECT COUNT(*) FROM plant"), 3);
    assert_eq!(
        strings(
            &conn,
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ),
        ["2"]
    );

    // Científico y sinónimos en `la`; comunes con su idioma.
    let calendula = seed
        .plants
        .iter()
        .find(|p| p.id == "calendula-officinalis")
        .unwrap();
    let scientific = strings(
        &conn,
        "SELECT text FROM plant_name WHERE plant_id = 'calendula-officinalis' AND kind = 'scientific' AND language = 'la' ORDER BY id",
    );
    let mut expected = vec![calendula.scientific_name.name.clone()];
    expected.extend(calendula.synonyms.iter().map(|s| s.name.clone()));
    assert_eq!(scientific, expected);
    let commons: BTreeSet<String> = strings(
        &conn,
        "SELECT text || '|' || language FROM plant_name WHERE plant_id = 'calendula-officinalis' AND kind = 'common'",
    )
    .into_iter()
    .collect();
    for c in &calendula.common_names {
        assert!(
            commons.contains(&format!("{}|{}", c.text, c.language)),
            "{}",
            c.text
        );
    }

    // Partes, familia y scientific_name_normalized.
    assert_eq!(
        strings(
            &conn,
            "SELECT label FROM plant_part WHERE plant_id = 'calendula-officinalis'"
        ),
        calendula
            .parts_used
            .iter()
            .map(|p| p.value.clone())
            .collect::<Vec<_>>()
    );
    assert_eq!(
        strings(
            &conn,
            "SELECT family || '|' || family_source_id FROM plant WHERE id = 'calendula-officinalis'"
        ),
        [format!(
            "{}|{}",
            calendula.family.as_ref().unwrap().value,
            calendula.refs[&calendula.scientific_name.refs[0]].dataset
        )]
    );
}

#[test]
fn one_use_per_resolved_reference_of_each_served_group() {
    let seed = seed();
    let (_dir, _out, conn) = built(&seed);
    for p in &seed.plants {
        let mut pairs = BTreeSet::new();
        for g in p.traditional_uses.iter().filter(|g| !g.pending_review) {
            for c in &g.citations {
                if let Some(r) = &c.reference {
                    pairs.insert((g.activity.clone(), r.clone()));
                }
            }
        }
        let rows: BTreeSet<(String, String)> = {
            let mut stmt = conn
                .prepare("SELECT activity, reference_id FROM plant_use WHERE plant_id = ?1 AND language = 'es'")
                .unwrap();
            stmt.query_map([&p.id], |r| Ok((r.get(0)?, r.get(1)?)))
                .unwrap()
                .map(Result::unwrap)
                .collect()
        };
        assert_eq!(rows, pairs, "{}", p.id);
        let total: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM plant_use WHERE plant_id = ?1",
                [&p.id],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(total as usize, pairs.len(), "{}", p.id);
    }
    // Cada uso y cada nombre tiene su atribución.
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_use u WHERE NOT EXISTS (SELECT 1 FROM plant_use_source s WHERE s.plant_use_id = u.id)"
        ),
        0
    );
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_name n WHERE NOT EXISTS (SELECT 1 FROM plant_name_source s WHERE s.plant_name_id = n.id)"
        ),
        0
    );
}

#[test]
fn display_name_is_in_the_profile_and_as_a_common_name() {
    let seed = seed();
    let (_dir, _out, conn) = built(&seed);
    for p in &seed.plants {
        let display: Option<String> = conn
            .query_row(
                "SELECT display_name FROM plant_profile WHERE plant_id = ?1",
                [&p.id],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(
            display,
            p.display_name.as_ref().map(|d| d.value.clone()),
            "{}",
            p.id
        );
        if let Some(d) = &p.display_name {
            let found = count(
                &conn,
                &format!(
                    "SELECT COUNT(*) FROM plant_name WHERE plant_id = '{}' AND kind = 'common' AND text = '{}' AND language = '{}'",
                    p.id,
                    d.value.replace('\'', "''"),
                    d.language
                ),
            );
            assert_eq!(found, 1, "{}", p.id);
        }
    }
    // «Lavanda» no es el primer nombre común por orden alfabético de la API («lavanda» va antes por id), así que se lee del perfil.
    let first_alpha = strings(
        &conn,
        "SELECT text FROM plant_name WHERE plant_id = 'lavandula-angustifolia' AND kind = 'common' ORDER BY text, language LIMIT 1",
    );
    let display = strings(
        &conn,
        "SELECT display_name FROM plant_profile WHERE plant_id = 'lavandula-angustifolia'",
    );
    assert_eq!(display, ["Lavanda"]);
    assert_ne!(
        first_alpha, display,
        "el orden de plant_name no es la fuente de verdad"
    );
}

#[test]
fn goal_catalog_is_loaded_and_plant_goals_point_to_it() {
    let seed = seed();
    let (_dir, _out, conn) = built(&seed);
    assert_eq!(
        count(&conn, "SELECT COUNT(*) FROM goal"),
        seed.goals.goals.len() as i64
    );
    assert_eq!(
        count(&conn, "SELECT COUNT(*) FROM goal_subarea"),
        seed.goals.subareas.len() as i64
    );
    let first = &seed.goals.goals[0];
    assert_eq!(
        strings(
            &conn,
            &format!(
                "SELECT label || '|' || position FROM goal WHERE id = '{}'",
                first.id
            )
        ),
        [format!("{}|{}", first.label, first.position)]
    );
    let sub = &seed.goals.subareas[0];
    assert_eq!(
        strings(
            &conn,
            &format!(
                "SELECT goal_id || '|' || label || '|' || position FROM goal_subarea WHERE id = '{}'",
                sub.id
            )
        ),
        [format!("{}|{}|{}", sub.goal_id, sub.label, sub.position)]
    );
    let expected: usize = seed.plants.iter().map(|p| p.goals.len()).sum();
    assert_eq!(
        count(&conn, "SELECT COUNT(*) FROM plant_goal"),
        expected as i64
    );
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_goal g JOIN goal ON goal.id = g.goal_id"
        ),
        expected as i64
    );
    assert_eq!(
        strings(
            &conn,
            "SELECT goal_id || '|' || COALESCE(subarea_id, '-') FROM plant_goal WHERE plant_id = 'calendula-officinalis' ORDER BY position"
        ),
        ["otros-objetivos|boca-y-garganta", "cuidado-de-la-piel|-"]
    );
    // Cada objetivo trae sus referencias.
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_goal g WHERE NOT EXISTS (SELECT 1 FROM plant_goal_ref r WHERE r.plant_goal_id = g.id)"
        ),
        0
    );
}

#[test]
fn pending_goal_is_stored_with_its_review_flag() {
    let mut seed = seed();
    let lav = plant(&mut seed, "lavandula-angustifolia");
    lav.goals[1].pending_review = true;
    lav.review_flags.push(catalog_ingest::seed::ReviewFlag {
        code: "interacciones-graves-estres".to_string(),
        target: "goals.relajacion-estres".to_string(),
        message: "Interacciones graves.".to_string(),
    });
    let (_dir, _out, conn) = built(&seed);
    assert_eq!(
        strings(
            &conn,
            "SELECT goal_id || '|' || pending_review FROM plant_goal WHERE plant_id = 'lavandula-angustifolia' ORDER BY position"
        ),
        ["mejorar-el-sueno|0", "relajacion-estres|1"]
    );
    assert_eq!(
        strings(
            &conn,
            "SELECT code || '|' || target || '|' || message FROM plant_review_flag WHERE plant_id = 'lavandula-angustifolia'"
        ),
        ["interacciones-graves-estres|goals.relajacion-estres|Interacciones graves."]
    );
}

#[test]
fn unresolved_citation_is_stored_but_not_served_as_a_use() {
    let seed = seed();
    let (_dir, _out, conn) = built(&seed);
    // «Estimulante» de la caléndula tiene una cita resuelta y dos sin resolver («Uph», «Woi.Syria»).
    assert_eq!(
        strings(
            &conn,
            "SELECT r.key || '|' || r.resolved || '|' || COALESCE(r.reference_id, 'NULL') || '|' || r.text \
             FROM plant_use_group_ref r JOIN plant_use_group g ON g.id = r.use_group_id \
             WHERE g.plant_id = 'calendula-officinalis' AND g.activity = 'Estimulante' ORDER BY r.position"
        ),
        [
            "Steinmetz|1|usda_reference:Steinmetz|Steinmetz, E.F. 1957. codex Vegetabilis. Published by the author, Amsterdam.",
            "Uph|0|NULL|Uph (sin resolver)",
            "Woi.Syria|0|NULL|Woi.Syria (sin resolver)"
        ]
    );
    // El grupo se sirve por su cita resuelta, no por las otras.
    assert_eq!(
        strings(
            &conn,
            "SELECT reference_id FROM plant_use WHERE plant_id = 'calendula-officinalis' AND activity = 'Estimulante'"
        ),
        ["usda_reference:Steinmetz"]
    );
    assert!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_use WHERE reference_id NOT IN (SELECT id FROM reference)"
        ) == 0
    );
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_use_group_ref WHERE resolved = 0 AND reference_id IS NOT NULL"
        ),
        0
    );
}

#[test]
fn pending_group_generates_no_api_uses() {
    let mut seed = seed();
    let lav = plant(&mut seed, "lavandula-angustifolia");
    let activity = lav.traditional_uses[0].activity.clone();
    for c in &mut lav.traditional_uses[0].citations {
        c.text = format!("{} (sin resolver)", c.key);
        c.reference = None;
    }
    lav.traditional_uses[0].pending_review = true;
    lav.review_flags.push(catalog_ingest::seed::ReviewFlag {
        code: "cita-sin-resolver".to_string(),
        target: "traditionalUses[0]".to_string(),
        message: "Sin citas resueltas.".to_string(),
    });
    let (_dir, _out, conn) = built(&seed);
    assert_eq!(
        strings(
            &conn,
            &format!(
                "SELECT CAST(pending_review AS TEXT) FROM plant_use_group WHERE plant_id = 'lavandula-angustifolia' AND activity = '{activity}'"
            )
        ),
        ["1"]
    );
    assert_eq!(
        count(
            &conn,
            &format!(
                "SELECT COUNT(*) FROM plant_use WHERE plant_id = 'lavandula-angustifolia' AND activity = '{activity}'"
            )
        ),
        0
    );
    assert!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_use_group_ref r JOIN plant_use_group g ON g.id = r.use_group_id WHERE g.plant_id = 'lavandula-angustifolia' AND g.position = 0 AND r.resolved = 0"
        ) >= 2
    );
}

#[test]
fn extra_fields_are_kept_in_the_new_tables() {
    let mut seed = seed();
    plant(&mut seed, "lavandula-angustifolia")
        .aliases
        .push("lavandula-vera".to_string());
    let (_dir, _out, conn) = built(&seed);
    assert_eq!(
        strings(
            &conn,
            "SELECT authors || '|' || origin || '|' || oil_type || '|' || record_version || '|' || prompt_version FROM plant_profile WHERE plant_id = 'lavandula-angustifolia'"
        ),
        ["Mill.|Sureste y suroeste de Europa.|Esencial|1|7"]
    );
    assert!(
        strings(
            &conn,
            "SELECT description FROM plant_profile WHERE plant_id = 'lavandula-angustifolia'"
        )[0]
        .starts_with("Especie de planta")
    );
    assert!(
        strings(
            &conn,
            "SELECT bundle_hash FROM plant_profile WHERE plant_id = 'lavandula-angustifolia'"
        )[0]
        .starts_with("sha256:")
    );
    assert_eq!(
        strings(&conn, "SELECT alias || '>' || plant_id FROM plant_alias"),
        ["lavandula-vera>lavandula-angustifolia"]
    );
    // Imagen con licencia.
    assert_eq!(
        strings(
            &conn,
            "SELECT license || '|' || attribution_required FROM plant_image WHERE plant_id = 'lavandula-angustifolia'"
        ),
        ["Public domain|0"]
    );
    // Avisos de revisión de la caléndula.
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_review_flag WHERE plant_id = 'calendula-officinalis' AND code = 'aceite-por-compuesto-eo' AND target = 'oil'"
        ),
        1
    );
    // Referencias con dataset, licencia y URL cuando la hay.
    assert_eq!(
        strings(
            &conn,
            "SELECT dataset || '|' || license || '|' || COALESCE(url, '-') FROM reference WHERE id = 'wikipedia_es:Lavandula angustifolia'"
        ),
        ["wikipedia_es|CC BY-SA 4.0|https://es.wikipedia.org/wiki/Lavandula_angustifolia"]
    );
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM reference WHERE dataset IS NULL OR license IS NULL"
        ),
        0
    );
    // La atribución de los campos del perfil: la descripción sale de Wikipedia.
    assert_eq!(
        strings(
            &conn,
            "SELECT p.field || '|' || r.dataset FROM plant_profile_ref p JOIN reference r ON r.id = p.reference_id \
             WHERE p.plant_id = 'lavandula-angustifolia' AND p.field IN ('description', 'family', 'partsUsed', 'oil') ORDER BY p.field, r.dataset"
        ),
        [
            "description|wikipedia_es",
            "family|wcvp",
            "oil|ema_json",
            "oil|usda",
            "partsUsed|ema_json"
        ]
    );
    // Cada campo presente tiene al menos una referencia.
    for p in &seed.plants {
        let fields = count(
            &conn,
            &format!(
                "SELECT COUNT(DISTINCT field) FROM plant_profile_ref WHERE plant_id = '{}'",
                p.id
            ),
        );
        let expected = 1
            + i64::from(p.family.is_some())
            + i64::from(p.display_name.is_some())
            + i64::from(p.origin.is_some())
            + i64::from(p.description.is_some())
            + i64::from(p.oil.is_some())
            + i64::from(!p.parts_used.is_empty());
        assert_eq!(fields, expected, "{}", p.id);
    }
    // Nombre y página legibles de cada fuente, tal como los trae el manifiesto.
    assert_eq!(
        strings(
            &conn,
            "SELECT name || '|' || url FROM source WHERE id = 'wikipedia_es'"
        ),
        ["Wikipedia en español|https://es.wikipedia.org"]
    );
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM source WHERE name = id OR url = ''"
        ),
        0
    );
    // Fuentes del manifiesto y su trazabilidad.
    assert_eq!(
        count(&conn, "SELECT COUNT(*) FROM source"),
        seed.manifest.sources.len() as i64
    );
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM reference r WHERE NOT EXISTS (SELECT 1 FROM source s WHERE s.id = r.dataset)"
        ),
        0
    );
    // El objetivo de la EMA es trazable hasta su dataset y licencia.
    assert!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_goal_ref gr JOIN reference r ON r.id = gr.reference_id WHERE r.dataset = 'ema_json' AND r.license <> ''"
        ) > 0
    );
}

#[test]
fn safety_without_level_keeps_its_text_and_missing_safety_has_no_row() {
    let mut seed = seed();
    // En los fixtures, la caléndula tiene precauciones sin nivel y el cicuta, nivel alto.
    let calendula = seed
        .plants
        .iter()
        .find(|p| p.id == "calendula-officinalis")
        .unwrap();
    let text = calendula.safety.as_ref().unwrap().text.clone();
    assert!(calendula.safety.as_ref().unwrap().level.is_none());
    // Sin `safety`: la lavanda no tiene fila.
    plant(&mut seed, "lavandula-angustifolia").safety = None;
    let (_dir, _out, conn) = built(&seed);
    assert_eq!(
        strings(
            &conn,
            "SELECT COALESCE(level, 'NULL') FROM plant_safety WHERE plant_id = 'calendula-officinalis'"
        ),
        ["NULL"]
    );
    assert_eq!(
        strings(
            &conn,
            "SELECT text FROM plant_safety WHERE plant_id = 'calendula-officinalis'"
        ),
        [text]
    );
    assert!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_safety_ref WHERE plant_id = 'calendula-officinalis'"
        ) > 0
    );
    assert_eq!(
        strings(
            &conn,
            "SELECT level FROM plant_safety WHERE plant_id = 'conium-maculatum'"
        ),
        ["alto"]
    );
    assert_eq!(
        count(
            &conn,
            "SELECT COUNT(*) FROM plant_safety WHERE plant_id = 'lavandula-angustifolia'"
        ),
        0
    );
}

// ---- Tarea 7.4: errores ----

#[test]
fn duplicate_id_fails_naming_the_plant() {
    let mut seed = seed();
    let copy = seed.plants[0].clone();
    let id = copy.id.clone();
    seed.plants.push(copy);
    assert_fails_naming(&seed, &id, "mismo id");
}

#[test]
fn alias_equal_to_another_plant_id_fails_naming_both() {
    let mut seed = seed();
    plant(&mut seed, "lavandula-angustifolia")
        .aliases
        .push("conium-maculatum".to_string());
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "conium-maculatum");
    assert!(matches!(err, BuildError::AliasIsPlantId { .. }));
}

#[test]
fn missing_ref_fails_naming_plant_and_ref() {
    let mut seed = seed();
    let lav = plant(&mut seed, "lavandula-angustifolia");
    lav.refs.remove("wcvp:108971");
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "wcvp:108971");
    assert!(matches!(err, BuildError::UnknownRef { .. }));
}

#[test]
fn missing_citation_ref_fails() {
    let mut seed = seed();
    let lav = plant(&mut seed, "lavandula-angustifolia");
    lav.refs.remove("usda_reference:WOI");
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "usda_reference:WOI");
    assert!(matches!(err, BuildError::UnknownRef { .. }));
}

#[test]
fn unknown_goal_fails_end_to_end_naming_plant_and_goal() {
    let tmp = tempfile::tempdir().unwrap();
    copy_dir(&fixture(), tmp.path());
    let path = tmp.path().join("plants/lavandula-angustifolia.json");
    let text = fs::read_to_string(&path).unwrap();
    assert!(text.contains("\"goal\": \"mejorar-el-sueno\""));
    fs::write(
        &path,
        text.replace(
            "\"goal\": \"mejorar-el-sueno\"",
            "\"goal\": \"inexistente\"",
        ),
    )
    .unwrap();
    let out = tmp.path().join("out/catalog.db");
    let msg = build_from_dir(tmp.path(), &out).unwrap_err().to_string();
    assert!(
        msg.contains("lavandula-angustifolia") && msg.contains("inexistente"),
        "{msg}"
    );
    assert!(!out.exists());
}

#[test]
fn invalid_safety_level_fails_end_to_end_naming_the_plant() {
    let tmp = tempfile::tempdir().unwrap();
    copy_dir(&fixture(), tmp.path());
    let path = tmp.path().join("plants/conium-maculatum.json");
    let text = fs::read_to_string(&path).unwrap();
    assert!(text.contains("\"level\": \"alto\""));
    fs::write(
        &path,
        text.replace("\"level\": \"alto\"", "\"level\": \"extremo\""),
    )
    .unwrap();
    let out = tmp.path().join("out/catalog.db");
    let msg = build_from_dir(tmp.path(), &out).unwrap_err().to_string();
    assert!(
        msg.contains("conium-maculatum") && msg.contains("extremo"),
        "{msg}"
    );
    assert!(!out.exists());
}

#[test]
fn unsupported_image_license_fails_naming_the_plant() {
    let mut seed = seed();
    plant(&mut seed, "lavandula-angustifolia")
        .image
        .as_mut()
        .unwrap()
        .license = "CC BY-NC 4.0".to_string();
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "CC BY-NC 4.0");
    assert!(matches!(err, BuildError::UnsupportedImageLicense { .. }));
}

#[test]
fn data_without_dataset_or_license_fails() {
    // Un ref sin dataset.
    let mut seed = seed();
    plant(&mut seed, "lavandula-angustifolia")
        .refs
        .get_mut("wcvp:108971")
        .unwrap()
        .dataset = String::new();
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "dataset");
    assert!(matches!(
        err,
        BuildError::RefWithoutProvenance {
            field: "dataset",
            ..
        }
    ));

    // Un ref sin licencia.
    let mut seed = self::seed();
    plant(&mut seed, "lavandula-angustifolia")
        .refs
        .get_mut("wcvp:108971")
        .unwrap()
        .license = "  ".to_string();
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "licen");
    assert!(matches!(
        err,
        BuildError::RefWithoutProvenance {
            field: "license",
            ..
        }
    ));

    // Un dato que no cita ningún ref.
    let mut seed = self::seed();
    plant(&mut seed, "lavandula-angustifolia")
        .origin
        .as_mut()
        .unwrap()
        .refs
        .clear();
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "origin");
    assert!(matches!(err, BuildError::DataWithoutRefs { .. }));

    // Un dataset que el manifiesto no declara.
    let mut seed = self::seed();
    plant(&mut seed, "lavandula-angustifolia")
        .refs
        .get_mut("wcvp:108971")
        .unwrap()
        .dataset = "desconocido".to_string();
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "desconocido");
    assert!(matches!(err, BuildError::UnknownDataset { .. }));
}

#[test]
fn pending_without_review_flag_fails() {
    let mut seed = seed();
    plant(&mut seed, "lavandula-angustifolia").goals[0].pending_review = true;
    let err = assert_fails_naming(&seed, "lavandula-angustifolia", "goals.mejorar-el-sueno");
    assert!(matches!(err, BuildError::PendingWithoutFlag { .. }));
}

#[test]
fn failure_keeps_an_existing_database_untouched() {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("catalog.db");
    build_seed(&seed(), &out).unwrap();
    let before = fs::read(&out).unwrap();

    let mut broken = seed();
    plant(&mut broken, "lavandula-angustifolia").refs.clear();
    assert!(build_seed(&broken, &out).is_err());
    assert_eq!(fs::read(&out).unwrap(), before);
    assert!(!dir.path().join("catalog.db.tmp").exists());
}

// ---- Escritura y determinismo ----

#[test]
fn two_builds_of_the_same_seed_have_the_same_hash() {
    let dir = tempfile::tempdir().unwrap();
    let a = build_from_dir(&fixture(), &dir.path().join("a/catalog.db")).unwrap();
    let b = build_from_dir(&fixture(), &dir.path().join("b/catalog.db")).unwrap();
    assert_eq!(a.content_hash, b.content_hash);
    assert_eq!(a, b);
    assert_eq!(
        a.content_hash,
        content_hash(&dir.path().join("a/catalog.db")).unwrap()
    );
    assert!(!dir.path().join("a/catalog.db.tmp").exists());

    // Un cambio en un registro cambia el hash.
    let mut changed = seed();
    plant(&mut changed, "lavandula-angustifolia")
        .origin
        .as_mut()
        .unwrap()
        .value = "Otro.".to_string();
    let c = build_seed(&changed, &dir.path().join("c/catalog.db")).unwrap();
    assert_ne!(a.content_hash, c.content_hash);
}

#[test]
fn cli_build_prints_the_same_hash_twice() {
    let dir = tempfile::tempdir().unwrap();
    let run = |name: &str| {
        let out = dir.path().join(name);
        let output = Command::new(env!("CARGO_BIN_EXE_catalog-ingest"))
            .args(["build", "--seed"])
            .arg(fixture())
            .arg("--out")
            .arg(&out)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(out.exists());
        String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .find_map(|l| l.strip_prefix("hash: "))
            .unwrap()
            .to_string()
    };
    let first = run("one.db");
    let second = run("two.db");
    assert_eq!(first.len(), 64);
    assert_eq!(first, second);
    assert_eq!(first, content_hash(&dir.path().join("one.db")).unwrap());
}

#[test]
fn cli_build_fails_without_seed_and_leaves_no_database() {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("catalog.db");
    let output = Command::new(env!("CARGO_BIN_EXE_catalog-ingest"))
        .args(["build", "--seed"])
        .arg(dir.path().join("nope"))
        .arg("--out")
        .arg(&out)
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("semilla"));
    assert!(!out.exists());
}
