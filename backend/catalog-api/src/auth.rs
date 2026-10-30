//! Tokens de API: validación de la configuración y comparación en tiempo constante.
//!
//! Los tokens nunca se imprimen: `ApiTokens` no implementa `Display`, su `Debug` solo muestra cuántos hay y sus errores no incluyen el valor ofrecido.

use std::error::Error;
use std::fmt;

use std::sync::Arc;

use axum::extract::{Request, State};
use axum::http::header::AUTHORIZATION;
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};
use subtle::{Choice, ConstantTimeEq};

use crate::error::ApiError;

/// Longitud mínima de un token, en caracteres.
pub const MIN_TOKEN_LEN: usize = 32;
/// Longitud máxima de un token, en caracteres.
pub const MAX_TOKEN_LEN: usize = 256;

/// Lista validada de tokens de API aceptados.
#[derive(Clone, PartialEq, Eq)]
pub struct ApiTokens(Vec<String>);

/// Motivo por el que un valor de `API_TOKENS` es inválido.
///
/// Los números de elemento empiezan en 1. Ninguna variante contiene el valor ofrecido.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ApiTokensError {
    /// El valor está vacío o solo tiene espacios.
    Empty,
    /// Hay un elemento vacío en la lista (por ejemplo `a,,b`).
    EmptyElement(usize),
    /// Un token tiene menos de [`MIN_TOKEN_LEN`] caracteres.
    TooShort(usize),
    /// Un token tiene más de [`MAX_TOKEN_LEN`] caracteres.
    TooLong(usize),
    /// Un token tiene un carácter fuera de `token68`.
    InvalidChar(usize),
}

impl fmt::Display for ApiTokensError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => write!(
                f,
                "API_TOKENS está vacía; define uno o más tokens separados por comas"
            ),
            Self::EmptyElement(n) => write!(
                f,
                "API_TOKENS tiene un elemento vacío en la posición {n}; quita las comas sobrantes"
            ),
            Self::TooShort(n) => write!(
                f,
                "API_TOKENS: el token {n} es demasiado corto; la longitud mínima es {MIN_TOKEN_LEN} caracteres"
            ),
            Self::TooLong(n) => write!(
                f,
                "API_TOKENS: el token {n} es demasiado largo; la longitud máxima es {MAX_TOKEN_LEN} caracteres"
            ),
            Self::InvalidChar(n) => write!(
                f,
                "API_TOKENS: el token {n} tiene un carácter no permitido; solo se admiten letras, dígitos y -._~+/"
            ),
        }
    }
}

impl Error for ApiTokensError {}

impl fmt::Debug for ApiTokens {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "ApiTokens({} tokens)", self.0.len())
    }
}

fn is_token68_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || matches!(c, '-' | '.' | '_' | '~' | '+' | '/')
}

impl ApiTokens {
    /// Valida la lista separada por comas de `API_TOKENS`.
    ///
    /// Se ignora el espacio en blanco alrededor de cada token (incluido el salto de línea final).
    pub fn parse(value: &str) -> Result<Self, ApiTokensError> {
        if value.trim().is_empty() {
            return Err(ApiTokensError::Empty);
        }
        let mut tokens = Vec::new();
        for (i, raw) in value.split(',').enumerate() {
            let n = i + 1;
            let token = raw.trim();
            if token.is_empty() {
                return Err(ApiTokensError::EmptyElement(n));
            }
            if !token.chars().all(is_token68_char) {
                return Err(ApiTokensError::InvalidChar(n));
            }
            // Solo hay caracteres ASCII, así que los bytes son los caracteres.
            if token.len() < MIN_TOKEN_LEN {
                return Err(ApiTokensError::TooShort(n));
            }
            if token.len() > MAX_TOKEN_LEN {
                return Err(ApiTokensError::TooLong(n));
            }
            tokens.push(token.to_string());
        }
        Ok(Self(tokens))
    }

    /// Cuántos tokens hay configurados.
    pub fn len(&self) -> usize {
        self.0.len()
    }

