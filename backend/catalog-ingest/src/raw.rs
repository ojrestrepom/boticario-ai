//! Capa cruda: vuelca los CSV de un ZIP a tablas SQLite sin transformarlos.
//!
//! Cada CSV se convierte en una tabla `raw_<fuente>_<archivo>`. Las columnas son las de la cabecera, todas `TEXT`, y se añade una primera columna `_row` que es la **única que no viene del dataset**: el número de fila del CSV (1 = primera fila de datos). Sirve para conservar el orden original y para comparar dos importaciones.

use std::collections::HashSet;
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};

use encoding_rs::Encoding;
use rusqlite::{Connection, ToSql};
use zip::ZipArchive;

use crate::error::IngestError;

/// Qué entradas del ZIP se importan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RawFiles {
    /// Todas las entradas cuyo nombre termina en `.csv` (sin distinguir mayúsculas).
    AllCsv,
    /// Solo las entradas con exactamente estos nombres.
    Only(Vec<String>),
}

/// Configuración de la importación cruda que declara cada adaptador.
#[derive(Debug, Clone)]
pub struct RawImportSpec {
    /// Identificador de la fuente; es parte del nombre de cada tabla.
    pub source_id: String,
    /// Ruta del ZIP ya verificado.
    pub archive: PathBuf,
    /// Codificación de los CSV (por ejemplo `encoding_rs::WINDOWS_1252`). `&'static` porque las codificaciones son constantes del programa.
    pub encoding: &'static Encoding,
    /// Entradas a importar.
    pub files: RawFiles,
}

/// Tabla creada y número de filas que recibió.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawTableReport {
    /// Nombre de la tabla.
    pub table: String,
    /// Filas de datos insertadas.
    pub rows: u64,
}

/// Resultado de una importación.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RawImportReport {
    /// Tablas creadas, en orden alfabético (byte a byte, mayúsculas primero) del nombre de entrada.
    pub tables: Vec<RawTableReport>,
}

/// Nombre de la tabla cruda para una entrada del ZIP: `raw_<fuente>_<archivo>`.
///
/// Se usa el nombre sin carpetas ni extensión, en minúsculas y con todo lo que no sea alfanumérico ASCII convertido en `_`.
pub fn raw_table_name(source_id: &str, entry_name: &str) -> String {
    let file = entry_name.rsplit('/').next().unwrap_or(entry_name);
    let stem = file.rsplit_once('.').map_or(file, |(stem, _ext)| stem);
    let sanitize = |s: &str| {
        s.chars()
            .map(|c| {
                if c.is_ascii_alphanumeric() {
                    c.to_ascii_lowercase()
                } else {
                    '_'
                }
            })
            .collect::<String>()
    };
    format!("raw_{}_{}", sanitize(source_id), sanitize(stem))
}

/// Entre comillas dobles, duplicando las internas, para usar nombres arbitrarios como identificadores SQL.
fn quote_ident(name: &str) -> String {
    format!("\"{}\"", name.replace('"', "\"\""))
}

/// Importa el ZIP de `spec` en `raw_db` (que se crea, con su carpeta, si no existe).
///
/// Todo ocurre en una transacción: se borran y recrean las tablas de esta fuente y, si algo falla, no se aplica nada. Las tablas de otras fuentes no se tocan.
pub fn import_raw(spec: &RawImportSpec, raw_db: &Path) -> Result<RawImportReport, IngestError> {
    let io_error = |path: &Path, err: std::io::Error| IngestError::Io {
        path: Some(path.to_path_buf()),
        message: err.to_string(),
    };

    let file = File::open(&spec.archive).map_err(|e| io_error(&spec.archive, e))?;
    let mut archive = ZipArchive::new(file)?;
    let entries = select_entries(spec, &mut archive)?;

    if let Some(parent) = raw_db.parent() {
        std::fs::create_dir_all(parent).map_err(|e| io_error(parent, e))?;
    }
    let mut conn = Connection::open(raw_db)?;
    // Si retornamos antes de `commit`, `tx` se destruye y SQLite revierte todo.
    let tx = conn.transaction()?;

    let mut report = RawImportReport::default();
    let mut seen = HashSet::new();
    for entry in &entries {
        let table = raw_table_name(&spec.source_id, entry);
        if !seen.insert(table.clone()) {
            return Err(IngestError::InvalidZip {
                message: format!("dos entradas darían la misma tabla `{table}` (última: {entry})"),
            });
        }
        let mut bytes = Vec::new();
        archive.by_name(entry)?.read_to_end(&mut bytes)?;
        let text = decode(spec.encoding, entry, &bytes)?;
        let rows = import_csv(&tx, &table, entry, &text)?;
        report.tables.push(RawTableReport { table, rows });
    }
    tx.commit()?;
    Ok(report)
}

