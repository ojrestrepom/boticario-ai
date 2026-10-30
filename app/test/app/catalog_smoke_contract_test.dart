import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../integration_test/catalog_smoke.dart';
import '../support/fake_catalog_api.dart';

/// Lavender with glossary (derived from the real fixture) and a plant without
/// glossary terms, which the smoke opens to check there is no explanation.
const _detailFixtures = {
  'lavandula-angustifolia':
      'consolidated_lavandula-angustifolia_glossary-derived.json',
  'anemopsis-californica': 'consolidated_anemopsis-californica_derived.json',
};
const _searchFixtures = {
  'anemopsis': 'consolidated_list_anemopsis_derived.json',
};

void main() {
  // The shared flow mounts the real app over a fake HTTP client serving the
  // fixtures: no network, no backend, no asset. This is contract evidence on
  // the host, not Android QA; the HTTP guard belongs to the integration test.
  testWidgets(
    'shared real-app smoke flow passes against the fake catalog API',
    (tester) async {
      final api = FakeCatalogApi(
        requiredToken: testApiToken,
        goalPageFixtures: realGoalPageFixtures,
        listFixture: 'consolidated_list_lavand.json',
        searchFixtures: _searchFixtures,
        detailFixtures: _detailFixtures,
      );
      await runCatalogSmoke(
        tester,
        overrides: [
          httpClientProvider.overrideWithValue(api.client),
          apiTokenProvider.overrideWithValue(testApiToken),
        ],
        guardApplicationHttp: false,
        requestCount: () => api.requests.length,
      );
      expect(api.requests, isNotEmpty);
      expect(api.requests.any((r) => r.url.path == '/v1/goals'), isTrue);
      for (final request in api.requests) {
        expect(
          request.url.path,
          anyOf(startsWith('/v1/plants'), startsWith('/v1/goals')),
        );
        expect(request.headers['Authorization'], 'Bearer $testApiToken');
      }
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
      // shrinks the viewport before the passport opens and its removal restores
      // it, so a retained scroll must clamp to the new extent.
      tester.view.physicalSize = const Size(1080, 3000);
      tester.view.devicePixelRatio = 3;
      final api = FakeCatalogApi(
        requiredToken: testApiToken,
        goalPageFixtures: realGoalPageFixtures,
        listFixture: 'consolidated_list_lavand.json',
        searchFixtures: _searchFixtures,
        detailFixtures: _detailFixtures,
      );
      await runCatalogSmoke(
        tester,
        overrides: [
          httpClientProvider.overrideWithValue(api.client),
          apiTokenProvider.overrideWithValue(testApiToken),
        ],
        guardApplicationHttp: false,
        simulateKeyboardViewport: true,
        requestCount: () => api.requests.length,
      );
    },
  );
}
