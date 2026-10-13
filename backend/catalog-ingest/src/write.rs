//! Escritura de la base neutral (`catalog.db`) desde un [`Catalog`] en memoria.
//!
//! Primero se valida el catálogo con errores claros; luego se escribe en un archivo temporal y solo si todo sale bien se renombra al destino. Así nunca queda una base parcial.

use std::collections::BTreeSet;
use std::ffi::OsString;
use std::path::{Path, PathBuf};

use catalog_core::domain::{NameKind, SourceId};
use catalog_core::normalize::normalize_name;
use catalog_core::rows::{
    MetadataRow, NewPlantName, NewPlantPart, NewPlantUse, PlantNameSourceRow, PlantPartSourceRow,
    PlantRow, PlantSourceIdRow, PlantUseSourceRow, ReferenceRow, ReferenceSourceRow, SourceRow,
};
use catalog_core::schema::{
    metadata, plant, plant_name, plant_name_source, plant_part, plant_part_source, plant_source_id,
    plant_use, plant_use_source, reference, reference_source, source,
};
use catalog_core::version::{SCHEMA_VERSION, SCHEMA_VERSION_KEY, apply_schema};
use diesel::prelude::*;

use crate::consolidate::{Catalog, ConsolidatedPlant};
use crate::error::IngestError;

/// Escribe el catálogo en `out`, de forma atómica.
///
/// Si algo falla, `out` no se toca (si existía conserva su contenido) y no queda archivo temporal.
pub fn write_catalog(catalog: &Catalog, out: &Path) -> Result<(), IngestError> {
    validate_catalog(catalog)?;

    let io_error = |path: &Path, err: std::io::Error| IngestError::Io {
        path: Some(path.to_path_buf()),
        message: err.to_string(),
    };
    if let Some(parent) = out.parent().filter(|p| !p.as_os_str().is_empty()) {
        std::fs::create_dir_all(parent).map_err(|e| io_error(parent, e))?;
    }

    let tmp = temp_path(out);
    // Un temporal previo es resto de una ejecución interrumpida: se descarta.
    let _ = std::fs::remove_file(&tmp);

    let result = write_db(catalog, &tmp)
        .and_then(|()| std::fs::rename(&tmp, out).map_err(|e| io_error(out, e)));
    if result.is_err() {
        // Limpieza best-effort: el error original es el que importa.
        let _ = std::fs::remove_file(&tmp);
    }
    result
}

/// `<out>.tmp`, en la misma carpeta: el renombrado solo es atómico dentro del mismo sistema de archivos.
fn temp_path(out: &Path) -> PathBuf {
    let mut name: OsString = out.as_os_str().to_owned();
    name.push(".tmp");
    PathBuf::from(name)
}

fn kind_label(kind: NameKind) -> &'static str {
    match kind {
        NameKind::Scientific => "scientific",
        NameKind::Common => "common",
    }
}

