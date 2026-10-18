import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../integration_test/catalog_smoke.dart';

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    // Resolve the real bundle asset before the widget test's FakeAsync zone.
    await rootBundle.loadString('assets/data/plant_catalog.json');
  });

  testWidgets(
    'shared real-app P06 and catalog smoke passes host preflight (not Android evidence)',
    (tester) async {
      // This host binding preloads the bundle via its test asset channel. It
      // intentionally does not run the app-level HTTP guard or claim network
      // verification; Android integration enables that guard separately.
      await runCatalogSmoke(tester, guardApplicationHttp: false);
    },
  );

  testWidgets(
    'shared flow retains P04 state when an IME viewport change clamps scroll',
    (tester) async {
      final originalPhysicalSize = tester.view.physicalSize;
      final originalDevicePixelRatio = tester.view.devicePixelRatio;
      addTearDown(() => tester.view.physicalSize = originalPhysicalSize);
      addTearDown(
        () => tester.view.devicePixelRatio = originalDevicePixelRatio,
      );
      // 360x1000 logical dp represents a tall phone. The 400dp simulated IME
      // makes Menta require scrolling; its removal makes the same list fit.
      tester.view.physicalSize = const Size(1080, 3000);
      tester.view.devicePixelRatio = 3;
      // Deliberately simulate the Android hypothesis: P04 is constrained by an
      // IME before push, then P05 has the inset removed. The shared flow still
      // requires identical controllers/query/filter and verifies the exact
      // clamp to the new extent; it is not Android evidence.
      await runCatalogSmoke(
        tester,
        guardApplicationHttp: false,
        simulateKeyboardViewport: true,
      );
    },
  );
}
