import 'dart:async';

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_image_source.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_predictions.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_recognition_service.dart';
import 'package:boticario_ai/features/plant_recognition/presentation/plant_recognition_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_plant_image_source.dart';
import '../../support/fake_plant_recognition_service.dart';

void main() {
  testWidgets('select, identify, Top-5, replace, cancel and discard', (
    tester,
  ) async {
    final first = (await tester.runAsync(() => plantTestImage()))!;
    final second = (await tester.runAsync(
      () => plantTestImage(width: 4, height: 8),
    ))!;
    final source = FakePlantImageSource()..onPick = (_) async => first;
    final service = FakePlantRecognitionService();
    final pending = Completer<List<PlantPrediction>>();
    service.onRecognize = (_) => pending.future;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantImageSourceProvider.overrideWithValue(source),
          plantRecognitionServiceProvider.overrideWithValue(service),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          home: PlantRecognitionPage(onBack: () {}, onHome: () {}),
        ),
      ),
    );

    final identify = find.byKey(const ValueKey('identifyPlant'));
    expect(tester.widget<FilledButton>(identify).onPressed, isNull);
    Future<void> tap(String label) async {
      final target = find.widgetWithText(OutlinedButton, label);
      await tester.ensureVisible(target);
      await tester.tap(target);
      await tester.pumpAndSettle();
    }

    await tap('Tomar fotografía');
    await tester.ensureVisible(identify);
    await tester.tap(identify);
    await tester.pump();
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(tester.widget<FilledButton>(identify).onPressed, isNull);
    await tester.tap(identify);
    expect(service.images, hasLength(1));
    pending.complete(FakePlantRecognitionService.candidates);
    await tester.pumpAndSettle();
    expect(find.text('Especies candidatas'), findsOneWidget);
    for (var i = 0; i < 5; i++) {
      expect(find.text('${i + 1}. Species candidate $i'), findsOneWidget);
    }
    expect(find.text('53.12 %'), findsOneWidget);
    expect(find.text('20.00 %'), findsOneWidget);
    expect(find.textContaining('no indican la probabilidad'), findsOneWidget);
    source.onPick = (_) async => null;
    await tap('Seleccionar de galería');
    expect(find.text('Especies candidatas'), findsOneWidget);
    source.onPick = (_) async => second;
    await tap('Seleccionar de galería');
    expect(find.text('Especies candidatas'), findsNothing);
    service.onRecognize = null;
    await tester.ensureVisible(identify);
    await tester.tap(identify);
    await tester.pumpAndSettle();
    expect(find.text('Especies candidatas'), findsOneWidget);
    await tap('Descartar imagen');
    expect(find.text('Especies candidatas'), findsNothing);
    expect(tester.widget<FilledButton>(identify).onPressed, isNull);
    expect(tester.takeException(), isNull);
  });

  testWidgets('friendly failure can retry; disposing ignores pending result', (
    tester,
  ) async {
    final image = (await tester.runAsync(() => plantTestImage()))!;
    final source = FakePlantImageSource()..onPick = (_) async => image;
    final service = FakePlantRecognitionService()
      ..onRecognize = (_) async => throw StateError('technical error');
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantImageSourceProvider.overrideWithValue(source),
          plantRecognitionServiceProvider.overrideWithValue(service),
        ],
        child: MaterialApp(
          home: PlantRecognitionPage(onBack: () {}, onHome: () {}),
        ),
      ),
    );
    await tester.tap(find.text('Tomar fotografía'));
    await tester.pumpAndSettle();
    final identify = find.byKey(const ValueKey('identifyPlant'));
    await tester.ensureVisible(identify);
    await tester.tap(identify);
    await tester.pumpAndSettle();
    expect(find.textContaining('No se pudo identificar'), findsOneWidget);
    expect(find.textContaining('technical'), findsNothing);
    final pending = Completer<List<PlantPrediction>>();
    service.onRecognize = (_) => pending.future;
    await tester.ensureVisible(identify);
    await tester.tap(identify);
    await tester.pump();
    await tester.pumpWidget(const SizedBox());
    pending.complete(FakePlantRecognitionService.candidates);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
