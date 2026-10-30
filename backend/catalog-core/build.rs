//! Avisa a Cargo de que debe recompilar si cambian las migraciones.
//!
//! `embed_migrations!` mete el SQL en el binario al compilar, pero Cargo no sabe que depende de esa carpeta: sin esto, añadir una migración nueva no dispararía la recompilación.

fn main() {
    println!("cargo:rerun-if-changed=../../data/migrations");
}
