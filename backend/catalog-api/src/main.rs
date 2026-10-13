//! Binario de la API HTTP de solo lectura del catálogo.
//!
//! Códigos de salida: 0 normal, 1 si el arranque falla (base ausente o incompatible, puerto ocupado), 2 si la configuración es inválida.

use std::process::ExitCode;

use catalog_api::config::{Mode, USAGE, from_env_and_args};
use catalog_api::openapi::openapi_json;
use catalog_api::startup::prepare;
use tokio::net::TcpListener;
use tracing_subscriber::EnvFilter;

// `#[tokio::main]` convierte este `async fn main` en un `main` normal que crea el runtime de Tokio y bloquea sobre él.
#[tokio::main]
async fn main() -> ExitCode {
    let config = match from_env_and_args(std::env::args().skip(1), |key| std::env::var(key).ok()) {
        Ok(config) => config,
        Err(err) => {
            eprintln!("error de configuración: {err}");
            return ExitCode::from(2);
        }
    };
    match config.mode {
        Mode::Help => {
            println!("{USAGE}");
            return ExitCode::SUCCESS;
        }
        Mode::PrintOpenApi => {
            print!("{}", openapi_json());
            return ExitCode::SUCCESS;
        }
        Mode::Serve => {}
    }

    // `RUST_LOG` controla el nivel; sin ella, `info`.
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let app = match prepare(&config) {
        Ok(app) => app,
        Err(err) => {
            eprintln!("no se pudo arrancar: {err}");
            return ExitCode::from(1);
        }
    };
    let listener = match TcpListener::bind((config.host.as_str(), config.port)).await {
        Ok(listener) => listener,
        Err(err) => {
            eprintln!(
                "no se pudo escuchar en {}:{}: {err}",
                config.host, config.port
            );
            return ExitCode::from(1);
        }
    };
    match listener.local_addr() {
        Ok(addr) => tracing::info!(%addr, db = %config.db_path.display(), "escuchando"),
        Err(err) => tracing::warn!(error = %err, "no se pudo leer la dirección local"),
    }

    // Con apagado ordenado: al recibir Ctrl-C deja de aceptar conexiones y termina las peticiones en curso.
    if let Err(err) = axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
    {
        eprintln!("error del servidor: {err}");
        return ExitCode::from(1);
    }
    tracing::info!("apagado completado");
    ExitCode::SUCCESS
}

/// Se completa cuando llega Ctrl-C (SIGINT).
async fn shutdown_signal() {
    if let Err(err) = tokio::signal::ctrl_c().await {
        tracing::error!(error = %err, "no se pudo escuchar la señal de apagado");
    }
}