    /// Siempre `false`: la validación exige al menos un token.
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }

    /// Indica si `candidate` coincide con algún token configurado.
    ///
    /// Compara con todos los tokens, sin cortocircuito, con `subtle::ConstantTimeEq`: el tiempo no depende de en qué posición difiere el candidato. `subtle` compara antes las longitudes, así que la longitud sí puede filtrarse; no importa porque el formato y la cota inferior son públicos.
    pub fn contains(&self, candidate: &[u8]) -> bool {
        let mut found = Choice::from(0);
        for token in &self.0 {
            found |= token.as_bytes().ct_eq(candidate);
        }
        found.into()
    }
}

/// Clase del fallo de autorización. Solo se registra; el cliente recibe siempre la misma respuesta.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AuthFailure {
    /// No hay cabecera `Authorization`.
    Missing,
    /// La cabecera no es válida o usa otro esquema que `Bearer`.
    Scheme,
    /// Esquema `Bearer`, pero el token falta o no coincide con ninguno.
    Mismatch,
}

impl AuthFailure {
    fn as_str(self) -> &'static str {
        match self {
            Self::Missing => "ausente",
            Self::Scheme => "esquema distinto",
            Self::Mismatch => "no coincide",
        }
    }
}

/// Indica si el camino pertenece a `/v1`: exactamente `/v1` o `/v1/...`.
fn is_protected(path: &str) -> bool {
    path == "/v1" || path.starts_with("/v1/")
}

/// Extrae el token de un valor `Authorization: Bearer <token>` (el esquema no distingue mayúsculas).
fn bearer_token(value: &str) -> Result<&str, AuthFailure> {
    let (scheme, rest) = value.split_once(' ').unwrap_or((value, ""));
    if !scheme.eq_ignore_ascii_case("Bearer") {
        return Err(AuthFailure::Scheme);
    }
    Ok(rest.trim_start_matches(' '))
}

fn authorize(headers: &axum::http::HeaderMap, tokens: &ApiTokens) -> Result<(), AuthFailure> {
    let value = headers.get(AUTHORIZATION).ok_or(AuthFailure::Missing)?;
    // Un valor que no es texto ASCII visible no puede ser un token válido.
    let value = value.to_str().map_err(|_| AuthFailure::Scheme)?;
    let token = bearer_token(value)?;
    if !token.is_empty() && tokens.contains(token.as_bytes()) {
        Ok(())
    } else {
        Err(AuthFailure::Mismatch)
    }
}

/// Middleware que exige un token de API válido a todo camino bajo `/v1`, antes del enrutado.
///
/// Registra el fallo a nivel `debug` con su clase, nunca con la cabecera ni el valor.
pub async fn require_token(
    State(tokens): State<Arc<ApiTokens>>,
    request: Request,
    next: Next,
) -> Response {
    let path = request.uri().path();
    if is_protected(path)
        && let Err(failure) = authorize(request.headers(), &tokens)
    {
        tracing::debug!(reason = failure.as_str(), path, "petición no autorizada");
        return ApiError::Unauthorized
            .into_response_at(request.uri())
            .into_response();
    }
    next.run(request).await
}

#[cfg(test)]
mod tests {
    use super::*;

    // Valores ficticios de prueba; no son secretos.
    const TOKEN_A: &str = "test-token-not-a-secret-aaaaaaaaaaaaaaaa";
    const TOKEN_B: &str = "test-token-not-a-secret-bbbbbbbbbbbbbbbb";
    const HEX_64: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    #[test]
    fn single_valid_token() {
        let tokens = ApiTokens::parse(HEX_64).unwrap();
        assert_eq!(tokens.len(), 1);
        assert!(tokens.contains(HEX_64.as_bytes()));
    }

    #[test]
    fn several_tokens_with_spaces_and_trailing_newline() {
        let tokens = ApiTokens::parse(&format!("{TOKEN_A} , {TOKEN_B}\n")).unwrap();
        assert_eq!(tokens.len(), 2);
        assert!(tokens.contains(TOKEN_A.as_bytes()));
        assert!(tokens.contains(TOKEN_B.as_bytes()));
        let tokens = ApiTokens::parse(&format!("{TOKEN_A},{TOKEN_B}\r\n")).unwrap();
        assert_eq!(tokens.len(), 2);
    }

