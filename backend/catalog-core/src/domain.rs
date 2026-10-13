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

/// Un dato junto con la fuente o fuentes que lo aportan.
///
/// Es genérico: `Attributed<PlantName>`, `Attributed<Part>`, etc. reutilizan la misma estructura sin repetir código.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Attributed<T> {
    /// El dato en sí.
    pub value: T,
    /// Fuentes que lo aportan; si dos fuentes coinciden, aparecen ambas.
    pub sources: Vec<SourceId>,
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

/// Detalle completo de una planta.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Plant {
    /// Identificador público.
    pub id: PlantId,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Familia, si alguna fuente la aporta (valor único, con la fuente elegida).
    pub family: Option<Attributed<String>>,
    /// Nombres de la planta.
    pub names: Vec<Attributed<PlantName>>,
    /// Partes de la planta.
    pub parts: Vec<Attributed<Part>>,
    /// Usos de la planta.
    pub uses: Vec<Attributed<Use>>,
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
