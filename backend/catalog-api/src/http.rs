//! Router HTTP v1 (solo lectura) y sus handlers.
//!
//! Los handlers dependen únicamente de [`AsyncCatalog`], que llega por el estado de Axum.
//! Para el campo `instance` de los errores se usa `OriginalUri`: dentro de `nest("/v1", …)` el `Uri` normal ya llega sin el prefijo.

use std::collections::HashMap;

use axum::extract::rejection::{PathRejection, QueryRejection};
use axum::extract::{OriginalUri, Path, Query, State};
use axum::http::{HeaderValue, header};
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use catalog_core::domain::{DEFAULT_LIMIT, ListQuery, MAX_LIMIT, PlantId};

use crate::async_catalog::AsyncCatalog;
use crate::dto::{HealthDto, PageDto, PlantDto, PlantSummaryDto, ProblemDto, SourceDto};
use crate::error::ApiError;
use crate::openapi::openapi;

/// Construye el router completo: `/healthz` y `/v1/...`, con errores `problem+json` para rutas y métodos desconocidos.
pub fn router(catalog: AsyncCatalog) -> Router {
    let v1 = Router::new()
        .route("/sources", get(sources))
        .route("/plants", get(list_plants))
        .route("/plants/{id}", get(get_plant));
    Router::new()
        .route("/healthz", get(healthz))
        .route("/openapi.json", get(openapi_json))
        .nest("/v1", v1)
        .fallback(not_found)
        .method_not_allowed_fallback(method_not_allowed)
        .with_state(catalog)
}

async fn not_found(OriginalUri(uri): OriginalUri) -> Response {
    ApiError::NotFound {
        detail: "el recurso solicitado no existe".to_string(),
    }
    .into_response_at(&uri)
}

async fn method_not_allowed(OriginalUri(uri): OriginalUri) -> Response {
    let mut response = ApiError::MethodNotAllowed.into_response_at(&uri);
    // RFC 9110 exige `Allow` en un 405. Todas las rutas de la API son solo `GET`, así que el valor es el mismo para todas.
    response
        .headers_mut()
        .insert(header::ALLOW, HeaderValue::from_static("GET"));
    response
}

/// Documento OpenAPI de esta misma API.
#[utoipa::path(
    get,
    path = "/openapi.json",
    tag = "health",
    responses(
        (status = 200, description = "Este mismo documento OpenAPI", content_type = "application/json"),
        (status = 405, description = "Método no permitido; la respuesta incluye `Allow: GET`", body = ProblemDto, content_type = "application/problem+json"),
    )
)]
pub(crate) async fn openapi_json() -> Json<utoipa::openapi::OpenApi> {
    Json(openapi())
}

/// El servicio está activo.
#[utoipa::path(
    get,
    path = "/healthz",
    tag = "health",
    responses(
        (status = 200, description = "El servicio está activo", body = HealthDto),
        (status = 405, description = "Método no permitido; la respuesta incluye `Allow: GET`", body = ProblemDto, content_type = "application/problem+json"),
    )
)]
pub(crate) async fn healthz() -> Json<HealthDto> {
    Json(HealthDto { status: "ok" })
}

/// Fuentes de datos del catálogo.
#[utoipa::path(
    get,
    path = "/v1/sources",
    tag = "catalog",
    responses(
        (status = 200, description = "Fuentes del catálogo, ordenadas por identificador", body = Vec<SourceDto>),
        (status = 405, description = "Método no permitido; la respuesta incluye `Allow: GET`", body = ProblemDto, content_type = "application/problem+json"),
        (status = 500, description = "Fallo interno", body = ProblemDto, content_type = "application/problem+json"),
    )
)]
pub(crate) async fn sources(
    State(catalog): State<AsyncCatalog>,
    OriginalUri(uri): OriginalUri,
) -> Response {
    match catalog.list_sources().await {
        Ok(list) => Json(list.into_iter().map(SourceDto::from).collect::<Vec<_>>()).into_response(),
        Err(err) => ApiError::from(err).into_response_at(&uri),
    }
}

/// Longitud máxima de `q`, en caracteres.
///
/// SQLite limita el patrón de `LIKE` a 50.000 caracteres y un `q` mayor acabaría en un 500; se rechaza antes con un 400.
/// Si cambia, actualiza también `max_length` del parámetro `q` en la anotación de `list_plants`.
const MAX_QUERY_CHARS: usize = 200;

