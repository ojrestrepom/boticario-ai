//! Ingesta del catálogo: verificación del insumo, capa cruda, adaptadores y consolidación.
//!
//! Este crate es biblioteca y binario a la vez: la lógica vive aquí (para poder probarla y reutilizarla) y `main.rs` será solo una CLI delgada que la invoque.

#![deny(missing_docs)]

pub mod adapter;
pub mod consolidate;
pub mod error;
pub mod input;
pub mod raw;
pub mod sources;

#[cfg(test)]
mod test_support;

pub use error::IngestError;
