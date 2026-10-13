//! Núcleo compartido del catálogo: tipos de dominio y reglas comunes.
//!
//! Lo usan tanto la ingesta (que construye la base) como la API (que la lee), así que no depende de HTTP ni de serde.
//! Sí depende de Diesel: aquí viven el esquema neutral (migración y `schema.rs` generado) y las filas de sus tablas, que ambos crates comparten.
#![deny(missing_docs)]

pub mod domain;
pub mod normalize;
pub mod repository;
pub mod rows;
// Generado por `diesel print-schema`: no se edita a mano ni se le añaden docs.
#[allow(missing_docs)]
pub mod schema;
pub mod sqlite;
pub mod version;
