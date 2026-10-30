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

    // Los datasets aparecen solo como créditos de la planta: sin repetir, por nombre y con licencia y atribución.
    let credits = body["credits"].as_array().unwrap();
    assert!(!credits.is_empty(), "{body}");
    let names = labels(&body["credits"], "name");
    let mut sorted = names.clone();
    sorted.sort();
    sorted.dedup();
    assert_eq!(names, sorted, "créditos sin repetir y por nombre: {body}");
    for credit in credits {
        assert!(!credit["license"].as_str().unwrap().is_empty(), "{credit}");
        assert!(
            !credit["attribution"].as_str().unwrap().is_empty(),
            "{credit}"
        );
        assert!(
            credit.get("licenseUrl").is_some() && credit.get("url").is_some(),
            "{credit}"
        );
    }
    assert!(body["displayName"].is_string());
    assert!(body.get("reviewFlags").is_none() && !body.to_string().contains("reviewFlags"));

    // El glosario de la fixture llega hasta la API: Carminativo (Wikcionario, literal) y Estimulante (Wikipedia, adaptado) llevan su explicación.
    let group = |body: &Value, activity: &str| -> Value {
        body["useGroups"]
            .as_array()
            .unwrap()
            .iter()
            .find(|g| g["activity"] == activity)
            .unwrap_or_else(|| panic!("falta el grupo {activity}: {body}"))
            .clone()
    };
    let carminative = group(&body, "Carminativo");
    assert_eq!(carminative["glossary"]["term"], "Carminativo");
    assert_eq!(carminative["glossary"]["sourceName"], "Wikcionario");
    assert_eq!(carminative["glossary"]["adapted"], false);
    assert!(
        carminative["glossary"]["url"]
            .as_str()
            .unwrap()
            .starts_with("https://es.wiktionary.org/"),
        "{carminative}"
    );
    let stimulant = group(&body, "Estimulante");
    assert_eq!(stimulant["glossary"]["sourceName"], "Wikipedia");
    assert_eq!(stimulant["glossary"]["adapted"], true);
    // Sin término: `glossary` está y es `null`.
    let spasm = group(&body, "Espasmo");
    assert!(spasm.get("glossary").is_some() && spasm["glossary"].is_null());
    // Créditos del glosario: Wikcionario una vez, y Wikipedia una sola vez aunque también acredite la descripción.
    assert_eq!(
        names
            .iter()
            .filter(|n| n.starts_with("Wikcionario"))
            .count(),
        1,
        "{names:?}"
    );
    assert_eq!(
        names.iter().filter(|n| n.starts_with("Wikipedia")).count(),
        1,
        "{names:?}"
    );
    let wiktionary = credits
        .iter()
        .find(|c| c["name"] == "Wikcionario en español")
        .unwrap();
    assert_eq!(wiktionary["license"], "CC BY-SA 4.0");
    assert_eq!(
        wiktionary["licenseUrl"],
        "https://creativecommons.org/licenses/by-sa/4.0/"
    );
    // La fórmula de enfermedad grave no se enlaza, y una planta sin términos del glosario no acredita Wikcionario.
    let (_, calendula) = get(&app, "/v1/plants/calendula-officinalis").await;
    let formula = group(
        &calendula,
        "Uso tradicional, sin eficacia demostrada: cáncer",
    );
    assert!(formula["glossary"].is_null(), "{formula}");
    assert_eq!(
        group(&calendula, "Diurético")["glossary"]["term"],
        "Diurético"
    );
    assert!(group(&calendula, "Fiebre")["glossary"].is_null());
    let (_, conium) = get(&app, "/v1/plants/conium-maculatum").await;
    assert!(
        conium["useGroups"]
            .as_array()
            .unwrap()
            .iter()
            .all(|g| g["glossary"].is_null()),
        "{conium}"
    );
    assert!(
        !labels(&conium["credits"], "name")
            .iter()
            .any(|n| n.starts_with("Wikcionario")),
        "{conium}"
    );

    // Un identificador que no es de planta ni alias es un 404.
    let (status, _) = get(&app, "/v1/plants/no-existe").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
}
