//! Base de fixture para las pruebas: se crea en un directorio temporal aplicando las migraciones de `catalog-core`, sin red.
//!
//! Contenido (35 plantas), pensado para los casos de prueba:
//! - `lavandula-angustifolia`: la planta completa. Familia, nombres de dos fuentes y un sinónimo, partes, usos con referencia, perfil (nombre para mostrar «Lavanda», origen, descripción de Wikipedia, aceite), tres grupos de uso (uno con una cita sin resolver y otro sin ninguna cita resuelta), objetivos (uno con subárea y uno pendiente de revisión), seguridad de nivel medio, imagen y marcas de revisión.
//! - `matricaria-chamomilla`: sin ninguna fuente registrada (sin créditos) y con el alias `matricaria-recutita`, que no es el nombre de ninguna planta.
//! - `lavandula-latifolia`: la planta vacía. Prefijo común con la anterior, sin perfil, partes, usos ni nada consolidado.
//! - `mentha-x-piperita`: sin familia; un nombre común con acentos y mayúsculas; una marca de revisión de identidad.
//! - `zea-mays`: nombres con `%` y `_` literales.
//! - `abutilon-theophrasti`: solo nombres comunes en inglés («Velvetleaf» y «Butterprint») y nombre para mostrar científico.
//! - `conium-maculatum`: la tóxica. Seguridad de nivel alto e imagen sin autor ni URL de licencia.
//! - `eucalyptus-globulus`: seguridad sin nivel (advertencias sin nivel).
//! - `twin-a` y `twin-b`: mismo nombre científico (se insertan en orden inverso) para probar el desempate por id.
//! - `fillerus-01` a `fillerus-25`: relleno para paginar.
//!
//! Alias: `lavandula-vera` (cuyo nombre coincide con un sinónimo de la planta), `matricaria-recutita` y `mentha-x-piperita-subsp-nothosubsp-piperita` (con puntuación al pasar de la consulta al alias).
//!
//! La fixture ampliada de `Fixture::with_goal_search` añade, para la búsqueda por objetivo, los objetivos `mejorar-el-sueno` y `cansancio-y-fatiga` (sin plantas), las subáreas `vias-urinarias` y `molestias-oculares` (sin plantas) de `otros-objetivos`, y los objetivos de las plantas descritos en `add_goal_search_data`.
//!
//! Fuentes `a` y `b` (sin URL de licencia), `wiki` (con URL de licencia), `ema` (sin ella) y `pend` (solo respalda contenido pendiente de revisión).

use std::path::PathBuf;

use catalog_core::normalize::normalize_name;
use catalog_core::rows::{
    GoalRow, GoalSubareaRow, MetadataRow, NewPlantGoal, NewPlantName, NewPlantPart,
    NewPlantReviewFlag, NewPlantUse, NewPlantUseGroup, PlantAliasRow, PlantGoalRefRow,
    PlantImageRow, PlantNameSourceRow, PlantPartSourceRow, PlantProfileRefRow, PlantProfileRow,
    PlantRow, PlantSafetyRefRow, PlantSafetyRow, PlantUseGroupRefRow, PlantUseSourceRow,
    ReferenceProvenanceRow, ReferenceSourceRow, SourceRow,
};
use catalog_core::schema::{
    goal, goal_subarea, metadata, plant, plant_alias, plant_goal, plant_goal_ref, plant_image,
    plant_name, plant_name_source, plant_part, plant_part_source, plant_profile, plant_profile_ref,
    plant_review_flag, plant_safety, plant_safety_ref, plant_use, plant_use_group,
    plant_use_group_ref, plant_use_source, reference, reference_source, source,
};
use catalog_core::version::{SCHEMA_VERSION, SCHEMA_VERSION_KEY, apply_schema};
use diesel::prelude::*;
use tempfile::TempDir;

use crate::repository::SqliteCatalogRepository;

/// Base de fixture en disco; el directorio temporal se borra al soltar este valor.
pub struct Fixture {
    _dir: TempDir,
    /// Ruta del archivo de la base.
    pub path: PathBuf,
}

impl Fixture {
    /// Base completa con la versión de esquema soportada.
    pub fn standard() -> Self {
        Self::with_version(Some(&SCHEMA_VERSION.to_string()))
    }

