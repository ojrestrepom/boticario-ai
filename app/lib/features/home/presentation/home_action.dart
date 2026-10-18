/// Los 11 controles de la pantalla Inicio con su mensaje de depuración.
enum HomeAction {
  /// Icono de menú de la cabecera.
  headerMenu,

  /// Icono de persona de la cabecera.
  headerProfile,

  /// Tarjeta `Explorar plantas y aceites`.
  explorePlantsAndOils,

  /// Tarjeta `Buscar por objetivo`.
  searchByGoal,

  /// Tarjeta `Identificar con cámara`.
  identifyWithCamera,

  /// Tarjeta `Formular mezclas`.
  formulateBlends,

  /// CTA `Preguntar al Boticario`.
  askTheBoticario,

  /// Pestaña `Inicio`.
  tabHome,

  /// Pestaña `Favoritos`.
  tabFavorites,

  /// Pestaña `Historial`.
  tabHistory,

  /// Pestaña `Perfil`.
  tabProfile,
}

/// Calcula el mensaje exacto de [action] o `null` si el modo no lo permite.
///
/// Función pura: no imprime, no navega y no muta estado. El llamador decide
/// emitir el resultado con `debugPrint`; producción pasa únicamente
/// `kDebugMode`, por lo que fuera de depuración el cálculo es silencioso.
String? homeActionMessage(HomeAction action, {required bool isDebugMode}) {
  if (!isDebugMode) {
    return null;
  }

  return switch (action) {
    HomeAction.headerMenu => '[Home] Cabecera: Menú',
    HomeAction.headerProfile => '[Home] Cabecera: Perfil',
    HomeAction.explorePlantsAndOils => '[Home] Explorar plantas y aceites',
    HomeAction.searchByGoal => '[Home] Buscar por objetivo',
    HomeAction.identifyWithCamera => '[Home] Identificar con cámara',
    HomeAction.formulateBlends => '[Home] Formular mezclas',
    HomeAction.askTheBoticario => '[Home] Preguntar al Boticario',
    HomeAction.tabHome => '[Home] Pestaña: Inicio',
    HomeAction.tabFavorites => '[Home] Pestaña: Favoritos',
    HomeAction.tabHistory => '[Home] Pestaña: Historial',
    HomeAction.tabProfile => '[Home] Pestaña: Perfil',
  };
}
