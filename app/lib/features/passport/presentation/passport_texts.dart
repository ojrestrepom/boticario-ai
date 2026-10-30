/// Fixed texts of the passport tabs, including `Fuentes`. They live
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
  static const highLevelNoticeTitle = 'Precauciones de nivel alto';
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

  // Usos.
  /// Provisional text (the user will adjust it in the app); see the
  /// `plant-passport` spec, "Usos como registros tradicionales trazables".
  static const usesNotice =
      'Usos registrados en fuentes etnobotánicas históricas. No son '
      'recomendaciones ni están comprobados clínicamente. Algunas citas no '
      'se pudieron identificar y se muestran como «sin resolver». Las '
      'explicaciones de términos son definiciones generales de diccionario o '
      'enciclopedia, no afirmaciones sobre esta planta.';
  static const noUses =
      'No hay usos tradicionales con referencia verificable disponibles';
  static const hideCitations = 'Ocultar citas';
  static const unresolvedSuffix = '(sin resolver)';

  /// Gray label above the explanation of a use group's term. It says the word
  /// is explained in general, not what the plant does.
  static const glossaryLabel = 'Significado general del término';
  static const glossaryOpenQuote = '«';
  static const glossaryCloseQuote = '»';

  /// Precedes the linked source when the text paraphrases it.
  static const glossaryAdaptedFrom = 'adaptado de';
  static const glossarySourceDestination = 'la fuente de la explicación';

  /// Data line of a use group: the places after `Lugares: `, as they arrive
  /// (`Lugares: China, Trinidad`), or null when the group has no countries.
  static String? useGroupPlaces(List<String> countries) =>
      countries.isEmpty ? null : 'Lugares: ${countries.join(', ')}';

  /// Visible label of the collapsed citations control.
  static String showCitations(int count) =>
      count == 1 ? 'Ver 1 cita' : 'Ver $count citas';

  /// Semantic labels of the citations control: the visible text plus the
  /// activity, so repeated controls can be told apart.
  static String showCitationsSemantics(int count, String activity) =>
      '${showCitations(count)} de $activity';
  static String hideCitationsSemantics(String activity) =>
      '$hideCitations de $activity';

  // Fuentes.
  static const sourcesTitle = 'Fuentes';
  static const sourcesIntro =
      'Los datos se reúnen de fuentes abiertas y cada fuente conserva su '
      'licencia.';
  static const noSources = 'No hay fuentes registradas para esta planta';
  static const imageSourceTitle = 'Imagen';
  static const licensePrefix = 'Licencia';
  static const attributionPrefix = 'Atribución';
  static const authorPrefix = 'Autor';
  static const imageFileLinkLabel = 'Archivo en Wikimedia Commons';

  // Enlaces y pie de la imagen.
  static const photoPrefix = 'Foto';
  static const commonsName = 'Wikimedia Commons';
  static const linkNotOpened = 'No se pudo abrir el enlace';
  static const linkCopied = 'Enlace copiado';

  // Destinos de los enlaces, para lectores de pantalla (nunca la URL).
  static const sourcePageDestination = 'la página de la fuente';
  static const licenseTextDestination = 'el texto de la licencia';
  static const imageFileDestination =
      'la página del archivo en Wikimedia Commons';
  static String linkSemantics(String text, String destination) =>
      '$text. Abre $destination';
  static String imageDescription(String plantName) =>
      'Fotografía de $plantName';

  static const levelHigh = 'Alto';
  static const levelMedium = 'Medio';
  static const levelLow = 'Bajo';

  /// Every fixed text of the passport, for the effect-language
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
    usesNotice,
    noUses,
    hideCitations,
    unresolvedSuffix,
    glossaryLabel,
    glossaryOpenQuote,
    glossaryCloseQuote,
    glossaryAdaptedFrom,
    glossarySourceDestination,
    sourcesTitle,
    sourcesIntro,
    noSources,
    imageSourceTitle,
    licensePrefix,
    attributionPrefix,
    authorPrefix,
    imageFileLinkLabel,
    photoPrefix,
    commonsName,
    linkNotOpened,
    linkCopied,
    sourcePageDestination,
    licenseTextDestination,
    imageFileDestination,
  ];
}
