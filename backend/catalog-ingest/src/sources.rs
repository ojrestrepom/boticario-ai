//! Configuración de fuentes activas y registro de adaptadores.

use std::collections::{BTreeMap, HashSet};
use std::path::Path;

use serde::Deserialize;

use crate::adapter::SourceAdapter;
use crate::error::IngestError;

/// Contenido de `data/sources.toml`.
///
/// Deriva `Deserialize` de serde: `toml` rellena la estructura directamente desde el texto. `deny_unknown_fields` convierte una errata en la clave (`prioritiy`) en error en vez de ignorarla.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourcesConfig {
    /// Fuentes activas.
    pub sources: Vec<SourceEntry>,
}

/// Una fuente activa y su prioridad.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceEntry {
    /// Identificador de la fuente.
    pub id: String,
    /// Prioridad: 1 es la más alta.
    pub priority: u32,
}

/// Interpreta y valida el texto de la configuración.
pub fn parse_sources_config(text: &str) -> Result<SourcesConfig, IngestError> {
    parse(text).map_err(|message| IngestError::InvalidConfig {
        path: None,
        message,
    })
}

/// Lee y valida un archivo de configuración.
pub fn load_sources_config(path: &Path) -> Result<SourcesConfig, IngestError> {
    let text = std::fs::read_to_string(path).map_err(|e| IngestError::Io {
        path: Some(path.to_path_buf()),
        message: e.to_string(),
    })?;
    parse(&text).map_err(|message| IngestError::InvalidConfig {
        path: Some(path.to_path_buf()),
        message,
    })
}

// El mensaje es un `String` para que quien llama decida si añade la ruta.
fn parse(text: &str) -> Result<SourcesConfig, String> {
    let config: SourcesConfig = toml::from_str(text).map_err(|e| e.to_string())?;
    if config.sources.is_empty() {
        return Err("debe haber al menos una fuente".to_string());
    }
    let mut ids = HashSet::new();
    let mut priorities = HashSet::new();
    for entry in &config.sources {
        if entry.priority < 1 {
            return Err(format!(
                "la fuente \"{}\" tiene prioridad 0: debe ser >= 1",
                entry.id
            ));
        }
        if !ids.insert(entry.id.as_str()) {
            return Err(format!("la fuente \"{}\" está repetida", entry.id));
        }
        if !priorities.insert(entry.priority) {
            return Err(format!("la prioridad {} está repetida", entry.priority));
        }
    }
    Ok(config)
}

/// Fuente activa: su prioridad y un préstamo de su adaptador.
///
/// El adaptador es una referencia (`&dyn`) y no un `Box`: el registro sigue siendo su dueño y la fuente activa solo lo "presta". El parámetro `'a` ata la vida de este valor a la del registro, de modo que el compilador impide usarlo si el registro desaparece.
pub struct ActiveSource<'a> {
    /// Prioridad de la fuente (1 = la más alta).
    pub priority: u32,
    /// Adaptador prestado por el registro.
    pub adapter: &'a dyn SourceAdapter,
}

/// Adaptadores conocidos por el programa, indexados por id de fuente.
#[derive(Default)]
pub struct AdapterRegistry {
    adapters: BTreeMap<String, Box<dyn SourceAdapter>>,
}

impl AdapterRegistry {
    /// Crea un registro vacío.
    pub fn new() -> Self {
        Self::default()
    }

    /// Registra un adaptador bajo el id de su fuente; falla si ya hay uno.
    ///
    /// `Box<dyn SourceAdapter>` permite guardar adaptadores de tipos distintos en la misma colección: el `Box` pone el valor en el montón y `dyn` despacha los métodos en tiempo de ejecución.
    pub fn register(&mut self, adapter: Box<dyn SourceAdapter>) -> Result<(), IngestError> {
        let id = adapter.source().id.0;
        if self.adapters.contains_key(&id) {
            return Err(IngestError::DuplicateAdapter { id });
        }
        self.adapters.insert(id, adapter);
        Ok(())
    }

