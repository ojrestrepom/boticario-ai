//! Configuración del servidor a partir de argumentos y variables de entorno.
//!
//! Prioridad para la ruta de la base: argumento `--db`, luego `CATALOG_DB`, luego el valor por defecto.
//! `HOST` y `PORT` solo se leen del entorno.

use std::error::Error;
use std::fmt;
use std::path::PathBuf;

/// Ruta de la base por defecto, relativa al directorio de trabajo.
///
/// Es una comodidad para el desarrollo local (`catalog-ingest build` escribe ahí); en un despliegue debe fijarse con `CATALOG_DB` o `--db`.
pub const DEFAULT_DB_PATH: &str = "data/build/catalog.db";
/// Dirección por defecto: solo la propia máquina.
pub const DEFAULT_HOST: &str = "127.0.0.1";
/// Puerto por defecto.
pub const DEFAULT_PORT: u16 = 8080;

/// Texto de ayuda de `--help`.
pub const USAGE: &str = "\
API de solo lectura del catálogo de plantas.

Uso: catalog-api [--db <ruta>] [--openapi] [--help]

Opciones:
  --db <ruta>  Ruta de la base del catálogo (prioridad sobre CATALOG_DB)
  --openapi    Imprime el documento OpenAPI y sale
  --help       Muestra esta ayuda

Variables de entorno:
  CATALOG_DB   Ruta de la base (por defecto data/build/catalog.db, relativa al directorio de trabajo)
  HOST         Dirección de escucha (por defecto 127.0.0.1)
  PORT         Puerto de escucha (por defecto 8080)
  RUST_LOG     Filtro de logs (por defecto info)";

/// Qué debe hacer el programa.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Servir la API.
    Serve,
    /// Imprimir la ayuda y salir.
    Help,
    /// Imprimir el documento OpenAPI y salir.
    PrintOpenApi,
}

/// Configuración resuelta.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Config {
    /// Ruta de la base SQLite.
    pub db_path: PathBuf,
    /// Dirección de escucha.
    pub host: String,
    /// Puerto de escucha.
    pub port: u16,
    /// Acción pedida por los argumentos.
    pub mode: Mode,
}

/// Configuración inválida.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConfigError {
    /// Argumento que no existe.
    UnknownArgument(String),
    /// `--db` sin valor.
    MissingValue(&'static str),
    /// `PORT` no es un número de puerto válido.
    InvalidPort(String),
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnknownArgument(arg) => write!(f, "argumento desconocido: {arg} (usa --help)"),
            Self::MissingValue(arg) => write!(f, "{arg} necesita un valor"),
            Self::InvalidPort(value) => {
                write!(
                    f,
                    "PORT inválido: {value:?}; debe ser un entero entre 0 y 65535"
                )
            }
        }
    }
}

impl Error for ConfigError {}

/// Resuelve la configuración.
///
/// `args` son los argumentos sin el nombre del programa. `env` consulta una variable de entorno: se recibe como función para poder probar sin tocar el entorno real. Una variable vacía cuenta como ausente.
pub fn from_env_and_args(
    args: impl Iterator<Item = String>,
    env: impl Fn(&str) -> Option<String>,
) -> Result<Config, ConfigError> {
    let env = |key: &str| env(key).filter(|v| !v.is_empty());

    let mut mode = Mode::Serve;
    let mut db_arg: Option<String> = None;
    let mut args = args;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--help" | "-h" => mode = Mode::Help,
            "--openapi" => mode = Mode::PrintOpenApi,
            "--db" => db_arg = Some(args.next().ok_or(ConfigError::MissingValue("--db"))?),
            other => match other.strip_prefix("--db=") {
                Some(value) => db_arg = Some(value.to_string()),
                None => return Err(ConfigError::UnknownArgument(arg)),
            },
        }
    }

    // Una ruta vacía no puede ser una base: se trata igual que si faltara el valor.
    if db_arg.as_deref() == Some("") {
        return Err(ConfigError::MissingValue("--db"));
    }
    let db_path = db_arg
        .or_else(|| env("CATALOG_DB"))
        .unwrap_or_else(|| DEFAULT_DB_PATH.to_string());
    let host = env("HOST").unwrap_or_else(|| DEFAULT_HOST.to_string());
    let port = match env("PORT") {
        None => DEFAULT_PORT,
        Some(text) => text.parse().map_err(|_| ConfigError::InvalidPort(text))?,
    };
    Ok(Config {
        db_path: PathBuf::from(db_path),
        host,
        port,
        mode,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn resolve(args: &[&str], env: &[(&str, &str)]) -> Result<Config, ConfigError> {
        from_env_and_args(args.iter().map(|s| s.to_string()), |key| {
            env.iter()
                .find(|(k, _)| *k == key)
                .map(|(_, v)| v.to_string())
        })
    }

    #[test]
    fn defaults() {
        let config = resolve(&[], &[]).unwrap();
        assert_eq!(config.db_path, PathBuf::from("data/build/catalog.db"));
        assert_eq!((config.host.as_str(), config.port), ("127.0.0.1", 8080));
        assert_eq!(config.mode, Mode::Serve);
    }

    #[test]
    fn db_argument_beats_environment() {
        let env = [("CATALOG_DB", "/env.db")];
        assert_eq!(
            resolve(&[], &env).unwrap().db_path,
            PathBuf::from("/env.db")
        );
        assert_eq!(
            resolve(&["--db", "/arg.db"], &env).unwrap().db_path,
            PathBuf::from("/arg.db")
        );
        assert_eq!(
            resolve(&["--db=/eq.db"], &env).unwrap().db_path,
            PathBuf::from("/eq.db")
        );
    }

    #[test]
    fn host_and_port_come_from_environment() {
        let config = resolve(&[], &[("HOST", "0.0.0.0"), ("PORT", "9000")]).unwrap();
        assert_eq!((config.host.as_str(), config.port), ("0.0.0.0", 9000));
        // Vacías cuentan como ausentes.
        assert_eq!(resolve(&[], &[("PORT", "")]).unwrap().port, 8080);
    }

    #[test]
    fn invalid_port_is_an_error() {
        for port in ["abc", "70000", "-1"] {
            let err = resolve(&[], &[("PORT", port)]).unwrap_err();
            assert_eq!(err, ConfigError::InvalidPort(port.to_string()));
            assert!(err.to_string().contains("PORT"));
        }
    }

    #[test]
    fn flags_and_errors() {
        assert_eq!(resolve(&["--help"], &[]).unwrap().mode, Mode::Help);
        assert_eq!(
            resolve(&["--openapi"], &[]).unwrap().mode,
            Mode::PrintOpenApi
        );
        assert_eq!(
            resolve(&["--nope"], &[]).unwrap_err(),
            ConfigError::UnknownArgument("--nope".to_string())
        );
        assert_eq!(
            resolve(&["--db"], &[]).unwrap_err(),
            ConfigError::MissingValue("--db")
        );
        for args in [&["--db", ""][..], &["--db="][..]] {
            assert_eq!(
                resolve(args, &[("CATALOG_DB", "/env.db")]).unwrap_err(),
                ConfigError::MissingValue("--db")
            );
        }
    }
}
