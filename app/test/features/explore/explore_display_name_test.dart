import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

const _imageHosts = ['commons.wikimedia.org', 'upload.wikimedia.org'];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // Real list response of the consolidated backend (`q=lavand`).
  Future<FakeCatalogApi> pumpExplore(WidgetTester tester) async {
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.view.physicalSize = const Size(360, 1200);
    tester.view.devicePixelRatio = 1;
    final api = FakeCatalogApi(listFixture: 'consolidated_list_lavand.json');
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          httpClientProvider.overrideWithValue(api.client),
          apiTokenProvider.overrideWithValue(testApiToken),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          home: ExplorePage(
            onBack: () {},
            onHome: () {},
            onPlantSelected: (_) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    return api;
  }

  testWidgets('Nombre en español: displayName es el principal', (tester) async {
    await pumpExplore(tester);
    // The old first common name ("English Lavender") is not what shows.
    expect(find.text('English Lavender'), findsNothing);
    expect(find.text('Lavanda'), findsNWidgets(2));
    expect(find.text('Alhusema'), findsOneWidget);
    expect(find.text('Lavandula angustifolia'), findsOneWidget);
    expect(find.text('Lavandula latifolia'), findsOneWidget);
    expect(
      find.bySemanticsLabel('Lavanda, Lavandula angustifolia'),
      findsOneWidget,
    );
  });

  testWidgets('Planta sin nombre común: solo el científico, sin secundario', (
    tester,
  ) async {
    await pumpExplore(tester);
    // displayName equals the scientific name: it appears once, not twice.
    expect(find.text('Lavandula spica'), findsOneWidget);
    expect(find.text('Lavandula × heterophylla'), findsOneWidget);
    expect(find.bySemanticsLabel('Lavandula spica'), findsOneWidget);
  });

  testWidgets('Arte local: las filas usan un icono y no cargan imágenes', (
    tester,
  ) async {
    final api = await pumpExplore(tester);
    expect(find.byType(Image), findsNothing);
    expect(find.byIcon(Icons.local_florist), findsWidgets);
    // Only the catalog API is called, never an image host.
    expect(api.requests, isNotEmpty);
    for (final request in api.requests) {
      expect(_imageHosts, isNot(contains(request.url.host)));
      expect(request.url.path, startsWith('/v1/plants'));
    }
  });
}
