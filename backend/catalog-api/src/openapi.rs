//! Documento OpenAPI de la API, generado desde el código.
//!
//! `#[derive(OpenApi)]` reúne las rutas anotadas con `#[utoipa::path]` y los esquemas de los DTOs (`ToSchema`) en un documento.
//! El documento versionado en `backend/openapi.json` debe coincidir con el generado: un test lo comprueba.

use utoipa::openapi::security::{HttpAuthScheme, HttpBuilder, SecurityScheme};
use utoipa::{Modify, OpenApi};

use crate::dto::{
    CommonNameDto, CreditDto, GoalDto, HealthDto, ImageDto, NameDto, NameKindDto, OilDto, PageDto,
    PartDto, PlantDto, PlantSummaryDto, ProblemDto, ReferenceDto, SafetyDto, SafetyLevelDto,
    UseDto, UseGroupDto, UseGroupReferenceDto,
};
use crate::http;

/// Definición del documento: metadatos, rutas y esquemas.
#[derive(OpenApi)]
#[openapi(
    info(
        title = "Boticario AI Catalog API",
        version = "1",
        description = "API de solo lectura del catálogo de plantas. Dentro de `/v1` solo habrá cambios aditivos: los clientes deben ignorar los campos desconocidos. Las rutas desconocidas responden 404 y los métodos distintos de `GET` responden 405, ambos como `application/problem+json`."
    ),
    paths(http::health, http::openapi_json, http::list_plants, http::get_plant),
    components(schemas(
        HealthDto,
        CommonNameDto,
        PlantSummaryDto,
        PageDto<PlantSummaryDto>,
        NameKindDto,
        NameDto,
        PartDto,
        ReferenceDto,
        UseDto,
        OilDto,
        UseGroupReferenceDto,
        UseGroupDto,
        GoalDto,
        SafetyLevelDto,
        SafetyDto,
        ImageDto,
        CreditDto,
        PlantDto,
        ProblemDto,
    )),
    modifiers(&BearerAuth)
)]
struct ApiDoc;

/// Declara el esquema de seguridad `bearerAuth`.
///
/// Las operaciones de `/v1` lo exigen con `security(...)` en su propia anotación; `/health` y `/openapi.json` no declaran seguridad y quedan públicas.
struct BearerAuth;

impl Modify for BearerAuth {
    fn modify(&self, openapi: &mut utoipa::openapi::OpenApi) {
        let components = openapi.components.get_or_insert_with(Default::default);
        components.add_security_scheme(
            "bearerAuth",
            SecurityScheme::Http(
                HttpBuilder::new()
                    .scheme(HttpAuthScheme::Bearer)
                    .description(Some(
                        "Token de API en la cabecera `Authorization: Bearer <token>`. Es una credencial de acceso compartida por la app: no identifica a usuarios.",
                    ))
                    .build(),
            ),
        );
    }
}

/// El documento OpenAPI del código actual.
pub fn openapi() -> utoipa::openapi::OpenApi {
    ApiDoc::openapi()
}

/// El documento como JSON legible, con salto de línea final: es exactamente el contenido de `backend/openapi.json`.
pub fn openapi_json() -> String {
    let mut text =
        serde_json::to_string_pretty(&openapi()).expect("el documento OpenAPI es serializable");
    text.push('\n');
    text
}

#[cfg(test)]
mod tests {
    use catalog_core::domain::{DEFAULT_LIMIT, MAX_LIMIT};

    use super::*;

    #[test]
    fn versioned_document_matches_the_generated_one() {
        let versioned = include_str!("../../openapi.json");
        assert!(
            versioned == openapi_json(),
            "backend/openapi.json está desactualizado respecto al código; regenéralo con:\n  mise exec -- cargo run -q --manifest-path backend/Cargo.toml -p catalog-api -- --openapi > backend/openapi.json"
        );
    }

    #[test]
    fn generation_is_deterministic() {
        assert_eq!(openapi_json(), openapi_json());
    }