    /// Base completa con otra versión de esquema (o sin ella si es `None`).
    pub fn with_version(version: Option<&str>) -> Self {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("catalog.db");
        let mut conn = SqliteConnection::establish(path.to_str().unwrap()).unwrap();
        apply_schema(&mut conn).unwrap();
        if let Some(version) = version {
            diesel::insert_into(metadata::table)
                .values(MetadataRow {
                    key: SCHEMA_VERSION_KEY.to_string(),
                    value: version.to_string(),
                })
                .execute(&mut conn)
                .unwrap();
        }
        populate(&mut conn);
        Self { _dir: dir, path }
    }

    /// Añade un alias a la base ya creada (para casos que la fixture estándar no cubre). Debe llamarse antes de abrir el repositorio: este se abre en solo lectura.
    pub fn insert_alias(&self, alias: &str, plant_id: &str) {
        let mut conn = SqliteConnection::establish(self.path.to_str().unwrap()).unwrap();
        add_alias(&mut conn, alias, plant_id);
    }

    /// Añade una marca de revisión a la base ya creada, como `insert_alias`.
    pub fn insert_review_flag(&self, plant_id: &str, code: &str, target: &str) {
        let mut conn = SqliteConnection::establish(self.path.to_str().unwrap()).unwrap();
        add_review_flag(&mut conn, plant_id, code, target);
    }

    /// Añade un nombre a la base ya creada, como `insert_alias`.
    pub fn insert_name(&self, plant_id: &str, text: &str, kind: &str, language: &str) {
        let mut conn = SqliteConnection::establish(self.path.to_str().unwrap()).unwrap();
        add_name(&mut conn, plant_id, text, kind, language, &["a"]);
    }

    /// Añade un grupo de uso resuelto (con una cita) a la base ya creada, como `insert_alias`.
    pub fn insert_use_group(&self, plant_id: &str, activity: &str, position: i32, n: i32) {
        let mut conn = SqliteConnection::establish(self.path.to_str().unwrap()).unwrap();
        let group = add_use_group(
            &mut conn,
            plant_id,
            position,
            activity,
            activity,
            n,
            &[],
            false,
        );
        add_use_group_ref(&mut conn, group, "k", 0, "Smith 1990", Some("ref-1"));
    }

    /// Base estándar ampliada para la búsqueda por objetivo (véase [`add_goal_search_data`]).
    pub fn with_goal_search() -> Self {
        let fixture = Self::standard();
        let mut conn = SqliteConnection::establish(fixture.path.to_str().unwrap()).unwrap();
        add_goal_search_data(&mut conn);
        fixture
    }

    /// Abre el repositorio sobre la fixture.
    pub fn repo(&self) -> SqliteCatalogRepository {
        SqliteCatalogRepository::open(&self.path).unwrap()
    }
}

fn add_source(conn: &mut SqliteConnection, id: &str) {
    add_source_with_license(conn, id, &format!("Fuente {id}"), "CC0", None);
}

/// Fuente con nombre, licencia y URL de licencia (la que sirven los créditos).
fn add_source_with_license(
    conn: &mut SqliteConnection,
    id: &str,
    name: &str,
    license: &str,
    license_url: Option<&str>,
) {
    diesel::insert_into(source::table)
        .values(SourceRow {
            id: id.to_string(),
            name: name.to_string(),
            version: "1".to_string(),
            license: license.to_string(),
            citation: format!("Cita de {id}"),
            url: format!("https://example.test/{id}"),
            checksum: "abc".to_string(),
            license_url: license_url.map(str::to_string),
        })
        .execute(conn)
        .unwrap();
}

/// Referencia con su etiqueta (`citation`), el dataset del que sale (el id de la fuente) y, si lo tiene, su URL.
fn add_reference(conn: &mut SqliteConnection, id: &str, citation: &str, source_id: &str) {
    add_reference_with_url(conn, id, citation, source_id, None);
}

