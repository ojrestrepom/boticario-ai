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
import '../../support/fake_plant_image_source.dart';

import 'package:boticario_ai/features/plant_recognition/data/plant_image_source.dart';

import 'dart:async';
import 'dart:typed_data';

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
              overrides: [
                httpClientProvider.overrideWithValue(api.client),
                plantImageSourceProvider.overrideWithValue(
                  FakePlantImageSource(),
                ),
              ],
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
            expect(button.onPressed, isNotNull);
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
          ProviderScope(
            overrides: [
              plantImageSourceProvider.overrideWithValue(
                FakePlantImageSource(),
              ),
            ],
            child: MaterialApp(
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
          ),
        );
        await tester.pumpAndSettle();
        for (final text in [
          'Identificar planta',
          'Aquí se mostrará la imagen',
          'Tomar fotografía',
          'Seleccionar de galería',
        ]) {
          // The page title and new recognition button share their label.
          final finder = find.text(text).first;
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
          expect(node.flagsCollection.isEnabled.toBoolOrNull(), isTrue);
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
  testWidgets(
    'preview, replace, cancel, recoverable error and discard without HTTP',
    (tester) async {
      final source = FakePlantImageSource();
      final first = (await tester.runAsync(() => plantTestImage()))!;
      final second = (await tester.runAsync(
        () => plantTestImage(width: 4, height: 8),
      ))!;
      source.onPick = (_) async => first;
      final api = FakeCatalogApi();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            plantImageSourceProvider.overrideWithValue(source),
            httpClientProvider.overrideWithValue(api.client),
          ],
          child: const BoticarioApp(),
        ),
      );
      await tester.pumpAndSettle();
      final router = GoRouter.of(tester.element(find.byType(HomePage)));
      router.go('/identify');
      await tester.pumpAndSettle();
      Future<void> tap(String label) async {
        await tester.ensureVisible(find.text(label));
        await tester.tap(find.text(label));
        await tester.pumpAndSettle();
      }

      await tap('Tomar fotografía');
      Image preview() => tester.widget<Image>(find.byType(Image));
      expect(preview().fit, BoxFit.contain);
      expect(
        ((preview().image as ResizeImage).imageProvider as MemoryImage).bytes,
        same(first),
      );
      source.onPick = (_) async => null;
      await tap('Seleccionar de galería');
      expect(
        ((preview().image as ResizeImage).imageProvider as MemoryImage).bytes,
        same(first),
      );
      source.onPick = (_) async =>
          throw const PlantImageFailure('Permiso denegado');
      await tap('Tomar fotografía');
      expect(find.text('Permiso denegado'), findsOneWidget);
      expect(
        ((preview().image as ResizeImage).imageProvider as MemoryImage).bytes,
        same(first),
      );
      source.onPick = (_) async => second;
      await tap('Seleccionar de galería');
      expect(
        ((preview().image as ResizeImage).imageProvider as MemoryImage).bytes,
        same(second),
      );
      expect(find.text('Permiso denegado'), findsNothing);
      await tap('Descartar imagen');
      expect(find.byType(Image), findsNothing);
      expect(find.text('Aquí se mostrará la imagen'), findsOneWidget);
      expect(api.requests, isEmpty);
      expect(source.origins, [
        PlantImageOrigin.camera,
        PlantImageOrigin.gallery,
        PlantImageOrigin.camera,
        PlantImageOrigin.gallery,
      ]);
    },
  );
  testWidgets(
    'leaving during acquisition clears the session and ignores its completion',
    (tester) async {
      final source = FakePlantImageSource();
      final pending = Completer<Uint8List?>();
      source.onPick = (_) => pending.future;
      final image = (await tester.runAsync(() => plantTestImage()))!;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [plantImageSourceProvider.overrideWithValue(source)],
          child: const BoticarioApp(),
        ),
      );
      await tester.pumpAndSettle();
      final router = GoRouter.of(tester.element(find.byType(HomePage)));
      router.go('/identify');
      await tester.pumpAndSettle();
      await tester.tap(find.text('Tomar fotografía'));
      await tester.pump();
      expect(
        tester
            .widget<OutlinedButton>(
              find.widgetWithText(OutlinedButton, 'Tomar fotografía'),
            )
            .onPressed,
        isNull,
      );
      await tester.tap(find.text('Inicio'));
      await tester.pumpAndSettle();
      router.go('/identify');
      await tester.pumpAndSettle();
      pending.complete(image);
      await tester.pumpAndSettle();
      expect(find.byType(Image), findsNothing);
      expect(find.text('Aquí se mostrará la imagen'), findsOneWidget);
      expect(
        tester
            .widget<OutlinedButton>(
              find.widgetWithText(OutlinedButton, 'Tomar fotografía'),
            )
            .onPressed,
        isNotNull,
      );
    },
  );

  for (final scale in [1.0, 2.0]) {
    for (final portrait in [false, true]) {
      testWidgets(
        'preview and discard accessible at $scale portrait=$portrait',
        (tester) async {
          tester.view.physicalSize = const Size(360, 640);
          tester.view.devicePixelRatio = 1;
          addTearDown(tester.view.reset);
          final image = (await tester.runAsync(
            () => plantTestImage(
              width: portrait ? 4 : 8,
              height: portrait ? 8 : 4,
            ),
          ))!;
          final source = FakePlantImageSource()..onPick = (_) async => image;
          await tester.pumpWidget(
            ProviderScope(
              overrides: [plantImageSourceProvider.overrideWithValue(source)],
              child: MaterialApp(
                theme: buildBoticarioTheme(),
                home: Builder(
                  builder: (context) => MediaQuery(
                    data: MediaQuery.of(context)
                        .copyWith(textScaler: TextScaler.linear(scale)),
                    child: PlantRecognitionPage(onBack: () {}, onHome: () {}),
                  ),
                ),
              ),
            ),
          );
          await tester.pumpAndSettle();
          await tester.ensureVisible(find.text('Seleccionar de galería'));
          await tester.tap(find.text('Seleccionar de galería'));
          await tester.pumpAndSettle();
          expect(tester.widget<Image>(find.byType(Image)).fit, BoxFit.contain);
          expect(
            tester.widget<Image>(find.byType(Image)).semanticLabel,
            'Imagen seleccionada de la planta',
          );
          await tester.ensureVisible(find.text('Descartar imagen'));
          final paragraph = tester.renderObject<RenderParagraph>(
            find.text('Descartar imagen'),
          );
          expect(paragraph.didExceedMaxLines, isFalse);
          expect(tester.takeException(), isNull);
          await tester.tap(find.text('Descartar imagen'));
          await tester.pumpAndSettle();
          expect(find.byType(Image), findsNothing);
        },
      );
    }
  }
}
