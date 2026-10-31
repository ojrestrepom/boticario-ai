// Native QA: cancel each picker with Back. With PLANT_NATIVE_ACQUIRE=true,
// accept a photo and select a gallery image instead (host/emulator interaction).
// flutter test integration_test/plant_image_acquisition_test.dart -d emulator-5554
import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/plant_recognition/application/plant_image_controller.dart';
import 'package:boticario_ai/features/plant_recognition/presentation/plant_recognition_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/testing.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  const acquire = bool.fromEnvironment('PLANT_NATIVE_ACQUIRE');
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'Android recovery, native picker cancellation and returns without HTTP',
    (tester) async {
      var httpRequests = 0;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            httpClientProvider.overrideWithValue(
              MockClient((request) async {
                httpRequests++;
                throw StateError('Unexpected HTTP during image acquisition');
              }),
            ),
          ],
          child: const BoticarioApp(),
        ),
      );
      await tester.pumpAndSettle();
      final home = tester.element(find.byType(HomePage));
      final router = GoRouter.of(home);
      final container = ProviderScope.containerOf(home);
      router.go('/identify');
      await tester.pumpAndSettle();
      expect(find.byType(PlantRecognitionPage), findsOneWidget);
      expect(container.read(plantImageControllerProvider).error, isNull);
      for (final action in ['Tomar fotografía', 'Seleccionar de galería']) {
        await tester.ensureVisible(find.text(action));
        await tester.tap(find.text(action));
        await tester.pump();
        debugPrint('[PlantImageAndroid] waiting for native result: $action');
        final deadline = DateTime.now().add(const Duration(seconds: 90));
        while (container.read(plantImageControllerProvider).busy &&
            DateTime.now().isBefore(deadline)) {
          await Future<void>.delayed(const Duration(milliseconds: 250));
          await tester.pump();
        }
        await tester.pumpAndSettle();
        final state = container.read(plantImageControllerProvider);
        expect(
          state.busy,
          isFalse,
          reason: 'Complete or cancel the system picker on the emulator',
        );
        expect(state.error, isNull);
        expect(state.image, acquire ? isNotNull : isNull);
        if (acquire) {
          expect(find.byType(Image), findsOneWidget);
          expect(tester.widget<Image>(find.byType(Image)).fit, BoxFit.contain);
          await tester.ensureVisible(find.text('Descartar imagen'));
          await tester.tap(find.text('Descartar imagen'));
          await tester.pumpAndSettle();
        }
        expect(find.text('Aquí se mostrará la imagen'), findsOneWidget);
      }
      await tester.ensureVisible(find.byTooltip('Volver a Inicio'));
      await tester.tap(find.byTooltip('Volver a Inicio'));
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/');
      router.go('/identify');
      await tester.pumpAndSettle();
      await tester.tap(find.text('Inicio'));
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/');
      expect(httpRequests, 0);
    },
  );
}
