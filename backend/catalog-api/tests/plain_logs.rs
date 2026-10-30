//! Logs sin secuencias ANSI con stdout redirigido, y `RUST_LOG` respetada.
//!
//! Lanza el binario compilado sobre una base de fixture. Una terminal real no es portable en CI: la combinación con colores la cubre la prueba unitaria de `use_ansi`.

use std::io::{BufRead, BufReader, Read};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::time::{Duration, Instant};

use catalog_ingest::seed_build::build_from_dir;

const DEADLINE: Duration = Duration::from_secs(20);

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

/// Puerto libre en loopback (hay una carrera mínima entre soltarlo y que lo use la API).
fn free_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .unwrap()
        .local_addr()
        .unwrap()
        .port()
}

/// Proceso de la API con stdout y stderr en tuberías; se mata al soltarlo.
struct Api {
    child: Child,
    port: u16,
}

impl Drop for Api {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn spawn_api(db: &Path, rust_log: Option<&str>) -> Api {
    let port = free_port();
    let mut command = Command::new(env!("CARGO_BIN_EXE_catalog-api"));
    command
        .env("CATALOG_DB", db)
        .env("HOST", "127.0.0.1")
        .env("PORT", port.to_string())
        // Valor ficticio de prueba; no es un secreto.
        .env("API_TOKENS", "test-token-not-a-secret-0000000000000000")
        .env_remove("NO_COLOR")
        .env_remove("RUST_LOG")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if let Some(filter) = rust_log {
        command.env("RUST_LOG", filter);
    }
    Api {
        child: command.spawn().unwrap(),
        port,
    }
}

/// Lee las líneas de stdout en un hilo y las envía por un canal.
fn stdout_lines(api: &mut Api) -> mpsc::Receiver<String> {
    let stdout = api.child.stdout.take().unwrap();
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if tx.send(line).is_err() {
                break;
            }
        }
    });
    rx
}

/// Pide `/health` hasta obtener 200 o agotar el plazo; devuelve si respondió.
fn wait_healthy(port: u16, deadline: Instant) -> bool {
    use std::io::Write;
    while Instant::now() < deadline {
        if let Ok(mut stream) = std::net::TcpStream::connect(("127.0.0.1", port)) {
            let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
            let request = b"GET /health HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n";
            if stream.write_all(request).is_ok() {
                let mut response = String::new();
                let _ = stream.read_to_string(&mut response);
                if response.starts_with("HTTP/1.1 200") {
                    return true;
                }
            }
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    false
}

/// Envía SIGTERM y espera la salida dentro del plazo; devuelve lo que quedó en stdout y stderr.
fn terminate(api: &mut Api, rx: &mpsc::Receiver<String>) -> (Vec<String>, String) {
    let status = Command::new("kill")
        .arg(api.child.id().to_string())
        .status()
        .unwrap();
    assert!(status.success());
    let deadline = Instant::now() + DEADLINE;
    loop {
        if api.child.try_wait().unwrap().is_some() {
            break;
        }
        assert!(
            Instant::now() < deadline,
            "la API no terminó en {DEADLINE:?}"
        );
        std::thread::sleep(Duration::from_millis(20));
    }
    // El hilo lector suelta `tx` al llegar al EOF: se drena hasta que el canal se cierre para no perder las últimas líneas.
    let mut lines = Vec::new();
    let drain_deadline = Instant::now() + DEADLINE;
    loop {
        let left = drain_deadline.saturating_duration_since(Instant::now());
        match rx.recv_timeout(left) {
            Ok(line) => lines.push(line),
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
            Err(mpsc::RecvTimeoutError::Timeout) => {
                panic!("stdout no se cerró en {DEADLINE:?}; capturado: {lines:?}")
            }
        }
    }
    let mut stderr = String::new();
    if let Some(mut pipe) = api.child.stderr.take() {
        let _ = pipe.read_to_string(&mut stderr);
    }
    (lines, stderr)
}

#[test]
fn logs_have_no_ansi_when_stdout_is_not_a_terminal() {
    let dir = tempfile::tempdir().unwrap();
    let db = build_fixture_db(dir.path());
    let mut api = spawn_api(&db, None);
    let rx = stdout_lines(&mut api);

    let mut seen = Vec::new();
    let deadline = Instant::now() + DEADLINE;
    let listening = loop {
        let left = deadline.saturating_duration_since(Instant::now());
        match rx.recv_timeout(left) {
            Ok(line) => {
                let found = line.contains("escuchando");
                seen.push(line);
                if found {
                    break seen.last().unwrap().clone();
                }
            }
            Err(_) => {
                let (_, stderr) = terminate(&mut api, &rx);
                panic!(
                    "no apareció la línea «escuchando» en {DEADLINE:?}; stdout: {seen:?}; stderr: {stderr}"
                );
            }
        }
    };
    let (rest, stderr) = terminate(&mut api, &rx);
    seen.extend(rest);

    assert!(
        !listening.contains('\x1b'),
        "la línea lleva ANSI: {listening:?}"
    );
    assert!(listening.contains("INFO"), "falta el nivel: {listening:?}");
    assert!(
        seen.iter().all(|line| !line.contains('\x1b')),
        "hay ANSI en los logs: {seen:?}; stderr: {stderr}"
    );
}

#[test]
fn rust_log_warn_suppresses_the_info_line() {
    let dir = tempfile::tempdir().unwrap();
    let db = build_fixture_db(dir.path());
    let mut api = spawn_api(&db, Some("warn"));
    let rx = stdout_lines(&mut api);

    // Sin la línea INFO no hay otra señal de arranque: se consulta `/health`.
    let healthy = wait_healthy(api.port, Instant::now() + DEADLINE);
    let (lines, stderr) = terminate(&mut api, &rx);
    assert!(
        healthy,
        "la API no respondió /health; stdout: {lines:?}; stderr: {stderr}"
    );
    assert!(
        lines.iter().all(|line| !line.contains("INFO")),
        "RUST_LOG=warn no suprimió INFO: {lines:?}"
    );
}
