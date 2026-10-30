//! Pruebas de la lectura de la semilla: fixtures pequeñas en `tests/fixtures/seed/` y la semilla real (ignorada).

use std::fs;
use std::path::{Path, PathBuf};

use catalog_ingest::seed::{SafetyLevel, SeedError, load_seed};
use sha2::{Digest, Sha256};

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
fn source_license_url_is_optional_https_or_null() {
    let seed = load_seed(&fixture()).unwrap();
    let url_of = |id: &str| {
        seed.manifest
            .sources
            .iter()
            .find(|s| s.id == id)
            .unwrap()
            .license_url
            .clone()
    };
    assert_eq!(
        url_of("wikipedia_es").as_deref(),
        Some("https://creativecommons.org/licenses/by-sa/4.0/")
    );
    assert_eq!(url_of("commons"), None);

    // Sin la clave, el manifiesto se lee igual (campo opcional).
    let tmp = copy_fixture();
    let path = tmp.path().join("manifest.json");
    let mut value: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    for source in value["sources"].as_array_mut().unwrap() {
        source.as_object_mut().unwrap().remove("licenseUrl");
    }
    fs::write(&path, serde_json::to_string(&value).unwrap()).unwrap();
    let seed = load_seed(tmp.path()).unwrap();
    assert!(
        seed.manifest
            .sources
            .iter()
            .all(|s| s.license_url.is_none())
    );

    // Una URL que no es https, o de otro tipo, se rechaza nombrando la fuente.
    for bad in [
        serde_json::json!("http://creativecommons.org/licenses/by/4.0/"),
        serde_json::json!("https://"),
        serde_json::json!("https://a b/"),
        serde_json::json!(""),
    ] {
        value["sources"][0]["licenseUrl"] = bad.clone();
        fs::write(&path, serde_json::to_string(&value).unwrap()).unwrap();
        let err = load_seed(tmp.path()).unwrap_err();
        assert!(err.to_string().contains("licenseUrl"), "{bad}: {err}");
    }
    value["sources"][0]["licenseUrl"] = serde_json::json!(3);
    fs::write(&path, serde_json::to_string(&value).unwrap()).unwrap();
    assert!(load_seed(tmp.path()).is_err());
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

// ---- Glosario de actividades (tarea 5.2) ----

/// Hash canónico del glosario: `serde_json` ordena las claves y no escapa el texto no ASCII, como la herramienta.
fn glossary_hash_of(value: &serde_json::Value) -> String {
    let canon = serde_json::to_string(value).unwrap();
    let digest: String = Sha256::digest(canon.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    format!("sha256:{digest}")
}

/// Reescribe `glossary.json` con `mutate` y vuelve a declarar su hash y su conteo en el manifiesto.
fn reseal_glossary(dir: &Path, mutate: impl FnOnce(&mut serde_json::Value)) {
    let path = dir.join("glossary.json");
    let mut glossary: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();
    mutate(&mut glossary);
    fs::write(&path, serde_json::to_string(&glossary).unwrap()).unwrap();
    let manifest_path = dir.join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&manifest_path).unwrap()).unwrap();
    manifest["glossaryHash"] = glossary_hash_of(&glossary).into();
    manifest["glossaryCount"] = glossary["rows"].as_array().unwrap().len().into();
    fs::write(&manifest_path, serde_json::to_string(&manifest).unwrap()).unwrap();
}

#[test]
fn intact_glossary_loads_with_its_rows() {
    let seed = load_seed(&fixture()).unwrap();
    let glossary = seed.glossary.expect("la fixture trae glosario");
    assert_eq!(glossary.rows.len(), 5);
    assert_eq!(seed.manifest.glossary_count, Some(5));
    let keys: Vec<&str> = glossary.rows.iter().map(|r| r.key.as_str()).collect();
    assert_eq!(
        keys,
        [
            "antídoto",
            "carminativo",
            "diurético",
            "emenagogo",
            "estimulante"
        ]
    );
    assert!(glossary.rows.iter().any(|r| r.adapted));
    assert!(
        glossary
            .rows
            .iter()
            .all(|r| r.entry_url.starts_with("https://"))
    );
}