/// Comprueba la consistencia del catálogo antes de tocar el disco.
fn validate_catalog(catalog: &Catalog) -> Result<(), IngestError> {
    let known: BTreeSet<&SourceId> = catalog.sources.iter().map(|s| &s.id).collect();
    let check_sources = |plant_id: &str,
                         kind: &'static str,
                         value: &str,
                         sources: &[SourceId]|
     -> Result<(), IngestError> {
        if sources.is_empty() {
            return Err(IngestError::DataWithoutSource {
                plant_id: plant_id.to_string(),
                kind,
                value: value.to_string(),
            });
        }
        match sources.iter().find(|s| !known.contains(s)) {
            Some(unknown) => Err(IngestError::UnknownSource {
                id: unknown.0.clone(),
            }),
            None => Ok(()),
        }
    };

    let mut reference_ids = BTreeSet::new();
    for r in &catalog.references {
        check_sources("", "reference", &r.value.id, &r.sources)?;
        reference_ids.insert(r.value.id.as_str());
    }

    let mut seen: BTreeSet<&str> = BTreeSet::new();
    let mut first_names: Vec<(&str, &str)> = Vec::new();
    for cp in &catalog.plants {
        let plant = &cp.plant;
        let (source, source_plant_id) = cp
            .source_plant_ids
            .iter()
            .next()
            .map(|(s, id)| (s.0.clone(), id.clone()))
            .unwrap_or_default();
        if plant.id.0.is_empty() || plant.scientific_name.trim().is_empty() {
            return Err(IngestError::EmptyScientificName {
                source,
                source_plant_id,
            });
        }
        let id = plant.id.0.as_str();
        if !seen.insert(id) {
            let first = first_names
                .iter()
                .find(|(i, _)| *i == id)
                .map_or("", |(_, n)| *n);
            return Err(IngestError::SlugCollision {
                slug: id.to_string(),
                first_identity: normalize_name(first),
                second_identity: normalize_name(&plant.scientific_name),
            });
        }
        first_names.push((id, plant.scientific_name.as_str()));

        for source in cp.source_plant_ids.keys() {
            check_sources(id, "plant_source_id", id, std::slice::from_ref(source))?;
        }
        if let Some(family) = &plant.family {
            check_sources(id, "family", &family.value, &family.sources)?;
        }
        for n in &plant.names {
            check_sources(id, "name", &n.value.text, &n.sources)?;
        }
        for p in &plant.parts {
            check_sources(id, "part", &p.value.label, &p.sources)?;
        }
        for u in &plant.uses {
            check_sources(id, "use", &u.value.activity, &u.sources)?;
            if !reference_ids.contains(u.value.reference.id.as_str()) {
                let source = u.sources[0].clone();
                return Err(IngestError::UnresolvedReference {
                    source_plant_id: cp
                        .source_plant_ids
                        .get(&source)
                        .cloned()
                        .unwrap_or_default(),
                    source: source.0,
                    reference_id: u.value.reference.id.clone(),
                });
            }
        }
    }
    Ok(())
}

/// Crea la base en `path` y la llena dentro de una sola transacción.
fn write_db(catalog: &Catalog, path: &Path) -> Result<(), IngestError> {
    let url = path.to_str().ok_or_else(|| IngestError::Io {
        path: Some(path.to_path_buf()),
        message: "la ruta no es UTF-8 válido".to_string(),
    })?;
    let mut conn = SqliteConnection::establish(url)?;
    // Es configuración de la conexión, no del esquema: por eso no está en la migración.
    // Debe ir fuera de la transacción: dentro, SQLite ignora este PRAGMA.
    diesel::sql_query("PRAGMA foreign_keys = ON").execute(&mut conn)?;
    apply_schema(&mut conn)?;
    // `transaction` ejecuta la closure: si devuelve `Ok` confirma (commit); si devuelve `Err` revierte todo (rollback).
    conn.transaction(|conn| insert_all(conn, catalog))
    // `conn` se cierra al salir; el archivo ya está completo y consistente.
}

fn insert_all(conn: &mut SqliteConnection, catalog: &Catalog) -> Result<(), IngestError> {
    diesel::insert_into(metadata::table)
        .values(MetadataRow {
            key: SCHEMA_VERSION_KEY.to_string(),
            value: SCHEMA_VERSION.to_string(),
        })
        .execute(conn)?;
    for s in &catalog.sources {
        diesel::insert_into(source::table)
            .values(SourceRow {
                id: s.id.0.clone(),
                name: s.name.clone(),
                version: s.version.clone(),
                license: s.license.clone(),
                citation: s.citation.clone(),
                url: s.url.clone(),
                checksum: s.checksum.clone(),
            })
            .execute(conn)?;
    }
    for r in &catalog.references {
        diesel::insert_into(reference::table)
            .values(ReferenceRow {
                id: r.value.id.clone(),
                citation: r.value.citation.clone(),
            })
            .execute(conn)?;
        let links: Vec<ReferenceSourceRow> = r
            .sources
            .iter()
            .map(|s| ReferenceSourceRow {
                reference_id: r.value.id.clone(),
                source_id: s.0.clone(),
            })
            .collect();
        diesel::insert_into(reference_source::table)
            .values(&links)
            .execute(conn)?;
    }
    for cp in &catalog.plants {
        insert_plant(conn, cp)?;
    }
    Ok(())
}

