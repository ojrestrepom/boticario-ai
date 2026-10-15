import 'dart:convert';

import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_catalog_api.dart';

Matcher _invalid([Object? message]) => throwsA(
  isA<CatalogClientException>()
      .having((e) => e.kind, 'kind', CatalogClientErrorKind.invalidResponse)
      .having((e) => e.message, 'message', message ?? isNotEmpty),
);

Map<String, Object?> _detail() =>
    jsonDecode(apiFixture('plant_lavandula-angustifolia.json'))
        as Map<String, Object?>;

void main() {
  group('parsePlantPage', () {
    test('parses a valid page', () {
      final page = parsePlantPage(apiFixture('list_lavandula.json'));
      expect(page.items, isNotEmpty);
      expect(page.total, 7);
      expect(page.limit, 50);
      expect(page.offset, 0);
      final lavender = page.items.firstWhere(
        (p) => p.id == 'lavandula-angustifolia',
      );
      expect(lavender.scientificName, 'Lavandula angustifolia');
      expect(lavender.commonNames, isNotEmpty);
      expect(lavender.family, 'Lamiaceae');
    });

    test('ignores unknown fields and accepts a null family', () {
      final page = parsePlantPage(
        jsonEncode({
          'items': [
            {
              'id': 'a',
              'scientificName': 'A a',
              'commonNames': <Object?>[],
              'family': null,
              'extra': 1,
            },
          ],
          'total': 1,
          'limit': 50,
          'offset': 0,
          'next': 'x',
        }),
      );
      expect(page.items.single.family, isNull);
    });

    test('treats an absent family as null', () {
      final page = parsePlantPage(
        '{"items":[{"id":"a","scientificName":"A a","commonNames":[]}],'
        '"total":1,"limit":50,"offset":0}',
      );
      expect(page.items.single.family, isNull);
    });

    test('rejects a missing items field naming it', () {
      expect(
        () => parsePlantPage('{"total":1,"limit":50,"offset":0}'),
        _invalid(contains('items')),
      );
    });

    test('rejects a wrong type', () {
      expect(
        () => parsePlantPage('{"items":[],"total":"1","limit":50,"offset":0}'),
        _invalid(contains('total')),
      );
    });

    test('rejects invalid JSON without dumping the body', () {
      expect(
        () => parsePlantPage('<html>' * 100),
        _invalid(isNot(contains('<html>'))),
      );
    });
  });

  group('parsePlant', () {
    test('parses a valid detail with names, parts and uses', () {
      final plant = parsePlant(apiFixture('plant_lavandula-angustifolia.json'));
      expect(plant.id, 'lavandula-angustifolia');
      expect(plant.family, 'Lamiaceae');
      expect(plant.names.map((n) => n.kind), contains(PlantNameKind.common));
      expect(plant.parts, isNotEmpty);
      expect(plant.uses, hasLength(10));
      expect(plant.uses.first.reference.citation, isNotEmpty);
      expect(plant.uses.first.language, isNotEmpty);
    });

    test('parses a plant with many uses, no uses and a null family', () {
      expect(
        parsePlant(apiFixture('plant_rosmarinus-officinalis.json')).uses,
        hasLength(greaterThan(50)),
      );
      final none = parsePlant(apiFixture('plant_chondrus-crispus.json'));
      expect(none.uses, isEmpty);
      expect(none.family, isNull);
      expect(
        parsePlant(apiFixture('plant_abies-spectabilis.json')).commonNames,
        isEmpty,
      );
    });

    test('ignores unknown fields', () {
      final json = _detail()
        ..['surprise'] = {'a': 1}
        ..['family'] = null;
      expect(parsePlant(jsonEncode(json)).family, isNull);
    });

    test('rejects a missing scientificName naming it', () {
      final json = _detail()..remove('scientificName');
      expect(
        () => parsePlant(jsonEncode(json)),
        _invalid(contains('scientificName')),
      );
    });

    test('treats an absent family as null', () {
      final json = _detail()..remove('family');
      expect(parsePlant(jsonEncode(json)).family, isNull);
    });

    test('rejects wrong types and unknown name kinds', () {
      expect(
        () => parsePlant(jsonEncode(_detail()..['parts'] = 'x')),
        _invalid(contains('parts')),
      );
      expect(
        () => parsePlant(jsonEncode(_detail()..['id'] = 3)),
        _invalid(contains('id')),
      );
      final badKind = _detail();
      (badKind['names']! as List<Object?>)[0] = {
        'text': 'x',
        'kind': 'nickname',
        'language': 'en',
      };
      expect(() => parsePlant(jsonEncode(badKind)), _invalid(contains('kind')));
    });

    test('rejects a use without reference', () {
      final json = _detail();
      ((json['uses']! as List<Object?>)[0]! as Map<String, Object?>).remove(
        'reference',
      );
      expect(
        () => parsePlant(jsonEncode(json)),
        _invalid(contains('reference')),
      );
    });

    test('rejects invalid JSON and non-object JSON', () {
      expect(() => parsePlant('nope'), _invalid());
      expect(() => parsePlant('[]'), _invalid());
    });
  });
}
