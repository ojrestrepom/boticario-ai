//! Extremo a extremo con fuentes de fixture distintas de la fuente real: ingesta (crudo y derivación) y servicio por la API, sin red y sin tocar `data/`.
//!
//! Demuestra que servir otro dataset no exige cambios de código en la API.

use std::sync::Arc;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use catalog_api::async_catalog::AsyncCatalog;
use catalog_api::http::router;
use catalog_api::repository::SqliteCatalogRepository;
use catalog_ingest::adapter::SourceAdapter;
use catalog_ingest::build::rederive;
use catalog_ingest::raw::import_raw;
use catalog_ingest::sources::{AdapterRegistry, SourceEntry, SourcesConfig};
use catalog_ingest::test_support::{FixtureAdapter, FixtureCsv, build_zip};
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

async fn get(app: &axum::Router, uri: &str) -> (StatusCode, Value) {
    let request = Request::builder().uri(uri).body(Body::empty()).unwrap();
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap())
}

#[tokio::test]
async fn api_serves_a_catalog_built_from_two_fixture_sources() {
    let dir = tempfile::tempdir().unwrap();
    let raw_db = dir.path().join("build").join("raw.db");
    let out = dir.path().join("build").join("catalog.db");

    // Capa cruda: un ZIP de fixture por fuente, en un mismo `raw.db`.
    for (id, csv) in [("alpha", FixtureCsv::alpha()), ("beta", FixtureCsv::beta())] {
        let zip_dir = tempfile::tempdir().unwrap();
        let zip = build_zip(&zip_dir, &csv.entries());
        let spec = FixtureAdapter::new(id).raw_import(&zip);
        import_raw(&spec, &raw_db).unwrap();
    }

    // Derivación con un registro que solo conoce los adaptadores de fixture.
    let mut registry = AdapterRegistry::new();
    for id in ["alpha", "beta"] {
        registry
            .register(Box::new(FixtureAdapter::new(id)))
            .unwrap();
    }
    let config = SourcesConfig {
        sources: vec![
            SourceEntry {
                id: "alpha".to_string(),
                priority: 1,
            },
            SourceEntry {
                id: "beta".to_string(),
                priority: 2,
            },
        ],
    };
    let report = rederive(&registry, &config, &raw_db, &out).unwrap();
    assert_eq!((report.sources, report.plants), (2, 2));

    // La API sirve la base resultante sin saber de dónde viene.
    let repo = SqliteCatalogRepository::open(&out).unwrap();
    let app = router(AsyncCatalog::new(Arc::new(repo)));

    let (status, body) = get(&app, "/healthz").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");

    // La procedencia es interna: la API no ofrece la lista de fuentes.
    let (status, _) = get(&app, "/v1/sources").await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, body) = get(&app, "/v1/plants").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["total"], 2, "{body}");
    let mut plant_ids: Vec<&str> = body["items"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| p["id"].as_str().unwrap())
        .collect();
    plant_ids.sort();
    assert_eq!(
        plant_ids,
        ["lavandula-angustifolia", "matricaria-chamomilla"],
        "{body}"
    );

    // La lavanda está en ambas fuentes: el detalle muestra los datos de las dos ya fusionados, sin decir de cuál viene cada uno.
    let (status, body) = get(&app, "/v1/plants/lavandula-angustifolia").await;
    assert_eq!(status, StatusCode::OK);
    let labels = |items: &Value, key: &str| -> Vec<String> {
        items
            .as_array()
            .unwrap()
            .iter()
            .map(|i| i[key].as_str().unwrap().to_string())
            .collect()
    };
    assert_eq!(labels(&body["parts"], "label"), ["Flower", "Leaf", "Root"]);
    assert!(labels(&body["uses"], "activity").contains(&"Sedative".to_string()));
    assert!(
        !body.to_string().contains("\"sources\""),
        "el detalle no debe exponer la procedencia: {body}"
    );
}
