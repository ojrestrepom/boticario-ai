//! Ningún log contiene los tokens, ni el configurado ni el rechazado, ni siquiera con `RUST_LOG=trace`.
//!
//! Lanza el binario compilado sobre una base de fixture, envía una petición con el token válido y otras con tokens inválidos, y revisa todo lo capturado en stdout y stderr.

use std::io::{BufRead, BufReader, Read, Write};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

use catalog_ingest::seed_build::build_from_dir;

const DEADLINE: Duration = Duration::from_secs(20);
// Valores ficticios de prueba; no son secretos. Los dos llevan una marca única para buscarla en los logs.
const VALID_TOKEN: &str = "test-token-not-a-secret-VALIDMARK0000000000";
const SECOND_TOKEN: &str = "test-token-not-a-secret-SECONDMARK000000000";
const INVALID_TOKEN: &str = "test-token-not-a-secret-INVALIDMARK00000000";

/// Semilla de fixture del crate de ingesta (3 plantas), construida sin red.
fn fixture_seed() -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../catalog-ingest/tests/fixtures/seed")
}

/// Construye con `build_from_dir` una base de catálogo desde la semilla de fixture y devuelve su ruta.
fn build_fixture_db(dir: &Path) -> std::path::PathBuf {
    let out = dir.join("build").join("catalog.db");
    build_from_dir(&fixture_seed(), &out).unwrap();
    out
}

fn free_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap()
        .port()
}

struct Api(Child);

impl Drop for Api {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

/// Envía una petición `GET` y devuelve la línea de estado, o `None` si no hubo conexión o respuesta.
fn request(port: u16, path: &str, authorization: Option<&str>) -> Option<String> {
    let mut stream = std::net::TcpStream::connect(("127.0.0.1", port)).ok()?;
    stream.set_read_timeout(Some(Duration::from_secs(2))).ok()?;
    let auth = authorization
        .map(|v| format!("Authorization: {v}\r\n"))
        .unwrap_or_default();
    let text = format!("GET {path} HTTP/1.1\r\nHost: x\r\n{auth}Connection: close\r\n\r\n");
    stream.write_all(text.as_bytes()).ok()?;
    let mut response = String::new();
    let _ = stream.read_to_string(&mut response);
    response.lines().next().map(str::to_string)
}

#[test]
fn trace_logs_never_contain_tokens() {
    let dir = tempfile::tempdir().unwrap();
    let db = build_fixture_db(dir.path());
    let port = free_port();
    let mut child = Command::new(env!("CARGO_BIN_EXE_catalog-api"))
        .env("CATALOG_DB", &db)
        .env("HOST", "127.0.0.1")
        .env("PORT", port.to_string())
        .env("API_TOKENS", format!("{VALID_TOKEN},{SECOND_TOKEN}"))
        .env("RUST_LOG", "trace")
        .env_remove("NO_COLOR")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    // Los dos flujos se leen en hilos para que ninguna tubería se llene y bloquee a la API.
    let stdout = child.stdout.take().unwrap();
    let stderr = child.stderr.take().unwrap();
    let mut api = Api(child);
    let out_reader = std::thread::spawn(move || {
        BufReader::new(stdout)
            .lines()
            .map_while(Result::ok)
            .collect::<Vec<_>>()
    });
    let err_reader = std::thread::spawn(move || {
        BufReader::new(stderr)
            .lines()
            .map_while(Result::ok)
            .collect::<Vec<_>>()
    });

    // Espera a que la API responda.
    let deadline = Instant::now() + DEADLINE;
    while request(port, "/health", None).as_deref() != Some("HTTP/1.1 200 OK") {
        assert!(Instant::now() < deadline, "la API no arrancó");
        std::thread::sleep(Duration::from_millis(50));
    }

    let valid = format!("Bearer {VALID_TOKEN}");
    let invalid = format!("Bearer {INVALID_TOKEN}");
    let basic = format!("Basic {INVALID_TOKEN}");
    let status = |auth: Option<&str>| request(port, "/v1/plants", auth).unwrap_or_default();
    assert!(status(Some(&valid)).contains("200"));
    assert!(status(Some(&invalid)).contains("401"));
    assert!(status(Some(&basic)).contains("401"));
    assert!(status(None).contains("401"));
    assert!(
        request(port, "/v1/no-existe", Some(&invalid))
            .unwrap_or_default()
            .contains("401")
    );

    let killed = Command::new("kill")
        .arg(api.0.id().to_string())
        .status()
        .unwrap();
    assert!(killed.success());
    let end = Instant::now() + DEADLINE;
    while api.0.try_wait().unwrap().is_none() {
        assert!(Instant::now() < end, "la API no terminó");
        std::thread::sleep(Duration::from_millis(20));
    }
    let mut lines = out_reader.join().unwrap();
    lines.extend(err_reader.join().unwrap());

    assert!(!lines.is_empty());
    // Las marcas únicas detectan también un valor parcial o con otro formato.
    for needle in [
        "VALIDMARK",
        "SECONDMARK",
        "INVALIDMARK",
        VALID_TOKEN,
        INVALID_TOKEN,
    ] {
        let leaked: Vec<&String> = lines.iter().filter(|l| l.contains(needle)).collect();
        assert!(leaked.is_empty(), "el log contiene {needle}: {leaked:?}");
    }
    assert!(
        lines
            .iter()
            .all(|l| !l.to_ascii_lowercase().contains("authorization")),
        "el log menciona la cabecera Authorization: {lines:?}"
    );
    // El 401 sí se registra a nivel debug, con la clase del fallo.
    for reason in ["esquema distinto", "no coincide", "ausente"] {
        assert!(
            lines
                .iter()
                .any(|l| l.contains("petición no autorizada") && l.contains(reason)),
            "falta el log debug del 401 ({reason}): {lines:?}"
        );
    }
}
