//! API de solo lectura del catálogo de plantas.
//!
//! Este crate es biblioteca y binario a la vez: la lógica vive aquí (para poder probarla) y `main.rs` es solo el arranque.
//! Contiene la capa de repositorio (la implementación SQLite del trait de `catalog-core` y el adaptador asíncrono), los DTOs de respuesta, los errores `problem+json`, el router HTTP, el documento OpenAPI y la configuración y el arranque.

#![deny(missing_docs)]

pub mod async_catalog;
pub mod config;
pub mod dto;
pub mod error;
pub mod http;
pub mod logging;
pub mod openapi;
pub mod repository;
pub mod startup;

#[cfg(test)]
mod test_support;
