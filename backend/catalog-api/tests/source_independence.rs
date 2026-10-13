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
