//! CLI de ingesta: descarga los insumos y (más adelante) construye el catálogo.

use std::path::{Path, PathBuf};
use std::process::exit;
use std::time::Instant;

use catalog_ingest::IngestError;
use catalog_ingest::build::{BuildReport, build, rederive};
use catalog_ingest::download::{DownloadOutcome, download_input};
use catalog_ingest::sources::{default_registry, load_sources_config};

/// Texto de ayuda; se imprime ante argumentos inválidos y con `--help`.
fn usage() -> &'static str {
    "Uso: catalog-ingest <subcomando> [--data-dir <ruta>]

Subcomandos:
  download   Descarga y verifica los insumos de las fuentes activas en <data-dir>/.cache
  build      Verifica los insumos de <data-dir>/.cache (no descarga), importa el crudo a <data-dir>/build/raw.db y escribe <data-dir>/build/catalog.db
  rederive   Rehace <data-dir>/build/catalog.db desde <data-dir>/build/raw.db, sin el insumo original

Opciones:
  --data-dir <ruta>   Directorio de datos (por defecto: data, relativo al directorio de trabajo)
  --help              Muestra esta ayuda

Se ejecuta desde la raíz del repositorio:
  mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-ingest -- download"
}

/// Subcomando elegido por el usuario.
enum Command {
    Download,
    Build,
    Rederive,
}

/// Argumentos ya interpretados.
struct Args {
    command: Command,
    data_dir: PathBuf,
}

/// Interpreta los argumentos (sin el nombre del programa). `Err` lleva el motivo para mostrar.
fn parse_args(mut args: impl Iterator<Item = String>) -> Result<Args, String> {
    let command = match args.next().as_deref() {
        Some("download") => Command::Download,
        Some("build") => Command::Build,
        Some("rederive") => Command::Rederive,
        Some(other) => return Err(format!("subcomando desconocido \"{other}\"")),
        None => return Err("falta el subcomando".to_string()),
    };
    let mut data_dir = PathBuf::from("data");
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--data-dir" => {
                data_dir = args
                    .next()
                    .map(PathBuf::from)
                    .ok_or("--data-dir necesita una ruta")?;
            }
            other => return Err(format!("argumento desconocido \"{other}\"")),
        }
    }
    Ok(Args { command, data_dir })
}

fn run_download(data_dir: &Path) -> Result<(), IngestError> {
    let config = load_sources_config(&data_dir.join("sources.toml"))?;
    let registry = default_registry();
    let cache_dir = data_dir.join(".cache");
    for active in registry.resolve(&config)? {
        let id = active.adapter.source().id.0;
        match download_input(active.adapter, &cache_dir)? {
            DownloadOutcome::AlreadyPresent(path) => {
                println!("{id}: ya estaba y está verificado: {}", path.display());
            }
            DownloadOutcome::Downloaded(path) => {
                println!("{id}: descargado y verificado: {}", path.display());
            }
        }
    }
    Ok(())
}

/// Resumen común de `build` y `rederive`.
fn print_report(report: &BuildReport, started: Instant) {
    println!("fuentes: {}", report.sources);
    println!("plantas: {}", report.plants);
    println!("hash: {}", report.content_hash);
    println!("tiempo: {:.2?}", started.elapsed());
}

fn run_build(data_dir: &Path) -> Result<(), IngestError> {
    let started = Instant::now();
    let config = load_sources_config(&data_dir.join("sources.toml"))?;
    let build_dir = data_dir.join("build");
    let report = build(
        &default_registry(),
        &config,
        &data_dir.join(".cache"),
        &build_dir.join("raw.db"),
        &build_dir.join("catalog.db"),
    )?;
    print_report(&report, started);
    Ok(())
}

fn run_rederive(data_dir: &Path) -> Result<(), IngestError> {
    let started = Instant::now();
    let config = load_sources_config(&data_dir.join("sources.toml"))?;
    let build_dir = data_dir.join("build");
    let report = rederive(
        &default_registry(),
        &config,
        &build_dir.join("raw.db"),
        &build_dir.join("catalog.db"),
    )?;
    print_report(&report, started);
    Ok(())
}

fn main() {
    let mut raw = std::env::args().skip(1).peekable();
    if matches!(raw.peek().map(String::as_str), Some("--help" | "-h")) {
        println!("{}", usage());
        return;
    }
    let args = match parse_args(raw) {
        Ok(args) => args,
        Err(message) => {
            eprintln!("error: {message}\n\n{}", usage());
            exit(2);
        }
    };
    let result = match args.command {
        Command::Download => run_download(&args.data_dir),
        Command::Build => run_build(&args.data_dir),
        Command::Rederive => run_rederive(&args.data_dir),
    };
    if let Err(err) = result {
        eprintln!("error: {err}");
        exit(1);
    }
}