fn insert_plant(conn: &mut SqliteConnection, cp: &ConsolidatedPlant) -> Result<(), IngestError> {
    let plant = &cp.plant;
    let id = plant.id.0.as_str();
    let family = plant.family.as_ref();
    diesel::insert_into(plant::table)
        .values(PlantRow {
            id: id.to_string(),
            scientific_name: plant.scientific_name.clone(),
            scientific_name_normalized: normalize_name(&plant.scientific_name),
            family: family.map(|f| f.value.clone()),
            family_source_id: family.map(|f| f.sources[0].0.clone()),
        })
        .execute(conn)?;
    let links: Vec<PlantSourceIdRow> = cp
        .source_plant_ids
        .iter()
        .map(|(source, source_plant_id)| PlantSourceIdRow {
            plant_id: id.to_string(),
            source_id: source.0.clone(),
            source_plant_id: source_plant_id.clone(),
        })
        .collect();
    diesel::insert_into(plant_source_id::table)
        .values(&links)
        .execute(conn)?;
    for n in &plant.names {
        let normalized = normalize_name(&n.value.text);
        // El id entero lo asigna SQLite; `RETURNING id` lo devuelve para enlazar la atribución.
        let row_id: i32 = diesel::insert_into(plant_name::table)
            .values(NewPlantName {
                plant_id: id,
                text: &n.value.text,
                kind: kind_label(n.value.kind),
                language: &n.value.language,
                normalized: &normalized,
            })
            .returning(plant_name::id)
            .get_result(conn)?;
        let links: Vec<PlantNameSourceRow> = n
            .sources
            .iter()
            .map(|s| PlantNameSourceRow {
                plant_name_id: row_id,
                source_id: s.0.clone(),
            })
            .collect();
        diesel::insert_into(plant_name_source::table)
            .values(&links)
            .execute(conn)?;
    }
    for p in &plant.parts {
        let row_id: i32 = diesel::insert_into(plant_part::table)
            .values(NewPlantPart {
                plant_id: id,
                label: &p.value.label,
            })
            .returning(plant_part::id)
            .get_result(conn)?;
        let links: Vec<PlantPartSourceRow> = p
            .sources
            .iter()
            .map(|s| PlantPartSourceRow {
                plant_part_id: row_id,
                source_id: s.0.clone(),
            })
            .collect();
        diesel::insert_into(plant_part_source::table)
            .values(&links)
            .execute(conn)?;
    }
    for u in &plant.uses {
        let row_id: i32 = diesel::insert_into(plant_use::table)
            .values(NewPlantUse {
                plant_id: id,
                activity: &u.value.activity,
                language: &u.value.language,
                reference_id: &u.value.reference.id,
            })
            .returning(plant_use::id)
            .get_result(conn)?;
        let links: Vec<PlantUseSourceRow> = u
            .sources
            .iter()
            .map(|s| PlantUseSourceRow {
                plant_use_id: row_id,
                source_id: s.0.clone(),
            })
            .collect();
        diesel::insert_into(plant_use_source::table)
            .values(&links)
            .execute(conn)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hash::NEUTRAL_TABLES;
    use crate::test_support::sample_catalog;
    use catalog_core::domain::SourceId;
    // `rusqlite` se usa a propósito como verificación independiente de Diesel.
    use rusqlite::{Connection, OpenFlags};

    fn open(path: &Path) -> Connection {
        Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap()
    }

    fn count(conn: &Connection, sql: &str) -> i64 {
        conn.query_row(sql, [], |r| r.get(0)).unwrap()
    }

    fn written() -> (tempfile::TempDir, PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        let out = dir.path().join("sub").join("catalog.db");
        write_catalog(&sample_catalog(), &out).unwrap();
        (dir, out)
    }

    #[test]
    fn creates_exactly_the_neutral_tables() {
        let (_dir, out) = written();
        let conn = open(&out);
        let mut stmt = conn
            .prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
            .unwrap();
        let tables: Vec<String> = stmt
            .query_map([], |r| r.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        let mut expected: Vec<String> = NEUTRAL_TABLES.iter().map(|t| t.to_string()).collect();
        expected.sort();
        assert_eq!(tables, expected);
        assert!(tables.iter().all(|t| !t.starts_with("raw_")));
        assert!(!temp_path(&out).exists());
    }

    #[test]
    fn stores_version_and_counts() {
        let (_dir, out) = written();
        let conn = open(&out);
        let version: String = conn
            .query_row(
                "SELECT value FROM metadata WHERE key = ?1",
                [SCHEMA_VERSION_KEY],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(version, SCHEMA_VERSION.to_string());
        // 2 fuentes, 2 plantas, 3 referencias; la lavanda tiene 5 nombres, la manzanilla 2.
        let expected = [
            ("source", 2),
            ("plant", 2),
            ("plant_source_id", 3),
            ("plant_name", 7),
            ("plant_part", 4),
            ("plant_use", 4),
            ("reference", 3),
            ("plant_name_source", 8),
            ("plant_part_source", 5),
            ("plant_use_source", 5),
            ("reference_source", 4),
        ];
        for (table, n) in expected {
            assert_eq!(
                count(&conn, &format!("SELECT COUNT(*) FROM {table}")),
                n,
                "{table}"
            );
        }
    }

    #[test]
    fn stores_attribution_and_links() {
        let (_dir, out) = written();
        let conn = open(&out);
        // El nombre compartido tiene dos filas de atribución.
        assert_eq!(
            count(
                &conn,
                "SELECT COUNT(*) FROM plant_name_source s JOIN plant_name n ON n.id = s.plant_name_id \
                 WHERE n.plant_id = 'lavandula-angustifolia' AND n.text = 'lavender'"
            ),
            2
        );
        let (family, source): (String, String) = conn
            .query_row(
                "SELECT family, family_source_id FROM plant WHERE id = 'lavandula-angustifolia'",
                [],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!((family.as_str(), source.as_str()), ("Lamiaceae", "alpha"));
        let link: String = conn
            .query_row(
                "SELECT source_plant_id FROM plant_source_id WHERE plant_id = 'lavandula-angustifolia' AND source_id = 'beta'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(link, "B7");
    }

    #[test]
    fn normalized_columns_use_the_shared_rule() {
        let (_dir, out) = written();
        let conn = open(&out);
        let mut stmt = conn
            .prepare("SELECT text, normalized FROM plant_name")
            .unwrap();
        let rows: Vec<(String, String)> = stmt
            .query_map([], |r| Ok((r.get(0)?, r.get(1)?)))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        assert!(!rows.is_empty());
        for (text, normalized) in rows {
            assert_eq!(normalized, normalize_name(&text));
        }
        let kinds = count(
            &conn,
            "SELECT COUNT(*) FROM plant_name WHERE kind = 'scientific'",
        );
        assert_eq!(kinds, 3);
    }

    #[test]
    fn foreign_keys_are_consistent() {
        let (_dir, out) = written();
        let conn = open(&out);
        let mut stmt = conn.prepare("PRAGMA foreign_key_check").unwrap();
        assert!(stmt.query([]).unwrap().next().unwrap().is_none());
    }

    fn assert_fails(mutate: impl FnOnce(&mut Catalog), expected: IngestError) {
        let dir = tempfile::tempdir().unwrap();
        let out = dir.path().join("catalog.db");
        let mut catalog = sample_catalog();
        mutate(&mut catalog);
        assert_eq!(write_catalog(&catalog, &out), Err(expected));
        assert!(!out.exists());
        assert!(!temp_path(&out).exists());
    }

    fn lavender(catalog: &mut Catalog) -> &mut ConsolidatedPlant {
        catalog
            .plants
            .iter_mut()
            .find(|p| p.plant.id.0 == "lavandula-angustifolia")
            .unwrap()
    }

    #[test]
    fn data_without_source_is_rejected() {
        assert_fails(
            |c| lavender(c).plant.parts[0].sources.clear(),
            IngestError::DataWithoutSource {
                plant_id: "lavandula-angustifolia".into(),
                kind: "part",
                value: "Flower".into(),
            },
        );
        assert_fails(
            |c| c.references[0].sources.clear(),
            IngestError::DataWithoutSource {
                plant_id: String::new(),
                kind: "reference",
                value: "r1".into(),
            },
        );
    }

    #[test]
    fn unresolved_reference_is_rejected() {
        assert_fails(
            |c| c.references.retain(|r| r.value.id != "r2"),
            IngestError::UnresolvedReference {
                source: "alpha".into(),
                source_plant_id: "A1".into(),
                reference_id: "r2".into(),
            },
        );
    }

    #[test]
    fn unknown_source_is_rejected() {
        assert_fails(
            |c| {
                lavender(c).plant.names[0]
                    .sources
                    .push(SourceId("ghost".into()))
            },
            IngestError::UnknownSource { id: "ghost".into() },
        );
        assert_fails(
            |c| lavender(c).plant.family.as_mut().unwrap().sources = vec![SourceId("ghost".into())],
            IngestError::UnknownSource { id: "ghost".into() },
        );
        assert_fails(
            |c| {
                lavender(c)
                    .source_plant_ids
                    .insert(SourceId("ghost".into()), "G1".into());
            },
            IngestError::UnknownSource { id: "ghost".into() },
        );
    }

    #[test]
    fn empty_ids_and_duplicates_are_rejected() {
        assert_fails(
            |c| lavender(c).plant.scientific_name = "  ".into(),
            IngestError::EmptyScientificName {
                source: "alpha".into(),
                source_plant_id: "A1".into(),
            },
        );
        assert_fails(
            |c| {
                let mut copy = lavender(c).clone();
                copy.plant.scientific_name = "Otra".into();
                c.plants.push(copy);
            },
            IngestError::SlugCollision {
                slug: "lavandula-angustifolia".into(),
                first_identity: "lavandula angustifolia".into(),
                second_identity: "otra".into(),
            },
        );
    }

    #[test]
    fn failure_keeps_existing_database_intact() {
        let (_dir, out) = written();
        let before = std::fs::read(&out).unwrap();
        let mut broken = sample_catalog();
        broken.references.clear();
        assert!(write_catalog(&broken, &out).is_err());
        assert_eq!(std::fs::read(&out).unwrap(), before);
        assert!(!temp_path(&out).exists());
    }

    #[test]
    fn database_failure_cleans_temp_and_keeps_destination() {
        // Pasa la validación pero SQLite lo rechaza: dos plantas con el mismo nombre normalizado.
        let (_dir, out) = written();
        let before = std::fs::read(&out).unwrap();
        let mut catalog = sample_catalog();
        let mut copy = catalog.plants[0].clone();
        copy.plant.id = catalog_core::domain::PlantId("copia".into());
        catalog.plants.push(copy);
        assert!(matches!(
            write_catalog(&catalog, &out),
            Err(IngestError::Storage(_))
        ));
        assert_eq!(std::fs::read(&out).unwrap(), before);
        assert!(!temp_path(&out).exists());
    }
}
