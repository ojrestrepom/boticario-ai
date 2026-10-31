import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_image_source.dart';
import 'package:boticario_ai/features/plant_recognition/presentation/plant_recognition_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/testing.dart';
import 'package:integration_test/integration_test.dart';

/// Only the system picker is substituted, to select known photos reproducibly.
/// The app, /identify route, recognition controller and ONNX service are real.
class _ReferenceImageSource implements PlantImageSource {
  int next = 1;
  final origins = <PlantImageOrigin>[];

  @override
  Future<Uint8List?> pick(PlantImageOrigin origin) async {
    origins.add(origin);
    final data = await rootBundle.load('assets/images/test/${next++}.jpg');
    return data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
  }

  @override
  Future<Uint8List?> recover() async => null;
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('real local ONNX recognition through /identify without HTTP', (
    tester,
  ) async {
    var requests = 0;
    final source = _ReferenceImageSource();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantImageSourceProvider.overrideWithValue(source),
          httpClientProvider.overrideWithValue(
            MockClient((request) async {
              requests++;
              throw StateError('Unexpected HTTP during local recognition');
            }),
          ),
        ],
        child: const BoticarioApp(),
      ),
    );
    await tester.pumpAndSettle();
    final router = GoRouter.of(tester.element(find.byType(HomePage)));
    router.go('/identify');
    await tester.pumpAndSettle();
    expect(find.byType(PlantRecognitionPage), findsOneWidget);

    Future<void> pick(String label) async {
      final button = find.widgetWithText(OutlinedButton, label);
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();
    }

    Future<void> identify(String scientificName) async {
      final button = find.byKey(const ValueKey('identifyPlant'));
      await tester.ensureVisible(button);
      expect(tester.widget<FilledButton>(button).onPressed, isNotNull);
      await tester.tap(button);
      await tester.pump();
      expect(tester.widget<FilledButton>(button).onPressed, isNull);
      final deadline = DateTime.now().add(const Duration(seconds: 60));
      while (find.byType(LinearProgressIndicator).evaluate().isNotEmpty &&
          DateTime.now().isBefore(deadline)) {
        await Future<void>.delayed(const Duration(milliseconds: 100));
        await tester.pump();
      }
      await tester.pumpAndSettle();
      expect(find.text('Especies candidatas'), findsOneWidget);
      expect(find.textContaining('1. $scientificName'), findsOneWidget);
      for (var i = 0; i < 5; i++) {
        expect(find.byKey(ValueKey('plantCandidate$i')), findsOneWidget);
      }
      expect(tester.widget<FilledButton>(button).onPressed, isNotNull);
    }

    await pick('Seleccionar de galería');
    await identify('Cirsium vulgare');
    await identify('Cirsium vulgare');
    await pick('Tomar fotografía');
    expect(find.text('Especies candidatas'), findsNothing);
    await identify('Chaerophyllum temulum');
    await pick('Descartar imagen');
    expect(find.text('Especies candidatas'), findsNothing);
    expect(
      tester
          .widget<FilledButton>(find.byKey(const ValueKey('identifyPlant')))
          .onPressed,
      isNull,
    );
    expect(source.origins, [PlantImageOrigin.gallery, PlantImageOrigin.camera]);
    await tester.tap(find.text('Inicio'));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, '/');
    router.go('/identify');
    await tester.pumpAndSettle();
    expect(find.text('Especies candidatas'), findsNothing);
    expect(find.byType(Image), findsNothing);
    expect(requests, 0);
    expect(tester.takeException(), isNull);
  });
}
