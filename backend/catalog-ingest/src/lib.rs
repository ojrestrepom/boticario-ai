//! Ingesta del catálogo: verificación del insumo y capa cruda.
//!
//! Este crate es biblioteca y binario a la vez: la lógica vive aquí (para poder probarla y reutilizarla) y `main.rs` será solo una CLI delgada que la invoque.

#![deny(missing_docs)]

pub mod error;
pub mod input;
pub mod raw;

#[cfg(test)]
mod test_support;

pub use error::IngestError;