    #[test]
    fn empty_or_blank_value() {
        for value in ["", "   ", "\n", " \t\r\n"] {
            assert_eq!(ApiTokens::parse(value), Err(ApiTokensError::Empty));
        }
    }

    #[test]
    fn length_bounds() {
        let at = |len: usize| "a".repeat(len);
        assert_eq!(ApiTokens::parse(&at(31)), Err(ApiTokensError::TooShort(1)));
        assert!(ApiTokens::parse(&at(32)).is_ok());
        assert!(ApiTokens::parse(&at(256)).is_ok());
        assert_eq!(ApiTokens::parse(&at(257)), Err(ApiTokensError::TooLong(1)));
        // El segundo elemento es el corto.
        assert_eq!(
            ApiTokens::parse(&format!("{TOKEN_A},{}", at(5))),
            Err(ApiTokensError::TooShort(2))
        );
    }

    #[test]
    fn empty_elements() {
        for value in [
            format!("{TOKEN_A},,{TOKEN_B}"),
            format!("{TOKEN_A},"),
            format!(",{TOKEN_A}"),
            format!("{TOKEN_A}, ,{TOKEN_B}"),
        ] {
            assert!(
                matches!(
                    ApiTokens::parse(&value),
                    Err(ApiTokensError::EmptyElement(_))
                ),
                "{value}"
            );
        }
    }

    #[test]
    fn disallowed_characters() {
        for bad in ['=', ' ', '"', '!', 'é', '\u{0}', '\\', ':'] {
            let value = format!("test-token-not-a-secret-{bad}aaaaaaaaaaaaaaaa");
            assert_eq!(
                ApiTokens::parse(&value),
                Err(ApiTokensError::InvalidChar(1)),
                "{bad:?}"
            );
        }
        // Todos los símbolos permitidos.
        assert!(ApiTokens::parse("-._~+/-._~+/AZaz09-._~+/-._~+/AZaz09").is_ok());
    }

    #[test]
    fn debug_and_errors_do_not_show_values() {
        let tokens = ApiTokens::parse(&format!("{TOKEN_A},{TOKEN_B}")).unwrap();
        let debug = format!("{tokens:?}");
        assert_eq!(debug, "ApiTokens(2 tokens)");
        assert!(!debug.contains("not-a-secret"));

        let short = "short-not-a-secret";
        for value in [short, "not-a-secret-=-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"] {
            let text = ApiTokens::parse(value).unwrap_err().to_string();
            assert!(!text.contains("not-a-secret"), "{text}");
            assert!(text.contains("API_TOKENS"), "{text}");
        }
        let too_short = ApiTokens::parse(short).unwrap_err().to_string();
        assert!(too_short.contains("32"), "{too_short}");
    }

    #[test]
    fn contains_matches_first_last_and_none() {
        let tokens = ApiTokens::parse(&format!("{TOKEN_A},{TOKEN_B}")).unwrap();
        assert!(tokens.contains(TOKEN_A.as_bytes()));
        assert!(tokens.contains(TOKEN_B.as_bytes()));
        assert!(!tokens.contains(b"test-token-not-a-secret-cccccccccccccccc"));
        assert!(!tokens.contains(b""));
    }

    #[test]
    fn contains_rejects_prefix_last_char_difference_and_other_length() {
        let tokens = ApiTokens::parse(TOKEN_A).unwrap();
        let bytes = TOKEN_A.as_bytes();
        assert!(!tokens.contains(&bytes[..bytes.len() - 1]));
        assert!(!tokens.contains(&bytes[..MIN_TOKEN_LEN - 1]));
        let mut last_differs = bytes.to_vec();
        *last_differs.last_mut().unwrap() = b'z';
        assert!(!tokens.contains(&last_differs));
        let mut longer = bytes.to_vec();
        longer.push(b'a');
        assert!(!tokens.contains(&longer));
    }
}