fn add_reference_with_url(
    conn: &mut SqliteConnection,
    id: &str,
    citation: &str,
    source_id: &str,
    url: Option<&str>,
) {
    diesel::insert_into(reference::table)
        .values(ReferenceProvenanceRow {
            id: id.to_string(),
            citation: citation.to_string(),
            dataset: Some(source_id.to_string()),
            license: Some("CC0".to_string()),
            url: url.map(str::to_string),
        })
        .execute(conn)
        .unwrap();
    diesel::insert_into(reference_source::table)
        .values(ReferenceSourceRow {
            reference_id: id.to_string(),
            source_id: source_id.to_string(),
        })
        .execute(conn)
        .unwrap();
}

/// Inserta una planta con `normalized` explícito (casi siempre `normalize_name(scientific)`).
fn add_plant_raw(
    conn: &mut SqliteConnection,
    id: &str,
    scientific: &str,
    normalized: &str,
    family: Option<(&str, &str)>,
    sources: &[&str],
) {
    diesel::insert_into(plant::table)
        .values(PlantRow {
            id: id.to_string(),
            scientific_name: scientific.to_string(),
            scientific_name_normalized: normalized.to_string(),
            family: family.map(|(f, _)| f.to_string()),
            family_source_id: family.map(|(_, s)| s.to_string()),
        })
        .execute(conn)
        .unwrap();
    // El nombre científico también es un nombre buscable.
    add_name(conn, id, scientific, "scientific", "la", sources);
}

fn add_plant(
    conn: &mut SqliteConnection,
    id: &str,
    scientific: &str,
    family: Option<(&str, &str)>,
    sources: &[&str],
) {
    add_plant_raw(
        conn,
        id,
        scientific,
        &normalize_name(scientific),
        family,
        sources,
    );
}

fn add_name(
    conn: &mut SqliteConnection,
    plant_id: &str,
    text: &str,
    kind: &str,
    language: &str,
    sources: &[&str],
) {
    let normalized = normalize_name(text);
    let name_id: i32 = diesel::insert_into(plant_name::table)
        .values(NewPlantName {
            plant_id,
            text,
            kind,
            language,
            normalized: &normalized,
        })
        .returning(plant_name::id)
        .get_result(conn)
        .unwrap();
    for s in sources {
        diesel::insert_into(plant_name_source::table)
            .values(PlantNameSourceRow {
                plant_name_id: name_id,
                source_id: s.to_string(),
            })
            .execute(conn)
            .unwrap();
    }
}

fn add_part(conn: &mut SqliteConnection, plant_id: &str, label: &str, sources: &[&str]) {
    let part_id: i32 = diesel::insert_into(plant_part::table)
        .values(NewPlantPart { plant_id, label })
        .returning(plant_part::id)
        .get_result(conn)
        .unwrap();
    for s in sources {
        diesel::insert_into(plant_part_source::table)
            .values(PlantPartSourceRow {
                plant_part_id: part_id,
                source_id: s.to_string(),
            })
            .execute(conn)
            .unwrap();
    }
}

fn add_use(
    conn: &mut SqliteConnection,
    plant_id: &str,
    activity: &str,
    reference_id: &str,
    sources: &[&str],
) {
    let use_id: i32 = diesel::insert_into(plant_use::table)
        .values(NewPlantUse {
            plant_id,
            activity,
            language: "en",
            reference_id,
        })
        .returning(plant_use::id)
        .get_result(conn)
        .unwrap();
    for s in sources {
        diesel::insert_into(plant_use_source::table)
            .values(PlantUseSourceRow {
                plant_use_id: use_id,
                source_id: s.to_string(),
            })
            .execute(conn)
            .unwrap();
    }
}

/// Perfil de la planta (`plant_profile`); sin llamarlo, la planta no tiene perfil.
fn add_profile(
    conn: &mut SqliteConnection,
    plant_id: &str,
    display_name: Option<&str>,
    origin: Option<&str>,
    description: Option<&str>,
    oil_type: Option<&str>,
) {
    diesel::insert_into(plant_profile::table)
        .values(PlantProfileRow {
            plant_id: plant_id.to_string(),
            display_name: display_name.map(str::to_string),
            authors: None,
            origin: origin.map(str::to_string),
            description: description.map(str::to_string),
            oil_type: oil_type.map(str::to_string),
            record_version: 1,
            bundle_hash: "hash".to_string(),
            prompt_version: 1,
        })
        .execute(conn)
        .unwrap();
}

