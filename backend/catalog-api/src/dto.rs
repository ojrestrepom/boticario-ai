//! Tipos de respuesta de la API (DTOs), separados del dominio.
//!
//! El dominio de `catalog-core` no conoce JSON; aquí se define la forma exacta del contrato HTTP y se convierte desde el dominio.
//! `rename_all = "camelCase"` hace que los campos Rust (`scientific_name`) salgan como `scientificName`.
//! Todos los DTOs viven en este módulo y derivan `ToSchema`: de ellos sale el documento OpenAPI, así que el contrato HTTP se define en un solo sitio.

use catalog_core::domain::{
    Credit, Goal, GoalPlant, GoalPlants, GoalSummary, IdName, Image, NameKind, Page, Part, Plant,
    PlantName, PlantSummary, Reference, Safety, SafetyLevel, SubareaSummary, Use, UseGroup,
    UseGroupReference,
};
use serde::Serialize;
use utoipa::ToSchema;

/// Respuesta de `GET /health`.
#[derive(Debug, Clone, Serialize, ToSchema)]
pub struct HealthDto {
    /// Siempre `"ok"` si el servicio está activo.
    pub status: &'static str,
}

/// Nombre común con su idioma, dentro del listado.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct CommonNameDto {
    /// Texto del nombre.
    pub text: String,
    /// Código de idioma.
    pub language: String,
}

/// Elemento del listado de plantas.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct PlantSummaryDto {
    /// Identificador público.
    pub id: String,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Nombre para mostrar: un nombre común en español o, si la planta no tiene ninguno, el nombre científico.
    pub display_name: String,
    /// Nombres comunes con su idioma; si el nombre para mostrar es uno de ellos, va primero.
    pub common_names: Vec<CommonNameDto>,
    /// Familia, o `null` si ninguna fuente la aporta.
    pub family: Option<String>,
}

impl From<PlantSummary> for PlantSummaryDto {
    fn from(p: PlantSummary) -> Self {
        Self {
            id: p.id.0,
            scientific_name: p.scientific_name,
            display_name: p.display_name,
            common_names: p
                .common_names
                .into_iter()
                .map(|n| CommonNameDto {
                    text: n.text,
                    language: n.language,
                })
                .collect(),
            family: p.family,
        }
    }
}

/// Página de resultados.
///
/// Es genérica: `T` es el tipo de elemento. Con `T: Serialize` el `derive` de serde genera la serialización de `PageDto<T>` para cualquier `T` serializable.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct PageDto<T: Serialize> {
    /// Elementos de la página.
    pub items: Vec<T>,
    /// Total de coincidencias, independiente de la página.
    pub total: u64,
    /// Límite aplicado.
    pub limit: u32,
    /// Desplazamiento aplicado.
    pub offset: u32,
}

impl PageDto<PlantSummaryDto> {
    /// Convierte la página del dominio, anotando el `limit` y el `offset` con que se pidió.
    pub fn from_page(page: Page<PlantSummary>, limit: u32, offset: u32) -> Self {
        Self {
            items: page.items.into_iter().map(Into::into).collect(),
            total: page.total,
            limit,
            offset,
        }
    }
}

/// Tipo de nombre, serializado como `"scientific"` o `"common"`.
#[derive(Debug, Clone, Copy, Serialize, ToSchema)]
#[serde(rename_all = "lowercase")]
pub enum NameKindDto {
    /// Nombre científico.
    Scientific,
    /// Nombre común.
    Common,
}

/// Nombre de planta con su tipo e idioma.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct NameDto {
    /// Texto del nombre.
    pub text: String,
    /// Tipo de nombre.
    pub kind: NameKindDto,
    /// Código de idioma.
    pub language: String,
}

impl From<PlantName> for NameDto {
    fn from(n: PlantName) -> Self {
        Self {
            text: n.text,
            kind: match n.kind {
                NameKind::Scientific => NameKindDto::Scientific,
                NameKind::Common => NameKindDto::Common,
            },
            language: n.language,
        }
    }
}

