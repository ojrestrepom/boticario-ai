//! Adaptador asíncrono sobre el trait síncrono del repositorio.
//!
//! Los handlers HTTP dependen solo de [`AsyncCatalog`], y este solo del trait [`CatalogRepository`]: ninguno conoce SQLite.

use std::sync::Arc;

use catalog_core::domain::{ListQuery, Page, Plant, PlantId, PlantSummary, Source};
use catalog_core::repository::{CatalogRepository, RepositoryError};
use tokio::task::{JoinError, spawn_blocking};

/// Catálogo con métodos `async`, apto para compartirse (es barato de clonar) entre handlers.
#[derive(Clone)]
pub struct AsyncCatalog {
    repo: Arc<dyn CatalogRepository>,
}

/// Un fallo al unir la tarea bloqueante (pánico o cancelación) se informa como error de almacenamiento.
fn join_error(err: JoinError) -> RepositoryError {
    RepositoryError::Storage(format!("la tarea bloqueante falló: {err}"))
}

impl AsyncCatalog {
    /// Crea el adaptador sobre cualquier implementación del trait.
    pub fn new(repo: Arc<dyn CatalogRepository>) -> Self {
        Self { repo }
    }

    /// Versión asíncrona de [`CatalogRepository::list_plants`].
    pub async fn list_plants(
        &self,
        query: ListQuery,
    ) -> Result<Page<PlantSummary>, RepositoryError> {
        // El closure es `move` y `'static`: toma su propio `Arc` clonado y la consulta, sin préstamos del `&self`.
        let repo = Arc::clone(&self.repo);
        spawn_blocking(move || repo.list_plants(&query))
            .await
            .map_err(join_error)?
    }

    /// Versión asíncrona de [`CatalogRepository::get_plant`].
    pub async fn get_plant(&self, id: PlantId) -> Result<Option<Plant>, RepositoryError> {
        let repo = Arc::clone(&self.repo);
        spawn_blocking(move || repo.get_plant(&id))
            .await
            .map_err(join_error)?
    }

    /// Versión asíncrona de [`CatalogRepository::list_sources`].
    pub async fn list_sources(&self) -> Result<Vec<Source>, RepositoryError> {
        let repo = Arc::clone(&self.repo);
        spawn_blocking(move || repo.list_sources())
            .await
            .map_err(join_error)?
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::Fixture;
    use catalog_core::domain::SourceId;

    /// Repositorio falso en memoria: demuestra que el adaptador solo depende del trait.
    struct FakeRepository {
        plants: Vec<PlantSummary>,
        sources: Vec<Source>,
    }

    impl CatalogRepository for FakeRepository {
        fn list_plants(&self, query: &ListQuery) -> Result<Page<PlantSummary>, RepositoryError> {
            let items = self
                .plants
                .iter()
                .skip(query.offset as usize)
                .take(query.limit as usize)
                .cloned()
                .collect();
            Ok(Page {
                items,
                total: self.plants.len() as u64,
            })
        }

        fn get_plant(&self, id: &PlantId) -> Result<Option<Plant>, RepositoryError> {
            Ok(self.plants.iter().find(|p| &p.id == id).map(|p| Plant {
                id: p.id.clone(),
                scientific_name: p.scientific_name.clone(),
                family: None,
                names: Vec::new(),
                parts: Vec::new(),
                uses: Vec::new(),
            }))
        }

        fn list_sources(&self) -> Result<Vec<Source>, RepositoryError> {
            Ok(self.sources.clone())
        }
    }

    /// Repositorio que entra en pánico: comprueba que el pánico se informa como error y no tumba al llamador.
    struct PanickingRepository;

    impl CatalogRepository for PanickingRepository {
        fn list_plants(&self, _: &ListQuery) -> Result<Page<PlantSummary>, RepositoryError> {
            panic!("boom")
        }
        fn get_plant(&self, _: &PlantId) -> Result<Option<Plant>, RepositoryError> {
            panic!("boom")
        }
        fn list_sources(&self) -> Result<Vec<Source>, RepositoryError> {
            panic!("boom")
        }
    }

    fn summary(id: &str) -> PlantSummary {
        PlantSummary {
            id: PlantId(id.to_string()),
            scientific_name: id.to_string(),
            common_names: Vec::new(),
            family: None,
        }
    }

    fn fake() -> AsyncCatalog {
        AsyncCatalog::new(Arc::new(FakeRepository {
            plants: vec![summary("a"), summary("b"), summary("c")],
            sources: vec![Source {
                id: SourceId("s".to_string()),
                name: "S".to_string(),
                version: "1".to_string(),
                license: "L".to_string(),
                citation: "C".to_string(),
                url: "U".to_string(),
                checksum: "K".to_string(),
            }],
        }))
    }

    #[tokio::test]
    async fn works_with_an_in_memory_repository() {
        let catalog = fake();
        let page = catalog
            .list_plants(ListQuery {
                q: None,
                limit: 2,
                offset: 1,
            })
            .await
            .unwrap();
        assert_eq!(page.total, 3);
        assert_eq!(page.items, vec![summary("b"), summary("c")]);
        let found = catalog.get_plant(PlantId("a".to_string())).await.unwrap();
        assert_eq!(found.unwrap().scientific_name, "a");
        assert_eq!(
            catalog.get_plant(PlantId("zzz".to_string())).await.unwrap(),
            None
        );
        assert_eq!(catalog.list_sources().await.unwrap().len(), 1);
    }

    #[tokio::test]
    async fn blocking_task_failure_becomes_a_storage_error() {
        let catalog = AsyncCatalog::new(Arc::new(PanickingRepository));
        let err = catalog.list_sources().await.unwrap_err();
        assert!(matches!(err, RepositoryError::Storage(_)), "{err:?}");
    }

    #[tokio::test]
    async fn concurrent_calls_over_sqlite() {
        let fixture = Fixture::standard();
        let catalog = AsyncCatalog::new(Arc::new(fixture.repo()));
        let (page, detail, sources) = tokio::join!(
            catalog.list_plants(ListQuery::default()),
            catalog.get_plant(PlantId("lavandula-angustifolia".to_string())),
            catalog.list_sources(),
        );
        assert_eq!(page.unwrap().total, 31);
        assert_eq!(detail.unwrap().unwrap().uses.len(), 2);
        assert_eq!(sources.unwrap().len(), 2);
    }
}
