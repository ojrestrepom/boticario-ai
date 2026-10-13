//! Construcción, derivación y rederivación del catálogo.
//!
//! [`build`] parte de los insumos descargados (importa el crudo y luego deriva); [`rederive`] solo lee `raw.db`, sin insumo original ni red.

use std::path::Path;

use catalog_core::sqlite::read_only_url;
use diesel::{Connection, SqliteConnection};

use crate::adapter::validate_source;
use crate::consolidate::{Catalog, SourceInput, consolidate};
use crate::error::IngestError;
use crate::hash::content_hash;
use crate::input::{InputSpec, verify_input};
use crate::raw::import_raw;
use crate::sources::{AdapterRegistry, SourcesConfig};
use crate::write::write_catalog;

/// Resumen de una reconstrucción.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuildReport {
    /// Plantas del catálogo.
    pub plants: usize,
    /// Fuentes del catálogo.
    pub sources: usize,
    /// Hash del contenido lógico de la base escrita.
    pub content_hash: String,
}

/// URL de solo lectura de `path` (ver [`read_only_url`]), con el error de ruta convertido a [`IngestError`].
fn read_only(path: &Path) -> Result<String, IngestError> {
    read_only_url(path).map_err(|e| IngestError::Io {
        path: Some(e.path),
        message: "la ruta no es UTF-8 válido".to_string(),
    })
}

/// Deriva el catálogo consolidado desde la base cruda, con las fuentes activas de `config`.
pub fn derive_catalog(
    registry: &AdapterRegistry,
    config: &SourcesConfig,
    raw_db: &Path,
) -> Result<Catalog, IngestError> {
    if !raw_db.exists() {
        return Err(IngestError::MissingRawLayer {
            path: raw_db.to_path_buf(),
        });
    }
    // Solo lectura: derivar no debe poder modificar el crudo.
    let mut conn = SqliteConnection::establish(&read_only(raw_db)?)?;

    let mut inputs = Vec::new();
    for active in registry.resolve(config)? {
        let source = active.adapter.source();
        validate_source(&source)?;
        let records = active.adapter.derive(&mut conn)?;
        inputs.push(SourceInput {
            source,
            priority: active.priority,
            records,
        });
    }
    consolidate(inputs)
}

/// Construcción completa: verifica cada insumo en `cache_dir`, importa el crudo a `raw_db` y reconstruye `out`.
///
/// No descarga nada: si falta un insumo, el error indica ejecutar `download`. `raw_db` se recrea desde cero para que no queden tablas de una construcción anterior.
pub fn build(
    registry: &AdapterRegistry,
    config: &SourcesConfig,
    cache_dir: &Path,
    raw_db: &Path,
    out: &Path,
) -> Result<BuildReport, IngestError> {
    let active = registry.resolve(config)?;
    // Se verifican todos los insumos antes de tocar el disco.
    let mut specs = Vec::new();
    for source in &active {
        validate_source(&source.adapter.source())?;
        let input = source.adapter.input();
        let archive = cache_dir.join(&input.file_name);
        verify_input(&InputSpec {
            path: &archive,
            expected_size: input.expected_size,
            expected_md5: &input.expected_md5,
        })?;
        specs.push(source.adapter.raw_import(&archive));
    }
    match std::fs::remove_file(raw_db) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
        Err(e) => {
            return Err(IngestError::Io {
                path: Some(raw_db.to_path_buf()),
                message: e.to_string(),
            });
        }
    }
    for spec in &specs {
        import_raw(spec, raw_db)?;
    }
    rederive(registry, config, raw_db, out)
}