/// Referencia que respalda un campo del perfil (por ejemplo `description`).
fn add_profile_ref(conn: &mut SqliteConnection, plant_id: &str, field: &str, reference_id: &str) {
    diesel::insert_into(plant_profile_ref::table)
        .values(PlantProfileRefRow {
            plant_id: plant_id.to_string(),
            field: field.to_string(),
            reference_id: reference_id.to_string(),
        })
        .execute(conn)
        .unwrap();
}

/// Grupo de uso tradicional; devuelve su id para añadirle citas.
#[allow(clippy::too_many_arguments)]
fn add_use_group(
    conn: &mut SqliteConnection,
    plant_id: &str,
    position: i32,
    activity: &str,
    activity_source: &str,
    n: i32,
    countries: &[&str],
    pending_review: bool,
) -> i32 {
    let countries = serde_json::to_string(countries).unwrap();
    diesel::insert_into(plant_use_group::table)
        .values(NewPlantUseGroup {
            plant_id,
            position,
            activity,
            activity_source,
            n,
            countries: &countries,
            pending_review,
        })
        .returning(plant_use_group::id)
        .get_result(conn)
        .unwrap()
}

/// Cita de un grupo: con `reference_id` está resuelta; sin él, es una cita «(sin resolver)».
fn add_use_group_ref(
    conn: &mut SqliteConnection,
    use_group_id: i32,
    key: &str,
    position: i32,
    text: &str,
    reference_id: Option<&str>,
) {
    diesel::insert_into(plant_use_group_ref::table)
        .values(PlantUseGroupRefRow {
            use_group_id,
            key: key.to_string(),
            position,
            text: text.to_string(),
            resolved: reference_id.is_some(),
            reference_id: reference_id.map(str::to_string),
        })
        .execute(conn)
        .unwrap();
}

fn add_goal_catalog(conn: &mut SqliteConnection) {
    for (position, (id, label)) in [
        ("cuidado-de-la-piel", "Cuidado de la piel"),
        ("otros-objetivos", "Otros objetivos"),
        ("relajacion-estres", "Relajación y estrés"),
    ]
    .into_iter()
    .enumerate()
    {
        diesel::insert_into(goal::table)
            .values(GoalRow {
                id: id.to_string(),
                label: label.to_string(),
                position: position as i32,
            })
            .execute(conn)
            .unwrap();
    }
    diesel::insert_into(goal_subarea::table)
        .values(GoalSubareaRow {
            id: "digestion".to_string(),
            goal_id: "otros-objetivos".to_string(),
            label: "Digestión".to_string(),
            position: 0,
        })
        .execute(conn)
        .unwrap();
}

/// Objetivo de una planta con sus referencias.
#[allow(clippy::too_many_arguments)]
fn add_plant_goal(
    conn: &mut SqliteConnection,
    plant_id: &str,
    goal_id: &str,
    subarea_id: Option<&str>,
    area: &str,
    evidence: &str,
    pending_review: bool,
    references: &[&str],
) {
    let id: i32 = diesel::insert_into(plant_goal::table)
        .values(NewPlantGoal {
            plant_id,
            goal_id,
            subarea_id,
            position: 0,
            area,
            evidence,
            pending_review,
        })
        .returning(plant_goal::id)
        .get_result(conn)
        .unwrap();
    for r in references {
        diesel::insert_into(plant_goal_ref::table)
            .values(PlantGoalRefRow {
                plant_goal_id: id,
                reference_id: r.to_string(),
            })
            .execute(conn)
            .unwrap();
    }
}

/// Precauciones de una planta; `level` nulo es una precaución sin nivel.
fn add_safety(
    conn: &mut SqliteConnection,
    plant_id: &str,
    level: Option<&str>,
    text: &str,
    references: &[&str],
) {
    diesel::insert_into(plant_safety::table)
        .values(PlantSafetyRow {
            plant_id: plant_id.to_string(),
            level: level.map(str::to_string),
            text: text.to_string(),
        })
        .execute(conn)
        .unwrap();
    for r in references {
        diesel::insert_into(plant_safety_ref::table)
            .values(PlantSafetyRefRow {
                plant_id: plant_id.to_string(),
                reference_id: r.to_string(),
            })
            .execute(conn)
            .unwrap();
    }
}

