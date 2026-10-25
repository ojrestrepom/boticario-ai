//! Extremo a extremo con la semilla de fixture del crate de ingesta: construcción de `catalog.db` y servicio por la API, sin red y sin tocar `data/`.

use std::path::Path;
use std::sync::Arc;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use catalog_api::async_catalog::AsyncCatalog;
use catalog_api::auth::ApiTokens;
use catalog_api::http::router;
use catalog_api::repository::SqliteCatalogRepository;
use catalog_ingest::seed_build::build_from_dir;
use http_body_util::BodyExt;
use serde_json::Value;
use tower::ServiceExt;

// Valor ficticio de prueba; no es un secreto.
const TEST_TOKEN: &str = "test-token-not-a-secret-0000000000000000";

async fn get(app: &axum::Router, uri: &str) -> (StatusCode, Value) {
    let request = Request::builder()
        .uri(uri)
        .header("Authorization", format!("Bearer {TEST_TOKEN}"))
        .body(Body::empty())
        .unwrap();
    let response = app.clone().oneshot(request).await.unwrap();
    let status = response.status();
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    (status, serde_json::from_slice(&bytes).unwrap())
}

#[tokio::test]
async fn api_serves_a_catalog_built_from_the_fixture_seed() {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("build").join("catalog.db");

    // Construcción desde la semilla de fixture (3 plantas), sin red.
    let seed = Path::new(env!("CARGO_MANIFEST_DIR")).join("../catalog-ingest/tests/fixtures/seed");
    let report = build_from_dir(&seed, &out).unwrap();
    assert_eq!(report.plants, 3);

    // La API sirve la base resultante sin saber de dónde viene.
    let repo = SqliteCatalogRepository::open(&out).unwrap();
    let app = router(
        AsyncCatalog::new(Arc::new(repo)),
        ApiTokens::parse(TEST_TOKEN).unwrap(),
    );

    let (status, body) = get(&app, "/health").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["status"], "ok");

    // La procedencia es interna: la API no ofrece la lista de fuentes.
    let (status, _) = get(&app, "/v1/sources").await;
    assert_eq!(status, StatusCode::NOT_FOUND);

    let (status, body) = get(&app, "/v1/plants").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(body["total"], 3, "{body}");
    let mut plant_ids: Vec<&str> = body["items"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| p["id"].as_str().unwrap())
        .collect();
    plant_ids.sort();
    assert_eq!(
        plant_ids,
        [
            "calendula-officinalis",
            "conium-maculatum",
            "lavandula-angustifolia"
        ],
        "{body}"
    );

    // El detalle de la lavanda trae partes y usos, sin decir de qué fuente viene cada dato.
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
    assert_eq!(labels(&body["parts"], "label"), ["Flor"]);
    assert!(labels(&body["uses"], "activity").contains(&"Carminativo".to_string()));
    assert!(
        !body.to_string().contains("\"sources\""),
        "el detalle no debe exponer la procedencia: {body}"
    );
}
