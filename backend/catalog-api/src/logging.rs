//! Decisión de color de los logs.

/// Indica si los logs deben llevar secuencias ANSI de color.
///
/// Solo hay color si stdout es una terminal y `NO_COLOR` no tiene un valor no vacío (<https://no-color.org/>).
/// Se reproduce a mano la regla de `NO_COLOR` porque `with_ansi(true)` la sobrescribiría.
pub fn use_ansi(stdout_is_terminal: bool, no_color: Option<&str>) -> bool {
    stdout_is_terminal && no_color.is_none_or(str::is_empty)
}

#[cfg(test)]
mod tests {
    use super::use_ansi;

    #[test]
    fn color_only_in_a_terminal_without_no_color() {
        assert!(use_ansi(true, None));
        assert!(use_ansi(true, Some("")));
        assert!(!use_ansi(true, Some("1")));
    }

    #[test]
    fn never_color_outside_a_terminal() {
        assert!(!use_ansi(false, None));
        assert!(!use_ansi(false, Some("")));
        assert!(!use_ansi(false, Some("1")));
    }
}