/// Reconstruye la base neutral `out` desde `raw_db` y devuelve su resumen.
pub fn rederive(
    registry: &AdapterRegistry,
    config: &SourcesConfig,
    raw_db: &Path,
    out: &Path,
) -> Result<BuildReport, IngestError> {
    let catalog = derive_catalog(registry, config, raw_db)?;
    write_catalog(&catalog, out)?;
    Ok(BuildReport {
        plants: catalog.plants.len(),
        sources: catalog.sources.len(),
        content_hash: content_hash(out)?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::raw::import_raw;
    use crate::sources::SourceEntry;
    use crate::test_support::{FixtureAdapter, FixtureCsv, build_zip, sample_catalog};

    fn registry(ids: &[&str]) -> AdapterRegistry {
        let mut registry = AdapterRegistry::new();
        for id in ids {
            registry
                .register(Box::new(FixtureAdapter::new(id)))
                .unwrap();
        }
        registry
    }

    fn config(entries: &[(&str, u32)]) -> SourcesConfig {
        SourcesConfig {
            sources: entries
                .iter()
                .map(|(id, priority)| SourceEntry {
                    id: id.to_string(),
                    priority: *priority,
                })
                .collect(),
        }
    }

    /// Importa los CSV de cada fuente a un mismo `raw.db`; el ZIP se borra al terminar.
    fn build_raw(dir: &tempfile::TempDir, sources: &[(&str, FixtureCsv)]) -> std::path::PathBuf {
        let raw_db = dir.path().join("build").join("raw.db");
        for (id, csv) in sources {
            let zip_dir = tempfile::tempdir().unwrap();
            let zip = build_zip(&zip_dir, &csv.entries());
            let spec = FixtureAdapter::new(id).raw_import(&zip);
            import_raw(&spec, &raw_db).unwrap();
            drop(zip_dir); // el ZIP desaparece: la rederivación no lo necesita
        }
        raw_db
    }

    use crate::adapter::SourceAdapter;
    use diesel::RunQueryDsl;

    #[test]
    fn rederive_without_the_zip_matches_direct_write() {
        let dir = tempfile::tempdir().unwrap();
        let raw_db = build_raw(
            &dir,
            &[("alpha", FixtureCsv::alpha()), ("beta", FixtureCsv::beta())],
        );
        let out = dir.path().join("build").join("catalog.db");
        let report = rederive(
            &registry(&["alpha", "beta"]),
            &config(&[("alpha", 1), ("beta", 2)]),
            &raw_db,
            &out,
        )
        .unwrap();
        assert_eq!((report.plants, report.sources), (2, 2));

        let direct = dir.path().join("direct.db");
        write_catalog(&sample_catalog(), &direct).unwrap();
        assert_eq!(report.content_hash, content_hash(&direct).unwrap());
    }

    #[test]
    fn two_sources_in_one_raw_db_are_attributed() {
        let dir = tempfile::tempdir().unwrap();
        let raw_db = build_raw(
            &dir,
            &[("alpha", FixtureCsv::alpha()), ("beta", FixtureCsv::beta())],
        );
        let catalog = derive_catalog(
            &registry(&["alpha", "beta"]),
            &config(&[("beta", 2), ("alpha", 1)]),
            &raw_db,
        )
        .unwrap();
        let lavender = &catalog.plants[0].plant;
        assert_eq!(lavender.id.0, "lavandula-angustifolia");
        let shared = lavender
            .names
            .iter()
            .find(|n| n.value.text == "lavender")
            .unwrap();
        assert_eq!(shared.sources.len(), 2);
        assert_eq!(lavender.family.as_ref().unwrap().value, "Lamiaceae");
    }

    #[test]
    fn config_selects_sources() {
        let dir = tempfile::tempdir().unwrap();
        let raw_db = build_raw(
            &dir,
            &[("alpha", FixtureCsv::alpha()), ("beta", FixtureCsv::beta())],
        );
        let catalog = derive_catalog(
            &registry(&["alpha", "beta"]),
            &config(&[("beta", 1)]),
            &raw_db,
        )
        .unwrap();
        assert_eq!(catalog.sources.len(), 1);
        assert_eq!(catalog.plants.len(), 2);
    }

    #[test]
    fn build_without_the_input_points_to_download() {
        let dir = tempfile::tempdir().unwrap();
        let err = build(
            &registry(&["alpha"]),
            &config(&[("alpha", 1)]),
            &dir.path().join(".cache"),
            &dir.path().join("build").join("raw.db"),
            &dir.path().join("build").join("catalog.db"),
        )
        .unwrap_err();
        assert!(matches!(err, IngestError::MissingInput { .. }));
        assert!(err.to_string().contains("download"));
        assert!(!dir.path().join("build").exists());
    }

    #[test]
    fn build_with_a_non_zip_input_fails_in_raw_import() {
        let dir = tempfile::tempdir().unwrap();
        let cache = dir.path().join(".cache");
        std::fs::create_dir_all(&cache).unwrap();
        // El adaptador de fixture declara tamaño 0 y el MD5 del vacío: un archivo vacío pasa la verificación.
        std::fs::write(cache.join("alpha.zip"), b"").unwrap();
        let err = build(
            &registry(&["alpha"]),
            &config(&[("alpha", 1)]),
            &cache,
            &dir.path().join("build").join("raw.db"),
            &dir.path().join("build").join("catalog.db"),
        )
        .unwrap_err();
        // El archivo vacío pasa la verificación pero no es un ZIP: falla en la importación cruda.
        assert!(matches!(err, IngestError::InvalidZip { .. }), "{err:?}");
    }

    #[test]
    fn derived_connection_is_read_only() {
        let dir = tempfile::tempdir().unwrap();
        let raw_db = build_raw(&dir, &[("alpha", FixtureCsv::alpha())]);
        let mut conn = SqliteConnection::establish(&read_only(&raw_db).unwrap()).unwrap();
        let err = diesel::sql_query("DROP TABLE raw_alpha_plants")
            .execute(&mut conn)
            .unwrap_err();
        assert!(err.to_string().contains("readonly"), "{err}");
    }

    #[test]
    fn missing_raw_db_is_reported() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("raw.db");
        let err =
            derive_catalog(&registry(&["alpha"]), &config(&[("alpha", 1)]), &path).unwrap_err();
        assert_eq!(err, IngestError::MissingRawLayer { path });
        assert!(err.to_string().contains("importación cruda"));
        assert!(!dir.path().join("raw.db").exists());
    }

    #[test]
    fn source_without_raw_tables_names_the_table() {
        let dir = tempfile::tempdir().unwrap();
        let raw_db = build_raw(&dir, &[("alpha", FixtureCsv::alpha())]);
        let err = derive_catalog(
            &registry(&["alpha", "beta"]),
            &config(&[("alpha", 1), ("beta", 2)]),
            &raw_db,
        )
        .unwrap_err();
        match err {
            IngestError::Storage(msg) => assert!(msg.contains("raw_beta_plants"), "{msg}"),
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn invalid_source_metadata_stops_the_build() {
        // El adaptador de fixture con id inválido es rechazado por `validate_source` antes de derivar.
        let dir = tempfile::tempdir().unwrap();
        let raw_db = build_raw(&dir, &[("alpha", FixtureCsv::alpha())]);
        let mut registry = AdapterRegistry::new();
        registry
            .register(Box::new(FixtureAdapter::new("Bad-Id")))
            .unwrap();
        let err = derive_catalog(&registry, &config(&[("Bad-Id", 1)]), &raw_db).unwrap_err();
        assert!(matches!(err, IngestError::InvalidSourceId { .. }));
    }
}
