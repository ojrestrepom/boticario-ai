import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
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
  _consolidatedTests();
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

Plant _consolidated({
  String? displayName,
  List<PlantName> names = const [],
  List<PlantUse> uses = const [],
  List<UseGroup>? useGroups,
}) => Plant(
  id: 'x',
  scientificName: 'Lavandula angustifolia',
  family: null,
  names: names,
  parts: const [],
  uses: uses,
  displayName: displayName,
  useGroups: useGroups,
);

PlantUse _use(String activity, String id) => PlantUse(
  activity: activity,
  language: 'es',
  reference: UseReference(id: id, citation: 'Cita $id'),
);

void _consolidatedTests() {
  group('Nombre para mostrar', () {
    const english = PlantName(
      text: 'English Lavender',
      kind: PlantNameKind.common,
      language: 'en',
    );

    test('Planta con nombre común: displayName primary, scientific second', () {
      final plant = _consolidated(displayName: 'Lavanda', names: [english]);
      expect(plant.primaryName, 'Lavanda');
      expect(plant.secondaryName, 'Lavandula angustifolia');
    });

    test('Planta sin nombre común: displayName is the scientific name', () {
      final plant = _consolidated(displayName: 'Lavandula angustifolia');
      expect(plant.primaryName, 'Lavandula angustifolia');
      expect(plant.secondaryName, isNull);
    });

    test(
      'displayName scientific wins over a common name in another language',
      () {
        final plant = _consolidated(
          displayName: 'Lavandula angustifolia',
          names: [english],
        );
        expect(plant.primaryName, 'Lavandula angustifolia');
        expect(plant.secondaryName, isNull);
      },
    );

    test('Backend sin nombre para mostrar: first common name', () {
      final plant = _consolidated(names: [english]);
      expect(plant.primaryName, 'English Lavender');
      expect(plant.secondaryName, 'Lavandula angustifolia');
    });

    test('Backend sin nombre para mostrar ni comunes: scientific only', () {
      final plant = _consolidated();
      expect(plant.primaryName, 'Lavandula angustifolia');
      expect(plant.secondaryName, isNull);
    });

    test('Idioma del nombre común: shown as is', () {
      final summary = PlantSummary(
        id: 'x',
        scientificName: 'Genus species',
        displayName: 'Velvet',
        commonNames: const [CommonName(text: 'Velvet', language: 'und')],
      );
      expect(summary.primaryName, 'Velvet');
      expect(summary.secondaryName, 'Genus species');
    });

    test('summary without displayName falls back; empty one is ignored', () {
      for (final name in [null, '']) {
        final summary = PlantSummary(
          id: 'x',
          scientificName: 'Genus species',
          displayName: name,
          commonNames: const [CommonName(text: 'Alfa', language: 'en')],
        );
        expect(summary.primaryName, 'Alfa');
      }
    });
  });

  group('Consolidated model defaults, equality and immutability', () {
    test('defaults are empty or null', () {
      final plant = _consolidated();
      expect(plant.displayName, isNull);
      expect(plant.synonyms, isEmpty);
      expect(plant.description, isNull);
      expect(plant.origin, isNull);
      expect(plant.oil, isNull);
      expect(plant.useGroups, isEmpty);
      expect(plant.goals, isEmpty);
      expect(plant.safety, isNull);
      expect(plant.image, isNull);
      expect(plant.credits, isEmpty);
    });

    test('lists are unmodifiable', () {
      final plant = _consolidated(uses: [_use('A', 'r1')]);
      expect(() => plant.synonyms.add('x'), throwsUnsupportedError);
      expect(() => plant.goals.add(_goal()), throwsUnsupportedError);
      expect(() => plant.credits.clear(), throwsUnsupportedError);
      expect(() => plant.useGroups.clear(), throwsUnsupportedError);
      expect(
        () => plant.useGroups.first.references.clear(),
        throwsUnsupportedError,
      );
    });

    test('value equality covers the new fields', () {
      Plant build({String? description, SafetyLevel? level}) => Plant(
        id: 'x',
        scientificName: 'A a',
        family: null,
        names: const [],
        parts: const [],
        uses: const [],
        description: description,
        oil: const PlantOil(type: 'Esencial'),
        goals: [_goal()],
        safety: PlantSafety(level: level, text: 't', references: const []),
        image: const PlantImage(
          url: 'u',
          pageUrl: 'p',
          author: null,
          license: 'l',
          licenseUrl: null,
          attributionRequired: false,
        ),
        credits: const [
          PlantCredit(
            name: 'n',
            license: 'l',
            licenseUrl: null,
            attribution: 'a',
            url: null,
          ),
        ],
      );
      expect(build(description: 'd'), build(description: 'd'));
      expect(
        build(description: 'd').hashCode,
        build(description: 'd').hashCode,
      );
      expect(build(description: 'd') == build(description: 'e'), isFalse);
      expect(build(level: SafetyLevel.low) == build(), isFalse);
    });

    test('references compare their resolved mark', () {
      const a = CitedReference(
        id: null,
        citation: 'k (sin resolver)',
        resolved: false,
      );
      const b = CitedReference(
        id: null,
        citation: 'k (sin resolver)',
        resolved: true,
      );
      expect(a == b, isFalse);
    });
  });

  group('Respaldo de useGroups desde uses', () {
    test('derives one group per activity, ordered by count then activity', () {
      final plant = _consolidated(
        uses: [
          _use('B', 'r1'),
          _use('A', 'r2'),
          _use('B', 'r3'),
          _use('C', 'r4'),
        ],
      );
      expect(plant.useGroups.map((g) => g.activity), ['B', 'A', 'C']);
      final b = plant.useGroups.first;
      expect(b.count, 2);
      expect(b.countries, isEmpty);
      expect(b.references.map((r) => r.id), ['r1', 'r3']);
      expect(b.references.every((r) => r.resolved), isTrue);
      expect(b.references.first.citation, 'Cita r1');
    });

    test('an explicit useGroups wins over uses', () {
      final plant = _consolidated(uses: [_use('A', 'r1')], useGroups: const []);
      expect(plant.useGroups, isEmpty);
    });

    test('no uses gives no groups', () {
      expect(_consolidated().useGroups, isEmpty);
    });
  });
}

PlantGoal _goal() => PlantGoal(
  id: 'g',
  name: 'Goal',
  subarea: null,
  area: 'Area',
  evidence: 'Monografía de la EMA',
  references: const [],
);
