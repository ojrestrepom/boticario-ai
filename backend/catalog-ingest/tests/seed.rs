//! Pruebas de la lectura de la semilla: fixtures pequeñas en `tests/fixtures/seed/` y la semilla real (ignorada).

use std::fs;
use std::path::{Path, PathBuf};

use catalog_ingest::seed::{SafetyLevel, SeedError, load_seed};

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

fn copy_fixture() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    copy_dir(&fixture(), tmp.path());
    tmp
}

#[test]
fn intact_seed_loads() {
    let seed = load_seed(&fixture()).unwrap();
    assert_eq!(seed.manifest.plant_count, 3);
    let ids: Vec<&str> = seed.plants.iter().map(|p| p.id.as_str()).collect();
    assert_eq!(
        ids,
        [
            "calendula-officinalis",
            "conium-maculatum",
            "lavandula-angustifolia"
        ]
    );
    assert_eq!(seed.goals.goals.len(), 6);
    assert!(seed.plants.iter().all(|p| !p.refs.is_empty()));
    assert!(seed.plants.iter().any(|p| {
        p.safety
            .as_ref()
            .is_some_and(|s| s.level == Some(SafetyLevel::Alto))
    }));
}

#[test]
fn altered_record_fails_naming_the_seed() {
    let tmp = copy_fixture();
    let path = tmp.path().join("plants/lavandula-angustifolia.json");
    let text = fs::read_to_string(&path).unwrap();
    assert!(text.contains("Lavandula angustifolia"));
    fs::write(
        &path,
        text.replacen("Lavandula angustifolia", "Lavandula angustifolia L.", 1),
    )
    .unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::HashMismatch { .. }), "{err}");
    let msg = err.to_string();
    assert!(
        msg.contains(&tmp.path().display().to_string()) && msg.contains("seedHash"),
        "{msg}"
    );
}

#[test]
fn missing_seed_explains_how_to_generate_it() {
    let tmp = tempfile::tempdir().unwrap();
    let err = load_seed(&tmp.path().join("nope")).unwrap_err();
    assert!(matches!(err, SeedError::Missing { .. }));
    assert!(
        err.to_string().contains("catalog-seed/cli.py seal"),
        "{err}"
    );
}

#[test]
fn file_name_must_equal_id() {
    let tmp = copy_fixture();
    fs::rename(
        tmp.path().join("plants/conium-maculatum.json"),
        tmp.path().join("plants/otra-planta.json"),
    )
    .unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(
        matches!(err, SeedError::FileNameMismatch { ref id, .. } if id == "conium-maculatum"),
        "{err}"
    );
    assert!(err.to_string().contains("otra-planta.json"));
}

#[test]
fn unknown_field_fails_naming_file_and_plant() {
    let tmp = copy_fixture();
    let path = tmp.path().join("plants/calendula-officinalis.json");
    let text = fs::read_to_string(&path).unwrap();
    fs::write(&path, text.replacen("{", "{\"extra\": 1,", 1)).unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::Parse { .. }), "{err}");
    let msg = err.to_string();
    assert!(
        msg.contains("calendula-officinalis") && msg.contains("extra"),
        "{msg}"
    );
}

#[test]
fn missing_required_nullable_field_fails() {
    let tmp = copy_fixture();
    let path = tmp.path().join("plants/calendula-officinalis.json");
    let mut value: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    value.as_object_mut().unwrap().remove("safety");
    fs::write(&path, serde_json::to_string(&value).unwrap()).unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(err.to_string().contains("safety"), "{err}");
}

#[test]
fn plant_count_must_match_manifest() {
    let tmp = copy_fixture();
    let path = tmp.path().join("manifest.json");
    let text = fs::read_to_string(&path).unwrap();
    fs::write(
        &path,
        text.replace("\"plantCount\": 3", "\"plantCount\": 4"),
    )
    .unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert_eq!(
        err,
        SeedError::CountMismatch {
            expected: 4,
            found: 3
        }
    );
}

#[test]
fn extra_record_is_detected() {
    let tmp = copy_fixture();
    fs::copy(
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../data/seed/plants/thymus-vulgaris.json"),
        tmp.path().join("plants/thymus-vulgaris.json"),
    )
    .unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert_eq!(
        err,
        SeedError::CountMismatch {
            expected: 3,
            found: 4
        }
    );
}

/// Carga la semilla real de `data/seed/` y comprueba que el hash de Rust coincide con el del manifiesto.
#[test]
#[ignore = "lee data/seed/ del repositorio; ejecutar con --ignored"]
fn real_seed_hash_matches_manifest() {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../data/seed");
    let seed = load_seed(&dir).unwrap();
    assert_eq!(seed.plants.len(), seed.manifest.plant_count);
    assert!(seed.manifest.seed_hash.starts_with("sha256:"));
}

fn set_first_goal(tmp: &Path, goal: &str, subarea: Option<&str>) {
    let path = tmp.join("plants/lavandula-angustifolia.json");
    let mut value: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    let first = &mut value["goals"][0];
    first["goal"] = goal.into();
    first["subarea"] = subarea.map_or(serde_json::Value::Null, Into::into);
    fs::write(&path, serde_json::to_string(&value).unwrap()).unwrap();
}

#[test]
fn unknown_goal_fails_naming_plant_and_value() {
    let tmp = copy_fixture();
    set_first_goal(tmp.path(), "inventado", None);
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::UnknownGoal { .. }), "{err}");
    let msg = err.to_string();
    assert!(
        msg.contains("lavandula-angustifolia") && msg.contains("inventado"),
        "{msg}"
    );
}

#[test]
fn unknown_subarea_and_foreign_subarea_fail() {
    let tmp = copy_fixture();
    set_first_goal(tmp.path(), "otros-objetivos", Some("inventada"));
    let msg = load_seed(tmp.path()).unwrap_err().to_string();
    assert!(
        msg.contains("lavandula-angustifolia") && msg.contains("inventada"),
        "{msg}"
    );
    set_first_goal(tmp.path(), "relajacion-estres", Some("digestion"));
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::UnknownGoal { .. }), "{err}");
    let msg = err.to_string();
    assert!(
        msg.contains("digestion") && msg.contains("relajacion-estres"),
        "{msg}"
    );
}
