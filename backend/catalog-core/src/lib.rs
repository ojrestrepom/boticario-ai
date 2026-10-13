//! Núcleo compartido del catálogo: tipos de dominio y reglas comunes.
//!
//! Lo usan tanto la ingesta (que construye la base) como la API (que la lee), así que no depende de HTTP, de serde ni de ningún crate de SQLite en producción.
#![deny(missing_docs)]

pub mod domain;
pub mod normalize;
pub mod repository;
pub mod schema;
