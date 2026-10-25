//! Ingesta del catálogo: verificación del insumo, capa cruda, adaptadores y consolidación.
//!
//! Este crate es biblioteca y binario a la vez: la lógica vive aquí (para poder probarla y reutilizarla) y `main.rs` es solo una CLI delgada que la invoca.

#![deny(missing_docs)]

pub mod adapter;
pub mod build;
pub mod consolidate;
pub mod download;
pub mod error;
pub mod hash;
pub mod input;
pub mod raw;
pub mod seed;
pub mod sources;
pub mod usda;
pub mod write;

#[cfg(any(test, feature = "test-fixtures"))]
pub mod test_support;

pub use error::IngestError;
