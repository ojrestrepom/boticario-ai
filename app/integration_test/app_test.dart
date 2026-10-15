import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'catalog_smoke.dart';

// Needs the backend running (`docker compose up -d`); see the header of
// catalog_smoke.dart for how to run it and for `API_BASE_URL`.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets(
    'real app against the catalog API: Home, Explore, passport and returns',
    (tester) async {
      await runCatalogSmoke(tester);
    },
  );
}
