//! Router HTTP v1 (solo lectura) y sus handlers.
//!
//! Los handlers dependen únicamente de [`AsyncCatalog`], que llega por el estado de Axum.
//! Para el campo `instance` de los errores se usa `OriginalUri`: dentro de `nest("/v1", …)` el `Uri` normal ya llega sin el prefijo.

use std::collections::HashMap;
use std::sync::Arc;

use axum::extract::rejection::{PathRejection, QueryRejection};
use axum::extract::{OriginalUri, Path, Query, State};
use axum::http::{HeaderValue, header};
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router, middleware};
use catalog_core::domain::{DEFAULT_LIMIT, ListQuery, MAX_LIMIT, PlantId};

use crate::async_catalog::AsyncCatalog;
use crate::auth::{ApiTokens, require_token};
use crate::dto::{HealthDto, PageDto, PlantDto, PlantSummaryDto, ProblemDto};
use crate::error::ApiError;
use crate::openapi::openapi;

/// Construye el router completo: `/health` y `/v1/...`, con errores `problem+json` para rutas y métodos desconocidos.
///
/// Todo camino bajo `/v1` exige un token de `tokens` (`Authorization: Bearer`), también las rutas inexistentes y los métodos no permitidos. La capa va después de declarar los `fallback`, porque `route_layer` no los cubre.
pub fn router(catalog: AsyncCatalog, tokens: ApiTokens) -> Router {
    let v1 = Router::new()
        .route("/plants", get(list_plants))
        .route("/plants/{id}", get(get_plant));
    Router::new()
        .route("/health", get(health))
        .route("/openapi.json", get(openapi_json))
        .nest("/v1", v1)
        .fallback(not_found)
        .method_not_allowed_fallback(method_not_allowed)
        .with_state(catalog)
        .layer(middleware::from_fn_with_state(
            Arc::new(tokens),
            require_token,
        ))
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
    path = "/health",
    tag = "health",
    responses(
        (status = 200, description = "El servicio está activo", body = HealthDto),
        (status = 405, description = "Método no permitido; la respuesta incluye `Allow: GET`", body = ProblemDto, content_type = "application/problem+json"),
    )
)]
pub(crate) async fn health() -> Json<HealthDto> {
    Json(HealthDto { status: "ok" })
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
    security(("bearerAuth" = [])),
    responses(
        (status = 200, description = "Página de plantas en orden de nombre científico e identificador", body = PageDto<PlantSummaryDto>),
        (status = 400, description = "Parámetro inválido", body = ProblemDto, content_type = "application/problem+json"),
        (status = 401, description = "Falta el token de API o no es válido", body = ProblemDto, content_type = "application/problem+json", headers(("WWW-Authenticate" = String, description = "Siempre `Bearer`"))),
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

/// Detalle de una planta.
#[utoipa::path(
    get,
    path = "/v1/plants/{id}",
    tag = "catalog",
    params(("id" = String, Path, description = "Identificador público de la planta, por ejemplo `lavandula-angustifolia`.")),
    security(("bearerAuth" = [])),
    responses(
        (status = 200, description = "Detalle de la planta", body = PlantDto),
        (status = 400, description = "Identificador no válido", body = ProblemDto, content_type = "application/problem+json"),
        (status = 401, description = "Falta el token de API o no es válido", body = ProblemDto, content_type = "application/problem+json", headers(("WWW-Authenticate" = String, description = "Siempre `Bearer`"))),
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
    use catalog_core::domain::{Page, Plant, PlantSummary};
    use catalog_core::repository::{CatalogRepository, RepositoryError};
    use http_body_util::BodyExt;
    use serde_json::Value;
    use tower::ServiceExt;

    use super::*;
    use crate::test_support::Fixture;

    /// Token ficticio de prueba; no es un secreto.
    const TEST_TOKEN: &str = "test-token-not-a-secret-0000000000000000";

    fn test_tokens() -> ApiTokens {
        ApiTokens::parse(TEST_TOKEN).unwrap()
    }

    /// Fixture y router sobre ella; la fixture debe vivir mientras se usa el router (borra su directorio al soltarse).
    fn app() -> (Fixture, Router) {
        let fixture = Fixture::standard();
        let router = router(AsyncCatalog::new(Arc::new(fixture.repo())), test_tokens());
        (fixture, router)
    }

    /// Envía una petición con el token de prueba válido.
    async fn send(app: &Router, method: Method, uri: &str) -> (StatusCode, HeaderMap, String) {
        let value = format!("Bearer {TEST_TOKEN}");
        send_with(app, method, uri, Some(&value)).await
    }

    /// Envía una petición al router sin abrir ningún puerto: `oneshot` consume una copia del servicio y devuelve la respuesta. `authorization` es el valor literal de la cabecera, si se envía.
    async fn send_with(
        app: &Router,
        method: Method,
        uri: &str,
        authorization: Option<&str>,
    ) -> (StatusCode, HeaderMap, String) {
        let mut builder = Request::builder().method(method).uri(uri);
        if let Some(value) = authorization {
            builder = builder.header(header::AUTHORIZATION, value);
        }
        let request = builder.body(Body::empty()).unwrap();
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
    async fn health_is_ok_and_outside_v1() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/health").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(json, serde_json::json!({"status": "ok"}));
        expect_problem(&app, Method::GET, "/v1/health", StatusCode::NOT_FOUND).await;
    }

    #[tokio::test]
    async fn sources_endpoint_no_longer_exists() {
        let (_fixture, app) = app();
        let json = expect_problem(&app, Method::GET, "/v1/sources", StatusCode::NOT_FOUND).await;
        assert_eq!(json["instance"], "/v1/sources");
    }

    // ---- 7.2 ----

    #[tokio::test]
    async fn lists_twenty_by_default_with_full_total() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/v1/plants").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(json["items"].as_array().unwrap().len(), 20);
        assert_eq!(json["total"], 34);
        assert_eq!(
            (json["limit"].as_u64(), json["offset"].as_u64()),
            (Some(20), Some(0))
        );
        // Las tres primeras son las plantas especiales de la fixture (Abutilon, Conium, Eucalyptus).
        let first = &json["items"][3];
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
        let (_, page) = get_json(&app, "/v1/plants?limit=5&offset=27").await;
        assert_eq!(page["total"], 34);
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
            (Some(5), Some(27))
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
            (0, Some(34))
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

    /// Recorre el JSON entero y devuelve la ruta de toda clave `sources`, en cualquier nivel.
    fn find_sources_keys(value: &Value, path: &str, found: &mut Vec<String>) {
        match value {
            Value::Object(map) => {
                for (key, v) in map {
                    let here = format!("{path}.{key}");
                    if key == "sources" {
                        found.push(here.clone());
                    }
                    find_sources_keys(v, &here, found);
                }
            }
            Value::Array(items) => {
                for (i, v) in items.iter().enumerate() {
                    find_sources_keys(v, &format!("{path}[{i}]"), found);
                }
            }
            _ => {}
        }
    }

    #[tokio::test]
    async fn detail_with_uses_has_a_flat_shape() {
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert_eq!(status, StatusCode::OK);
        assert_camel_case(&json);
        assert_eq!(json["scientificName"], "Lavandula angustifolia");
        assert_eq!(json["family"], "Lamiaceae");
        assert_eq!(
            json["names"][0],
            serde_json::json!({"text": "Lavandula angustifolia", "kind": "scientific", "language": "la"})
        );
        assert_eq!(json["names"][3]["kind"], "common");
        assert_eq!(json["parts"][1], serde_json::json!({"label": "Leaf"}));
        assert_eq!(
            json["uses"][1],
            serde_json::json!({
                "activity": "Sedative",
                "language": "en",
                "reference": {"id": "ref-2", "citation": "Jones 2001"}
            })
        );
    }

    #[tokio::test]
    async fn detail_never_contains_a_sources_key() {
        let (_fixture, app) = app();
        // Plantas con y sin familia, con y sin usos: ninguna debe llevar `sources` en ningún nivel.
        for id in [
            "lavandula-angustifolia",
            "lavandula-latifolia",
            "mentha-x-piperita",
        ] {
            let (status, json) = get_json(&app, &format!("/v1/plants/{id}")).await;
            assert_eq!(status, StatusCode::OK);
            let mut found = Vec::new();
            find_sources_keys(&json, "$", &mut found);
            assert!(found.is_empty(), "{id}: claves `sources` en {found:?}");
        }
        let (_, list) = get_json(&app, "/v1/plants?limit=100").await;
        let mut found = Vec::new();
        find_sources_keys(&list, "$", &mut found);
        assert!(found.is_empty(), "listado: {found:?}");
    }

    #[tokio::test]
    async fn family_is_text_or_null() {
        let (_fixture, app) = app();
        let (_, with_family) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert!(with_family["family"].is_string());
        let (_, without) = get_json(&app, "/v1/plants/mentha-x-piperita").await;
        assert_eq!(without["family"], Value::Null);
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

    // ---- nombre para mostrar y contenido consolidado ----

    #[tokio::test]
    async fn list_items_and_detail_carry_display_name_as_text() {
        // Escenarios «Contenido de cada elemento» y «Nombre para mostrar en el listado».
        let (_fixture, app) = app();
        let (_, list) = get_json(&app, "/v1/plants?limit=100").await;
        for item in list["items"].as_array().unwrap() {
            assert!(item["displayName"].is_string(), "{item}");
        }
        let (_, lavender) = get_json(&app, "/v1/plants?q=lavandula%20angustifolia").await;
        assert_eq!(lavender["items"][0]["displayName"], "Lavanda");
        assert_eq!(lavender["items"][0]["commonNames"][0]["text"], "Lavanda");
        // Planta sin nombre común: el nombre para mostrar es el científico.
        let (_, twin) = get_json(&app, "/v1/plants?q=twin").await;
        assert_eq!(twin["items"][0]["displayName"], "Twin plant");
        assert_eq!(twin["items"][0]["commonNames"], serde_json::json!([]));
        // Solo nombres en otros idiomas: el nombre para mostrar no es uno de ellos.
        let (_, velvet) = get_json(&app, "/v1/plants?q=abutilon").await;
        assert_eq!(velvet["items"][0]["displayName"], "Abutilon theophrasti");
        assert_eq!(velvet["items"][0]["commonNames"][1]["text"], "Velvetleaf");

        let (_, detail) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert_eq!(detail["displayName"], "Lavanda");
        assert_eq!(detail["names"][2]["text"], "Lavanda");
        let (_, latifolia) = get_json(&app, "/v1/plants/lavandula-latifolia").await;
        assert_eq!(latifolia["displayName"], "Lavandula latifolia");
    }

    #[tokio::test]
    async fn complete_detail_has_every_consolidated_field() {
        // Escenario «Planta con todos los campos».
        let (_fixture, app) = app();
        let (status, json) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert_eq!(status, StatusCode::OK);
        assert_camel_case(&json);
        assert_eq!(json["synonyms"], serde_json::json!(["Lavandula vera"]));
        assert_eq!(json["description"], "Arbusto aromático de flores violetas.");
        assert_eq!(json["origin"], "Sureste de Europa.");
        assert_eq!(json["oil"], serde_json::json!({"type": "Esencial"}));
        assert_eq!(
            json["useGroups"][0],
            serde_json::json!({
                "activity": "Sedante",
                "activitySource": "Sedative",
                "count": 12,
                "countries": ["Turquía", "Francia", "Otros lugares"],
                "references": [
                    {"id": "ref-2", "citation": "Jones, A. 2001. Plantas medicinales. Editorial Ejemplo, Madrid.", "resolved": true},
                    {"id": null, "citation": "Woi.6 (sin resolver)", "resolved": false}
                ]
            })
        );
        assert_eq!(
            json["goals"][1],
            serde_json::json!({
                "id": "otros-objetivos",
                "name": "Otros objetivos",
                "subarea": "Digestión",
                "area": "Digestión lenta",
                "evidence": "La agencia tiene una entrada de lista en esta área.",
                "references": [
                    {"id": "ref-1", "citation": "Smith 1990"},
                    {"id": "ref-ema-skin", "citation": "Monografía sobre la piel"}
                ]
            })
        );
        assert_eq!(json["goals"][0]["subarea"], Value::Null);
        assert_eq!(json["safety"]["level"], "medio");
        assert_eq!(json["safety"]["text"], "Evitar durante el embarazo.");
        assert_eq!(json["safety"]["references"][0]["id"], "ref-1");
        assert_eq!(
            json["image"],
            serde_json::json!({
                "url": "https://imagenes.invalid/lavandula-angustifolia.jpg",
                "pageUrl": "https://commons.wikimedia.org/wiki/File:lavandula-angustifolia.jpg",
                "author": "Autora Ejemplo",
                "license": "CC BY-SA 4.0",
                "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attributionRequired": true
            })
        );
    }

    #[tokio::test]
    async fn uses_keep_the_label_while_use_groups_carry_the_full_citation() {
        // Escenarios «Cita de `uses` sin cambios» y «Cita completa en los grupos de uso».
        let (_fixture, app) = app();
        let (_, json) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert_eq!(json["uses"][0]["reference"]["citation"], "Smith 1990");
        assert_eq!(
            json["useGroups"][1]["references"][0]["citation"],
            "Smith, J. 1990. Registros de plantas. Publicado por el autor, Lisboa."
        );
        assert_eq!(json["uses"].as_array().unwrap().len(), 2);
    }

    #[tokio::test]
    async fn empty_detail_has_null_and_empty_consolidated_fields() {
        // Escenario «Planta con campos vacíos»: los campos están presentes aunque vacíos.
        let (_fixture, app) = app();
        let (_, json) = get_json(&app, "/v1/plants/lavandula-latifolia").await;
        for key in ["description", "origin", "oil", "safety", "image"] {
            assert_eq!(json[key], Value::Null, "{key}");
        }
        for key in ["synonyms", "useGroups", "goals", "uses", "parts"] {
            assert_eq!(json[key], serde_json::json!([]), "{key}");
        }
    }

    #[tokio::test]
    async fn safety_distinguishes_no_data_from_no_level() {
        // Escenarios «Seguridad sin datos» y «Seguridad sin nivel».
        let (_fixture, app) = app();
        let (_, none) = get_json(&app, "/v1/plants/zea-mays").await;
        assert_eq!(none["safety"], Value::Null);
        let (_, eucalyptus) = get_json(&app, "/v1/plants/eucalyptus-globulus").await;
        assert_eq!(eucalyptus["safety"]["level"], Value::Null);
        assert_eq!(
            eucalyptus["safety"]["text"],
            "Contraindicado en niños pequeños."
        );
        assert_eq!(
            eucalyptus["safety"]["references"][0]["id"],
            "ref-ema-safety"
        );
        let (_, toxic) = get_json(&app, "/v1/plants/conium-maculatum").await;
        assert_eq!(toxic["safety"]["level"], "alto");
    }

    #[tokio::test]
    async fn image_is_served_as_data_without_network_access() {
        // Escenarios «Sin imagen» y «Sin acceso a la red»: la URL de la fixture es de un dominio `.invalid`
        // que nunca resuelve, así que un 200 con los datos prueba que la API no descarga nada.
        let (_fixture, app) = app();
        let (status, toxic) = get_json(&app, "/v1/plants/conium-maculatum").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(
            toxic["image"]["url"],
            "https://imagenes.invalid/conium-maculatum.jpg"
        );
        assert_eq!(toxic["image"]["author"], Value::Null);
        assert_eq!(toxic["image"]["licenseUrl"], Value::Null);
        assert_eq!(toxic["image"]["attributionRequired"], false);
        let (_, none) = get_json(&app, "/v1/plants/lavandula-latifolia").await;
        assert_eq!(none["image"], Value::Null);
    }

    #[tokio::test]
    async fn pending_content_and_review_flags_are_not_served() {
        // Avance de la regla de 3.5: el grupo sin cita resuelta y el objetivo pendiente no salen, y ningún flag se expone.
        let (_fixture, app) = app();
        let (_, json) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        let text = json.to_string();
        assert!(!text.contains("Actividad pendiente"), "{text}");
        assert!(!text.contains("Estrés"), "{text}");
        assert!(!text.contains("cita-sin-resolver"), "{text}");
        assert!(!text.contains("reviewFlags"), "{text}");
    }

    #[tokio::test]
    async fn openapi_declares_display_name_in_summary_and_detail() {
        let (_fixture, app) = app();
        let (_, doc) = get_json(&app, "/openapi.json").await;
        for schema in ["PlantSummaryDto", "PlantDto"] {
            let property = &doc["components"]["schemas"][schema]["properties"]["displayName"];
            assert_eq!(property["type"], "string", "{schema}");
            let required = doc["components"]["schemas"][schema]["required"]
                .as_array()
                .unwrap();
            assert!(required.iter().any(|r| r == "displayName"), "{schema}");
        }
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

        let (status, page) = get_json(&app, "/v1/plants?q=lavandula").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(page["total"], 2);

        let (status, detail) = get_json(&app, "/v1/plants/lavandula-angustifolia").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(detail["scientificName"], "Lavandula angustifolia");
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
        assert_eq!(json["total"], 34);
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
            (Method::PATCH, "/v1/plants/zea-mays"),
            (Method::POST, "/health"),
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
    }

    #[tokio::test]
    async fn internal_failures_do_not_leak_details() {
        let app = router(
            AsyncCatalog::new(Arc::new(FailingRepository)),
            test_tokens(),
        );
        for uri in ["/v1/plants", "/v1/plants/x"] {
            let (status, headers, body) = send(&app, Method::GET, uri).await;
            assert_eq!(status, StatusCode::INTERNAL_SERVER_ERROR, "{uri}");
            assert_eq!(headers[header::CONTENT_TYPE], "application/problem+json");
            assert!(!body.contains("secret") && !body.contains("/tmp"), "{body}");
            let json: Value = serde_json::from_str(&body).unwrap();
            assert_eq!(json["detail"], "error interno");
        }
    }

    // ---- autorización por token ----

    #[tokio::test]
    async fn valid_token_is_accepted_in_any_scheme_case() {
        let (_fixture, app) = app();
        for scheme in ["Bearer", "bearer", "BEARER"] {
            let value = format!("{scheme} {TEST_TOKEN}");
            let (status, _, _) = send_with(&app, Method::GET, "/v1/plants", Some(&value)).await;
            assert_eq!(status, StatusCode::OK, "{scheme}");
        }
        // Varios espacios entre el esquema y el token.
        let value = format!("Bearer   {TEST_TOKEN}");
        let (status, _, _) = send_with(&app, Method::GET, "/v1/plants", Some(&value)).await;
        assert_eq!(status, StatusCode::OK);
    }

    #[tokio::test]
    async fn rejected_credentials_all_get_the_same_401() {
        let (_fixture, app) = app();
        let prefix = format!("Bearer {}", &TEST_TOKEN[..TEST_TOKEN.len() - 1]);
        let wrong = "Bearer test-token-not-a-secret-ffffffffffffffff".to_string();
        let basic = format!("Basic {TEST_TOKEN}");
        let cases: [Option<&str>; 7] = [
            None,
            Some(&wrong),
            Some(&basic),
            Some(&prefix),
            Some(""),
            Some("Bearer"),
            Some("Bearer "),
        ];
        let mut reference: Option<(HeaderMap, String)> = None;
        for authorization in cases {
            let (status, headers, body) =
                send_with(&app, Method::GET, "/v1/plants", authorization).await;
            assert_eq!(status, StatusCode::UNAUTHORIZED, "{authorization:?}");
            assert_eq!(
                headers[header::CONTENT_TYPE],
                "application/problem+json",
                "{authorization:?}"
            );
            assert_eq!(headers[header::WWW_AUTHENTICATE], "Bearer");
            match &reference {
                None => reference = Some((headers, body)),
                Some((ref_headers, ref_body)) => {
                    assert_eq!(&body, ref_body, "{authorization:?}");
                    assert_eq!(&headers, ref_headers, "{authorization:?}");
                }
            }
        }
        let body = reference.unwrap().1;
        assert!(!body.contains("not-a-secret"), "{body}");
    }

    #[tokio::test]
    async fn non_text_authorization_header_is_unauthorized() {
        let (_fixture, app) = app();
        let request = Request::builder()
            .uri("/v1/plants")
            .header(
                header::AUTHORIZATION,
                header::HeaderValue::from_bytes(b"Bearer \xff\xfe").unwrap(),
            )
            .body(Body::empty())
            .unwrap();
        let response = app.clone().oneshot(request).await.unwrap();
        assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn unknown_paths_and_methods_under_v1_need_the_token_first() {
        let (_fixture, app) = app();
        for (method, uri) in [
            (Method::GET, "/v1/no-existe"),
            (Method::GET, "/v1"),
            (Method::GET, "/v1/"),
            (Method::POST, "/v1/plants"),
            (Method::GET, "/v1/plants/x/y"),
        ] {
            let (status, headers, _) = send_with(&app, method.clone(), uri, None).await;
            assert_eq!(status, StatusCode::UNAUTHORIZED, "{method} {uri}");
            assert_eq!(headers[header::WWW_AUTHENTICATE], "Bearer");
        }
        // Con token vuelven los errores normales.
        expect_problem(
            &app,
            Method::POST,
            "/v1/plants",
            StatusCode::METHOD_NOT_ALLOWED,
        )
        .await;
        expect_problem(&app, Method::GET, "/v1/no-existe", StatusCode::NOT_FOUND).await;
    }

    #[tokio::test]
    async fn health_and_openapi_are_public() {
        let (_fixture, app) = app();
        for uri in ["/health", "/openapi.json"] {
            let (status, _, _) = send_with(&app, Method::GET, uri, None).await;
            assert_eq!(status, StatusCode::OK, "{uri}");
        }
        // Fuera de `/v1` un camino desconocido sigue siendo 404, y `/v10` no cuenta como `/v1`.
        for uri in ["/nope", "/v10"] {
            let (status, _, _) = send_with(&app, Method::GET, uri, None).await;
            assert_eq!(status, StatusCode::NOT_FOUND, "{uri}");
        }
    }

    #[tokio::test]
    async fn any_configured_token_works() {
        let fixture = Fixture::standard();
        let second = "test-token-not-a-secret-1111111111111111";
        let tokens = ApiTokens::parse(&format!("{TEST_TOKEN},{second}")).unwrap();
        let app = router(AsyncCatalog::new(Arc::new(fixture.repo())), tokens);
        let value = format!("Bearer {second}");
        let (status, _, _) = send_with(&app, Method::GET, "/v1/plants", Some(&value)).await;
        assert_eq!(status, StatusCode::OK);
    }
}
