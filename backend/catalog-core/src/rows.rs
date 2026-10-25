//! Filas de las tablas del esquema neutral, como structs de Diesel.
//!
//! Las comparten la ingesta (que escribe) y la API (que lee).
//! Son la forma de la tabla, no el modelo de dominio: los tipos de `domain` no saben nada de Diesel y cada crate convierte entre unos y otros.
//!
//! - `Queryable` + `Selectable`: Diesel construye la fila al leer, y `Selectable` comprueba en compilación que los campos coinciden con las columnas.
//! - `Insertable`: Diesel la acepta en `insert_into(tabla).values(&fila)`.
//!
//! Las tablas con id entero que asigna SQLite (`plant_name`, `plant_part`, `plant_use`, `plant_use_group`, `plant_goal`, `plant_review_flag`) tienen además un `New…` para insertar: no lleva el id, que se pide de vuelta con `RETURNING`.

use diesel::prelude::*;

use crate::schema::{
    goal, goal_subarea, metadata, plant, plant_alias, plant_goal, plant_goal_ref, plant_image,
    plant_name, plant_name_source, plant_part, plant_part_source, plant_profile, plant_review_flag,
    plant_safety, plant_safety_ref, plant_source_id, plant_use, plant_use_group,
    plant_use_group_ref, plant_use_source, reference, reference_source, source,
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

/// Fila de `reference` con su procedencia (`dataset`, `license` y `url`), que las filas de la v1 no traen.
///
/// `ReferenceRow` sigue siendo la forma que lee la API; esta es la que escribe la construcción desde la semilla.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = reference)]
pub struct ReferenceProvenanceRow {
    /// Identificador de la referencia.
    pub id: String,
    /// Cita bibliográfica.
    pub citation: String,
    /// Dataset del que sale la referencia.
    pub dataset: Option<String>,
    /// Licencia del dato.
    pub license: Option<String>,
    /// URL de la referencia, si la tiene.
    pub url: Option<String>,
}

/// Fila de `plant_profile`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_profile)]
pub struct PlantProfileRow {
    /// Planta (ID público).
    pub plant_id: String,
    /// Nombre para mostrar.
    pub display_name: Option<String>,
    /// Autores del nombre científico canónico.
    pub authors: Option<String>,
    /// Origen de la planta.
    pub origin: Option<String>,
    /// Descripción breve.
    pub description: Option<String>,
    /// Tipo de aceite, si la planta lo tiene.
    pub oil_type: Option<String>,
    /// Versión del formato del registro de origen.
    pub record_version: i32,
    /// Hash del paquete de evidencia del registro.
    pub bundle_hash: String,
    /// Versión del prompt que produjo el registro.
    pub prompt_version: i32,
}

/// Fila de `plant_use_group`, tal como se lee.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable)]
#[diesel(table_name = plant_use_group)]
pub struct PlantUseGroupRow {
    /// Id asignado por SQLite.
    pub id: i32,
    /// Planta (ID público).
    pub plant_id: String,
    /// Posición del grupo en el registro.
    pub position: i32,
    /// Actividad en español.
    pub activity: String,
    /// Etiqueta original de la actividad.
    pub activity_source: String,
    /// Número de registros que respaldan el grupo.
    pub n: i32,
    /// Países, como arreglo JSON de textos en español.
    pub countries: String,
    /// Verdadero si ninguna cita del grupo está resuelta.
    pub pending_review: bool,
}

/// Fila nueva de `plant_use_group`: sin id.
#[derive(Debug, Clone, Insertable)]
#[diesel(table_name = plant_use_group)]
pub struct NewPlantUseGroup<'a> {
    /// Planta (ID público).
    pub plant_id: &'a str,
    /// Posición del grupo en el registro.
    pub position: i32,
    /// Actividad en español.
    pub activity: &'a str,
    /// Etiqueta original de la actividad.
    pub activity_source: &'a str,
    /// Número de registros que respaldan el grupo.
    pub n: i32,
    /// Países, como arreglo JSON de textos en español.
    pub countries: &'a str,
    /// Verdadero si ninguna cita del grupo está resuelta.
    pub pending_review: bool,
}

/// Fila de `plant_use_group_ref`: una cita de un grupo, resuelta o no.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_use_group_ref)]
pub struct PlantUseGroupRefRow {
    /// Grupo al que pertenece la cita.
    pub use_group_id: i32,
    /// Clave de la cita en el registro.
    pub key: String,
    /// Posición de la cita en el grupo.
    pub position: i32,
    /// Texto de la cita (para una sin resolver, la clave seguida de «(sin resolver)»).
    pub text: String,
    /// Si la cita se resolvió a una referencia.
    pub resolved: bool,
    /// Referencia resuelta; es `None` si y solo si `resolved` es falso.
    pub reference_id: Option<String>,
}

