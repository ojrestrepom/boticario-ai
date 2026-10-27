import 'dart:convert';

import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
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
  _consolidatedTests();
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

Map<String, Object?> _full() =>
    jsonDecode(apiFixture('plant_consolidated_synthetic.json'))
        as Map<String, Object?>;

List<Object?> _at(Map<String, Object?> json, String key) =>
    json[key]! as List<Object?>;

void _consolidatedTests() {
  group('parsePlant consolidated fields', () {
    test('Detalle válido: parses every new field', () {
      final plant = parsePlant(apiFixture('plant_consolidated_synthetic.json'));
      expect(plant.displayName, 'Lavanda');
      expect(plant.synonyms, ['Lavandula officinalis']);
      expect(plant.description, isNotNull);
      expect(plant.origin, 'Región mediterránea');
      expect(plant.oil, const PlantOil(type: 'Esencial'));
      final group = plant.useGroups.single;
      expect(group.count, 12);
      expect(group.activitySource, 'insomnia');
      expect(group.countries, ['España', 'Francia', 'Italia']);
      expect(group.references.first.citation, startsWith('Steinmetz'));
      expect(plant.goals.single.subarea, 'Digestión');
      expect(plant.goals.single.area, 'Digestión');
      expect(plant.goals.single.references.single.id, 'ema-1');
      expect(plant.safety!.level, SafetyLevel.high);
      expect(plant.safety!.references, hasLength(1));
      expect(plant.image!.author, isNull);
      expect(plant.image!.attributionRequired, isTrue);
      expect(plant.credits.single.url, isNull);
      expect(plant.credits.single.licenseUrl, isNotNull);
    });

    test('Detalle válido: every safety level maps to the enum', () {
      for (final (raw, level) in [
        ('alto', SafetyLevel.high),
        ('medio', SafetyLevel.medium),
        ('bajo', SafetyLevel.low),
      ]) {
        final json = _full();
        (json['safety']! as Map<String, Object?>)['level'] = raw;
        expect(parsePlant(jsonEncode(json)).safety!.level, level);
      }
    });

    test('Backend anterior sin los campos nuevos', () {
      final plant = parsePlant(apiFixture('plant_lavandula-angustifolia.json'));
      expect(plant.displayName, isNull);
      expect(plant.synonyms, isEmpty);
      expect(plant.description, isNull);
      expect(plant.origin, isNull);
      expect(plant.oil, isNull);
      expect(plant.goals, isEmpty);
      expect(plant.safety, isNull);
      expect(plant.image, isNull);
      expect(plant.credits, isEmpty);
      // useGroups is derived from uses (task 6.3).
      expect(plant.useGroups, isNotEmpty);
    });

    test('Backend anterior: explicit nulls behave like absent fields', () {
      final json = _detail()
        ..['oil'] = null
        ..['safety'] = null
        ..['image'] = null
        ..['goals'] = null
        ..['credits'] = null
        ..['synonyms'] = null
        ..['description'] = null;
      final plant = parsePlant(jsonEncode(json));
      expect(plant.safety, isNull);
      expect(plant.goals, isEmpty);
    });

    test('an explicit empty useGroups is not replaced by the fallback', () {
      final json = _detail()..['useGroups'] = <Object?>[];
      expect(parsePlant(jsonEncode(json)).useGroups, isEmpty);
    });

    test('Precauciones sin nivel: level null is valid, safety is kept', () {
      final json = _full();
      (json['safety']! as Map<String, Object?>)['level'] = null;
      final safety = parsePlant(jsonEncode(json)).safety;
      expect(safety, isNotNull);
      expect(safety!.level, isNull);
      expect(safety.text, isNotEmpty);
      expect(safety.references, hasLength(1));
    });

    test('Precauciones sin nivel: an absent level is also null', () {
      final json = _full();
      (json['safety']! as Map<String, Object?>).remove('level');
      expect(parsePlant(jsonEncode(json)).safety!.level, isNull);
    });

    test('Cita sin resolver: keeps the unresolved mark', () {
      final plant = parsePlant(apiFixture('plant_consolidated_synthetic.json'));
      final refs = plant.useGroups.single.references;
      expect(refs[0].resolved, isTrue);
      expect(refs[1].id, isNull);
      expect(refs[1].resolved, isFalse);
      expect(refs[1].citation, 'dukeref99 (sin resolver)');
    });

    test('Campo nuevo con tipo erróneo: goals as text', () {
      expect(
        () => parsePlant(jsonEncode(_full()..['goals'] = 'x')),
        _invalid(contains('goals')),
      );
    });

    test('Campo nuevo con tipo erróneo: unknown safety level', () {
      final json = _full();
      (json['safety']! as Map<String, Object?>)['level'] = 'critico';
      expect(() => parsePlant(jsonEncode(json)), _invalid(contains('level')));
    });

    test('Campo nuevo con tipo erróneo: resolved not boolean', () {
      final json = _full();
      final group = _at(json, 'useGroups').first! as Map<String, Object?>;
      (_at(group, 'references').first! as Map<String, Object?>)['resolved'] =
          'true';
      expect(
        () => parsePlant(jsonEncode(json)),
        _invalid(contains('resolved')),
      );
    });

    test('Campo nuevo con tipo erróneo: other fields', () {
      for (final (key, value) in <(String, Object?)>[
        ('displayName', 3),
        ('description', 1),
        ('oil', 'Esencial'),
        ('image', []),
        ('credits', {}),
        ('synonyms', [1]),
        ('safety', 'alto'),
      ]) {
        expect(
          () => parsePlant(jsonEncode(_full()..[key] = value)),
          _invalid(contains(key)),
          reason: key,
        );
      }
    });
  });

  group('parsePlantPage displayName', () {
    test('reads displayName and tolerates its absence', () {
      final page = parsePlantPage(
        '{"items":[{"id":"a","scientificName":"A a","displayName":"Ala",'
        '"commonNames":[]},{"id":"b","scientificName":"B b","commonNames":[]}],'
        '"total":2,"limit":50,"offset":0}',
      );
      expect(page.items[0].displayName, 'Ala');
      expect(page.items[1].displayName, isNull);
    });

    test('rejects a displayName of the wrong type', () {
      expect(
        () => parsePlantPage(
          '{"items":[{"id":"a","scientificName":"A a","displayName":1,'
          '"commonNames":[]}],"total":1,"limit":50,"offset":0}',
        ),
        _invalid(contains('displayName')),
      );
    });
  });
}