/// Resuelve qué entradas importar, en orden alfabético para que el resultado no dependa del orden interno del ZIP.
fn select_entries(
    spec: &RawImportSpec,
    archive: &mut ZipArchive<File>,
) -> Result<Vec<String>, IngestError> {
    let mut names: Vec<String> = match &spec.files {
        RawFiles::AllCsv => {
            let mut found = Vec::new();
            for i in 0..archive.len() {
                let entry = archive.by_index(i)?;
                let name = entry.name()?;
                if entry.is_file() && name.to_ascii_lowercase().ends_with(".csv") {
                    found.push(name.into_owned());
                }
            }
            found
        }
        RawFiles::Only(wanted) => {
            for name in wanted {
                if archive.by_name(name).is_err() {
                    return Err(IngestError::InvalidZip {
                        message: format!("falta la entrada `{name}`"),
                    });
                }
            }
            wanted.clone()
        }
    };
    names.sort();
    Ok(names)
}

/// Decodifica los bytes; si hubo que sustituir alguno, es un error y no un `U+FFFD` silencioso.
fn decode(encoding: &'static Encoding, file: &str, bytes: &[u8]) -> Result<String, IngestError> {
    let (text, _used, had_errors) = encoding.decode(bytes);
    if had_errors {
        return Err(IngestError::InvalidCsv {
            file: file.to_string(),
            row: None,
            message: format!("bytes inválidos para la codificación {}", encoding.name()),
        });
    }
    Ok(text.into_owned())
}

/// Crea la tabla de un CSV y la llena. Devuelve el número de filas.
fn import_csv(conn: &Connection, table: &str, file: &str, text: &str) -> Result<u64, IngestError> {
    // Sin `flexible`: una fila con otro número de campos es un error.
    let mut reader = csv::ReaderBuilder::new().from_reader(text.as_bytes());
    let headers: Vec<String> = reader
        .headers()
        .map_err(|e| csv_error(file, &e))?
        .iter()
        .map(str::to_string)
        .collect();
    validate_headers(file, &headers)?;

    let columns: Vec<String> = headers
        .iter()
        .map(|h| format!("{} TEXT NOT NULL", quote_ident(h)))
        .collect();
    let placeholders = vec!["?"; headers.len() + 1].join(", ");
    conn.execute(&format!("DROP TABLE IF EXISTS {}", quote_ident(table)), [])?;
    conn.execute(
        &format!(
            "CREATE TABLE {} (_row INTEGER PRIMARY KEY, {})",
            quote_ident(table),
            columns.join(", ")
        ),
        [],
    )?;
    let mut insert = conn.prepare(&format!(
        "INSERT INTO {} VALUES ({placeholders})",
        quote_ident(table)
    ))?;

    let mut count: u64 = 0;
    for record in reader.records() {
        let record = record.map_err(|e| csv_error(file, &e))?;
        count += 1;
        let row = count as i64;
        let fields: Vec<&str> = record.iter().collect();
        let mut params: Vec<&dyn ToSql> = Vec::with_capacity(fields.len() + 1);
        params.push(&row);
        params.extend(fields.iter().map(|f| f as &dyn ToSql));
        insert.execute(params.as_slice())?;
    }
    Ok(count)
}

fn validate_headers(file: &str, headers: &[String]) -> Result<(), IngestError> {
    let invalid = |column: &str, message: &str| IngestError::InvalidHeader {
        file: file.to_string(),
        column: column.to_string(),
        message: message.to_string(),
    };
    if headers.is_empty() || (headers.len() == 1 && headers[0].is_empty()) {
        return Err(invalid("", "el archivo no tiene cabecera"));
    }
    // SQLite no distingue mayúsculas en nombres de columna, y `_row` está reservada.
    let mut seen = HashSet::from(["_row".to_string()]);
    for name in headers {
        if name.is_empty() {
            return Err(invalid("", "columna sin nombre"));
        }
        if !seen.insert(name.to_ascii_lowercase()) {
            return Err(invalid(name, "nombre de columna duplicado o reservado"));
        }
    }
    Ok(())
}

