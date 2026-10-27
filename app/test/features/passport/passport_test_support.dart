import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

/// Parses a real consolidated API fixture (`consolidated_<id>.json`).
Plant consolidatedPlant(String id) =>
    parsePlant(apiFixture('consolidated_$id.json'));

/// Pumps the passport of [plant] and selects [tab] (`General` by default).
Future<void> showPassport(
  WidgetTester tester,
  Plant plant, {
  String tab = 'General',
}) async {
  tester.view.physicalSize = const Size(360, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      theme: buildBoticarioTheme(),
      home: PlantPassportPage(plant: plant, onBack: () {}, onHome: () {}),
    ),
  );
  if (tab != 'General') {
    await tester.tap(find.text(tab));
    await tester.pumpAndSettle();
  }
}