fn add_image(
    conn: &mut SqliteConnection,
    plant_id: &str,
    author: Option<&str>,
    license: &str,
    license_url: Option<&str>,
    attribution_required: bool,
) {
    diesel::insert_into(plant_image::table)
        .values(PlantImageRow {
            plant_id: plant_id.to_string(),
            // Dominio reservado `.invalid`, que nunca resuelve: servir el detalle sin red prueba que la API no descarga nada.
            url: format!("https://imagenes.invalid/{plant_id}.jpg"),
            page_url: format!("https://commons.wikimedia.org/wiki/File:{plant_id}.jpg"),
            author: author.map(str::to_string),
            license: license.to_string(),
            license_url: license_url.map(str::to_string),
            attribution_required,
        })
        .execute(conn)
        .unwrap();
}

fn add_alias(conn: &mut SqliteConnection, alias: &str, plant_id: &str) {
    diesel::insert_into(plant_alias::table)
        .values(PlantAliasRow {
            alias: alias.to_string(),
            plant_id: plant_id.to_string(),
        })
        .execute(conn)
        .unwrap();
}

/// Marca de revisión: la API no debe exponerla.
fn add_review_flag(conn: &mut SqliteConnection, plant_id: &str, code: &str, target: &str) {
    diesel::insert_into(plant_review_flag::table)
        .values(NewPlantReviewFlag {
            plant_id,
            code,
            target,
            message: "Mensaje para quien revisa",
        })
        .execute(conn)
        .unwrap();
}

