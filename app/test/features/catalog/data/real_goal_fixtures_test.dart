import 'dart:io';

import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/goal.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_catalog_api.dart';

/// The `goals_catalog.json` and `goal_plants_*.json` fixtures are real
/// responses of the local API (`data/build/catalog.db`), reformatted, except
/// `goal_plants_no_safety_synthetic.json`, which is synthetic (no seed plant
/// with a goal lacks safety data). These tests pin the real shape.
void main() {
  group('real goal fixtures', () {
    test('the catalog has the six goals in order and the subareas', () {
      final goals = parseGoals(apiFixture('goals_catalog.json'));
      expect(
        [for (final goal in goals) goal.id],
        [
          'relajacion-estres',
          'mejorar-el-sueno',
          'cuidado-de-la-piel',
          'alivio-respiratorio',
          'cansancio-y-fatiga',
          'otros-objetivos',
        ],
      );
      expect(goals.first.plantCount, 17);
      final others = goals.last;
      expect(others.hasSubareas, isTrue);
      expect(others.subareas, hasLength(6));
      expect(others.subareas.first.id, 'digestion');
    });

    test('a goal page has the goal, no subarea and the whole goal', () {
      final page = parseGoalPlantPage(
        apiFixture('goal_plants_relajacion-estres.json'),
      );
      expect(page.goal.id, 'relajacion-estres');
      expect(page.subarea, isNull);
      expect(page.items, hasLength(17));
      expect(page.total, 17);
      expect(page.items.first.primaryName, 'Acerolo');
    });

    test('a subarea page names the subarea', () {
      final page = parseGoalPlantPage(
        apiFixture('goal_plants_subarea_digestion.json'),
      );
      expect(page.goal.id, 'otros-objetivos');
      expect(page.subarea, const GoalRef(id: 'digestion', name: 'Digestión'));
      expect(page.items, hasLength(20));
      expect(page.total, 68);
    });

    test('pages 1 and 2 do not repeat plants', () {
      final first = parseGoalPlantPage(
        apiFixture('goal_plants_otros-objetivos_page1.json'),
      );
      final second = parseGoalPlantPage(
        apiFixture('goal_plants_otros-objetivos_page2.json'),
      );
      expect(first.total, 135);
      expect(second.offset, 20);
      final ids = [
        for (final plant in [...first.items, ...second.items]) plant.id,
      ];
      expect(ids.toSet(), hasLength(40));
    });

    test('an offset past the total gives an empty page with the total', () {
      final page = parseGoalPlantPage(
        apiFixture('goal_plants_empty_offset.json'),
      );
      expect(page.items, isEmpty);
      expect(page.total, 17);
      expect(page.offset, 1000);
    });

    test('a plant without image', () {
      final plant = parseGoalPlantPage(apiFixture('goal_plants_no_image.json'))
          .items
          .single;
      expect(plant.id, 'sisymbrium-officinale');
      expect(plant.image, isNull);
      expect(plant.safetyLevel, SafetyLevel.medium);
    });

    test('eucalyptus has precautions without a level', () {
      final plant = parseGoalPlantPage(
        apiFixture('goal_plants_safety_without_level.json'),
      ).items.single;
      expect(plant.id, 'eucalyptus-globulus');
      expect(plant.safetyLevel, isNull);
      expect(plant.hasSafety, isTrue);
    });

    test('an image can come without author', () {
      final plant = parseGoalPlantPage(apiFixture('goal_plants_no_author.json'))
          .items
          .single;
      expect(plant.image, isNotNull);
      expect(plant.image!.author, isNull);
      expect(plant.safetyLevel, SafetyLevel.high);
    });

    test('the synthetic fixture has no safety data', () {
      final plant = parseGoalPlantPage(
        apiFixture('goal_plants_no_safety_synthetic.json'),
      ).items.single;
      expect(plant.hasSafety, isFalse);
      expect(plant.safetyLevel, isNull);
    });

    test('no fixture carries a token or an Authorization header', () {
      final files = Directory('test/fixtures/api').listSync().whereType<File>();
      for (final file in files) {
        final text = file.readAsStringSync();
        expect(text, isNot(contains('Authorization')), reason: file.path);
        expect(text, isNot(contains('Bearer')), reason: file.path);
        expect(
          RegExp(r'[0-9a-f]{64}').hasMatch(text),
          isFalse,
          reason: file.path,
        );
      }
    });
  });
}