    /// Resuelve las fuentes de la configuración, ordenadas por prioridad.
    ///
    /// Falla con [`IngestError::UnknownSource`] si alguna no tiene adaptador.
    pub fn resolve(&self, config: &SourcesConfig) -> Result<Vec<ActiveSource<'_>>, IngestError> {
        let mut active = Vec::new();
        for entry in &config.sources {
            let adapter =
                self.adapters
                    .get(&entry.id)
                    .ok_or_else(|| IngestError::UnknownSource {
                        id: entry.id.clone(),
                    })?;
            active.push(ActiveSource {
                priority: entry.priority,
                // `as_ref` convierte `&Box<dyn T>` en `&dyn T`, prestado del registro.
                adapter: adapter.as_ref(),
            });
        }
        active.sort_by_key(|a| a.priority);
        Ok(active)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::{FixtureAdapter, alpha_records, beta_records};

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

    fn registry() -> AdapterRegistry {
        let mut registry = AdapterRegistry::new();
        registry
            .register(Box::new(FixtureAdapter::new("alpha", alpha_records())))
            .unwrap();
        registry
            .register(Box::new(FixtureAdapter::new("beta", beta_records())))
            .unwrap();
        registry
    }

    fn ids(active: &[ActiveSource<'_>]) -> Vec<String> {
        active.iter().map(|a| a.adapter.source().id.0).collect()
    }

    #[test]
    fn parses_example() {
        let text = "[[sources]]\nid = \"usda\"\npriority = 1\n";
        assert_eq!(parse_sources_config(text), Ok(config(&[("usda", 1)])));
    }

    #[test]
    fn project_config_is_valid() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../data/sources.toml");
        assert_eq!(load_sources_config(&path), Ok(config(&[("usda", 1)])));
    }

    #[test]
    fn rejects_invalid_configs() {
        let cases = [
            (
                "está repetida",
                "[[sources]]\nid=\"a\"\npriority=1\n[[sources]]\nid=\"a\"\npriority=2\n",
            ),
            (
                "prioridad 1 está repetida",
                "[[sources]]\nid=\"a\"\npriority=1\n[[sources]]\nid=\"b\"\npriority=1\n",
            ),
            ("prioridad 0", "[[sources]]\nid=\"a\"\npriority=0\n"),
            ("al menos una", "sources = []\n"),
            ("priority", "[[sources]]\nid=\"a\"\n"),
        ];
        for (needle, text) in cases {
            match parse_sources_config(text) {
                Err(IngestError::InvalidConfig { message, .. }) => {
                    assert!(message.contains(needle), "{needle}: {message}")
                }
                other => panic!("{needle}: {other:?}"),
            }
        }
    }

    #[test]
    fn load_reports_missing_file() {
        let err = load_sources_config(Path::new("/no/existe/sources.toml")).unwrap_err();
        assert!(matches!(err, IngestError::Io { path: Some(_), .. }));
    }

    #[test]
    fn resolve_orders_by_priority() {
        let registry = registry();
        let active = registry
            .resolve(&config(&[("beta", 1), ("alpha", 2)]))
            .unwrap();
        assert_eq!(ids(&active), ["beta", "alpha"]);
        assert_eq!(active[0].priority, 1);
    }

    #[test]
    fn changing_config_changes_resolved_sources() {
        let registry = registry();
        let both = registry
            .resolve(&config(&[("alpha", 1), ("beta", 2)]))
            .unwrap();
        let only_beta = registry.resolve(&config(&[("beta", 1)])).unwrap();
        assert_eq!(ids(&both), ["alpha", "beta"]);
        assert_eq!(ids(&only_beta), ["beta"]);
    }

    #[test]
    fn unknown_source_is_named() {
        let registry = registry();
        let err = registry
            .resolve(&config(&[("alpha", 1), ("gamma", 2)]))
            .err()
            .unwrap();
        assert_eq!(
            err,
            IngestError::UnknownSource {
                id: "gamma".to_string()
            }
        );
        assert!(err.to_string().contains("gamma"));
    }

    #[test]
    fn duplicate_adapter_is_rejected() {
        let mut registry = registry();
        let err = registry
            .register(Box::new(FixtureAdapter::new("alpha", alpha_records())))
            .unwrap_err();
        assert_eq!(
            err,
            IngestError::DuplicateAdapter {
                id: "alpha".to_string()
            }
        );
    }
}
