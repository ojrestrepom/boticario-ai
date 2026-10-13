//! API de solo lectura del catálogo de plantas.
//!
//! Este crate es biblioteca y binario a la vez: la lógica vive aquí (para poder probarla) y `main.rs` será solo el arranque.
//! Contiene la capa de repositorio (la implementación SQLite del trait de `catalog-core` y el adaptador asíncrono), los DTOs de respuesta, los errores `problem+json` y el router HTTP.

#![deny(missing_docs)]

pub mod async_catalog;
pub mod dto;
pub mod error;
pub mod http;
pub mod repository;

#[cfg(test)]
mod test_support;