fn populate(conn: &mut SqliteConnection) {
    add_source(conn, "a");
    add_source(conn, "b");
    add_source_with_license(
        conn,
        "wiki",
        "Enciclopedia libre",
        "CC BY-SA 4.0",
        Some("https://creativecommons.org/licenses/by-sa/4.0/"),
    );
    add_source_with_license(conn, "ema", "Agencia reguladora", "Términos propios", None);
    // La etiqueta de una referencia es corta; el texto completo de la cita de un grupo de uso vive en `plant_use_group_ref.text`.
    add_reference(conn, "ref-1", "Smith 1990", "a");
    add_reference(conn, "ref-2", "Jones 2001", "b");
    add_reference(conn, "ref-ema-skin", "Monografía sobre la piel", "ema");
    add_reference(conn, "ref-ema-safety", "Advertencias de la agencia", "ema");
    add_source_with_license(conn, "pend", "Fuente pendiente", "CC0", None);
    add_reference(conn, "ref-pending", "Referencia solo pendiente", "pend");
    add_reference_with_url(
        conn,
        "ref-wiki",
        "Artículo de la enciclopedia",
        "wiki",
        Some("https://es.example.test/wiki/Lavandula_angustifolia"),
    );
    add_goal_catalog(conn);

    add_plant(
        conn,
        "lavandula-angustifolia",
        "Lavandula angustifolia",
        Some(("Lamiaceae", "a")),
        &["a", "b"],
    );
    add_name(
        conn,
        "lavandula-angustifolia",
        "Lavender",
        "common",
        "en",
        &["a", "b"],
    );
    add_name(
        conn,
        "lavandula-angustifolia",
        "Lavanda",
        "common",
        "es",
        &["a"],
    );
    add_name(
        conn,
        "lavandula-angustifolia",
        "Espliego",
        "common",
        "es",
        &["b"],
    );
    add_part(conn, "lavandula-angustifolia", "Leaf", &["a", "b"]);
    add_part(conn, "lavandula-angustifolia", "Flower", &["a"]);
    add_use(
        conn,
        "lavandula-angustifolia",
        "Sedative",
        "ref-2",
        &["a", "b"],
    );
    add_use(
        conn,
        "lavandula-angustifolia",
        "Antiseptic",
        "ref-1",
        &["a"],
    );
    add_name(
        conn,
        "lavandula-angustifolia",
        "Lavandula vera",
        "scientific",
        "la",
        &["b"],
    );
    add_profile(
        conn,
        "lavandula-angustifolia",
        Some("Lavanda"),
        Some("Sureste de Europa."),
        Some("Arbusto aromático de flores violetas."),
        Some("Esencial"),
    );
    add_profile_ref(conn, "lavandula-angustifolia", "description", "ref-wiki");
    // Un grupo con 12 registros de 3 países, con una cita resuelta y otra sin resolver.
    let sedative = add_use_group(
        conn,
        "lavandula-angustifolia",
        0,
        "Sedante",
        "Sedative",
        12,
        &["Turquía", "Francia", "Otros lugares"],
        false,
    );
    add_use_group_ref(
        conn,
        sedative,
        "Jones",
        0,
        "Jones, A. 2001. Plantas medicinales. Editorial Ejemplo, Madrid.",
        Some("ref-2"),
    );
    add_use_group_ref(conn, sedative, "Woi.6", 1, "Woi.6 (sin resolver)", None);
    // Un grupo con 2 registros y una sola cita resuelta, cuyo texto completo difiere de la etiqueta («Smith 1990»).
    let antiseptic = add_use_group(
        conn,
        "lavandula-angustifolia",
        1,
        "Antiséptico",
        "Antiseptic",
        2,
        &["Estados Unidos"],
        false,
    );
    add_use_group_ref(
        conn,
        antiseptic,
        "Smith",
        0,
        "Smith, J. 1990. Registros de plantas. Publicado por el autor, Lisboa.",
        Some("ref-1"),
    );
    // Un grupo sin ninguna cita resuelta: está pendiente de revisión y no se sirve.
    let pending = add_use_group(
        conn,
        "lavandula-angustifolia",
        2,
        "Actividad pendiente",
        "Pending activity",
        30,
        &[],
        true,
    );
    add_use_group_ref(conn, pending, "Xyz.1", 0, "Xyz.1 (sin resolver)", None);
    add_plant_goal(
        conn,
        "lavandula-angustifolia",
        "cuidado-de-la-piel",
        None,
        "Piel irritada",
        "La agencia tiene una monografía en esta área.",
        false,
        &["ref-ema-skin"],
    );
    add_plant_goal(
        conn,
        "lavandula-angustifolia",
        "otros-objetivos",
        Some("digestion"),
        "Digestión lenta",
        "La agencia tiene una entrada de lista en esta área.",
        false,
        &["ref-ema-skin", "ref-1"],
    );
    // Objetivo pendiente de revisión: no se sirve.
    add_plant_goal(
        conn,
        "lavandula-angustifolia",
        "relajacion-estres",
        None,
        "Estrés",
        "La agencia tiene una monografía en esta área.",
        true,
        &["ref-ema-skin", "ref-pending"],
    );
    add_safety(
        conn,
        "lavandula-angustifolia",
        Some("medio"),
        "Evitar durante el embarazo.",
        &["ref-ema-safety", "ref-1"],
    );
    add_image(
        conn,
        "lavandula-angustifolia",
        Some("Autora Ejemplo"),
        "CC BY-SA 4.0",
        Some("https://creativecommons.org/licenses/by-sa/4.0/"),
        true,
    );
    // Su alias coincide con un sinónimo científico de la misma planta (la búsqueda no debe duplicarla).
    add_alias(conn, "lavandula-vera", "lavandula-angustifolia");
    add_review_flag(
        conn,
        "lavandula-angustifolia",
        "cita-sin-resolver",
        "traditionalUses",
    );

    add_plant(
        conn,
        "lavandula-latifolia",
        "Lavandula latifolia",
        Some(("Lamiaceae", "a")),
        &["a"],
    );
    add_name(
        conn,
        "lavandula-latifolia",
        "Spike lavender",
        "common",
        "en",
        &["a"],
    );

    // Sin ninguna fuente registrada: ni sus nombres ni nada de la planta acreditan un dataset. Su alias no es nombre de ninguna planta.
    add_plant(
        conn,
        "matricaria-chamomilla",
        "Matricaria chamomilla",
        None,
        &[],
    );
    add_alias(conn, "matricaria-recutita", "matricaria-chamomilla");

    add_plant(conn, "mentha-x-piperita", "Mentha x piperita", None, &["b"]);
    add_alias(
        conn,
        "mentha-x-piperita-subsp-nothosubsp-piperita",
        "mentha-x-piperita",
    );
    add_name(
        conn,
        "mentha-x-piperita",
        "Ñandú Café",
        "common",
        "es",
        &["b"],
    );
    add_name(
        conn,
        "mentha-x-piperita",
        "Peppermint",
        "common",
        "en",
        &["b"],
    );

    add_review_flag(
        conn,
        "mentha-x-piperita",
        "identidad-ambigua",
        "scientificName",
    );

    add_plant(conn, "zea-mays", "Zea mays", Some(("Poaceae", "b")), &["b"]);
    add_name(conn, "zea-mays", "100% Corn", "common", "en", &["b"]);
    add_name(conn, "zea-mays", "corn_meal", "common", "en", &["b"]);

    // Solo nombres comunes en otros idiomas: el nombre para mostrar de la semilla es el científico.
    add_plant(
        conn,
        "abutilon-theophrasti",
        "Abutilon theophrasti",
        Some(("Malvaceae", "a")),
        &["a"],
    );
    add_name(
        conn,
        "abutilon-theophrasti",
        "Velvetleaf",
        "common",
        "en",
        &["a"],
    );
    add_name(
        conn,
        "abutilon-theophrasti",
        "Butterprint",
        "common",
        "en",
        &["a"],
    );
    add_profile(
        conn,
        "abutilon-theophrasti",
        Some("Abutilon theophrasti"),
        None,
        None,
        None,
    );

    // La tóxica: nivel alto e imagen sin autor ni URL de licencia.
    add_plant(
        conn,
        "conium-maculatum",
        "Conium maculatum",
        Some(("Apiaceae", "a")),
        &["a"],
    );
    add_name(conn, "conium-maculatum", "Cicuta", "common", "es", &["a"]);
    add_profile(conn, "conium-maculatum", Some("Cicuta"), None, None, None);
    add_safety(
        conn,
        "conium-maculatum",
        Some("alto"),
        "Planta tóxica: puede causar la muerte.",
        &["ref-ema-safety"],
    );
    add_image(
        conn,
        "conium-maculatum",
        None,
        "Dominio público",
        None,
        false,
    );

    // Advertencias sin nivel, como las contraindicaciones del eucalipto.
    add_plant(
        conn,
        "eucalyptus-globulus",
        "Eucalyptus globulus",
        Some(("Myrtaceae", "a")),
        &["a"],
    );
    add_name(
        conn,
        "eucalyptus-globulus",
        "Eucalipto",
        "common",
        "es",
        &["a"],
    );
    add_profile(
        conn,
        "eucalyptus-globulus",
        Some("Eucalipto"),
        None,
        None,
        None,
    );
    add_safety(
        conn,
        "eucalyptus-globulus",
        None,
        "Contraindicado en niños pequeños.",
        &["ref-ema-safety"],
    );

    // `twin-b` va primero a propósito: si el desempate dependiera del orden de inserción, el test fallaría.
    // La columna normalizada es UNIQUE, así que la de `twin-b` se altera solo para poder repetir el nombre científico.
    add_plant_raw(conn, "twin-b", "Twin plant", "twin plant b", None, &["a"]);
    add_plant_raw(conn, "twin-a", "Twin plant", "twin plant", None, &["a"]);

    for n in 1..=25 {
        let id = format!("fillerus-{n:02}");
        add_plant(
            conn,
            &id,
            &format!("Fillerus {n:02}"),
            Some(("Fillerfam", "a")),
            &["a"],
        );
        add_name(conn, &id, &format!("Filler {n:02}"), "common", "en", &["a"]);
    }
}

