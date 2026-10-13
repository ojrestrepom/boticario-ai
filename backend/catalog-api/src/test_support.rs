//! Base de fixture para las pruebas: se crea en un directorio temporal aplicando las migraciones de `catalog-core`, sin red.
//!
//! Contenido (31 plantas), pensado para los casos de prueba:
//! - `lavandula-angustifolia`: familia, nombres de dos fuentes, partes y usos con referencia.
//! - `lavandula-latifolia`: prefijo común con la anterior, sin partes ni usos.
//! - `mentha-x-piperita`: sin familia; un nombre común con acentos y mayúsculas.
//! - `zea-mays`: nombres con `%` y `_` literales.
//! - `twin-a` y `twin-b`: mismo nombre científico (se insertan en orden inverso) para probar el desempate por id.
//! - `fillerus-01` a `fillerus-25`: relleno para paginar.

use std::path::PathBuf;

use catalog_core::normalize::normalize_name;
use catalog_core::rows::{
    MetadataRow, NewPlantName, NewPlantPart, NewPlantUse, PlantNameSourceRow, PlantPartSourceRow,
    PlantRow, PlantUseSourceRow, ReferenceRow, ReferenceSourceRow, SourceRow,
};
use catalog_core::schema::{
    metadata, plant, plant_name, plant_name_source, plant_part, plant_part_source, plant_use,
    plant_use_source, reference, reference_source, source,
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

    /// Abre el repositorio sobre la fixture.
    pub fn repo(&self) -> SqliteCatalogRepository {
        SqliteCatalogRepository::open(&self.path).unwrap()
    }
}

fn add_source(conn: &mut SqliteConnection, id: &str) {
    diesel::insert_into(source::table)
        .values(SourceRow {
            id: id.to_string(),
            name: format!("Fuente {id}"),
            version: "1".to_string(),
            license: "CC0".to_string(),
            citation: format!("Cita de {id}"),
            url: format!("https://example.test/{id}"),
            checksum: "abc".to_string(),
        })
        .execute(conn)
        .unwrap();
}

fn add_reference(conn: &mut SqliteConnection, id: &str, citation: &str, source_id: &str) {
    diesel::insert_into(reference::table)
        .values(ReferenceRow {
            id: id.to_string(),
            citation: citation.to_string(),
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

fn populate(conn: &mut SqliteConnection) {
    add_source(conn, "a");
    add_source(conn, "b");
    add_reference(conn, "ref-1", "Smith 1990", "a");
    add_reference(conn, "ref-2", "Jones 2001", "b");

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

    add_plant(conn, "mentha-x-piperita", "Mentha x piperita", None, &["b"]);
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

    add_plant(conn, "zea-mays", "Zea mays", Some(("Poaceae", "b")), &["b"]);
    add_name(conn, "zea-mays", "100% Corn", "common", "en", &["b"]);
    add_name(conn, "zea-mays", "corn_meal", "common", "en", &["b"]);

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
