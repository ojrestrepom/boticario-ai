//! Documento OpenAPI de la API, generado desde el código.
//!
//! `#[derive(OpenApi)]` reúne las rutas anotadas con `#[utoipa::path]` y los esquemas de los DTOs (`ToSchema`) en un documento.
//! El documento versionado en `backend/openapi.json` debe coincidir con el generado: un test lo comprueba.

use utoipa::OpenApi;

use crate::dto::{
    CommonNameDto, FamilyDto, HealthDto, NameDto, NameKindDto, PageDto, PartDto, PlantDto,
    PlantSummaryDto, ProblemDto, ReferenceDto, SourceDto, UseDto,
};
use crate::http;

/// Definición del documento: metadatos, rutas y esquemas.
#[derive(OpenApi)]
#[openapi(
    info(
        title = "Boticario AI Catalog API",
        version = "1",
        description = "API de solo lectura del catálogo de plantas y sus fuentes. Dentro de `/v1` solo habrá cambios aditivos: los clientes deben ignorar los campos desconocidos."
    ),
    paths(http::healthz, http::sources, http::list_plants, http::get_plant),
    components(schemas(
        HealthDto,
        SourceDto,
        CommonNameDto,
        PlantSummaryDto,
        PageDto<PlantSummaryDto>,
        FamilyDto,
        NameKindDto,
        NameDto,
        PartDto,
        ReferenceDto,
        UseDto,
        PlantDto,
        ProblemDto,
    ))
)]
struct ApiDoc;

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
            ["/healthz", "/v1/plants", "/v1/plants/{id}", "/v1/sources"]
        );
    }
}
