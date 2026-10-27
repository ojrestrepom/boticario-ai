import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_catalog_api.dart';

/// The `consolidated_*.json` fixtures are real responses of the local API
/// (`data/build/catalog.db`), reformatted. These tests pin the real shape of
/// `references` in `useGroups`, `goals` and `safety`.
void main() {
  group('real consolidated fixtures', () {
    test('lavender has everything', () {
      final plant = parsePlant(
        apiFixture('consolidated_lavandula-angustifolia.json'),
      );
      expect(plant.displayName, 'Lavanda');
      expect(plant.primaryName, 'Lavanda');
      expect(plant.secondaryName, 'Lavandula angustifolia');
      expect(plant.oil, isNotNull);
      expect(plant.description, isNotEmpty);
      expect(plant.useGroups, isNotEmpty);
      expect(plant.goals, isNotEmpty);
      expect(plant.safety, isNotNull);
      expect(plant.image, isNotNull);
      expect(plant.image!.url, startsWith('https://'));
      expect(plant.credits, isNotEmpty);
      for (final group in plant.useGroups) {
        // Group references carry the full citation text, not the label.
        expect(group.references, isNotEmpty);
      }
    });

    test('a plant without data has empty lists and no safety or image', () {
      final plant = parsePlant(apiFixture('consolidated_acinos-sp.json'));
      expect(plant.useGroups, isEmpty);
      expect(plant.goals, isEmpty);
      expect(plant.safety, isNull);
      expect(plant.image, isNull);
      expect(plant.displayName, plant.scientificName);
      expect(plant.secondaryName, isNull);
    });

    test('a toxic plant has high safety level and serious warnings', () {
      final plant = parsePlant(apiFixture('consolidated_blighia-sapida.json'));
      expect(plant.safety!.level, SafetyLevel.high);
      expect(plant.safety!.text, contains('casos mortales'));
      expect(plant.safety!.text, contains('veneno'));
    });

    test('eucalyptus has safety without level', () {
      final plant = parsePlant(
        apiFixture('consolidated_eucalyptus-globulus.json'),
      );
      expect(plant.safety, isNotNull);
      expect(plant.safety!.level, isNull);
      expect(plant.safety!.text, isNotEmpty);
    });

    test('goal and safety references have an id and a citation only', () {
      // The API serves `{id, citation}` here (no `resolved`): present means
      // resolved. Only use groups add `resolved`.
      final plant = parsePlant(
        apiFixture('consolidated_capsella-bursa-pastoris.json'),
      );
      expect(plant.goals.single.references, isNotEmpty);
      expect(plant.safety!.references, isNotEmpty);
      for (final ref in [
        ...plant.goals.single.references,
        ...plant.safety!.references,
      ]) {
        expect(ref.id, isNotNull);
        expect(ref.citation, isNotEmpty);
        expect(ref.resolved, isTrue);
      }
    });

    test(
      'a group with an unresolved citation and a traditional-use activity',
      () {
        final plant = parsePlant(
          apiFixture('consolidated_capsella-bursa-pastoris.json'),
        );
        final mixed = plant.useGroups.firstWhere(
          (g) => g.references.any((r) => !r.resolved),
        );
        expect(mixed.references.any((r) => r.resolved), isTrue);
        final unresolved = mixed.references.firstWhere((r) => !r.resolved);
        expect(unresolved.id, isNull);
        expect(unresolved.citation, endsWith('(sin resolver)'));
        expect(
          plant.useGroups.map((g) => g.activity),
          contains(startsWith('Uso tradicional, sin eficacia demostrada: ')),
        );
      },
    );

    test('a goal of otros-objetivos has a subarea', () {
      final plant = parsePlant(
        apiFixture('consolidated_agrimonia-eupatoria.json'),
      );
      final goal = plant.goals.firstWhere((g) => g.id == 'otros-objetivos');
      expect(goal.name, 'Otros objetivos');
      expect(goal.subarea, 'Boca y garganta');
      expect(goal.area, isNotEmpty);
    });

    test('an alias answer is the canonical plant', () {
      final plant = parsePlant(
        apiFixture('consolidated_alias_rosmarinus-officinalis.json'),
      );
      expect(plant.id, 'salvia-rosmarinus');
      expect(plant.displayName, 'Romero');
    });

    test('the list carries displayName', () {
      final page = parsePlantPage(apiFixture('consolidated_list_lavand.json'));
      expect(page.total, page.items.length);
      final lavender = page.items.firstWhere(
        (p) => p.id == 'lavandula-angustifolia',
      );
      expect(lavender.displayName, 'Lavanda');
      expect(lavender.primaryName, 'Lavanda');
      expect(lavender.secondaryName, 'Lavandula angustifolia');
      final spica = page.items.firstWhere((p) => p.id == 'lavandula-spica');
      expect(spica.primaryName, 'Lavandula spica');
      expect(spica.secondaryName, isNull);
    });
  });
}