/// Fila de `goal`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = goal)]
pub struct GoalRow {
    /// Identificador del objetivo.
    pub id: String,
    /// Etiqueta para mostrar.
    pub label: String,
    /// Orden de presentación.
    pub position: i32,
}

/// Fila de `goal_subarea`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = goal_subarea)]
pub struct GoalSubareaRow {
    /// Identificador de la subárea.
    pub id: String,
    /// Objetivo al que pertenece.
    pub goal_id: String,
    /// Etiqueta para mostrar.
    pub label: String,
    /// Orden de presentación.
    pub position: i32,
}

/// Fila de `plant_goal`, tal como se lee.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable)]
#[diesel(table_name = plant_goal)]
pub struct PlantGoalRow {
    /// Id asignado por SQLite.
    pub id: i32,
    /// Planta (ID público).
    pub plant_id: String,
    /// Objetivo.
    pub goal_id: String,
    /// Subárea, si el objetivo la tiene.
    pub subarea_id: Option<String>,
    /// Posición en el registro.
    pub position: i32,
    /// Área concreta dentro del objetivo.
    pub area: String,
    /// Evidencia que respalda el objetivo.
    pub evidence: String,
    /// Si el objetivo espera una revisión humana.
    pub pending_review: bool,
}

/// Fila nueva de `plant_goal`: sin id.
#[derive(Debug, Clone, Insertable)]
#[diesel(table_name = plant_goal)]
pub struct NewPlantGoal<'a> {
    /// Planta (ID público).
    pub plant_id: &'a str,
    /// Objetivo.
    pub goal_id: &'a str,
    /// Subárea, si el objetivo la tiene.
    pub subarea_id: Option<&'a str>,
    /// Posición en el registro.
    pub position: i32,
    /// Área concreta dentro del objetivo.
    pub area: &'a str,
    /// Evidencia que respalda el objetivo.
    pub evidence: &'a str,
    /// Si el objetivo espera una revisión humana.
    pub pending_review: bool,
}

/// Fila de `plant_goal_ref`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_goal_ref)]
pub struct PlantGoalRefRow {
    /// Objetivo de planta respaldado.
    pub plant_goal_id: i32,
    /// Referencia que lo respalda.
    pub reference_id: String,
}

/// Fila de `plant_safety`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_safety)]
pub struct PlantSafetyRow {
    /// Planta (ID público).
    pub plant_id: String,
    /// `alto`, `medio` o `bajo`; `None` es una precaución sin nivel.
    pub level: Option<String>,
    /// Texto de la precaución.
    pub text: String,
}

/// Fila de `plant_safety_ref`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_safety_ref)]
pub struct PlantSafetyRefRow {
    /// Planta (ID público).
    pub plant_id: String,
    /// Referencia que respalda la seguridad.
    pub reference_id: String,
}

/// Fila de `plant_image`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_image)]
pub struct PlantImageRow {
    /// Planta (ID público).
    pub plant_id: String,
    /// URL de la imagen.
    pub url: String,
    /// URL de la página de origen de la imagen.
    pub page_url: String,
    /// Autor, si se conoce.
    pub author: Option<String>,
    /// Licencia de la imagen.
    pub license: String,
    /// URL del texto de la licencia, si existe.
    pub license_url: Option<String>,
    /// Si hay que mostrar la atribución al usar la imagen.
    pub attribution_required: bool,
}

/// Fila de `plant_alias`.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable, Insertable)]
#[diesel(table_name = plant_alias)]
pub struct PlantAliasRow {
    /// ID anterior de la planta.
    pub alias: String,
    /// Planta a la que resuelve (ID público).
    pub plant_id: String,
}

/// Fila de `plant_review_flag`, tal como se lee.
#[derive(Debug, Clone, PartialEq, Eq, Queryable, Selectable)]
#[diesel(table_name = plant_review_flag)]
pub struct PlantReviewFlagRow {
    /// Id asignado por SQLite.
    pub id: i32,
    /// Planta (ID público).
    pub plant_id: String,
    /// Código de la marca.
    pub code: String,
    /// Dato al que apunta la marca.
    pub target: String,
    /// Mensaje para quien revisa.
    pub message: String,
}

/// Fila nueva de `plant_review_flag`: sin id.
#[derive(Debug, Clone, Insertable)]
#[diesel(table_name = plant_review_flag)]
pub struct NewPlantReviewFlag<'a> {
    /// Planta (ID público).
    pub plant_id: &'a str,
    /// Código de la marca.
    pub code: &'a str,
    /// Dato al que apunta la marca.
    pub target: &'a str,
    /// Mensaje para quien revisa.
    pub message: &'a str,
}