/// Parte de la planta.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct PartDto {
    /// Etiqueta de la parte.
    pub label: String,
}

impl From<Part> for PartDto {
    fn from(p: Part) -> Self {
        Self { label: p.label }
    }
}

/// Referencia bibliográfica de un uso.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct ReferenceDto {
    /// Identificador de la referencia.
    pub id: String,
    /// Cita completa.
    pub citation: String,
}

/// Uso de la planta con su referencia.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct UseDto {
    /// Actividad atribuida.
    pub activity: String,
    /// Idioma de la etiqueta de actividad.
    pub language: String,
    /// Referencia que respalda el uso.
    pub reference: ReferenceDto,
}

impl From<Use> for UseDto {
    fn from(u: Use) -> Self {
        Self {
            activity: u.activity,
            language: u.language,
            reference: ReferenceDto {
                id: u.reference.id,
                citation: u.reference.citation,
            },
        }
    }
}

/// Aceite de la planta.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct OilDto {
    /// Tipo de aceite, por ejemplo `Esencial`.
    #[serde(rename = "type")]
    #[schema(rename = "type")]
    pub oil_type: String,
}

/// Cita de un grupo de uso: el texto completo de la cita, resuelta o no.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct UseGroupReferenceDto {
    /// Identificador de la referencia, o `null` si la cita no tiene una obra identificada.
    #[schema(required = true)]
    pub id: Option<String>,
    /// Texto completo de la cita; en una cita sin resolver, la clave seguida de «(sin resolver)».
    pub citation: String,
    /// Si la cita tiene una obra identificada.
    pub resolved: bool,
}

impl From<UseGroupReference> for UseGroupReferenceDto {
    fn from(r: UseGroupReference) -> Self {
        Self {
            resolved: r.is_resolved(),
            id: r.id,
            citation: r.citation,
        }
    }
}

/// Grupo de uso tradicional: una actividad con el número de registros, los países y sus citas.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct UseGroupDto {
    /// Actividad, en español.
    pub activity: String,
    /// Actividad tal como la trae la fuente original.
    pub activity_source: String,
    /// Número de registros que respaldan el grupo.
    pub count: u32,
    /// Países, en español.
    pub countries: Vec<String>,
    /// Citas del grupo, resueltas o no.
    pub references: Vec<UseGroupReferenceDto>,
}

impl From<UseGroup> for UseGroupDto {
    fn from(g: UseGroup) -> Self {
        Self {
            activity: g.activity,
            activity_source: g.activity_source,
            count: g.count,
            countries: g.countries,
            references: g.references.into_iter().map(Into::into).collect(),
        }
    }
}

impl From<Reference> for ReferenceDto {
    fn from(r: Reference) -> Self {
        Self {
            id: r.id,
            citation: r.citation,
        }
    }
}

/// Objetivo registrado para la planta.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct GoalDto {
    /// Identificador del objetivo.
    pub id: String,
    /// Nombre del objetivo, en español.
    pub name: String,
    /// Subárea (solo en «otros objetivos»), o `null`.
    #[schema(required = true)]
    pub subarea: Option<String>,
    /// Área, en español.
    pub area: String,
    /// Tipo de respaldo, en español.
    pub evidence: String,
    /// Referencias que respaldan el objetivo.
    pub references: Vec<ReferenceDto>,
}

impl From<Goal> for GoalDto {
    fn from(g: Goal) -> Self {
        Self {
            id: g.id,
            name: g.name,
            subarea: g.subarea,
            area: g.area,
            evidence: g.evidence,
            references: g.references.into_iter().map(Into::into).collect(),
        }
    }
}