/// Lee `limit` y `offset` del mapa de parámetros, validándolos a mano para controlar el formato del error.
fn parse_list_query(params: &HashMap<String, String>) -> Result<ListQuery, ApiError> {
    let limit = match params.get("limit") {
        None => DEFAULT_LIMIT,
        Some(text) => match text.parse::<i64>() {
            Ok(n) if (1..=i64::from(MAX_LIMIT)).contains(&n) => n as u32,
            Ok(_) => {
                return Err(ApiError::bad_request(
                    "limit",
                    format!("limit debe estar entre 1 y {MAX_LIMIT}"),
                ));
            }
            Err(_) => {
                return Err(ApiError::bad_request("limit", "limit debe ser un entero"));
            }
        },
    };
    let offset = match params.get("offset") {
        None => 0,
        Some(text) => match text.parse::<i64>() {
            // El contrato declara `offset` como `int32`: el máximo es `i32::MAX`, aunque se guarde en `u32`.
            Ok(n) if n >= 0 => u32::try_from(n)
                .ok()
                .filter(|n| i32::try_from(*n).is_ok())
                .ok_or_else(|| ApiError::bad_request("offset", "offset es demasiado grande"))?,
            Ok(_) => {
                return Err(ApiError::bad_request(
                    "offset",
                    "offset no puede ser negativo",
                ));
            }
            Err(_) => {
                return Err(ApiError::bad_request("offset", "offset debe ser un entero"));
            }
        },
    };
    let q = params.get("q").cloned();
    // SQLite trunca el patrón de `LIKE` en un NUL y la búsqueda cambiaría en silencio; se rechaza cualquier carácter de control.
    if q.as_ref().is_some_and(|q| q.chars().any(char::is_control)) {
        return Err(ApiError::bad_request(
            "q",
            "q no puede contener caracteres de control",
        ));
    }
    if q.as_ref()
        .is_some_and(|q| q.chars().count() > MAX_QUERY_CHARS)
    {
        return Err(ApiError::bad_request(
            "q",
            format!("q no puede superar {MAX_QUERY_CHARS} caracteres"),
        ));
    }
    Ok(ListQuery { q, limit, offset })
}

/// Lista plantas con búsqueda y paginación.
#[utoipa::path(
    get,
    path = "/v1/plants",
    tag = "catalog",
    params(
        ("q" = Option<String>, Query, max_length = 200, description = "Subcadena a buscar en el nombre científico y los nombres comunes, sin distinguir mayúsculas, acentos ni espacios repetidos o exteriores. Vacío o solo espacios no filtra; `%` y `_` se buscan como texto literal. No admite caracteres de control."),
        // Los literales de `limit` reflejan `MAX_LIMIT` y `DEFAULT_LIMIT` de catalog-core; el test de `openapi.rs` avisa si divergen.
        ("limit" = Option<u32>, Query, minimum = 1, maximum = 100, description = "Elementos por página (1 a 100, por defecto 20)."),
        ("offset" = Option<u32>, Query, minimum = 0, maximum = 2147483647, description = "Elementos a saltar (por defecto 0)."),
    ),
    responses(
        (status = 200, description = "Página de plantas en orden de nombre científico e identificador", body = PageDto<PlantSummaryDto>),
        (status = 400, description = "Parámetro inválido", body = ProblemDto, content_type = "application/problem+json"),
        (status = 405, description = "Método no permitido; la respuesta incluye `Allow: GET`", body = ProblemDto, content_type = "application/problem+json"),
        (status = 500, description = "Fallo interno", body = ProblemDto, content_type = "application/problem+json"),
    )
)]
pub(crate) async fn list_plants(
    State(catalog): State<AsyncCatalog>,
    OriginalUri(uri): OriginalUri,
    params: Result<Query<HashMap<String, String>>, QueryRejection>,
) -> Response {
    let result = async {
        let Query(params) = params
            .map_err(|_| ApiError::bad_request("query", "la cadena de consulta es inválida"))?;
        let query = parse_list_query(&params)?;
        let (limit, offset) = (query.limit, query.offset);
        let page = catalog.list_plants(query).await?;
        Ok::<_, ApiError>(Json(PageDto::<PlantSummaryDto>::from_page(
            page, limit, offset,
        )))
    }
    .await;
    match result {
        Ok(json) => json.into_response(),
        Err(err) => err.into_response_at(&uri),
    }
}

