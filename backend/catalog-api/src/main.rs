//! Binario de la API HTTP de solo lectura del catálogo.
//!
//! Códigos de salida: 0 normal, 1 si el arranque falla (base ausente o incompatible, puerto ocupado), 2 si la configuración es inválida.

use std::process::ExitCode;

use catalog_api::config::{Mode, USAGE, from_env_and_args};
use catalog_api::openapi::openapi_json;
use catalog_api::startup::{SHUTDOWN_GRACE, ShutdownOutcome, prepare, serve};
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

    // Con apagado ordenado: al recibir Ctrl-C o SIGTERM deja de aceptar conexiones y espera a las peticiones en curso como máximo `SHUTDOWN_GRACE`.
    match serve(listener, app, shutdown_signal(), SHUTDOWN_GRACE).await {
        Ok(ShutdownOutcome::Completed) => {}
        Ok(ShutdownOutcome::Forced) => tracing::warn!(
            grace_secs = SHUTDOWN_GRACE.as_secs(),
            "se fuerza el apagado: quedaban conexiones abiertas tras {} s",
            SHUTDOWN_GRACE.as_secs()
        ),
        Err(err) => {
            eprintln!("error del servidor: {err}");
            return ExitCode::from(1);
        }
    }
    // También tras un apagado forzado: este texto indica que la señal fue atendida.
    tracing::info!("apagado completado");
    ExitCode::SUCCESS
}

/// Se completa cuando llega Ctrl-C (SIGINT) o, en Unix, SIGTERM.
///
/// SIGTERM es lo que envía un contenedor al pararse, así que sin él no habría apagado ordenado.
async fn shutdown_signal() {
    let ctrl_c = async {
        if let Err(err) = tokio::signal::ctrl_c().await {
            tracing::error!(error = %err, "no se pudo escuchar Ctrl-C");
            // Sin señal que escuchar, este brazo no debe disparar el apagado.
            std::future::pending::<()>().await;
        }
    };
    #[cfg(unix)]
    let terminate = async {
        use tokio::signal::unix::{SignalKind, signal};
        match signal(SignalKind::terminate()) {
            Ok(mut stream) => {
                stream.recv().await;
            }
            Err(err) => {
                tracing::error!(error = %err, "no se pudo escuchar SIGTERM");
                std::future::pending::<()>().await;
            }
        }
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();
    tokio::select! {
        () = ctrl_c => {},
        () = terminate => {},
    }
}