/// Nivel de precaución, serializado como `"alto"`, `"medio"` o `"bajo"`.
#[derive(Debug, Clone, Copy, Serialize, ToSchema)]
pub enum SafetyLevelDto {
    /// Nivel alto.
    #[serde(rename = "alto")]
    #[schema(rename = "alto")]
    High,
    /// Nivel medio.
    #[serde(rename = "medio")]
    #[schema(rename = "medio")]
    Medium,
    /// Nivel bajo.
    #[serde(rename = "bajo")]
    #[schema(rename = "bajo")]
    Low,
}

impl From<SafetyLevel> for SafetyLevelDto {
    fn from(level: SafetyLevel) -> Self {
        match level {
            SafetyLevel::High => Self::High,
            SafetyLevel::Medium => Self::Medium,
            SafetyLevel::Low => Self::Low,
        }
    }
}

/// Precauciones de la planta. Su ausencia (`null`) significa que no hay ningún dato, no que la planta sea segura.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct SafetyDto {
    /// Nivel, o `null` si las fuentes traen advertencias pero ninguna fija un nivel.
    #[schema(required = true)]
    pub level: Option<SafetyLevelDto>,
    /// Texto de las advertencias.
    pub text: String,
    /// Referencias que respaldan el texto.
    pub references: Vec<ReferenceDto>,
}

impl From<Safety> for SafetyDto {
    fn from(s: Safety) -> Self {
        Self {
            level: s.level.map(Into::into),
            text: s.text,
            references: s.references.into_iter().map(Into::into).collect(),
        }
    }
}

/// Imagen de la planta con su licencia. La API solo entrega los datos del registro: nunca sirve los bytes de la imagen.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct ImageDto {
    /// URL de la imagen.
    pub url: String,
    /// Página del archivo de la imagen.
    pub page_url: String,
    /// Autor, o `null` si no se conoce.
    #[schema(required = true)]
    pub author: Option<String>,
    /// Licencia de la imagen.
    pub license: String,
    /// URL de la licencia, o `null` si no existe.
    #[schema(required = true)]
    pub license_url: Option<String>,
    /// Si hay que mostrar la atribución al usar la imagen.
    pub attribution_required: bool,
}

impl From<Image> for ImageDto {
    fn from(i: Image) -> Self {
        Self {
            url: i.url,
            page_url: i.page_url,
            author: i.author,
            license: i.license,
            license_url: i.license_url,
            attribution_required: i.attribution_required,
        }
    }
}

/// Crédito de un dataset que respalda los datos de la planta. Es neutral: no dice qué campo proviene de él.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct CreditDto {
    /// Nombre legible del dataset.
    pub name: String,
    /// Licencia, en texto.
    pub license: String,
    /// URL de la licencia, o `null` si la fuente no tiene una.
    #[schema(required = true)]
    pub license_url: Option<String>,
    /// Atribución exigida por la licencia.
    pub attribution: String,
    /// Página del dataset o, si la descripción resume un artículo, enlace a ese artículo; `null` si no existe.
    #[schema(required = true)]
    pub url: Option<String>,
}

impl From<Credit> for CreditDto {
    fn from(c: Credit) -> Self {
        Self {
            name: c.name,
            license: c.license,
            license_url: c.license_url,
            attribution: c.attribution,
            url: c.url,
        }
    }
}

