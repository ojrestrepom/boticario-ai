import 'dart:convert';

import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/goal.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:flutter_test/flutter_test.dart';

// Synthetic fixtures that follow the contract of the `catalog-api` delta.

Matcher _invalid() => throwsA(
  isA<CatalogClientException>()
      .having((e) => e.kind, 'kind', CatalogClientErrorKind.invalidResponse)
      .having((e) => e.message, 'message', isNotEmpty),
);

List<dynamic> _catalog() => <dynamic>[
  <String, dynamic>{
    'id': 'relajacion-estres',
    'name': 'Relajación / Estrés',
    'plantCount': 17,
    'subareas': <Object?>[],
  },
  <String, dynamic>{
    'id': 'otros-objetivos',
    'name': 'Otros objetivos',
    'plantCount': 90,
    'subareas': <dynamic>[
      {'id': 'digestion', 'name': 'Digestión', 'plantCount': 60},
      {
        'id': 'molestias-oculares',
        'name': 'Molestias oculares',
        'plantCount': 1,
      },
    ],
  },
];

Map<String, Object?> _item({Map<String, Object?> overrides = const {}}) => {
  'id': 'matricaria-recutita',
  'displayName': 'Manzanilla',
  'scientificName': 'Matricaria recutita',
  'commonNames': [
    {'text': 'Manzanilla', 'language': 'es'},
  ],
  'family': 'Asteraceae',
  'areas': ['Estreñimiento; Trastornos gastrointestinales', 'Sueño'],
  'safetyLevel': 'medio',
  'hasSafety': true,
  'image': {
    'url': 'https://upload.wikimedia.org/wikipedia/commons/a/a1/M.jpg',
    'pageUrl': 'https://commons.wikimedia.org/wiki/File:M.jpg',
    'author': 'Ana',
    'license': 'CC BY-SA 4.0',
    'licenseUrl': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'attributionRequired': true,
  },
  ...overrides,
};

Map<String, Object?> _page({
  Map<String, Object?> item = const {},
  Map<String, Object?> overrides = const {},
}) => {
  'goal': {'id': 'otros-objetivos', 'name': 'Otros objetivos'},
  'subarea': {'id': 'digestion', 'name': 'Digestión'},
  'items': [_item(overrides: item)],
  'total': 61,
  'limit': 20,
  'offset': 0,
  ...overrides,
};

String _enc(Object? value) => jsonEncode(value);

