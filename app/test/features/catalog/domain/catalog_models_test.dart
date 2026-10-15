import 'package:boticario_ai/features/catalog/domain/catalog_plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_summary.dart';
import 'package:flutter_test/flutter_test.dart';

Plant _plant(List<PlantName> names) => Plant(
  id: 'x',
  scientificName: 'Lavandula angustifolia',
  family: null,
  names: names,
  parts: const [],
  uses: const [],
);

void main() {
  group('PlantSummary display names', () {
    test('uses the first common name as primary and the scientific second', () {
      final plant = PlantSummary(
        id: 'lavandula-angustifolia',
        scientificName: 'Lavandula angustifolia',
        commonNames: const [
          CommonName(text: 'English Lavender', language: 'en'),
          CommonName(text: 'Lavanda', language: 'es'),
        ],
      );
      expect(plant.primaryName, 'English Lavender');
      expect(plant.secondaryName, 'Lavandula angustifolia');
    });

    test('without common names shows the scientific name only', () {
      final plant = PlantSummary(
        id: 'x',
        scientificName: 'Abies spectabilis',
        commonNames: const [],
      );
      expect(plant.primaryName, 'Abies spectabilis');
      expect(plant.secondaryName, isNull);
    });

    test('shows en and und names untranslated', () {
      for (final language in ['en', 'und']) {
        final plant = PlantSummary(
          id: 'x',
          scientificName: 'Genus species',
          commonNames: [CommonName(text: 'Some name', language: language)],
        );
        expect(plant.primaryName, 'Some name');
        expect(plant.secondaryName, 'Genus species');
      }
    });
  });

  group('Plant display names', () {
    test('first common name wins; scientific entries are skipped', () {
      final plant = _plant(const [
        PlantName(
          text: 'Lavandula angustifolia',
          kind: PlantNameKind.scientific,
          language: 'la',
        ),
        PlantName(
          text: 'English Lavender',
          kind: PlantNameKind.common,
          language: 'en',
        ),
        PlantName(text: 'Lavanda', kind: PlantNameKind.common, language: 'es'),
      ]);
      expect(plant.primaryName, 'English Lavender');
      expect(plant.secondaryName, 'Lavandula angustifolia');
      expect(plant.commonNames, hasLength(2));
    });

    test('without common names the scientific name is primary', () {
      final plant = _plant(const [
        PlantName(
          text: 'Lavandula angustifolia',
          kind: PlantNameKind.scientific,
          language: 'la',
        ),
      ]);
      expect(plant.primaryName, 'Lavandula angustifolia');
      expect(plant.secondaryName, isNull);
    });

    test('keeps und names as they come', () {
      final plant = _plant(const [
        PlantName(text: 'Alfa', kind: PlantNameKind.common, language: 'und'),
      ]);
      expect(plant.primaryName, 'Alfa');
      expect(plant.secondaryName, 'Lavandula angustifolia');
    });
  });
}