/// Detalle completo de una planta.
///
/// Los campos consolidados están siempre presentes: con `null` o lista vacía cuando la planta no tiene el dato.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct PlantDto {
    /// Identificador público.
    pub id: String,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Nombre para mostrar: un nombre común en español o, si la planta no tiene ninguno, el nombre científico.
    pub display_name: String,
    /// Familia, o `null` si ninguna fuente la aporta.
    pub family: Option<String>,
    /// Nombres de la planta.
    pub names: Vec<NameDto>,
    /// Partes de la planta.
    pub parts: Vec<PartDto>,
    /// Usos de la planta (una fila por referencia resuelta); su cita es la etiqueta de la referencia.
    pub uses: Vec<UseDto>,
    /// Nombres científicos distintos del aceptado, ordenados por texto.
    pub synonyms: Vec<String>,
    /// Descripción neutra, o `null`.
    #[schema(required = true)]
    pub description: Option<String>,
    /// Origen, o `null`.
    #[schema(required = true)]
    pub origin: Option<String>,
    /// Aceite de la planta, o `null`.
    #[schema(required = true)]
    pub oil: Option<OilDto>,
    /// Grupos de uso tradicional, por número de registros descendente y actividad, con la cita completa.
    pub use_groups: Vec<UseGroupDto>,
    /// Objetivos registrados, por nombre.
    pub goals: Vec<GoalDto>,
    /// Precauciones, o `null` solo cuando no hay ningún dato (lo que no significa que la planta sea segura).
    #[schema(required = true)]
    pub safety: Option<SafetyDto>,
    /// Imagen con su licencia, o `null`.
    #[schema(required = true)]
    pub image: Option<ImageDto>,
    /// Datasets que respaldan los datos de la planta, sin repeticiones y ordenados por nombre; no indica qué dato viene de cuál.
    pub credits: Vec<CreditDto>,
}

impl From<Plant> for PlantDto {
    fn from(p: Plant) -> Self {
        Self {
            id: p.id.0,
            scientific_name: p.scientific_name,
            display_name: p.display_name,
            family: p.family,
            names: p.names.into_iter().map(Into::into).collect(),
            parts: p.parts.into_iter().map(Into::into).collect(),
            uses: p.uses.into_iter().map(Into::into).collect(),
            synonyms: p.synonyms,
            description: p.description,
            origin: p.origin,
            oil: p.oil_type.map(|oil_type| OilDto { oil_type }),
            use_groups: p.use_groups.into_iter().map(Into::into).collect(),
            goals: p.goals.into_iter().map(Into::into).collect(),
            safety: p.safety.map(Into::into),
            image: p.image.map(Into::into),
            credits: p.credits.into_iter().map(Into::into).collect(),
        }
    }
}

/// Subárea de un objetivo con sus plantas visibles.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct SubareaSummaryDto {
    /// Identificador de la subárea, por ejemplo `digestion`.
    pub id: String,
    /// Nombre en español.
    pub name: String,
    /// Plantas distintas visibles en la subárea; coincide con el `total` de sus resultados.
    pub plant_count: u64,
}

impl From<SubareaSummary> for SubareaSummaryDto {
    fn from(s: SubareaSummary) -> Self {
        Self {
            id: s.id,
            name: s.name,
            plant_count: s.plant_count,
        }
    }
}

/// Objetivo del catálogo con su conteo de plantas visibles.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct GoalSummaryDto {
    /// Identificador del objetivo, por ejemplo `mejorar-el-sueno`.
    pub id: String,
    /// Nombre en español.
    pub name: String,
    /// Plantas distintas visibles; coincide con el `total` de sus resultados y, si hay subáreas, es la unión sin repetir plantas.
    pub plant_count: u64,
    /// Subáreas con plantas visibles, en su orden de presentación; vacía si el objetivo no tiene.
    pub subareas: Vec<SubareaSummaryDto>,
}

impl From<GoalSummary> for GoalSummaryDto {
    fn from(g: GoalSummary) -> Self {
        Self {
            id: g.id,
            name: g.name,
            plant_count: g.plant_count,
            subareas: g.subareas.into_iter().map(Into::into).collect(),
        }
    }
}

/// Objetivo al que pertenecen los resultados.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct GoalRefDto {
    /// Identificador del objetivo.
    pub id: String,
    /// Nombre en español.
    pub name: String,
}

impl From<IdName> for GoalRefDto {
    fn from(g: IdName) -> Self {
        Self {
            id: g.id,
            name: g.name,
        }
    }
}