/// Detalle de una planta con la fuente de cada dato.
#[utoipa::path(
    get,
    path = "/v1/plants/{id}",
    tag = "catalog",
    params(("id" = String, Path, description = "Identificador público de la planta, por ejemplo `lavandula-angustifolia`.")),
    responses(
        (status = 200, description = "Detalle de la planta", body = PlantDto),
        (status = 400, description = "Identificador no válido", body = ProblemDto, content_type = "application/problem+json"),
        (status = 404, description = "La planta no existe", body = ProblemDto, content_type = "application/problem+json"),
        (status = 405, description = "Método no permitido; la respuesta incluye `Allow: GET`", body = ProblemDto, content_type = "application/problem+json"),
        (status = 500, description = "Fallo interno", body = ProblemDto, content_type = "application/problem+json"),
    )
)]
pub(crate) async fn get_plant(
    State(catalog): State<AsyncCatalog>,
    OriginalUri(uri): OriginalUri,
    id: Result<Path<String>, PathRejection>,
) -> Response {
    // Un identificador que no se decodifica (por ejemplo `%FF`, UTF-8 inválido) se responde como `problem+json`, no con el texto plano de axum.
    let Path(id) = match id {
        Ok(path) => path,
        Err(_) => {
            return ApiError::bad_request("id", "el identificador no es válido")
                .into_response_at(&uri);
        }
    };
    match catalog.get_plant(PlantId(id)).await {
        Ok(Some(plant)) => Json(PlantDto::from(plant)).into_response(),
        Ok(None) => ApiError::NotFound {
            detail: "no existe una planta con ese identificador".to_string(),
        }
        .into_response_at(&uri),
        Err(err) => ApiError::from(err).into_response_at(&uri),
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use axum::body::Body;
    use axum::http::{HeaderMap, Method, Request, StatusCode, header};
    use catalog_core::domain::{Page, Plant, PlantSummary, Source};
    use catalog_core::repository::{CatalogRepository, RepositoryError};
    use http_body_util::BodyExt;
    use serde_json::Value;
    use tower::ServiceExt;

    use super::*;
    use crate::test_support::Fixture;

    /// Fixture y router sobre ella; la fixture debe vivir mientras se usa el router (borra su directorio al soltarse).
    fn app() -> (Fixture, Router) {
        let fixture = Fixture::standard();
        let router = router(AsyncCatalog::new(Arc::new(fixture.repo())));
        (fixture, router)
    }

    /// Envía una petición al router sin abrir ningún puerto: `oneshot` consume una copia del servicio y devuelve la respuesta.
    async fn send(app: &Router, method: Method, uri: &str) -> (StatusCode, HeaderMap, String) {
        let request = Request::builder()
            .method(method)
            .uri(uri)
            .body(Body::empty())
            .unwrap();
        let response = app.clone().oneshot(request).await.unwrap();
        let (parts, body) = response.into_parts();
        let bytes = body.collect().await.unwrap().to_bytes();
        (
            parts.status,
            parts.headers,
            String::from_utf8(bytes.to_vec()).unwrap(),
        )
    }

    async fn get_json(app: &Router, uri: &str) -> (StatusCode, Value) {
        let (status, headers, body) = send(app, Method::GET, uri).await;
        assert_eq!(headers[header::CONTENT_TYPE], "application/json", "{uri}");
        (status, serde_json::from_str(&body).unwrap())
    }

    /// Comprueba un error: estado, `Content-Type` exacto y cuerpo `problem+json`.
    async fn expect_problem(app: &Router, method: Method, uri: &str, status: StatusCode) -> Value {
        let (got, headers, body) = send(app, method, uri).await;
        assert_eq!(got, status, "{uri}: {body}");
        assert_eq!(
            headers[header::CONTENT_TYPE],
            "application/problem+json",
            "{uri}"
        );
        let json: Value = serde_json::from_str(&body).unwrap();
        assert_eq!(json["status"], status.as_u16());
        assert_eq!(json["type"], "about:blank");
        json
    }

    fn ids(page: &Value) -> Vec<&str> {
        page["items"]
            .as_array()
            .unwrap()
            .iter()
            .map(|i| i["id"].as_str().unwrap())
            .collect()
    }

    // ---- 7.1 ----

    #[tokio::test]
    async fn healthz_is_ok_and_outside_v1() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/healthz").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(json, serde_json::json!({"status": "ok"}));
        expect_problem(&app, Method::GET, "/v1/healthz", StatusCode::NOT_FOUND).await;
    }

    #[tokio::test]
    async fn sources_have_the_expected_fields_sorted_by_id() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/v1/sources").await;
        assert_eq!(status, StatusCode::OK);
        let list = json.as_array().unwrap();
        assert_eq!(list.len(), 2);
        assert_eq!(list[0]["id"], "a");
        assert_eq!(list[1]["id"], "b");
        let mut keys: Vec<&str> = list[0]
            .as_object()
            .unwrap()
            .keys()
            .map(String::as_str)
            .collect();
        keys.sort();
        assert_eq!(
            keys,
            [
                "checksum", "citation", "id", "license", "name", "url", "version"
            ]
        );
        assert_eq!(list[0]["url"], "https://example.test/a");
    }

    // ---- 7.2 ----

    #[tokio::test]
    async fn lists_twenty_by_default_with_full_total() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/v1/plants").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(json["items"].as_array().unwrap().len(), 20);
        assert_eq!(json["total"], 31);
        assert_eq!(
            (json["limit"].as_u64(), json["offset"].as_u64()),
            (Some(20), Some(0))
        );
        let first = &json["items"][0];
        assert_eq!(first["id"], "fillerus-01");
        assert_eq!(first["scientificName"], "Fillerus 01");
        assert_eq!(first["family"], "Fillerfam");
        assert_eq!(first["commonNames"][0]["text"], "Filler 01");
        assert_eq!(first["commonNames"][0]["language"], "en");
    }

    #[tokio::test]
    async fn searches_scientific_and_common_names() {
        let (_fixture, app) = app();
        let (_, sci) = get_json(&app, "/v1/plants?q=lavandula").await;
        assert_eq!(ids(&sci), ["lavandula-angustifolia", "lavandula-latifolia"]);
        assert_eq!(sci["total"], 2);
        let (_, common) = get_json(&app, "/v1/plants?q=%C3%91AND%C3%9A%20%20caf%C3%A9").await;
        assert_eq!(ids(&common), ["mentha-x-piperita"]);
    }

    #[tokio::test]
    async fn paginates_with_constant_total() {
        let (_fixture, app) = app();
        let (_, page) = get_json(&app, "/v1/plants?limit=5&offset=24").await;
        assert_eq!(page["total"], 31);
        assert_eq!(
            ids(&page),
            [
                "fillerus-25",
                "lavandula-angustifolia",
                "lavandula-latifolia",
                "mentha-x-piperita",
                "twin-a"
            ]
        );
        assert_eq!(
            (page["limit"].as_u64(), page["offset"].as_u64()),
            (Some(5), Some(24))
        );
    }

    #[tokio::test]
    async fn offset_past_total_and_no_matches_are_empty_lists() {
        let (_fixture, app) = app();
        let (status, past) = get_json(&app, "/v1/plants?offset=500").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            (
                past["items"].as_array().unwrap().len(),
                past["total"].as_u64()
            ),
            (0, Some(31))
        );
        let (status, none) = get_json(&app, "/v1/plants?q=zzzz").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            (
                none["items"].as_array().unwrap().len(),
                none["total"].as_u64()
            ),
            (0, Some(0))
        );
    }

    #[tokio::test]
    async fn blank_query_equals_no_filter() {
        let (_fixture, app) = app();
        let (_, all) = get_json(&app, "/v1/plants?limit=100").await;
        for uri in ["/v1/plants?limit=100&q=", "/v1/plants?limit=100&q=%20%20"] {
            let (_, json) = get_json(&app, uri).await;
            assert_eq!(json, all, "{uri}");
        }
    }

    #[tokio::test]
    async fn pattern_characters_are_literal() {
        let (_fixture, app) = app();
        for uri in ["/v1/plants?q=%25", "/v1/plants?q=_"] {
            let (_, json) = get_json(&app, uri).await;
            assert_eq!(ids(&json), ["zea-mays"], "{uri}");
        }
    }

    // ---- 7.3 ----

    fn assert_camel_case(value: &Value) {
        match value {
            Value::Object(map) => {
                for (key, v) in map {
                    assert!(
                        key.chars().all(|c| c.is_ascii_alphanumeric())
                            && key.chars().next().is_some_and(|c| c.is_ascii_lowercase()),
                        "clave no camelCase: {key}"
                    );
                    assert_camel_case(v);
                }
            }
            Value::Array(items) => items.iter().for_each(assert_camel_case),
            _ => {}
        }
    }

    #[tokio::test]
    async fn detail_with_uses_and_two_sources() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert_eq!(status, StatusCode::OK);
        assert_camel_case(&json);
        assert_eq!(json["scientificName"], "Lavandula angustifolia");
        assert_eq!(
            json["family"],
            serde_json::json!({"value": "Lamiaceae", "sources": ["a"]})
        );
        assert_eq!(json["names"][0]["kind"], "scientific");
        assert_eq!(json["names"][0]["sources"], serde_json::json!(["a", "b"]));
        assert_eq!(json["names"][3]["kind"], "common");
        assert_eq!(
            json["parts"][1],
            serde_json::json!({"label": "Leaf", "sources": ["a", "b"]})
        );
        assert_eq!(
            json["uses"][1],
            serde_json::json!({
                "activity": "Sedative",
                "language": "en",
                "reference": {"id": "ref-2", "citation": "Jones 2001"},
                "sources": ["a", "b"]
            })
        );
    }

    #[tokio::test]
    async fn detail_without_uses_or_family() {
        let (_fixture, app) = app();
        let (_, latifolia) = get_json(&app, "/v1/plants/lavandula-latifolia").await;
        assert_eq!(latifolia["uses"], serde_json::json!([]));
        assert_eq!(latifolia["parts"], serde_json::json!([]));
        let (_, mentha) = get_json(&app, "/v1/plants/mentha-x-piperita").await;
        assert_eq!(mentha["family"], Value::Null);
        assert_camel_case(&mentha);
    }

    #[tokio::test]
    async fn serves_the_openapi_document_outside_v1() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/openapi.json").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(json["info"]["title"], "Boticario AI Catalog API");
        assert!(json["paths"]["/v1/plants/{id}"].is_object());
    }

    // ---- 7.7: la fixture usa las fuentes genéricas `a` y `b`, y todos los endpoints de /v1 responden ----

    #[tokio::test]
    async fn every_v1_endpoint_works_with_non_dataset_sources() {
        let (_fixture, app) = app();
        let known = ["a", "b"];

        let (status, sources) = get_json(&app, "/v1/sources").await;
        assert_eq!(status, StatusCode::OK);
        let source_ids: Vec<&str> = sources
            .as_array()
            .unwrap()
            .iter()
            .map(|s| s["id"].as_str().unwrap())
            .collect();
        assert_eq!(source_ids, known);

        let (status, page) = get_json(&app, "/v1/plants?q=lavandula").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(page["total"], 2);

        let (status, detail) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert_eq!(status, StatusCode::OK);
        // Cada fuente citada en el detalle es una de las de la fixture.
        let mut cited = Vec::new();
        for group in ["names", "parts", "uses"] {
            for item in detail[group].as_array().unwrap() {
                cited.extend(item["sources"].as_array().unwrap());
            }
        }
        cited.extend(detail["family"]["sources"].as_array().unwrap());
        assert!(!cited.is_empty());
        assert!(cited.iter().all(|s| known.contains(&s.as_str().unwrap())));
    }

    // ---- 7.4 ----

    #[tokio::test]
    async fn invalid_limit_is_a_400_naming_the_parameter() {
        let (_fixture, app) = app();
        for value in ["abc", "0", "-1", "101", ""] {
            let uri = format!("/v1/plants?limit={value}");
            let json = expect_problem(&app, Method::GET, &uri, StatusCode::BAD_REQUEST).await;
            assert_eq!(json["param"], "limit", "{uri}");
            assert!(json["detail"].as_str().unwrap().contains("limit"));
            assert_eq!(json["instance"], "/v1/plants");
        }
    }

    #[tokio::test]
    async fn invalid_offset_is_a_400_naming_the_parameter() {
        let (_fixture, app) = app();
        for value in ["abc", "-1", "1.5"] {
            let uri = format!("/v1/plants?offset={value}");
            let json = expect_problem(&app, Method::GET, &uri, StatusCode::BAD_REQUEST).await;
            assert_eq!(json["param"], "offset", "{uri}");
        }
    }

    #[tokio::test]
    async fn undecodable_plant_id_is_a_problem_json_400() {
        let (_fixture, app) = app();
        let json =
            expect_problem(&app, Method::GET, "/v1/plants/%FF", StatusCode::BAD_REQUEST).await;
        assert_eq!(json["param"], "id");
        assert_eq!(json["instance"], "/v1/plants/%FF");
    }

    #[tokio::test]
    async fn query_text_is_limited_to_200_characters() {
        let (_fixture, app) = app();
        // 200 caracteres multibyte: el límite cuenta caracteres, no bytes.
        let ok = format!("/v1/plants?q={}", "%C3%A1".repeat(200));
        let (status, _) = get_json(&app, &ok).await;
        assert_eq!(status, StatusCode::OK);
        let long = format!("/v1/plants?q={}", "a".repeat(201));
        let json = expect_problem(&app, Method::GET, &long, StatusCode::BAD_REQUEST).await;
        assert_eq!(json["param"], "q");
    }

    #[tokio::test]
    async fn control_characters_in_q_are_rejected() {
        let (_fixture, app) = app();
        for uri in [
            "/v1/plants?q=%00zzzz",
            "/v1/plants?q=a%00",
            "/v1/plants?q=a%0Ab",
        ] {
            let json = expect_problem(&app, Method::GET, uri, StatusCode::BAD_REQUEST).await;
            assert_eq!(json["param"], "q", "{uri}");
        }
    }

    #[tokio::test]
    async fn offset_is_limited_to_int32() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/v1/plants?offset=2147483647").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(json["items"].as_array().unwrap().len(), 0);
        assert_eq!(json["total"], 31);
        for value in ["2147483648", "4294967295"] {
            let uri = format!("/v1/plants?offset={value}");
            let json = expect_problem(&app, Method::GET, &uri, StatusCode::BAD_REQUEST).await;
            assert_eq!(json["param"], "offset", "{uri}");
        }
    }

    #[tokio::test]
    async fn boundary_limits_and_unknown_params_are_accepted() {
        let (_fixture, app) = app();
        for uri in ["/v1/plants?limit=1", "/v1/plants?limit=100&extra=1"] {
            let (status, _) = get_json(&app, uri).await;
            assert_eq!(status, StatusCode::OK, "{uri}");
        }
    }

    #[tokio::test]
    async fn unknown_plant_and_unknown_route_are_404() {
        let (_fixture, app) = app();
        let json =
            expect_problem(&app, Method::GET, "/v1/plants/nope", StatusCode::NOT_FOUND).await;
        assert_eq!(json["instance"], "/v1/plants/nope");
        expect_problem(&app, Method::GET, "/v1/unknown", StatusCode::NOT_FOUND).await;
        expect_problem(&app, Method::GET, "/", StatusCode::NOT_FOUND).await;
    }

    #[tokio::test]
    async fn write_methods_are_405_and_change_nothing() {
        let (_fixture, app) = app();
        let (_, before) = get_json(&app, "/v1/plants?limit=100").await;
        for (method, uri) in [
            (Method::POST, "/v1/plants"),
            (Method::DELETE, "/v1/plants/zea-mays"),
            (Method::PUT, "/v1/plants/zea-mays"),
            (Method::PATCH, "/v1/sources"),
            (Method::POST, "/healthz"),
        ] {
            expect_problem(&app, method.clone(), uri, StatusCode::METHOD_NOT_ALLOWED).await;
            let (_, headers, _) = send(&app, method, uri).await;
            assert_eq!(headers[header::ALLOW], "GET", "{uri}");
        }
        let (_, after) = get_json(&app, "/v1/plants?limit=100").await;
        assert_eq!(before, after);
        let (status, _) = get_json(&app, "/v1/plants/zea-mays").await;
        assert_eq!(status, StatusCode::OK);
    }

    /// Repositorio cuyo almacenamiento siempre falla, con un mensaje que no debe llegar al cliente.
    struct FailingRepository;

    const SECRET: &str = "ruta secreta /tmp/x.db";

    impl CatalogRepository for FailingRepository {
        fn list_plants(&self, _: &ListQuery) -> Result<Page<PlantSummary>, RepositoryError> {
            Err(RepositoryError::Storage(SECRET.to_string()))
        }
        fn get_plant(&self, _: &PlantId) -> Result<Option<Plant>, RepositoryError> {
            Err(RepositoryError::Storage(SECRET.to_string()))
        }
        fn list_sources(&self) -> Result<Vec<Source>, RepositoryError> {
            Err(RepositoryError::Storage(SECRET.to_string()))
        }
    }

    #[tokio::test]
    async fn internal_failures_do_not_leak_details() {
        let app = router(AsyncCatalog::new(Arc::new(FailingRepository)));
        for uri in ["/v1/plants", "/v1/plants/x", "/v1/sources"] {
            let (status, headers, body) = send(&app, Method::GET, uri).await;
            assert_eq!(status, StatusCode::INTERNAL_SERVER_ERROR, "{uri}");
            assert_eq!(headers[header::CONTENT_TYPE], "application/problem+json");
            assert!(!body.contains("secret") && !body.contains("/tmp"), "{body}");
            let json: Value = serde_json::from_str(&body).unwrap();
            assert_eq!(json["detail"], "error interno");
        }
    }
}
