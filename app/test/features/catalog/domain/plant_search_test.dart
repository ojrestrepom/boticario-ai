import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_search.dart';
import 'package:flutter_test/flutter_test.dart';

Plant _plant(
  int id,
  String common,
  String scientific, {
  List<PlantPart> parts = const [],
}) => Plant(
  usdaPlantId: id,
  editorialCommonName: common,
  sourceScientificName: scientific,
  parts: parts,
);

void main() {
  final lavender = _plant(544, 'LÁVÁNDA', 'Lavandula angustifolia');
  final chamomile = _plant(605, 'Manzanílla', 'Matricaria recutita');
  final mint = _plant(
    619,
    'Menta',
    'Mentha x piperita',
    parts: [
      PlantPart(name: 'Essential Oil', sourceCode: 'EO', sources: const []),
    ],
  );
  final orderedPlants = [lavender, chamomile, mint];

  test('normalizes case, accents and repeated or surrounding whitespace', () {
    expect(searchPlants(orderedPlants, query: '  lavanda  ').single, lavender);
    expect(
      searchPlants(orderedPlants, query: '\tMANZANILLA\n').single,
      chamomile,
    );
    expect(searchPlants(orderedPlants, query: '  laVaNdA  '), [lavender]);
    expect(searchPlants(orderedPlants, query: 'manzanilla'), [chamomile]);
    expect(searchPlants(orderedPlants, query: 'manzanílla'), [chamomile]);
    expect(searchPlants(orderedPlants, query: 'lavandula angusti\u0301folia'), [
      lavender,
    ]);
  });

  test('matches substrings in either name independently', () {
    expect(searchPlants(orderedPlants, query: 'tricaria'), [chamomile]);
    expect(searchPlants(orderedPlants, query: 'enta'), [mint]);
    expect(searchPlants(orderedPlants, query: 'la ang'), [lavender]);
    expect(searchPlants(orderedPlants, query: 'lavanda lavandula'), isEmpty);
    expect(
      searchPlants([
        _plant(700, 'Synthetic', 'Méntha   x piperita'),
      ], query: '  MÉNTHA   X\tPIPERITA\n'),
      hasLength(1),
    );
  });

  test(
    'empty and whitespace-only query returns all plants for all/plant filters',
    () {
      expect(searchPlants(orderedPlants), orderedPlants);
      expect(searchPlants(orderedPlants, query: ' \t\n '), orderedPlants);
      expect(
        searchPlants(orderedPlants, filter: PlantFilter.plants),
        orderedPlants,
      );
    },
  );

  test(
    'query combines with filter, and oils stay empty even with oil parts',
    () {
      expect(
        searchPlants(orderedPlants, query: 'ment', filter: PlantFilter.plants),
        [mint],
      );
      expect(
        searchPlants(orderedPlants, query: '', filter: PlantFilter.oils),
        isEmpty,
      );
      expect(
        searchPlants(orderedPlants, query: 'ment', filter: PlantFilter.oils),
        isEmpty,
      );
      expect(
        () => searchPlants(orderedPlants, filter: PlantFilter.oils).clear(),
        throwsUnsupportedError,
      );
    },
  );

  test(
    'results preserve input order, object identity, and do not mutate inputs',
    () {
      final input = [chamomile, lavender, mint];
      final result = searchPlants(input, query: 'la');
      expect(result, [chamomile, lavender]);
      expect(identical(result[0], chamomile), isTrue);
      expect(identical(result[1], lavender), isTrue);
      expect(input, [chamomile, lavender, mint]);
      expect(() => result.clear(), throwsUnsupportedError);
    },
  );

  test('query with no matches returns empty', () {
    expect(searchPlants(orderedPlants, query: 'nonexistent'), isEmpty);
  });
}
