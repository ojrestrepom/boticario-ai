/// Fixed texts of the passport tabs `General` and `Propiedades`. They live
/// here, in one place, so a test can scan them for effect language.
abstract final class PassportTexts {
  static const notAvailable = 'No disponible en fuente';

  // General.
  static const commonNameLabel = 'Nombre común';
  static const noSpanishCommonName =
      'No hay nombre común en español registrado';
  static const synonymsLabel = 'Sinónimos';
  static const noSynonyms = 'No hay sinónimos registrados';
  static const familyLabel = 'Familia';
  static const originLabel = 'Origen';
  static const partLabel = 'Parte utilizada';
  static const noParts = 'No hay partes registradas en fuente';
  static const oilLabel = 'Tipo de aceite';
  static const descriptionLabel = 'Descripción';
  static const otherCommonNamesLabel = 'Otros nombres comunes';
  static const noCommonNames = 'No hay nombres comunes registrados';
  static const highLevelNoticeTitle = 'Precauciones de nivel Alto';
  static const highLevelNoticeBody =
      'Consulta las precauciones de esta planta en la pestaña Propiedades.';

  // Propiedades.
  static const goalsTitle = 'Objetivos registrados por la EMA';
  static const noGoals =
      'No hay objetivos registrados por la EMA para esta planta';
  static const goalDisclaimer =
      'Clasificación de la Agencia Europea de Medicamentos (EMA), no una '
      'indicación de uso ni una promesa de eficacia.';
  static const subareaLabel = 'Subárea';
  static const areaLabel = 'Área';
  static const documentTypeLabel = 'Tipo de documento';
  static const citationsLabel = 'Citas';
  static const safetyTitle = 'Precauciones';
  static const safetyLevelLabel = 'Nivel';
  static const noSafety =
      'No hay precauciones registradas en las fuentes consultadas. '
      'Esto no significa que la planta sea segura.';

  static const levelHigh = 'Alto';
  static const levelMedium = 'Medio';
  static const levelLow = 'Bajo';

  /// Every fixed text of `General` and `Propiedades`, for the effect-language
  /// scan.
  static const all = <String>[
    notAvailable,
    commonNameLabel,
    noSpanishCommonName,
    synonymsLabel,
    noSynonyms,
    familyLabel,
    originLabel,
    partLabel,
    noParts,
    oilLabel,
    descriptionLabel,
    otherCommonNamesLabel,
    noCommonNames,
    highLevelNoticeTitle,
    highLevelNoticeBody,
    goalsTitle,
    noGoals,
    goalDisclaimer,
    subareaLabel,
    areaLabel,
    documentTypeLabel,
    citationsLabel,
    safetyTitle,
    safetyLevelLabel,
    noSafety,
    levelHigh,
    levelMedium,
    levelLow,
  ];
}