/// Traduce un error del crate `csv` indicando archivo y fila de datos.
fn csv_error(file: &str, err: &csv::Error) -> IngestError {
    // `record()` es 0-based y cuenta la cabecera, así que coincide con el número de fila de datos.
    let row = err.position().map(csv::Position::record).filter(|r| *r > 0);
    IngestError::InvalidCsv {
        file: file.to_string(),
        row,
        message: err.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_support::build_zip;

    const PLANTS: &str =
        "ID,Nombre común,Nota\r\n1,Ñandú café,\"a, b\"\r\n2, con espacios ,\r\n3,,último\r\n";
    const ONE: &str = "k\r\nsolo\r\n";

    fn spec(zip: PathBuf, source: &str, files: RawFiles) -> RawImportSpec {
        RawImportSpec {
            source_id: source.to_string(),
            archive: zip,
            encoding: encoding_rs::WINDOWS_1252,
            files,
        }
    }

    fn dump(conn: &Connection, table: &str) -> Vec<Vec<String>> {
        let mut stmt = conn
            .prepare(&format!("SELECT * FROM \"{table}\" ORDER BY _row"))
            .unwrap();
        let n = stmt.column_count();
        stmt.query_map([], |row| {
            (0..n)
                .map(|i| {
                    row.get::<_, rusqlite::types::Value>(i).map(|v| match v {
                        rusqlite::types::Value::Integer(i) => i.to_string(),
                        rusqlite::types::Value::Text(s) => s,
                        other => format!("{other:?}"),
                    })
                })
                .collect()
        })
        .unwrap()
        .collect::<Result<_, _>>()
        .unwrap()
    }

    fn tables(conn: &Connection) -> Vec<String> {
        let mut stmt = conn
            .prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            .unwrap();
        stmt.query_map([], |r| r.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap()
    }

    fn setup(entries: &[(&str, &str)]) -> (tempfile::TempDir, PathBuf, PathBuf) {
        let dir = tempfile::tempdir().unwrap();
        let zip = build_zip(&dir, entries);
        let db = dir.path().join("sub/raw.db");
        (dir, zip, db)
    }

    #[test]
    fn table_name_is_sanitized() {
        assert_eq!(
            raw_table_name("usda", "data/My File-1.CSV"),
            "raw_usda_my_file_1"
        );
    }

    #[test]
    fn imports_all_csv_faithfully() {
        let (_dir, zip, db) = setup(&[
            ("PLANTS.csv", PLANTS),
            ("one.csv", ONE),
            ("readme.txt", "x"),
        ]);
        let report = import_raw(&spec(zip, "t", RawFiles::AllCsv), &db).unwrap();
        assert_eq!(
            report.tables,
            vec![
                RawTableReport {
                    table: "raw_t_plants".into(),
                    rows: 3
                },
                RawTableReport {
                    table: "raw_t_one".into(),
                    rows: 1
                },
            ]
        );

        let conn = Connection::open(&db).unwrap();
        assert_eq!(tables(&conn), ["raw_t_one", "raw_t_plants"]);
        let cols: Vec<String> = conn
            .prepare("SELECT name FROM pragma_table_info('raw_t_plants')")
            .unwrap()
            .query_map([], |r| r.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        assert_eq!(cols, ["_row", "ID", "Nombre común", "Nota"]);
        assert_eq!(
            dump(&conn, "raw_t_plants"),
            vec![
                vec!["1", "1", "Ñandú café", "a, b"],
                vec!["2", "2", " con espacios ", ""],
                vec!["3", "3", "", "último"],
            ]
        );
        assert_eq!(dump(&conn, "raw_t_one"), vec![vec!["1", "solo"]]);
    }

    #[test]
    fn only_imports_requested_entries() {
        let (_dir, zip, db) = setup(&[("a.csv", ONE), ("b.csv", ONE)]);
        import_raw(&spec(zip, "t", RawFiles::Only(vec!["b.csv".into()])), &db).unwrap();
        assert_eq!(tables(&Connection::open(&db).unwrap()), ["raw_t_b"]);
    }

    #[test]
    fn only_with_missing_entry_fails() {
        let (_dir, zip, db) = setup(&[("a.csv", ONE)]);
        let err =
            import_raw(&spec(zip, "t", RawFiles::Only(vec!["z.csv".into()])), &db).unwrap_err();
        assert!(matches!(err, IngestError::InvalidZip { .. }));
    }

    #[test]
    fn duplicate_header_fails() {
        let (_dir, zip, db) = setup(&[("a.csv", "x,X\r\n1,2\r\n")]);
        let err = import_raw(&spec(zip, "t", RawFiles::AllCsv), &db).unwrap_err();
        assert!(
            matches!(err, IngestError::InvalidHeader { ref file, ref column, .. } if file == "a.csv" && column == "X")
        );
    }

    #[test]
    fn empty_file_has_no_header() {
        let (_dir, zip, db) = setup(&[("a.csv", "")]);
        let err = import_raw(&spec(zip, "t", RawFiles::AllCsv), &db).unwrap_err();
        assert!(matches!(err, IngestError::InvalidHeader { .. }));
    }

    #[test]
    fn short_row_reports_file_and_row() {
        let (_dir, zip, db) = setup(&[("a.csv", "x,y\r\n1,2\r\n3\r\n")]);
        let err = import_raw(&spec(zip, "t", RawFiles::AllCsv), &db).unwrap_err();
        match err {
            IngestError::InvalidCsv { file, row, .. } => {
                assert_eq!(file, "a.csv");
                assert_eq!(row, Some(2));
            }
            other => panic!("error inesperado: {other:?}"),
        }
    }

    #[test]
    fn invalid_bytes_for_encoding_fail() {
        // El fixture está en Windows-1252 ("é" = 0xE9), que no es UTF-8 válido.
        let (_dir, zip, db) = setup(&[("a.csv", "x\r\né\r\n")]);
        let mut s = spec(zip, "t", RawFiles::AllCsv);
        s.encoding = encoding_rs::UTF_8;
        let err = import_raw(&s, &db).unwrap_err();
        assert!(err.to_string().contains("bytes inválidos"), "{err}");
    }

    #[test]
    fn importing_twice_gives_identical_dump() {
        let (_dir, zip, db) = setup(&[("PLANTS.csv", PLANTS), ("one.csv", ONE)]);
        let s = spec(zip, "t", RawFiles::AllCsv);
        let snapshot = |db: &Path| {
            let conn = Connection::open(db).unwrap();
            tables(&conn)
                .iter()
                .map(|t| (t.clone(), dump(&conn, t)))
                .collect::<Vec<_>>()
        };
        import_raw(&s, &db).unwrap();
        let first = snapshot(&db);
        import_raw(&s, &db).unwrap();
        assert_eq!(first, snapshot(&db));
    }

    #[test]
    fn importing_another_source_keeps_the_first() {
        let (_dir, zip, db) = setup(&[("PLANTS.csv", PLANTS)]);
        import_raw(&spec(zip.clone(), "a", RawFiles::AllCsv), &db).unwrap();
        let before = dump(&Connection::open(&db).unwrap(), "raw_a_plants");
        import_raw(&spec(zip, "b", RawFiles::AllCsv), &db).unwrap();
        let conn = Connection::open(&db).unwrap();
        assert_eq!(tables(&conn), ["raw_a_plants", "raw_b_plants"]);
        assert_eq!(dump(&conn, "raw_a_plants"), before);
    }

    #[test]
    fn failure_midway_rolls_back_everything() {
        let (dir, good_zip, db) = setup(&[("a.csv", ONE)]);
        import_raw(&spec(good_zip, "t", RawFiles::AllCsv), &db).unwrap();
        let before = dump(&Connection::open(&db).unwrap(), "raw_t_a");

        // "a.csv" (cambiado) se importa bien y "b.csv" falla después.
        let bad_dir = tempfile::tempdir_in(dir.path()).unwrap();
        let bad_zip = build_zip(
            &bad_dir,
            &[("a.csv", "k\r\nnuevo\r\n"), ("b.csv", "x,y\r\n1\r\n")],
        );
        assert!(import_raw(&spec(bad_zip, "t", RawFiles::AllCsv), &db).is_err());

        let conn = Connection::open(&db).unwrap();
        assert_eq!(tables(&conn), ["raw_t_a"]);
        assert_eq!(dump(&conn, "raw_t_a"), before);
    }
}
