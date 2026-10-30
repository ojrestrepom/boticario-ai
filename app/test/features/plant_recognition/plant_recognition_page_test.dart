import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/plant_recognition/presentation/plant_recognition_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../../support/fake_catalog_api.dart';

void main() {
  for (final direct in [false, true]) {
    for (final exit in ['app', 'system', 'home']) {
      testWidgets('identify direct=$direct return=$exit without HTTP', (
        tester,
      ) async {
        final api = FakeCatalogApi(requiredToken: testApiToken);
        final logs = <String>[];
        final original = debugPrint;
        debugPrint = (String? message, {int? wrapWidth}) {
          if (message?.startsWith('[Home]') ?? false) {
            logs.add(message!);
          } else {
            original(message, wrapWidth: wrapWidth);
          }
        };
        try {
          await tester.pumpWidget(
            ProviderScope(
              overrides: [httpClientProvider.overrideWithValue(api.client)],
              child: const BoticarioApp(),
            ),
          );
          await tester.pumpAndSettle();
          final router = GoRouter.of(tester.element(find.byType(HomePage)));
          if (direct) {
            router.go('/identify');
          } else {
            final card = find.byKey(
              const ValueKey(HomeAction.identifyWithCamera),
            );
            await tester.ensureVisible(card);
            await tester.tap(card);
          }
          await tester.pumpAndSettle();
          expect(router.state.uri.path, '/identify');
          expect(find.byType(PlantRecognitionPage), findsOneWidget);
          expect(
            logs,
            direct ? isEmpty : equals(['[Home] Identificar con cámara']),
          );
          for (final tab in ['Favoritos', 'Historial', 'Perfil']) {
            await tester.tap(find.text(tab));
            await tester.pumpAndSettle();
            expect(router.state.uri.path, '/identify');
          }
          for (final button in tester.widgetList<OutlinedButton>(
            find.byType(OutlinedButton),
          )) {
            expect(button.onPressed, isNull);
            await tester.ensureVisible(find.byWidget(button));
            await tester.tap(find.byWidget(button));
          }
          expect(find.byType(SnackBar), findsNothing);
          expect(find.byType(Dialog), findsNothing);
          if (exit == 'system') {
            await tester.binding.handlePopRoute();
          } else if (exit == 'home') {
            await tester.tap(find.text('Inicio'));
          } else {
            await tester.ensureVisible(find.byTooltip('Volver a Inicio'));
            await tester.tap(find.byTooltip('Volver a Inicio'));
          }
          await tester.pumpAndSettle();
          expect(router.state.uri.path, '/');
          expect(router.canPop(), isFalse);
          expect(find.byType(HomePage), findsOneWidget);
          expect(api.requests, isEmpty);
        } finally {
          debugPrint = original;
        }
      });
    }
  }

  for (final scale in [1.0, 2.0]) {
    testWidgets('accessible layout at $scale in 360x640 with insets', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(360, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      final semantics = tester.ensureSemantics();
      try {
        await tester.pumpWidget(
          MaterialApp(
            theme: buildBoticarioTheme(),
            home: Builder(
              builder: (context) => MediaQuery(
                data: MediaQuery.of(context).copyWith(
                  textScaler: TextScaler.linear(scale),
                  padding: const EdgeInsets.fromLTRB(8, 24, 12, 24),
                ),
                child: PlantRecognitionPage(onBack: () {}, onHome: () {}),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        for (final text in [
          'Identificar planta',
          'Aquí se mostrará la imagen',
          'Cámara y galería no disponibles por ahora.',
          'Tomar fotografía',
          'Seleccionar de galería',
        ]) {
          final finder = find.text(text);
          await tester.ensureVisible(finder);
          await tester.pumpAndSettle();
          final paragraph = tester.renderObject<RenderParagraph>(finder);
          expect(paragraph.didExceedMaxLines, isFalse);
          final rect = tester.getRect(finder);
          expect(rect.left, greaterThanOrEqualTo(8));
          expect(rect.right, lessThanOrEqualTo(348));
        }
        for (final label in ['Tomar fotografía', 'Seleccionar de galería']) {
          final node = tester.getSemantics(
            find.widgetWithText(OutlinedButton, label),
          );
          expect(node.flagsCollection.isEnabled.toBoolOrNull(), isFalse);
        }
        final home = find.bySemanticsLabel('Inicio');
        expect(tester.getSize(home).height, greaterThanOrEqualTo(48));
        expect(tester.getRect(home).bottom, lessThanOrEqualTo(616));
        expect(tester.takeException(), isNull);
      } finally {
        semantics.dispose();
      }
    });
  }
}
