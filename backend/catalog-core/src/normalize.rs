//! Reglas de normalización de nombres y de slug.
//!
//! Son la única implementación del sistema: la ingesta las usa para la columna normalizada y el ID público, y la API para normalizar la consulta de búsqueda.

use unicode_normalization::{UnicodeNormalization, char::is_combining_mark};

/// Normaliza un nombre para comparar y buscar.
///
/// Pasa a minúsculas, descompone en NFD y descarta las marcas diacríticas combinantes, recorta los espacios exteriores y colapsa los internos repetidos en uno.
pub fn normalize_name(input: &str) -> String {
    // El signo de híbrido `×` se separa como palabra `x`, igual que la `x` suelta de los nombres antiguos; las `x` dentro de una palabra no cambian.
    let stripped: String = input
        .replace('×', " x ")
        .to_lowercase()
        .nfd()
        .filter(|c| !is_combining_mark(*c))
        .collect();
    // `split_whitespace` ignora los espacios exteriores y agrupa los repetidos.
    stripped.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Fórmula con que la consolidación nombra una actividad de enfermedad grave; esas actividades no se enlazan al glosario.
pub const SERIOUS_DISEASE_PREFIX: &str = "Uso tradicional, sin eficacia demostrada: ";

/// Forma base de una actividad para enlazarla con el glosario (D8).
///
/// Es el texto antes del primer paréntesis, en NFC, con los espacios colapsados y en minúsculas, sin quitar acentos. Es la misma regla que `base_key` de `tools/catalog-seed` (Python); ambas se prueban con `glossary-key-cases.json`.
pub fn activity_base_key(activity: &str) -> String {
    let nfc: String = activity.nfc().collect();
    let before_paren = nfc.split('(').next().unwrap_or("");
    before_paren
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase()
}

/// Indica si una actividad se enlaza al glosario: no empieza por la fórmula de enfermedad grave.
pub fn activity_can_link_glossary(activity: &str) -> bool {
    !activity.starts_with(SERIOUS_DISEASE_PREFIX)
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
    ("Mentha × piperita", "mentha x piperita"),
    ("Mentha x piperita", "mentha x piperita"),
    ("×Citrofortunella", "x citrofortunella"),
    ("Xanthium Maximowiczii Alex", "xanthium maximowiczii alex"),
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
    fn activity_base_key_follows_the_glossary_rule() {
        // Los casos compartidos con Python viven en `glossary-key-cases.json`, que prueba `catalog-ingest`.
        for (activity, key) in [
            ("Diurético", "diurético"),
            ("Antídoto (escorpión)", "antídoto"),
            ("  Tónico   ", "tónico"),
            ("TÓNICO", "tónico"),
            ("Tonico", "tonico"),
            ("To\u{0301}nico", "tónico"),
            ("", ""),
        ] {
            assert_eq!(activity_base_key(activity), key, "{activity:?}");
        }
        assert!(activity_can_link_glossary("Fiebre"));
        assert!(!activity_can_link_glossary(
            "Uso tradicional, sin eficacia demostrada: cáncer"
        ));
    }

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
