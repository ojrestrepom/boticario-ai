import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/services.dart';
import 'package:integration_test/integration_test.dart';

import 'catalog_smoke.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    await rootBundle.loadString('assets/data/plant_catalog.json');
  });

  testWidgets('real app: Home, local catalog, passport and session returns', (
    tester,
  ) async {
    await runCatalogSmoke(tester);
  });
}
