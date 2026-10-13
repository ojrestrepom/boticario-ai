//! Errores de la API en formato `application/problem+json` (RFC 9457).

use axum::Json;
use axum::http::{HeaderValue, StatusCode, Uri, header};
use axum::response::{IntoResponse, Response};
use catalog_core::repository::RepositoryError;
use serde_json::json;

/// Tipo de medio de los errores.
pub const PROBLEM_JSON: &str = "application/problem+json";

/// Error de la API, ya clasificado por el código HTTP que le corresponde.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ApiError {
    /// 400: un parámetro tiene un valor inválido.
    BadRequest {
        /// Nombre del parámetro afectado.
        param: String,
        /// Explicación para el cliente.
        detail: String,
    },
    /// 404: el recurso no existe.
    NotFound {
        /// Explicación para el cliente.
        detail: String,
    },
    /// 405: método no permitido en un recurso existente.
    MethodNotAllowed,
    /// 500: fallo interno. No lleva datos: el motivo real se registra en el log y nunca se envía al cliente.
    Internal,
}

impl ApiError {
    /// Error 400 para el parámetro `param`.
    pub fn bad_request(param: &str, detail: impl Into<String>) -> Self {
        Self::BadRequest {
            param: param.to_string(),
            detail: detail.into(),
        }
    }

    /// Respuesta con el campo `instance` (la ruta pedida) rellenado.
    pub fn into_response_at(self, uri: &Uri) -> Response {
        self.respond(Some(uri.path()))
    }

    fn respond(self, instance: Option<&str>) -> Response {
        let (status, detail, param) = match self {
            Self::BadRequest { param, detail } => (StatusCode::BAD_REQUEST, detail, Some(param)),
            Self::NotFound { detail } => (StatusCode::NOT_FOUND, detail, None),
            Self::MethodNotAllowed => (
                StatusCode::METHOD_NOT_ALLOWED,
                "método no permitido: la API es de solo lectura".to_string(),
                None,
            ),
            Self::Internal => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "error interno".to_string(),
                None,
            ),
        };
        let mut body = json!({
            "type": "about:blank",
            "title": status.canonical_reason().unwrap_or("Error"),
            "status": status.as_u16(),
            "detail": detail,
        });
        // `body` es un objeto JSON, así que `as_object_mut` siempre devuelve `Some`.
        if let Some(map) = body.as_object_mut() {
            if let Some(instance) = instance {
                map.insert("instance".into(), instance.into());
            }
            if let Some(param) = param {
                // Extensión de RFC 9457: el parámetro que causó el error.
                map.insert("param".into(), param.into());
            }
        }
        let mut response = (status, Json(body)).into_response();
        response
            .headers_mut()
            .insert(header::CONTENT_TYPE, HeaderValue::from_static(PROBLEM_JSON));
        response
    }
}

/// Un fallo del repositorio siempre es 500; el detalle va solo al log.
impl From<RepositoryError> for ApiError {
    fn from(err: RepositoryError) -> Self {
        tracing::error!(error = %err, "fallo del repositorio");
        Self::Internal
    }
}

/// Permite devolver un `ApiError` directamente desde un handler (sin `instance`; los handlers usan [`ApiError::into_response_at`]).
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        self.respond(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn internal_error_has_generic_detail() {
        let response =
            ApiError::from(RepositoryError::Storage("/tmp/secreto.db".into())).into_response();
        assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
        assert_eq!(
            response.headers()[header::CONTENT_TYPE],
            "application/problem+json"
        );
    }
}