void main() {
  group('parseGoals', () {
    test('parses a valid catalog in order', () {
      final goals = parseGoals(_enc(_catalog()));
      expect(
        [for (final g in goals) g.id],
        ['relajacion-estres', 'otros-objetivos'],
      );
      expect(goals[0].name, 'Relajación / Estrés');
      expect(goals[0].plantCount, 17);
      expect(goals[0].subareas, isEmpty);
      expect(goals[0].hasSubareas, isFalse);
      expect(goals[1].hasSubareas, isTrue);
      expect(
        goals[1].subareas.last,
        const GoalSubarea(
          id: 'molestias-oculares',
          name: 'Molestias oculares',
          plantCount: 1,
        ),
      );
    });

    test('an empty list is valid', () {
      expect(parseGoals('[]'), isEmpty);
    });

    test('ignores unknown fields', () {
      final json = _catalog();
      (json[0] as Map)['extra'] = 1;
      (json[1]['subareas'] as List).first['extra'] = {'a': 1};
      expect(parseGoals(_enc(json)), hasLength(2));
    });

    test('rejects invalid JSON and a non-list body', () {
      expect(() => parseGoals('<html>'), _invalid());
      expect(() => parseGoals('{"items":[]}'), _invalid());
    });

    for (final key in ['id', 'name', 'plantCount', 'subareas']) {
      test('rejects a goal without $key', () {
        final json = _catalog();
        (json[0] as Map).remove(key);
        expect(() => parseGoals(_enc(json)), _invalid());
      });
    }

    test('rejects wrong types', () {
      for (final (key, value) in [
        ('id', 3),
        ('name', null),
        ('plantCount', '17'),
        ('plantCount', 1.5),
        ('subareas', 'x'),
      ]) {
        final json = _catalog();
        (json[0] as Map)[key] = value;
        expect(() => parseGoals(_enc(json)), _invalid(), reason: key);
      }
    });

    test('rejects an incomplete or mistyped subarea', () {
      for (final mutate in <void Function(Map)>[
        (s) => s.remove('id'),
        (s) => s.remove('name'),
        (s) => s.remove('plantCount'),
        (s) => s['plantCount'] = 'uno',
      ]) {
        final json = _catalog();
        mutate((json[1]['subareas'] as List).first as Map);
        expect(() => parseGoals(_enc(json)), _invalid());
      }
      final json = _catalog();
      (json[1]['subareas'] as List)[0] = 'digestion';
      expect(() => parseGoals(_enc(json)), _invalid());
    });
  });

  group('parseGoalPlantPage', () {
    test('parses a valid page with attribution', () {
      final page = parseGoalPlantPage(_enc(_page()));
      expect(
        page.goal,
        const GoalRef(id: 'otros-objetivos', name: 'Otros objetivos'),
      );
      expect(page.subarea, const GoalRef(id: 'digestion', name: 'Digestión'));
      expect(page.total, 61);
      expect(page.limit, 20);
      expect(page.offset, 0);
      final plant = page.items.single;
      expect(plant.id, 'matricaria-recutita');
      expect(plant.displayName, 'Manzanilla');
      expect(plant.primaryName, 'Manzanilla');
      expect(plant.secondaryName, 'Matricaria recutita');
      expect(plant.commonNames.single.language, 'es');
      expect(plant.family, 'Asteraceae');
      // Shown as they come: the "; " value is not split.
      expect(plant.areas, [
        'Estreñimiento; Trastornos gastrointestinales',
        'Sueño',
      ]);
      expect(plant.safetyLevel, SafetyLevel.medium);
      expect(plant.hasSafety, isTrue);
      expect(plant.image?.author, 'Ana');
      expect(plant.image?.license, 'CC BY-SA 4.0');
      expect(plant.image?.attributionRequired, isTrue);
    });

    test(
      'accepts null subarea, safetyLevel, image, family and displayName',
      () {
        final page = parseGoalPlantPage(
          _enc(
            _page(
              item: {
                'safetyLevel': null,
                'hasSafety': false,
                'image': null,
                'family': null,
                'displayName': null,
              },
              overrides: {'subarea': null},
            ),
          ),
        );
        expect(page.subarea, isNull);
        final plant = page.items.single;
        expect(plant.safetyLevel, isNull);
        expect(plant.hasSafety, isFalse);
        expect(plant.image, isNull);
        expect(plant.family, isNull);
        // Display-name rule: first common name.
        expect(plant.primaryName, 'Manzanilla');
      },
    );

    test('a scientific displayName has no secondary name', () {
      final plant = parseGoalPlantPage(
        _enc(
          _page(
            item: {
              'displayName': 'Matricaria recutita',
              'commonNames': <Object?>[],
            },
          ),
        ),
      ).items.single;
      expect(plant.primaryName, 'Matricaria recutita');
      expect(plant.secondaryName, isNull);
    });

    test('safety without level keeps hasSafety true', () {
      final plant = parseGoalPlantPage(
        _enc(_page(item: {'safetyLevel': null, 'hasSafety': true})),
      ).items.single;
      expect(plant.safetyLevel, isNull);
      expect(plant.hasSafety, isTrue);
    });

    test('an empty page is valid', () {
      final page = parseGoalPlantPage(
        _enc(_page(overrides: {'items': <Object?>[], 'total': 0})),
      );
      expect(page.items, isEmpty);
      expect(page.total, 0);
    });

    test('maps the three known levels', () {
      for (final (text, level) in [
        ('alto', SafetyLevel.high),
        ('medio', SafetyLevel.medium),
        ('bajo', SafetyLevel.low),
      ]) {
        final plant = parseGoalPlantPage(
          _enc(_page(item: {'safetyLevel': text})),
        ).items.single;
        expect(plant.safetyLevel, level);
      }
    });

    test('hasSafety absent derives from safetyLevel', () {
      Map<String, Object?> withoutHasSafety(Object? level) {
        final json = _page(item: {'safetyLevel': level});
        ((json['items']! as List).single as Map).remove('hasSafety');
        return json;
      }

      expect(
        parseGoalPlantPage(_enc(withoutHasSafety('bajo')))
            .items
            .single
            .hasSafety,
        isTrue,
      );
      expect(
        parseGoalPlantPage(_enc(withoutHasSafety(null))).items.single.hasSafety,
        isFalse,
      );
    });

    test('absent displayName and image are tolerated', () {
      final json = _page();
      final item = (json['items']! as List).single as Map;
      item
        ..remove('displayName')
        ..remove('image');
      final plant = parseGoalPlantPage(_enc(json)).items.single;
      expect(plant.displayName, isNull);
      expect(plant.image, isNull);
      expect(plant.primaryName, 'Manzanilla');
    });

    test('ignores unknown fields everywhere', () {
      final json = _page(
        item: {
          'extra': 1,
          'image': {
            ...(_item()['image']! as Map<String, Object?>),
            'extra': true,
          },
        },
        overrides: {
          'extra': [],
          'goal': {'id': 'otros-objetivos', 'name': 'Otros objetivos', 'x': 1},
        },
      );
      expect(parseGoalPlantPage(_enc(json)).items, hasLength(1));
    });

    test('rejects an unknown safety level', () {
      expect(
        () => parseGoalPlantPage(_enc(_page(item: {'safetyLevel': 'extremo'}))),
        _invalid(),
      );
      expect(
        () => parseGoalPlantPage(_enc(_page(item: {'safetyLevel': 'ALTO'}))),
        _invalid(),
      );
    });

    test('rejects invalid JSON and a non-object body', () {
      expect(() => parseGoalPlantPage('nope'), _invalid());
      expect(() => parseGoalPlantPage('[]'), _invalid());
    });

    for (final key in [
      'goal',
      'subarea',
      'items',
      'total',
      'limit',
      'offset',
    ]) {
      test('rejects a page without $key', () {
        final json = _page()..remove(key);
        expect(() => parseGoalPlantPage(_enc(json)), _invalid());
      });
    }

    for (final key in [
      'id',
      'scientificName',
      'commonNames',
      'areas',
      'safetyLevel',
    ]) {
      test('rejects an item without $key', () {
        final json = _page();
        ((json['items']! as List).single as Map).remove(key);
        expect(() => parseGoalPlantPage(_enc(json)), _invalid());
      });
    }

    test('rejects wrong page types', () {
      for (final overrides in <Map<String, Object?>>[
        {'items': 'x'},
        {'items': null},
        {'total': '61'},
        {'limit': 20.5},
        {'offset': null},
        {'goal': 'otros-objetivos'},
        {
          'goal': {'id': 'a'},
        },
        {'subarea': 'digestion'},
        {
          'subarea': {'id': 'digestion'},
        },
      ]) {
        expect(
          () => parseGoalPlantPage(_enc(_page(overrides: overrides))),
          _invalid(),
          reason: '$overrides',
        );
      }
    });

    test('rejects wrong item types', () {
      for (final item in <Map<String, Object?>>[
        {'id': 1},
        {'scientificName': null},
        {'commonNames': 'x'},
        {
          'commonNames': ['x'],
        },
        {
          'commonNames': [
            {'text': 'a'},
          ],
        },
        {'family': 3},
        {'displayName': 3},
        {'areas': 'Sueño'},
        {
          'areas': ['Sueño', 2],
        },
        {'safetyLevel': 2},
        {'hasSafety': 'true'},
        {'image': 'x'},
        {
          'image': {'url': 'x'},
        },
      ]) {
        expect(
          () => parseGoalPlantPage(_enc(_page(item: item))),
          _invalid(),
          reason: '$item',
        );
      }
    });

    test('rejects a non-object item', () {
      expect(
        () => parseGoalPlantPage(
          _enc(
            _page(
              overrides: {
                'items': [1],
              },
            ),
          ),
        ),
        _invalid(),
      );
    });
  });
}