/// Subárea por la que se filtraron los resultados.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct SubareaRefDto {
    /// Identificador de la subárea.
    pub id: String,
    /// Nombre en español.
    pub name: String,
}

impl From<IdName> for SubareaRefDto {
    fn from(s: IdName) -> Self {
        Self {
            id: s.id,
            name: s.name,
        }
    }
}

/// Planta de un objetivo, con lo que necesita una tarjeta de resultados.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct GoalPlantDto {
    /// Identificador público.
    pub id: String,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Nombre para mostrar: un nombre común en español o, si la planta no tiene ninguno, el nombre científico.
    pub display_name: String,
    /// Nombres comunes con su idioma, como en el listado.
    pub common_names: Vec<CommonNameDto>,
    /// Familia, o `null` si ninguna fuente la aporta.
    pub family: Option<String>,
    /// Nombres en español de las áreas de la EMA que respaldan a la planta en ese objetivo o subárea. Algunas unen dos áreas con «; » y se muestran tal cual.
    pub areas: Vec<String>,
    /// Nivel de precaución (`alto`, `medio` o `bajo`), o `null` si no hay datos o si las precauciones no tienen nivel.
    #[schema(required = true)]
    pub safety_level: Option<SafetyLevelDto>,
    /// Si la planta tiene datos de precauciones, aunque no tengan nivel.
    pub has_safety: bool,
    /// Imagen con su licencia, el mismo objeto del detalle, o `null`.
    #[schema(required = true)]
    pub image: Option<ImageDto>,
}

impl From<GoalPlant> for GoalPlantDto {
    fn from(p: GoalPlant) -> Self {
        Self {
            id: p.id.0,
            scientific_name: p.scientific_name,
            display_name: p.display_name,
            common_names: p
                .common_names
                .into_iter()
                .map(|n| CommonNameDto {
                    text: n.text,
                    language: n.language,
                })
                .collect(),
            family: p.family,
            areas: p.areas,
            safety_level: p.safety_level.map(Into::into),
            has_safety: p.has_safety,
            image: p.image.map(Into::into),
        }
    }
}

/// Página de plantas de un objetivo.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct GoalPlantsPageDto {
    /// Objetivo pedido.
    pub goal: GoalRefDto,
    /// Subárea pedida, o `null` si no se filtró por una.
    #[schema(required = true)]
    pub subarea: Option<SubareaRefDto>,
    /// Plantas de la página.
    pub items: Vec<GoalPlantDto>,
    /// Total de plantas visibles, independiente de la página.
    pub total: u64,
    /// Límite aplicado.
    pub limit: u32,
    /// Desplazamiento aplicado.
    pub offset: u32,
}

impl GoalPlantsPageDto {
    /// Convierte la página del dominio, anotando el `limit` y el `offset` con que se pidió.
    pub fn from_domain(plants: GoalPlants, limit: u32, offset: u32) -> Self {
        Self {
            goal: plants.goal.into(),
            subarea: plants.subarea.map(Into::into),
            items: plants.page.items.into_iter().map(Into::into).collect(),
            total: plants.page.total,
            limit,
            offset,
        }
    }
}

/// Cuerpo de error `application/problem+json` (RFC 9457).
#[derive(Debug, Clone, Serialize, ToSchema)]
pub struct ProblemDto {
    /// URI que identifica el tipo de problema; siempre `about:blank`.
    // `type` es palabra reservada en Rust: el campo se llama distinto y serde lo renombra en el JSON.
    #[serde(rename = "type")]
    pub problem_type: String,
    /// Resumen corto del problema (el texto estándar del código HTTP).
    pub title: String,
    /// Código de estado HTTP.
    pub status: u16,
    /// Explicación específica de esta ocurrencia; en los 500 es siempre genérica.
    pub detail: String,
    /// Ruta pedida, cuando aplica.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub instance: Option<String>,
    /// Parámetro afectado, en los errores 400 (extensión de RFC 9457).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub param: Option<String>,
}
