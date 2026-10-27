//! Tipos de dominio del catálogo, independientes de la fuente de datos y del transporte.

/// Identificador de una fuente de datos (por ejemplo `fuente-a`).
///
/// Es un newtype: un `String` envuelto en un tipo propio para que el compilador no deje mezclarlo con otros textos, como un [`PlantId`].
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SourceId(pub String);

/// Metadatos de una fuente de datos y su procedencia.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Source {
    /// Identificador de la fuente.
    pub id: SourceId,
    /// Nombre legible.
    pub name: String,
    /// Versión del dataset.
    pub version: String,
    /// Licencia bajo la que se publica.
    pub license: String,
    /// Cita bibliográfica recomendada.
    pub citation: String,
    /// URL de origen.
    pub url: String,
    /// Checksum del insumo original, como texto.
    pub checksum: String,
}

/// Identificador público de una planta: el slug de su nombre científico canónico.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct PlantId(pub String);

/// Tipo de un nombre de planta.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NameKind {
    /// Nombre científico.
    Scientific,
    /// Nombre común.
    Common,
}

/// Un nombre de planta con su tipo e idioma.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlantName {
    /// Texto del nombre tal como se muestra.
    pub text: String,
    /// Si es científico o común.
    pub kind: NameKind,
    /// Código de idioma, por ejemplo `en`.
    pub language: String,
}

/// Parte de la planta (hoja, raíz, etc.).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Part {
    /// Etiqueta de la parte.
    pub label: String,
}

/// Referencia bibliográfica.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reference {
    /// Identificador de la referencia.
    pub id: String,
    /// Cita completa.
    pub citation: String,
}

/// Uso de una planta, respaldado por una referencia.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Use {
    /// Actividad o propiedad atribuida.
    pub activity: String,
    /// Código de idioma de la etiqueta de actividad.
    pub language: String,
    /// Referencia que respalda el uso.
    pub reference: Reference,
}

/// Perfil consolidado de una planta: lo que la semilla guarda además de nombres, partes y usos.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlantProfile {
    /// Nombre para mostrar elegido en la semilla: un nombre en español o, si no lo hay, el científico.
    pub display_name: Option<String>,
    /// Origen de la planta.
    pub origin: Option<String>,
    /// Descripción neutra.
    pub description: Option<String>,
    /// Tipo de aceite (por ejemplo `Esencial`), si la planta tiene aceite registrado.
    pub oil_type: Option<String>,
}

/// Referencia de un grupo de uso: una cita que puede o no tener obra identificada.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UseGroupReference {
    /// Identificador de la obra; `None` si la cita no se pudo resolver.
    pub id: Option<String>,
    /// Texto completo de la cita, o «<clave> (sin resolver)» si no está resuelta.
    pub citation: String,
}

impl UseGroupReference {
    /// Si la cita tiene una obra identificada.
    pub fn is_resolved(&self) -> bool {
        self.id.is_some()
    }
}

/// Grupo de uso tradicional: una actividad con el número de registros, los países y sus citas.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UseGroup {
    /// Actividad traducida.
    pub activity: String,
    /// Actividad tal como la trae la fuente original.
    pub activity_source: String,
    /// Número de registros que respaldan el grupo.
    pub count: u32,
    /// Países, en español.
    pub countries: Vec<String>,
    /// Citas del grupo, resueltas o no.
    pub references: Vec<UseGroupReference>,
}

/// Objetivo de una planta registrado en la semilla.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Goal {
    /// Identificador del objetivo.
    pub id: String,
    /// Nombre del objetivo, en español.
    pub name: String,
    /// Subárea, solo para «otros objetivos».
    pub subarea: Option<String>,
    /// Área, en español.
    pub area: String,
    /// Tipo de respaldo, en español.
    pub evidence: String,
    /// Referencias que respaldan el objetivo.
    pub references: Vec<Reference>,
}

/// Nivel de precaución de una planta.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum SafetyLevel {
    /// Bajo (`bajo`): por ejemplo, alergénica.
    Low,
    /// Medio (`medio`).
    Medium,
    /// Alto (`alto`).
    High,
}

impl SafetyLevel {
    /// Interpreta el valor guardado (`alto`, `medio` o `bajo`); cualquier otro es `None`.
    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "alto" => Some(Self::High),
            "medio" => Some(Self::Medium),
            "bajo" => Some(Self::Low),
            _ => None,
        }
    }

    /// El valor guardado y servido por la API.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::High => "alto",
            Self::Medium => "medio",
            Self::Low => "bajo",
        }
    }
}