    #[test]
    fn document_declares_the_expected_paths() {
        let doc = openapi();
        let paths: Vec<&str> = doc.paths.paths.keys().map(String::as_str).collect();
        assert_eq!(
            paths,
            ["/health", "/openapi.json", "/v1/plants", "/v1/plants/{id}"]
        );
    }

    #[test]
    fn limit_parameter_matches_the_pagination_constants() {
        let doc = serde_json::to_value(openapi()).unwrap();
        let params = doc["paths"]["/v1/plants"]["get"]["parameters"]
            .as_array()
            .unwrap();
        let limit = params.iter().find(|p| p["name"] == "limit").unwrap();
        assert_eq!(limit["schema"]["maximum"], u64::from(MAX_LIMIT));
        let description = limit["description"].as_str().unwrap();
        assert!(
            description.contains(&format!("por defecto {DEFAULT_LIMIT}")),
            "{description}"
        );
    }

    #[test]
    fn only_health_and_openapi_live_outside_v1() {
        let doc = openapi();
        for path in doc.paths.paths.keys() {
            let in_v1 = path == "/v1" || path.starts_with("/v1/");
            assert!(
                in_v1 || path == "/health" || path == "/openapi.json",
                "la ruta {path} está fuera de /v1 y no es /health ni /openapi.json: se serviría sin token; muévela bajo /v1 o decide explícitamente que es pública"
            );
        }
    }

    #[test]
    fn security_is_required_exactly_on_v1_operations() {
        let doc = serde_json::to_value(openapi()).unwrap();
        let scheme = &doc["components"]["securitySchemes"]["bearerAuth"];
        assert_eq!(scheme["type"], "http");
        assert_eq!(scheme["scheme"], "bearer");
        assert!(
            doc.get("security").is_none(),
            "no debe haber seguridad global"
        );
        for (path, item) in doc["paths"].as_object().unwrap() {
            let in_v1 = path == "/v1" || path.starts_with("/v1/");
            for (method, operation) in item.as_object().unwrap() {
                let security = operation.get("security");
                if in_v1 {
                    assert_eq!(
                        security,
                        Some(&serde_json::json!([{"bearerAuth": []}])),
                        "{method} {path}"
                    );
                    let unauthorized = &operation["responses"]["401"];
                    assert!(
                        unauthorized["content"]["application/problem+json"].is_object(),
                        "{method} {path}: falta el 401 problem+json"
                    );
                    assert!(
                        unauthorized["headers"]["WWW-Authenticate"].is_object(),
                        "{method} {path}: falta WWW-Authenticate"
                    );
                } else {
                    assert!(
                        security.is_none(),
                        "{method} {path} no debe exigir seguridad"
                    );
                }
            }
        }
    }
    #[test]
    fn plant_detail_documents_credits_and_the_content_location_header() {
        let doc = serde_json::to_value(openapi()).unwrap();
        let ok = &doc["paths"]["/v1/plants/{id}"]["get"]["responses"]["200"];
        assert!(
            ok["headers"]["Content-Location"].is_object(),
            "falta Content-Location en la respuesta 200: {ok}"
        );
        let plant = &doc["components"]["schemas"]["PlantDto"];
        assert_eq!(plant["properties"]["credits"]["type"], "array", "{plant}");
        let required = plant["required"].as_array().unwrap();
        assert!(required.iter().any(|r| r == "credits"));
        let credit = &doc["components"]["schemas"]["CreditDto"];
        let credit_required: Vec<&str> = credit["required"]
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r.as_str().unwrap())
            .collect();
        for field in ["name", "license", "licenseUrl", "attribution", "url"] {
            assert!(
                credit_required.contains(&field),
                "{field} no es obligatorio"
            );
        }
    }

    #[test]
    fn document_never_mentions_review_flags() {
        let text = openapi_json().to_lowercase();
        for term in [
            "reviewflag",
            "review_flag",
            "pending_review",
            "pendingreview",
        ] {
            assert!(!text.contains(term), "el documento menciona {term}");
        }
    }
}