/// Datos de objetivos para las pruebas de la búsqueda por objetivo, sobre la fixture estándar.
///
/// Resultado visible por objetivo (las filas `pending_review` no cuentan):
/// - `cuidado-de-la-piel`: `lavandula-angustifolia` y `arnica-montana` (planta en dos objetivos).
/// - `otros-objetivos`: `lavandula-angustifolia` (`digestion`) y `mentha-x-piperita` (en `digestion` y `vias-urinarias`, una planta en dos subáreas con una marca de revisión sin `pending_review`); `molestias-oculares` queda sin plantas.
/// - `relajacion-estres`: solo `zea-mays` (sin imagen ni seguridad); `lavandula-angustifolia` y `eucalyptus-globulus` están pendientes de revisión aquí.
/// - `mejorar-el-sueno`: siete plantas con nombres que prueban el orden (`abedul`, el científico `Abutilon theophrasti` con nombres comunes en inglés, `Árnica`, `Eucalipto` con seguridad sin nivel, dos «Twin plant» empatadas y `Zarzaparrilla`).
/// - `cansancio-y-fatiga`: sin plantas.
///
/// `conium-maculatum` (tóxica) no tiene objetivos.
fn add_goal_search_data(conn: &mut SqliteConnection) {
    for (position, (id, label)) in [
        ("mejorar-el-sueno", "Mejorar el sueño"),
        ("cansancio-y-fatiga", "Cansancio y fatiga"),
    ]
    .into_iter()
    .enumerate()
    {
        diesel::insert_into(goal::table)
            .values(GoalRow {
                id: id.to_string(),
                label: label.to_string(),
                position: 3 + position as i32,
            })
            .execute(conn)
            .unwrap();
    }
    for (position, (id, label)) in [
        ("vias-urinarias", "Vías urinarias"),
        ("molestias-oculares", "Molestias oculares"),
    ]
    .into_iter()
    .enumerate()
    {
        diesel::insert_into(goal_subarea::table)
            .values(GoalSubareaRow {
                id: id.to_string(),
                goal_id: "otros-objetivos".to_string(),
                label: label.to_string(),
                position: 1 + position as i32,
            })
            .execute(conn)
            .unwrap();
    }

    // Plantas nuevas con un nombre para mostrar que prueba el orden sin acentos ni mayúsculas.
    for (id, scientific, display) in [
        ("betula-pendula", "Betula pendula", "abedul"),
        ("arnica-montana", "Arnica montana", "Árnica"),
        ("smilax-aspera", "Smilax aspera", "Zarzaparrilla"),
    ] {
        add_plant(conn, id, scientific, Some(("Familia", "a")), &["a"]);
        add_name(conn, id, display, "common", "es", &["a"]);
        add_profile(conn, id, Some(display), None, None, None);
    }

    let goal_row = |conn: &mut SqliteConnection, plant: &str, goal: &str, area: &str| {
        add_plant_goal(conn, plant, goal, None, area, "Evidencia.", false, &[]);
    };
    let subarea_row = |conn: &mut SqliteConnection, plant: &str, subarea: &str, area: &str| {
        add_plant_goal(
            conn,
            plant,
            "otros-objetivos",
            Some(subarea),
            area,
            "Evidencia.",
            false,
            &[],
        );
    };

    // Piel: la lavanda ya está; la árnica está además en el sueño con otra área.
    goal_row(
        conn,
        "arnica-montana",
        "cuidado-de-la-piel",
        "Heridas leves",
    );
    // Otros objetivos: la menta está en dos subáreas, cada una con su área.
    subarea_row(conn, "mentha-x-piperita", "digestion", "Gases");
    subarea_row(conn, "mentha-x-piperita", "vias-urinarias", "Vejiga");
    // Relajación: solo `zea-mays` es visible, con una marca de revisión que no oculta nada.
    goal_row(conn, "zea-mays", "relajacion-estres", "Estrés mental");
    add_review_flag(conn, "zea-mays", "sin-datos-de-seguridad", "safety");
    // El eucalipto está pendiente de revisión en relajación y visible en el sueño.
    add_plant_goal(
        conn,
        "eucalyptus-globulus",
        "relajacion-estres",
        None,
        "Estrés mental",
        "Evidencia.",
        true,
        &[],
    );
    // Sueño.
    for plant in [
        "betula-pendula",
        "abutilon-theophrasti",
        "arnica-montana",
        "eucalyptus-globulus",
        "twin-a",
        "twin-b",
        "smilax-aspera",
    ] {
        goal_row(conn, plant, "mejorar-el-sueno", "Trastornos del sueño");
    }
    // La árnica tiene imagen; el resto de las plantas del sueño no.
    add_image(
        conn,
        "arnica-montana",
        Some("Autor"),
        "CC BY 4.0",
        Some("https://creativecommons.org/licenses/by/4.0/"),
        true,
    );
}
