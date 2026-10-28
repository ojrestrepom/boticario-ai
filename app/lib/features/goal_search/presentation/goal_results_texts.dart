/// Fixed texts of P07 («Recomendaciones»). They live here, in one place, so
/// a test can scan them for effect language.
abstract final class GoalResultsTexts {
  static const title = 'Recomendaciones';
  static String subtitle(String name) => 'Para: $name';

  static const notice =
      'Estas recomendaciones se basan en información especializada. '
      'Consulta detalles y precauciones.';

  static const moreDetails = 'Ver más detalles';
  static const sheetTitle = 'Sobre estas recomendaciones';
  static const sheetClose = 'Cerrar';

  /// Fixed body of the «Ver más detalles» sheet: the basis and the limits of
  /// the list. It does not depend on the registry.
  static const sheetBody =
      'Las plantas que ves aquí son las que la Agencia Europea de '
      'Medicamentos (EMA) registra en el área indicada en cada tarjeta. '
      'Esta información no es un consejo médico ni una dosis. '
      'La marca de precaución señala advertencias de seguridad del '
      'registro. '
      'El detalle y las citas están en el pasaporte de cada planta. '
      'Consulta a un profesional de la salud antes de usar cualquier planta.';

  static const loading = 'Cargando recomendaciones';
  static const loadingMore = 'Cargando más resultados';
  static const endOfList = 'No hay más resultados';
  static const empty =
      'Aún no hay plantas con información registrada para este objetivo';
  static const notFound = 'Objetivo no encontrado';
  static const retry = 'Reintentar';

  static const caution = 'Precaución';
  static const noSafetyData =
      'Sin datos de precauciones (esto no significa que sea segura)';

  /// `La EMA la registra en: A, B y N más`: up to two areas as they come.
  static String emaLine(List<String> areas) {
    final shown = areas.take(2).join(', ');
    final more = areas.length - 2;
    return 'La EMA la registra en: $shown${more > 0 ? ' y $more más' : ''}';
  }

  /// Short attribution next to a loaded photo.
  static String photoCredit(String? author, String license) =>
      'Foto: ${author ?? 'autor no disponible'} · $license';
}
