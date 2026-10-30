//! Ingesta del catálogo: lectura y verificación de la semilla, construcción de `catalog.db` y hash de su contenido.
//!
//! Este crate es biblioteca y binario a la vez: la lógica vive aquí (para poder probarla y reutilizarla) y `main.rs` es solo una CLI delgada que la invoca.

#![deny(missing_docs)]

pub mod error;
pub mod hash;
pub mod seed;
pub mod seed_build;

pub use error::IngestError;
