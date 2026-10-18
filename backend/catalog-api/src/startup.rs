//! Preparación del servidor: abre la base y construye el router.

use std::error::Error;
use std::fmt;
use std::future::{Future, IntoFuture};
use std::sync::Arc;
use std::time::Duration;

use axum::Router;
use tokio::net::TcpListener;
use tokio::sync::oneshot;

use crate::async_catalog::AsyncCatalog;
use crate::config::Config;
use crate::http::router;
use crate::repository::{OpenError, SqliteCatalogRepository};

/// El servidor no puede arrancar.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StartupError {
    /// No se pudo abrir la base (ausente, ilegible o de versión incompatible).
    Open(OpenError),
    /// Se pidió servir sin tokens de API. `Config` los exige en modo `Serve`, así que solo ocurre si se construye a mano.
    MissingApiTokens,
}

// Se delega en el `Display` de `OpenError`, que ya trae los mensajes accionables (ruta y `catalog-ingest build`, o versión encontrada y soportada).
impl fmt::Display for StartupError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Open(err) => err.fmt(f),
            Self::MissingApiTokens => {
                write!(f, "falta API_TOKENS: no se puede servir sin tokens de API")
            }
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
///
/// Los tokens de API salen de `config.api_tokens`; sin ellos no hay router.
pub fn prepare(config: &Config) -> Result<Router, StartupError> {
    let tokens = config
        .api_tokens
        .clone()
        .ok_or(StartupError::MissingApiTokens)?;
    let repo = SqliteCatalogRepository::open(&config.db_path)?;
    Ok(router(AsyncCatalog::new(Arc::new(repo)), tokens))
}

/// Plazo máximo, tras la señal de apagado, para que terminen las peticiones en curso.
///
/// Debe quedar por debajo del plazo por defecto más corto conocido entre SIGTERM y SIGKILL: unos 3 s en `docker stop` (Docker Engine 29), 10 s en Cloud Run y 30 s en Kubernetes.
/// Las peticiones de esta API tardan milisegundos, así que 2 s sobran para drenar las legítimas y dejan margen para que el proceso termine por sí mismo.
pub const SHUTDOWN_GRACE: Duration = Duration::from_secs(2);

/// Cómo terminó el servidor tras la señal de apagado.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ShutdownOutcome {
    /// Todas las conexiones terminaron dentro del plazo.
    Completed,
    /// Se agotó el plazo con conexiones aún abiertas y se abandonaron.
    Forced,
}

/// Sirve `app` en `listener` hasta que `shutdown` se resuelva y espera a las peticiones en curso como máximo `grace`.
///
/// `axum::serve(...).with_graceful_shutdown(...)` espera sin límite a todas las conexiones, y una petición con cabeceras incompletas cuenta como en curso: un cliente colgado impediría terminar.
/// Por eso se cronometra el drenaje aparte: al llegar la señal arranca el plazo y, si vence, se abandona el servidor (al soltarlo se cierran las conexiones).
pub async fn serve(
    listener: TcpListener,
    app: Router,
    shutdown: impl Future<Output = ()> + Send + 'static,
    grace: Duration,
) -> Result<ShutdownOutcome, std::io::Error> {
    // Avisa de que la señal ya llegó, justo cuando axum empieza a drenar.
    let (signalled_tx, signalled_rx) = oneshot::channel::<()>();
    let server = axum::serve(listener, app)
        .with_graceful_shutdown(async move {
            shutdown.await;
            // Si el receptor ya no existe, el servidor terminó antes y el aviso sobra.
            let _ = signalled_tx.send(());
        })
        // `WithGracefulShutdown` solo es `IntoFuture`; hay que convertirlo para poder sondearlo por referencia.
        .into_future();
    tokio::pin!(server);

    tokio::select! {
        // Si el servidor termina antes de la señal (error de E/S), su resultado manda.
        result = &mut server => result.map(|()| ShutdownOutcome::Completed),
        _ = signalled_rx => match tokio::time::timeout(grace, &mut server).await {
            Ok(result) => result.map(|()| ShutdownOutcome::Completed),
            Err(_elapsed) => Ok(ShutdownOutcome::Forced),
        },
    }
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
            api_tokens: Some(
                crate::auth::ApiTokens::parse("test-token-not-a-secret-0000000000000000").unwrap(),
            ),
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
    async fn valid_database_serves_health() {
        let fixture = Fixture::standard();
        let app = prepare(&config_for(fixture.path.clone())).unwrap();
        let response = app
            .oneshot(Request::get("/health").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[test]
    fn serving_without_tokens_is_a_startup_error() {
        let fixture = Fixture::standard();
        let mut config = config_for(fixture.path.clone());
        config.api_tokens = None;
        let err = prepare(&config).unwrap_err();
        assert_eq!(err, StartupError::MissingApiTokens);
        assert!(err.to_string().contains("API_TOKENS"));
    }
}
