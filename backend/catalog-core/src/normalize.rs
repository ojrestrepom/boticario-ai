//! Reglas de normalización de nombres y de slug.
//!
//! Son la única implementación del sistema: la ingesta las usa para la columna normalizada y el ID público, y la API para normalizar la consulta de búsqueda.

use unicode_normalization::{UnicodeNormalization, char::is_combining_mark};

/// Normaliza un nombre para comparar y buscar.
///
/// Pasa a minúsculas, descompone en NFD y descarta las marcas diacríticas combinantes, recorta los espacios exteriores y colapsa los internos repetidos en uno.
pub fn normalize_name(input: &str) -> String {
    let stripped: String = input
        .to_lowercase()
        .nfd()
        .filter(|c| !is_combining_mark(*c))
        .collect();
    // `split_whitespace` ignora los espacios exteriores y agrupa los repetidos.
    stripped.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Convierte un nombre en slug: minúsculas sin acentos y cada secuencia de caracteres no alfanuméricos ASCII reducida a un guion, sin guiones en los extremos.
pub fn slug(input: &str) -> String {
    let mut out = String::new();
    let mut pending_dash = false;
    for c in normalize_name(input).chars() {
        if c.is_ascii_alphanumeric() {
            // El guion se escribe solo cuando llega el siguiente carácter válido: así no quedan guiones al inicio ni al final.
            if pending_dash && !out.is_empty() {
                out.push('-');
            }
            pending_dash = false;
            out.push(c);
        } else {
            pending_dash = true;
        }
    }
    out
}

/// Casos compartidos `(entrada, resultado esperado)` de [`normalize_name`], para reutilizar en los tests de la ingesta y la API.
pub const NORMALIZATION_CASES: &[(&str, &str)] = &[
    ("Lavándula", "lavandula"),
    ("LAVANDULA Angustifolia", "lavandula angustifolia"),
    ("  Lavandula angustifolia  ", "lavandula angustifolia"),
    ("Lavandula    angustifolia", "lavandula angustifolia"),
    ("\tLavandula \n angustifolia ", "lavandula angustifolia"),
    (
        "Mentha x piperita subsp. nothosubsp. piperita",
        "mentha x piperita subsp. nothosubsp. piperita",
    ),
    ("Ñandú Café", "nandu cafe"),
    ("", ""),
    ("   ", ""),
];

/// Casos compartidos `(entrada, resultado esperado)` de [`slug`].
pub const SLUG_CASES: &[(&str, &str)] = &[
    ("Lavandula angustifolia", "lavandula-angustifolia"),
    ("Lavándula   Angustifolia ", "lavandula-angustifolia"),
    (
        "Mentha x piperita subsp. nothosubsp. piperita",
        "mentha-x-piperita-subsp-nothosubsp-piperita",
    ),
    ("--Aloe (vera)--", "aloe-vera"),
    ("Ñandú", "nandu"),
    ("", ""),
    ("   ", ""),
    ("!!!", ""),
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_shared_cases() {
        for (input, expected) in NORMALIZATION_CASES {
            assert_eq!(normalize_name(input), *expected, "entrada: {input:?}");
        }
    }

    #[test]
    fn slugs_shared_cases() {
        for (input, expected) in SLUG_CASES {
            assert_eq!(slug(input), *expected, "entrada: {input:?}");
        }
    }

    #[test]
    fn normalization_is_idempotent() {
        for (_, expected) in NORMALIZATION_CASES {
            assert_eq!(normalize_name(expected), *expected);
        }
    }
}
