//! Independencia de la fuente: el código de `catalog-core` y `catalog-api` (y el documento OpenAPI) no nombran ningún dataset concreto.
//!
//! Solo `catalog-ingest` puede nombrar tablas, campos o identificadores de un dataset.
//! Los términos prohibidos se arman con `concat!` a partir de fragmentos, así este archivo no los contiene literalmente y puede escanearse a sí mismo como cualquier otro; excluirlo por ruta habría dejado un punto ciego en el escaneo.

use std::fs;
use std::path::{Path, PathBuf};

const FORBIDDEN: [&str; 9] = [
    concat!("us", "da"),
    concat!("fnf", "num"),
    concat!("fnf", "tax"),
    concat!("ethno", "bot"),
    concat!("far", "macy"),
    concat!("pp", "co"),
    concat!("pp", "na"),
    concat!("long", "ref"),
    concat!("du", "ke"),
];

/// Recoge los `.rs` bajo `dir`, ignorando `target/`.
fn collect_rs(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).unwrap() {
        let path = entry.unwrap().path();
        if path.is_dir() {
            if path.file_name().is_some_and(|n| n == "target") {
                continue;
            }
            collect_rs(&path, out);
        } else if path.extension().is_some_and(|e| e == "rs") {
            out.push(path);
        }
    }
}

#[test]
fn core_api_and_openapi_do_not_name_any_dataset() {
    // `CARGO_MANIFEST_DIR` es `backend/catalog-api`.
    let api = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let backend = api.parent().unwrap();
    let mut files = Vec::new();
    collect_rs(&api, &mut files);
    collect_rs(&backend.join("catalog-core"), &mut files);
    files.push(backend.join("openapi.json"));
    assert!(
        files.len() > 10,
        "el escaneo debería encontrar los fuentes: {files:?}"
    );

    let mut hits = Vec::new();
    for file in &files {
        let text = fs::read_to_string(file).unwrap().to_lowercase();
        for term in FORBIDDEN {
            if text.contains(term) {
                hits.push(format!("{} contiene {term:?}", file.display()));
            }
        }
    }
    assert!(hits.is_empty(), "{hits:#?}");
}

/// Nombres de dataset (ids de fuente) que no pueden aparecer como palabra en un nombre de esquema ni de campo.
/// Se arman con `concat!` por la misma razón que `FORBIDDEN`. Se comparan palabras completas: `ema` sería subcadena de `schema`.
const FORBIDDEN_WORDS: [&str; 14] = [
    concat!("us", "da"),
    concat!("du", "ke"),
    concat!("wc", "vp"),
    concat!("w", "fo"),
    concat!("ef", "sa"),
    concat!("tp", "pt"),
    concat!("e", "ma"),
    concat!("wiki", "data"),
    concat!("wiki", "pedia"),
    concat!("com", "mons"),
    concat!("fnf", "num"),
    concat!("fnf", "tax"),
    concat!("ethno", "bot"),
    concat!("far", "macy"),
];

/// Palabras de un identificador `camelCase`, `snake_case` o `kebab-case`, en minúsculas.
fn words(identifier: &str) -> Vec<String> {
    let mut words = Vec::new();
    let mut current = String::new();
    for c in identifier.chars() {
        if (!c.is_ascii_alphanumeric() || c.is_ascii_uppercase()) && !current.is_empty() {
            words.push(std::mem::take(&mut current));
        }
        if c.is_ascii_alphanumeric() {
            current.push(c.to_ascii_lowercase());
        }
    }
    if !current.is_empty() {
        words.push(current);
    }
    words
}

/// Reúne los nombres de las propiedades de todos los objetos del documento, en cualquier nivel.
fn property_names(value: &serde_json::Value, out: &mut Vec<String>) {
    match value {
        serde_json::Value::Object(map) => {
            for (key, v) in map {
                if key == "properties"
                    && let Some(props) = v.as_object()
                {
                    out.extend(props.keys().cloned());
                }
                property_names(v, out);
            }
        }
        serde_json::Value::Array(items) => items.iter().for_each(|v| property_names(v, out)),
        _ => {}
    }
}

#[test]
fn openapi_schema_and_field_names_do_not_name_any_dataset() {
    let doc = serde_json::to_value(catalog_api::openapi::openapi()).unwrap();
    let mut names: Vec<String> = doc["components"]["schemas"]
        .as_object()
        .unwrap()
        .keys()
        .cloned()
        .collect();
    let schema_count = names.len();
    property_names(&doc, &mut names);
    assert!(
        schema_count >= 15 && names.len() > schema_count + 30,
        "el recorrido debería encontrar los esquemas y sus campos: {names:?}"
    );
    // Los campos nuevos de este cambio están entre los revisados.
    for expected in [
        "credits",
        "licenseUrl",
        "displayName",
        "useGroups",
        "CreditDto",
    ] {
        assert!(names.iter().any(|n| n == expected), "falta {expected}");
    }
    let mut hits = Vec::new();
    for name in &names {
        for word in words(name) {
            if FORBIDDEN_WORDS.contains(&word.as_str()) {
                hits.push(format!("{name} contiene {word:?}"));
            }
        }
    }
    assert!(hits.is_empty(), "{hits:#?}");
}

#[test]
fn word_splitting_handles_camel_snake_and_kebab_case() {
    assert_eq!(words("licenseUrl"), ["license", "url"]);
    assert_eq!(words("PlantSummaryDto"), ["plant", "summary", "dto"]);
    assert_eq!(words("use_group-ref"), ["use", "group", "ref"]);
    // `schema` no contiene la palabra `ema`.
    assert_eq!(words("schema"), ["schema"]);
}
