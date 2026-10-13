//! Preparación del servidor: abre la base y construye el router.

use std::error::Error;
use std::fmt;
use std::sync::Arc;

use axum::Router;

use crate::async_catalog::AsyncCatalog;
use crate::config::Config;
use crate::http::router;
use crate::repository::{OpenError, SqliteCatalogRepository};

/// El servidor no puede arrancar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StartupError {
    /// No se pudo abrir la base (ausente, ilegible o de versión incompatible).
    Open(OpenError),
}

// Se delega en el `Display` de `OpenError`, que ya trae los mensajes accionables (ruta y `catalog-ingest build`, o versión encontrada y soportada).
impl fmt::Display for StartupError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Open(err) => err.fmt(f),
        }
    }
}

impl Error for StartupError {}

impl From<OpenError> for StartupError {
    fn from(err: OpenError) -> Self {
        Self::Open(err)
    }
}

/// Abre la base en solo lectura, comprueba su versión y devuelve el router listo para servir.
pub fn prepare(config: &Config) -> Result<Router, StartupError> {
    let repo = SqliteCatalogRepository::open(&config.db_path)?;
    Ok(router(AsyncCatalog::new(Arc::new(repo))))
}

#[cfg(test)]
mod tests {
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use tower::ServiceExt;

    use super::*;
    use crate::config::{DEFAULT_HOST, DEFAULT_PORT, Mode};
    use crate::test_support::Fixture;

    fn config_for(path: std::path::PathBuf) -> Config {
        Config {
            db_path: path,
            host: DEFAULT_HOST.to_string(),
            port: DEFAULT_PORT,
            mode: Mode::Serve,
        }
    }

    #[test]
    fn missing_database_message_names_path_and_build() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("nope.db");
        let text = prepare(&config_for(path.clone())).unwrap_err().to_string();
        assert!(text.contains(path.to_str().unwrap()), "{text}");
        assert!(text.contains("build"), "{text}");
    }

    #[test]
    fn incompatible_version_message_has_found_and_supported() {
        let fixture = Fixture::with_version(Some("99"));
        let text = prepare(&config_for(fixture.path.clone()))
            .unwrap_err()
            .to_string();
        assert!(text.contains("99") && text.contains('1'), "{text}");
    }

    #[tokio::test]
    async fn valid_database_serves_healthz() {
        let fixture = Fixture::standard();
        let app = prepare(&config_for(fixture.path.clone())).unwrap();
        let response = app
            .oneshot(Request::get("/healthz").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }
}
