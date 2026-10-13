//! Filas de las tablas del esquema neutral, como structs de Diesel.
//!
//! Las comparten la ingesta (que escribe) y la API (que lee).
//! Son la forma de la tabla, no el modelo de dominio: los tipos de `domain` no saben nada de Diesel y cada crate convierte entre unos y otros.
//!
//! - `Queryable` + `Selectable`: Diesel construye la fila al leer, y `Selectable` comprueba en compilación que los campos coinciden con las columnas.
//! - `Insertable`: Diesel la acepta en `insert_into(tabla).values(&fila)`.
//!
//! Las tablas con id entero que asigna SQLite (`plant_name`, `plant_part`, `plant_use`) tienen además un `New…` para insertar: no lleva el id, que se pide de vuelta con `RETURNING`.

use diesel::prelude::*;

use crate::schema::{
    metadata, plant, plant_name, plant_name_source, plant_part, plant_part_source, plant_source_id,
    plant_use, plant_use_source, reference, reference_source, source,
};

/// Fila de `metadata`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = metadata)]
pub struct MetadataRow {
    /// Clave del metadato.
    pub key: String,
    /// Valor del metadato.
    pub value: String,
}

/// Fila de `source`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = source)]
pub struct SourceRow {
    /// Identificador de la fuente.
    pub id: String,
    /// Nombre legible.
    pub name: String,
    /// Versión del dataset.
    pub version: String,
    /// Licencia.
    pub license: String,
    /// Cita recomendada.
    pub citation: String,
    /// URL de origen.
    pub url: String,
    /// Checksum del insumo original.
    pub checksum: String,
}

/// Fila de `plant`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant)]
pub struct PlantRow {
    /// ID público (slug del nombre científico).
    pub id: String,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Nombre científico normalizado; es la identidad canónica.
    pub scientific_name_normalized: String,
    /// Familia, si alguna fuente la aporta.
    pub family: Option<String>,
    /// Fuente elegida para la familia; es `None` si y solo si `family` lo es.
    pub family_source_id: Option<String>,
}

/// Fila de `plant_source_id`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_source_id)]
pub struct PlantSourceIdRow {
    /// Planta (ID público).
    pub plant_id: String,
    /// Fuente que le da el identificador.
    pub source_id: String,
    /// Identificador de la planta en esa fuente.
    pub source_plant_id: String,
}

/// Fila de `plant_name`, tal como se lee.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable)]
#[diesel(table_name = plant_name)]
pub struct PlantNameRow {
    /// Id asignado por SQLite.
    pub id: i32,
    /// Planta (ID público).
    pub plant_id: String,
    /// Texto del nombre.
    pub text: String,
    /// `scientific` o `common`.
    pub kind: String,
    /// Idioma del nombre.
    pub language: String,
    /// Texto normalizado para buscar.
    pub normalized: String,
}

/// Fila nueva de `plant_name`: sin id, que lo asigna SQLite.
#[derive(Debug, Clone, Insertable)]
#[diesel(table_name = plant_name)]
pub struct NewPlantName<'a> {
    /// Planta (ID público).
    pub plant_id: &'a str,
    /// Texto del nombre.
    pub text: &'a str,
    /// `scientific` o `common`.
    pub kind: &'a str,
    /// Idioma del nombre.
    pub language: &'a str,
    /// Texto normalizado para buscar.
    pub normalized: &'a str,
}

/// Fila de `plant_part`, tal como se lee.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable)]
#[diesel(table_name = plant_part)]
pub struct PlantPartRow {
    /// Id asignado por SQLite.
    pub id: i32,
    /// Planta (ID público).
    pub plant_id: String,
    /// Etiqueta de la parte.
    pub label: String,
}

/// Fila nueva de `plant_part`: sin id.
#[derive(Debug, Clone, Insertable)]
#[diesel(table_name = plant_part)]
pub struct NewPlantPart<'a> {
    /// Planta (ID público).
    pub plant_id: &'a str,
    /// Etiqueta de la parte.
    pub label: &'a str,
}

/// Fila de `reference`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = reference)]
pub struct ReferenceRow {
    /// Identificador de la referencia.
    pub id: String,
    /// Cita bibliográfica.
    pub citation: String,
}

/// Fila de `plant_use`, tal como se lee.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable)]
#[diesel(table_name = plant_use)]
pub struct PlantUseRow {
    /// Id asignado por SQLite.
    pub id: i32,
    /// Planta (ID público).
    pub plant_id: String,
    /// Actividad.
    pub activity: String,
    /// Idioma de la etiqueta de actividad.
    pub language: String,
    /// Referencia que respalda el uso.
    pub reference_id: String,
}

/// Fila nueva de `plant_use`: sin id.
#[derive(Debug, Clone, Insertable)]
#[diesel(table_name = plant_use)]
pub struct NewPlantUse<'a> {
    /// Planta (ID público).
    pub plant_id: &'a str,
    /// Actividad.
    pub activity: &'a str,
    /// Idioma de la etiqueta de actividad.
    pub language: &'a str,
    /// Referencia que respalda el uso.
    pub reference_id: &'a str,
}

/// Fila de `plant_name_source`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_name_source)]
pub struct PlantNameSourceRow {
    /// Nombre atribuido.
    pub plant_name_id: i32,
    /// Fuente que lo aporta.
    pub source_id: String,
}

/// Fila de `plant_part_source`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_part_source)]
pub struct PlantPartSourceRow {
    /// Parte atribuida.
    pub plant_part_id: i32,
    /// Fuente que la aporta.
    pub source_id: String,
}

/// Fila de `plant_use_source`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_use_source)]
pub struct PlantUseSourceRow {
    /// Uso atribuido.
    pub plant_use_id: i32,
    /// Fuente que lo aporta.
    pub source_id: String,
}

/// Fila de `reference_source`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = reference_source)]
pub struct ReferenceSourceRow {
    /// Referencia atribuida.
    pub reference_id: String,
    /// Fuente que la aporta.
    pub source_id: String,
}
