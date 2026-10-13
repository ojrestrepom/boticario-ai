//! Utilidades compartidas por los tests (no se compila fuera de `cargo test`).

use std::io::Write;
use std::path::PathBuf;

use zip::write::SimpleFileOptions;

/// Crea un ZIP en `dir` con las entradas `(nombre, contenido)`, codificando cada contenido en Windows-1252.
pub fn build_zip(dir: &tempfile::TempDir, entries: &[(&str, &str)]) -> PathBuf {
    let path = dir.path().join("fixture.zip");
    let mut writer = zip::ZipWriter::new(std::fs::File::create(&path).unwrap());
    // `Stored` evita depender de la compresión: el fixture solo necesita ser un ZIP válido.
    let options = SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored);
    for (name, content) in entries {
        let (bytes, _, unmappable) = encoding_rs::WINDOWS_1252.encode(content);
        assert!(
            !unmappable,
            "el fixture usa un carácter fuera de Windows-1252"
        );
        writer.start_file(*name, options).unwrap();
        writer.write_all(&bytes).unwrap();
    }
    writer.finish().unwrap();
    path
}