#[test]
fn altered_glossary_fails_naming_the_glossary_hash() {
    let tmp = copy_fixture();
    let path = tmp.path().join("glossary.json");
    let text = fs::read_to_string(&path).unwrap();
    assert!(text.contains("producción y excreción de orina"));
    fs::write(
        &path,
        text.replacen("producción y excreción", "producción o excreción", 1),
    )
    .unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(
        matches!(err, SeedError::GlossaryHashMismatch { .. }),
        "{err}"
    );
    assert!(err.to_string().contains("glossaryHash"), "{err}");
}

#[test]
fn missing_glossary_with_declaring_manifest_fails() {
    let tmp = copy_fixture();
    fs::remove_file(tmp.path().join("glossary.json")).unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::GlossaryMissing { .. }), "{err}");
    assert!(err.to_string().contains("falta glossary.json"), "{err}");
}

#[test]
fn seed_without_glossary_loads_with_none() {
    let tmp = copy_fixture();
    fs::remove_file(tmp.path().join("glossary.json")).unwrap();
    let manifest_path = tmp.path().join("manifest.json");
    let mut manifest: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&manifest_path).unwrap()).unwrap();
    let object = manifest.as_object_mut().unwrap();
    object.remove("glossaryHash");
    object.remove("glossaryCount");
    fs::write(&manifest_path, serde_json::to_string(&manifest).unwrap()).unwrap();
    let seed = load_seed(tmp.path()).unwrap();
    assert!(seed.glossary.is_none());
    assert!(seed.manifest.glossary_hash.is_none());
}

#[test]
fn glossary_count_must_match_the_manifest() {
    let tmp = copy_fixture();
    let path = tmp.path().join("manifest.json");
    let text = fs::read_to_string(&path).unwrap();
    fs::write(
        &path,
        text.replace("\"glossaryCount\": 5", "\"glossaryCount\": 6"),
    )
    .unwrap();
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::GlossaryInvalid { .. }), "{err}");
    assert!(err.to_string().contains("glossaryCount"), "{err}");
}

#[test]
fn duplicate_glossary_keys_fail() {
    let tmp = copy_fixture();
    reseal_glossary(tmp.path(), |g| {
        let rows = g["rows"].as_array_mut().unwrap();
        let first = rows[0].clone();
        rows.push(first);
    });
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::GlossaryInvalid { .. }), "{err}");
    assert!(err.to_string().contains("repetida"), "{err}");
}

#[test]
fn glossary_urls_must_be_https() {
    for (field, row) in [("entryUrl", true), ("licenseUrl", false)] {
        let tmp = copy_fixture();
        reseal_glossary(tmp.path(), |g| {
            if row {
                g["rows"][0][field] = "http://es.wiktionary.org/x".into();
            } else {
                g[field] = "ftp://creativecommons.org/".into();
            }
        });
        let err = load_seed(tmp.path()).unwrap_err();
        assert!(matches!(err, SeedError::GlossaryInvalid { .. }), "{err}");
        assert!(err.to_string().contains(field), "{err}");
    }
}

#[test]
fn glossary_key_must_be_a_base_form() {
    let tmp = copy_fixture();
    reseal_glossary(tmp.path(), |g| {
        g["rows"][0]["key"] = "Antídoto (escorpión)".into();
    });
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(err.to_string().contains("forma base"), "{err}");
}

#[test]
fn glossary_with_unknown_field_or_format_fails() {
    let tmp = copy_fixture();
    reseal_glossary(tmp.path(), |g| {
        g["rows"][0]["extra"] = 1.into();
    });
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::Parse { .. }), "{err}");

    let tmp = copy_fixture();
    reseal_glossary(tmp.path(), |g| {
        g["format"] = "catalog-glossary/2".into();
    });
    let err = load_seed(tmp.path()).unwrap_err();
    assert!(matches!(err, SeedError::UnsupportedVersion { .. }), "{err}");
}
