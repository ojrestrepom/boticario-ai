//! Tipos de respuesta de la API (DTOs), separados del dominio.
//!
//! El dominio de `catalog-core` no conoce JSON; aquí se define la forma exacta del contrato HTTP y se convierte desde el dominio.
//! `rename_all = "camelCase"` hace que los campos Rust (`scientific_name`) salgan como `scientificName`.
//! Todos los DTOs viven en este módulo y derivan `ToSchema`: de ellos sale el documento OpenAPI, así que el contrato HTTP se define en un solo sitio.

use catalog_core::domain::{NameKind, Page, Part, Plant, PlantName, PlantSummary, Use};
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
    /// Nombres comunes con su idioma.
    pub common_names: Vec<CommonNameDto>,
    /// Familia, o `null` si ninguna fuente la aporta.
    pub family: Option<String>,
}

impl From<PlantSummary> for PlantSummaryDto {
    fn from(p: PlantSummary) -> Self {
        Self {
            id: p.id.0,
            scientific_name: p.scientific_name,
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

/// Detalle completo de una planta.
#[derive(Debug, Clone, Serialize, ToSchema)]
#[serde(rename_all = "camelCase")]
pub struct PlantDto {
    /// Identificador público.
    pub id: String,
    /// Nombre científico canónico.
    pub scientific_name: String,
    /// Familia, o `null` si ninguna fuente la aporta.
    pub family: Option<String>,
    /// Nombres de la planta.
    pub names: Vec<NameDto>,
    /// Partes de la planta.
    pub parts: Vec<PartDto>,
    /// Usos de la planta.
    pub uses: Vec<UseDto>,
}

impl From<Plant> for PlantDto {
    fn from(p: Plant) -> Self {
        Self {
            id: p.id.0,
            scientific_name: p.scientific_name,
            family: p.family,
            names: p.names.into_iter().map(Into::into).collect(),
            parts: p.parts.into_iter().map(Into::into).collect(),
            uses: p.uses.into_iter().map(Into::into).collect(),
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
