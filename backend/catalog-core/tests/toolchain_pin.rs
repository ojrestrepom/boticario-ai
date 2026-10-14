//! Guardia de versión del toolchain: la versión de Rust fijada en `mise.toml`
//! debe coincidir con la etiqueta de la imagen base del `Dockerfile`.
//! Si divergen, el desarrollo local y la imagen compilan con compiladores
//! distintos y los fallos solo aparecen al construir la imagen.

use std::fs;
use std::path::PathBuf;

/// Devuelve la versión de Rust de `mise.toml` (clave `tools.rust`).
/// Se parsea con la dependencia `toml` (ya declarada en el workspace) en lugar de
/// buscar texto, para no depender del formato exacto (comillas, espacios, comentarios).
fn mise_rust_version(mise_toml: &str) -> Result<String, String> {
    let table: toml::Table = mise_toml
        .parse()
        .map_err(|e| format!("mise.toml no es TOML válido: {e}"))?;
    table
        .get("tools")
        .and_then(|tools| tools.get("rust"))
        .and_then(|rust| rust.as_str())
        .map(str::to_owned)
        .ok_or_else(|| "mise.toml no define la clave `tools.rust`".to_owned())
}

/// Devuelve la versión de Rust de la primera línea `FROM rust:` del `Dockerfile`.
/// La etiqueta puede llevar sufijo de distribución (`1.99.0-slim-bookworm`), que se descarta.
fn dockerfile_rust_version(dockerfile: &str) -> Result<String, String> {
    let line = dockerfile
        .lines()
        .map(str::trim_start)
        .find(|line| line.starts_with("FROM rust:"))
        .ok_or_else(|| "el Dockerfile no contiene ninguna línea `FROM rust:`".to_owned())?;
    let tag = line["FROM rust:".len()..]
        .split_whitespace()
        .next()
        .unwrap_or("");
    let version = tag.split('-').next().unwrap_or("");
    if version.is_empty() {
        return Err(format!("la línea `{line}` del Dockerfile no trae versión"));
    }
    Ok(version.to_owned())
}

/// Compara ambas versiones; es pura para poder probarla sin tocar el disco.
fn compare_rust_pins(mise_toml: &str, dockerfile: &str) -> Result<(), String> {
    let mise = mise_rust_version(mise_toml)?;
    let docker = dockerfile_rust_version(dockerfile)?;
    if mise == docker {
        Ok(())
    } else {
        Err(format!(
            "la versión de Rust difiere: mise.toml fija {mise} y el Dockerfile usa {docker}"
        ))
    }
}

fn read_repo_file(name: &str) -> String {
    // catalog-core vive en <raíz>/backend/catalog-core: la raíz está dos niveles arriba.
    let path: PathBuf = [env!("CARGO_MANIFEST_DIR"), "..", ".."]
        .iter()
        .collect::<PathBuf>()
        .join(name);
    fs::read_to_string(&path).unwrap_or_else(|e| panic!("no se pudo leer {}: {e}", path.display()))
}

#[test]
fn dockerfile_and_mise_pin_the_same_rust_version() {
    let mise = read_repo_file("mise.toml");
    let dockerfile = read_repo_file("Dockerfile");
    if let Err(msg) = compare_rust_pins(&mise, &dockerfile) {
        panic!("{msg}. Alinea `mise.toml` y el `Dockerfile` a la misma versión de Rust.");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MISE: &str = "[tools]\nrust = \"1.99.0\"\n";

    #[test]
    fn matching_versions_pass() {
        let docker = "# c\nFROM rust:1.99.0-slim-bookworm AS build\n";
        assert_eq!(compare_rust_pins(MISE, docker), Ok(()));
    }

    #[test]
    fn diverging_versions_name_both() {
        let docker = "FROM rust:1.98.0-slim-bookworm AS build\n";
        let err = compare_rust_pins(MISE, docker).unwrap_err();
        assert!(err.contains("1.99.0") && err.contains("1.98.0"), "{err}");
    }

    #[test]
    fn missing_key_in_mise_fails() {
        let err = compare_rust_pins("[tools]\nnode = \"22\"\n", "FROM rust:1.99.0\n").unwrap_err();
        assert!(err.contains("tools.rust"), "{err}");
    }

    #[test]
    fn missing_from_rust_in_dockerfile_fails() {
        let err = compare_rust_pins(MISE, "FROM debian:bookworm-slim\n").unwrap_err();
        assert!(err.contains("FROM rust:"), "{err}");
    }

    #[test]
    fn tag_without_suffix_is_accepted() {
        assert_eq!(
            compare_rust_pins(MISE, "  FROM rust:1.99.0 AS build\n"),
            Ok(())
        );
    }
}