/// Precauciones de una planta. Un `Safety` ausente significa que no hay ningún dato, no que la planta sea segura.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Safety {
    /// Nivel, o `None` si las fuentes traen advertencias pero ninguna fija un nivel.
    pub level: Option<SafetyLevel>,
    /// Texto de las advertencias.
    pub text: String,
    /// Referencias que respaldan el texto.
    pub references: Vec<Reference>,
}

/// Imagen de una planta con la licencia que permite usarla.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Image {
    /// URL de la imagen.
    pub url: String,
    /// Página del archivo de la imagen.
    pub page_url: String,
    /// Autor, si se conoce.
    pub author: Option<String>,
    /// Licencia de la imagen.
    pub license: String,
    /// URL de la licencia, si existe.
    pub license_url: Option<String>,
    /// Si hay que mostrar la atribución al usar la imagen.
    pub attribution_required: bool,
}

/// Crédito neutral a nivel de planta: la fuente que respalda sus datos, sin decir qué campo vino de ella.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Credit {
    /// Nombre legible de la fuente.
    pub name: String,
    /// Licencia, en texto.
    pub license: String,
    /// URL de la licencia, si la fuente tiene una.
    pub license_url: Option<String>,
    /// Atribución exigida.
    pub attribution: String,
    /// Página de la fuente o del artículo, si existe.
    pub url: Option<String>,
}

/// Detalle completo de una planta, ya consolidado: no dice qué fuente aportó cada dato.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Plant {
    /// Identificador público.
    pub id: PlantId,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Familia, si alguna fuente la aporta.
    pub family: Option<String>,
    /// Nombres de la planta.
    pub names: Vec<PlantName>,
    /// Partes de la planta.
    pub parts: Vec<Part>,
    /// Usos de la planta.
    pub uses: Vec<Use>,
}

/// Elemento del listado de plantas.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlantSummary {
    /// Identificador público.
    pub id: PlantId,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Nombres comunes con su idioma.
    pub common_names: Vec<PlantName>,
    /// Familia, si existe.
    pub family: Option<String>,
}

/// Límite de página por defecto.
pub const DEFAULT_LIMIT: u32 = 20;
/// Límite de página máximo.
pub const MAX_LIMIT: u32 = 100;

/// Parámetros de consulta del listado.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ListQuery {
    /// Texto de búsqueda sin normalizar; `None` (o vacío) no filtra.
    pub q: Option<String>,
    /// Elementos por página.
    pub limit: u32,
    /// Elementos a saltar.
    pub offset: u32,
}

impl Default for ListQuery {
    /// Sin filtro, primera página con el límite por defecto.
    fn default() -> Self {
        Self {
            q: None,
            limit: DEFAULT_LIMIT,
            offset: 0,
        }
    }
}

/// Una página de resultados con el total de coincidencias, independiente de la página.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Page<T> {
    /// Elementos de la página.
    pub items: Vec<T>,
    /// Total de coincidencias.
    pub total: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn safety_level_round_trips_and_rejects_unknown_values() {
        for level in [SafetyLevel::High, SafetyLevel::Medium, SafetyLevel::Low] {
            assert_eq!(SafetyLevel::parse(level.as_str()), Some(level));
        }
        assert_eq!(SafetyLevel::parse("extremo"), None);
        assert_eq!(SafetyLevel::parse(""), None);
        assert!(SafetyLevel::High > SafetyLevel::Medium && SafetyLevel::Medium > SafetyLevel::Low);
    }

    #[test]
    fn use_group_reference_is_resolved_only_with_a_work() {
        let resolved = UseGroupReference {
            id: Some("ref:1".into()),
            citation: "Steinmetz, E.F. 1957.".into(),
        };
        let unresolved = UseGroupReference {
            id: None,
            citation: "Woi.6 (sin resolver)".into(),
        };
        assert!(resolved.is_resolved());
        assert!(!unresolved.is_resolved());
    }

    #[test]
    fn credit_and_safety_admit_missing_optional_values() {
        let credit = Credit {
            name: "Fuente".into(),
            license: "por archivo".into(),
            license_url: None,
            attribution: "Atribución".into(),
            url: None,
        };
        assert_eq!(credit.license_url, None);
        let safety = Safety {
            level: None,
            text: "Contraindicaciones.".into(),
            references: vec![],
        };
        assert_eq!(safety.level, None);
    }
}
