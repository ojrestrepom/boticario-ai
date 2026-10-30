//! Apagado ordenado con plazo: `serve` termina aunque haya una conexión colgada.

use std::sync::Arc;
use std::time::{Duration, Instant};

use catalog_api::async_catalog::AsyncCatalog;
use catalog_api::auth::ApiTokens;
use catalog_api::http::router;
use catalog_api::startup::{ShutdownOutcome, serve};
use catalog_core::repository::CatalogRepository;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::oneshot;

/// Repositorio vacío: `/health` no lo consulta.
struct EmptyRepo;

impl CatalogRepository for EmptyRepo {
    fn list_plants(
        &self,
        _query: &catalog_core::domain::ListQuery,
    ) -> Result<
        catalog_core::domain::Page<catalog_core::domain::PlantSummary>,
        catalog_core::repository::RepositoryError,
    > {
        unreachable!("el test solo pide /health")
    }

    fn get_plant(
        &self,
        _id: &catalog_core::domain::PlantId,
    ) -> Result<Option<catalog_core::domain::Plant>, catalog_core::repository::RepositoryError>
    {
        Ok(None)
    }

    fn list_goals(
        &self,
    ) -> Result<Vec<catalog_core::domain::GoalSummary>, catalog_core::repository::RepositoryError>
    {
        unreachable!("el test solo pide /health")
    }

    fn list_goal_plants(
        &self,
        _goal: &str,
        _subarea: Option<&str>,
        _limit: u32,
        _offset: u32,
    ) -> Result<catalog_core::domain::GoalPlantsOutcome, catalog_core::repository::RepositoryError>
    {
        unreachable!("el test solo pide /health")
    }
}

/// Arranca `serve` en una tarea y devuelve su dirección, el disparador de la señal y la tarea.
async fn start(
    grace: Duration,
) -> (
    std::net::SocketAddr,
    oneshot::Sender<()>,
    tokio::task::JoinHandle<Result<ShutdownOutcome, std::io::Error>>,
) {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    let app = router(
        AsyncCatalog::new(Arc::new(EmptyRepo)),
        // Valor ficticio de prueba; no es un secreto.
        ApiTokens::parse("test-token-not-a-secret-0000000000000000").unwrap(),
    );
    let (tx, rx) = oneshot::channel::<()>();
    let handle = tokio::spawn(serve(
        listener,
        app,
        async move {
            let _ = rx.await;
        },
        grace,
    ));
    (addr, tx, handle)
}

/// Escribe una petición pequeña de una vez (sin la feature `io-util` de Tokio).
fn send(stream: &TcpStream, bytes: &[u8]) {
    assert_eq!(stream.try_write(bytes).unwrap(), bytes.len());
}

#[tokio::test]
async fn idle_keep_alive_connection_does_not_delay_shutdown() {
    let (addr, signal, handle) = start(Duration::from_secs(5)).await;
    let stream = TcpStream::connect(addr).await.unwrap();
    send(&stream, b"GET /health HTTP/1.1\r\nHost: x\r\n\r\n");
    // Se lee la respuesta para asegurar que la petición terminó y la conexión queda inactiva.
    let mut buf = [0u8; 1024];
    stream.readable().await.unwrap();
    let n = stream.try_read(&mut buf).unwrap();
    assert!(String::from_utf8_lossy(&buf[..n]).starts_with("HTTP/1.1 200"));

    let started = Instant::now();
    signal.send(()).unwrap();
    let outcome = handle.await.unwrap().unwrap();
    assert_eq!(outcome, ShutdownOutcome::Completed);
    assert!(started.elapsed() < Duration::from_secs(1));
    drop(stream);
}

#[tokio::test]
async fn incomplete_request_forces_shutdown_after_grace() {
    let grace = Duration::from_millis(300);
    let (addr, signal, handle) = start(grace).await;
    let stream = TcpStream::connect(addr).await.unwrap();
    // Cabeceras sin la línea vacía final y socket abierto.
    send(&stream, b"GET /health HTTP/1.1\r\nHost: x\r\n");
    // Margen para que el servidor haya aceptado la conexión antes de la señal.
    tokio::time::sleep(Duration::from_millis(100)).await;

    let started = Instant::now();
    signal.send(()).unwrap();
    let outcome = handle.await.unwrap().unwrap();
    let elapsed = started.elapsed();
    assert_eq!(outcome, ShutdownOutcome::Forced);
    assert!(elapsed >= grace, "{elapsed:?}");
    assert!(elapsed < Duration::from_secs(3), "{elapsed:?}");
    drop(stream);
}
