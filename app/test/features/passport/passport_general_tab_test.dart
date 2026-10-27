import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:flutter_test/flutter_test.dart';

import 'passport_test_support.dart';

Plant _plant({
  String? displayName,
  String scientificName = 'Planta sintetica',
  List<PlantName> names = const [],
  PlantSafety? safety,
}) => Plant(
  id: 'planta-sintetica',
  scientificName: scientificName,
  displayName: displayName,
  family: null,
  names: names,
  parts: const [],
  uses: const [],
  safety: safety,
);

PlantSafety _safety(SafetyLevel? level) => PlantSafety(
  level: level,
  text: 'Texto de advertencia',
  references: const [],
);

void main() {
  const noticeTitle = 'Precauciones de nivel Alto';

  testWidgets('Campos de P05 presentes', (tester) async {
    await showPassport(tester, consolidatedPlant('lavandula-angustifolia'));
    expect(find.text('Nombre común'), findsOneWidget);
    expect(find.text('Lavanda'), findsWidgets);
    expect(find.text('Origen'), findsOneWidget);
    expect(find.text('Sureste y suroeste de Europa.'), findsOneWidget);
    expect(find.text('Parte utilizada'), findsOneWidget);
    expect(find.text('Flor'), findsOneWidget);
    expect(find.text('Tipo de aceite'), findsOneWidget);
    expect(find.text('Esencial'), findsOneWidget);
    expect(find.text('Descripción'), findsOneWidget);
    expect(find.text('No aplicable: ficha de planta'), findsNothing);
  });

  testWidgets('Datos generales ausentes', (tester) async {
    await showPassport(tester, _plant());
    // Familia, origen, tipo de aceite and descripción.
    expect(find.text('No disponible en fuente'), findsNWidgets(4));
    expect(find.text('Esencial'), findsNothing);
  });

  testWidgets('Parte registrada', (tester) async {
    await showPassport(tester, consolidatedPlant('agrimonia-eupatoria'));
    expect(find.text('Parte utilizada'), findsOneWidget);
    expect(find.text('Parte aérea'), findsOneWidget);
    expect(find.textContaining('recomend'), findsNothing);
  });

  testWidgets('Familia y nombres comunes', (tester) async {
    await showPassport(tester, consolidatedPlant('lavandula-angustifolia'));
    expect(find.text('Lamiaceae'), findsOneWidget);
    expect(find.text('Sinónimos'), findsOneWidget);
    expect(find.text('Otros nombres comunes'), findsOneWidget);
    expect(find.text('English Lavender (en)'), findsOneWidget);
    expect(find.text('Echter Lavendel (de)'), findsOneWidget);
    // The display name is `Nombre común`, not repeated among the others.
    expect(find.text('Lavanda (es)'), findsNothing);

    await showPassport(tester, consolidatedPlant('blighia-sapida'));
    expect(find.text('Cupania sapida'), findsOneWidget);
    expect(find.text('Akee (en)'), findsOneWidget);
  });

  testWidgets('Sin partes ni nombres comunes', (tester) async {
    await showPassport(tester, consolidatedPlant('acinos-sp'));
    expect(find.text('No hay partes registradas en fuente'), findsOneWidget);
    expect(find.text('No hay sinónimos registrados'), findsOneWidget);
    expect(find.text('No hay nombres comunes registrados'), findsOneWidget);
  });

  testWidgets('Planta sin nombre en español', (tester) async {
    await showPassport(tester, consolidatedPlant('acinos-sp'));
    expect(
      find.text('No hay nombre común en español registrado'),
      findsOneWidget,
    );
    // The scientific name is only in the header, never as `Nombre común`.
    expect(find.text('Acinos sp'), findsOneWidget);

    // With common names in other languages: they stay listed with language.
    await showPassport(
      tester,
      _plant(
        displayName: 'Planta sintetica',
        names: const [
          PlantName(
            text: 'Velvetleaf',
            kind: PlantNameKind.common,
            language: 'en',
          ),
        ],
      ),
    );
    expect(
      find.text('No hay nombre común en español registrado'),
      findsOneWidget,
    );
    expect(find.text('Velvetleaf (en)'), findsOneWidget);
    expect(find.text('No hay nombres comunes registrados'), findsNothing);
  });

  testWidgets('Aviso de nivel alto', (tester) async {
    await showPassport(tester, consolidatedPlant('blighia-sapida'));
    expect(find.text(noticeTitle), findsOneWidget);
    expect(find.textContaining('Propiedades'), findsWidgets);
    expect(find.textContaining('pestaña Propiedades'), findsOneWidget);
  });

  testWidgets('Sin aviso para otros niveles', (tester) async {
    // Medium (lavender), null level (eucalyptus) and no safety (acinos).
    for (final id in [
      'lavandula-angustifolia',
      'eucalyptus-globulus',
      'acinos-sp',
    ]) {
      await showPassport(tester, consolidatedPlant(id));
      expect(find.text(noticeTitle), findsNothing, reason: id);
    }
    for (final level in [SafetyLevel.medium, SafetyLevel.low, null]) {
      await showPassport(tester, _plant(safety: _safety(level)));
      expect(find.text(noticeTitle), findsNothing, reason: '$level');
    }
    await showPassport(tester, _plant());
    expect(find.text(noticeTitle), findsNothing);
  });
}
