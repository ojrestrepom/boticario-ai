//! API de solo lectura del catálogo de plantas.
//!
//! Este crate es biblioteca y binario a la vez: la lógica vive aquí (para poder probarla) y `main.rs` será solo el arranque.
//! Por ahora contiene la capa de repositorio: la implementación SQLite del trait de `catalog-core` y el adaptador asíncrono que usarán los handlers HTTP.

#![deny(missing_docs)]

pub mod async_catalog;
pub mod repository;

#[cfg(test)]
mod test_support;
