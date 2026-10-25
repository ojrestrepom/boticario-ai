//! CLI de ingesta: construye el catálogo desde la semilla.

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use catalog_ingest::seed_build::build_from_dir;

/// Texto de ayuda; se imprime ante argumentos inválidos y con `--help`.
fn usage() -> &'static str {
    "Uso: catalog-ingest <subcomando> [--data-dir <ruta>]

Subcomandos:
  build      Lee y verifica la semilla (<data-dir>/seed por defecto) y escribe el catálogo (<data-dir>/build/catalog.db por defecto), sin red ni LLM

Opciones:
  --data-dir <ruta>   Directorio de datos (por defecto: data, relativo al directorio de trabajo)
  --seed <ruta>       directorio de la semilla (por defecto: <data-dir>/seed)
  --out <ruta>        archivo de salida (por defecto: <data-dir>/build/catalog.db)
  --help              Muestra esta ayuda

Se ejecuta desde la raíz del repositorio:
  mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-ingest -- build"
}

/// Subcomando elegido por el usuario.
enum Command {
    Build,
}

/// Argumentos ya interpretados.
struct Args {
    command: Command,
    data_dir: PathBuf,
    seed: Option<PathBuf>,
    out: Option<PathBuf>,
}

/// Interpreta los argumentos (sin el nombre del programa). `Err` lleva el motivo para mostrar.
fn parse_args(mut args: impl Iterator<Item = String>) -> Result<Args, String> {
    let command = match args.next().as_deref() {
        Some("build") => Command::Build,
        Some(other) => return Err(format!("subcomando desconocido \"{other}\"")),
        None => return Err("falta el subcomando".to_string()),
    };
    let mut data_dir = PathBuf::from("data");
    let mut seed = None;
    let mut out = None;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--data-dir" => {
                data_dir = args
                    .next()
                    .map(PathBuf::from)
                    .ok_or("--data-dir necesita una ruta")?;
            }
            "--seed" => {
                seed = Some(
                    args.next()
                        .map(PathBuf::from)
                        .ok_or("--seed necesita una ruta")?,
                );
            }
            "--out" => {
                out = Some(
                    args.next()
                        .map(PathBuf::from)
                        .ok_or("--out necesita una ruta")?,
                );
            }
            other => return Err(format!("argumento desconocido \"{other}\"")),
        }
    }
    Ok(Args {
        command,
        data_dir,
        seed,
        out,
    })
}

fn run_build(args: &Args) -> Result<(), Box<dyn std::error::Error>> {
    let started = Instant::now();
    let seed_dir = args
        .seed
        .clone()
        .unwrap_or_else(|| args.data_dir.join("seed"));
    let out = args
        .out
        .clone()
        .unwrap_or_else(|| args.data_dir.join("build").join("catalog.db"));
    let report = build_from_dir(&seed_dir, &out)?;
    println!("semilla: {}", seed_dir.display());
    println!("salida: {}", out.display());
    println!("plantas: {}", report.plants);
    println!("nombres: {}", report.names);
    println!(
        "grupos de uso: {} ({} pendientes de revisión)",
        report.use_groups, report.pending_use_groups
    );
    println!("usos: {}", report.uses);
    println!("citas sin resolver: {}", report.unresolved_citations);
    println!(
        "objetivos de planta: {} ({} pendientes de revisión)",
        report.plant_goals, report.pending_goals
    );
    println!("seguridad: {}", report.safety);
    println!("imágenes: {}", report.images);
    println!("referencias: {}", report.references);
    println!("fuentes: {}", report.sources);
    println!("alias: {}", report.aliases);
    println!("avisos de revisión: {}", report.review_flags);
    println!("hash: {}", report.content_hash);
    println!("tiempo: {:.2?}", started.elapsed());
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
        Command::Build => run_build(&args),
    };
    if let Err(err) = result {
        eprintln!("error: {err}");
        exit(1);
    }
}
