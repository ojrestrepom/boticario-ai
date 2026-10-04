import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_repository.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const identities = [
  ('544', 'Lavanda', 'Lavandula angustifolia'),
  ('401', 'Eucalipto', 'Eucalyptus globulus'),
  ('873', 'Romero', 'Rosmarinus officinalis'),
  ('605', 'Manzanilla', 'Matricaria recutita'),
  ('619', 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
];
const invalidIds = [
  '999999',
  'text',
  '-544',
  '-1',
  '0',
  '',
  '99999999999999999999999999999999999999999999999999',
  '-99999999999999999999999999999999999999999999999999',
];
const insets = EdgeInsets.fromLTRB(8, 24, 8, 20);
const notFound = 'Planta no encontrada';
const loading = 'Cargando catálogo...';
const failed = 'No se pudo cargar el catálogo';
const disabledNav = [
  'Favoritos no disponible',
  'Historial no disponible',
  'Perfil no disponible',
];

class DenyHttp extends HttpOverrides {
  int calls = 0;
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    calls++;
    throw StateError('QA denies network');
  }
}

class Harness {
  Harness(String initialId, this.load) : id = ValueNotifier(initialId);
  final ValueNotifier<String> id;
  final Future<String> Function(String) load;
  int backs = 0;
  int homes = 0;

  Future<void> mount(WidgetTester tester, {double scale = 1}) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(id.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantCatalogAssetDataSourceProvider.overrideWithValue(
            PlantCatalogAssetDataSource(loadAsset: load),
          ),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: TextScaler.linear(scale),
              padding: insets,
              viewPadding: insets,
            ),
            child: child!,
          ),
          home: ValueListenableBuilder<String>(
            valueListenable: id,
            builder: (_, value, _) => PlantPassportRoutePage(
              key: const ValueKey('same-P05-entry'),
              plantId: value,
              onBack: () => backs++,
              onHome: () => homes++,
            ),
          ),
        ),
      ),
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  // IO outside fake async, no product assets/config/dependencies changed.
  final json = File('assets/data/plant_catalog.json').readAsStringSync();
  final sdk =
      Platform.environment['QA_FLUTTER_SDK'] ?? '/opt/homebrew/share/flutter';
  final fontDir =
      Platform.environment['QA_PASSPORT_ROBOTO_DIR'] ??
      '$sdk/engine/src/flutter/txt/third_party/fonts';
  setUpAll(() async {
    final loader = FontLoader('Roboto');
    for (final name in ['Roboto-Regular.ttf', 'Roboto-Medium.ttf']) {
      loader.addFont(
        Future.value(
          ByteData.sublistView(File('$fontDir/$name').readAsBytesSync()),
        ),
      );
    }
    await loader.load();
    print(
      'Route QA: SDK Roboto, host 360x640, safe insets 8/24/8/20; not Android',
    );
  });

  void noSubstitute() {
    expect(find.byType(PlantPassportPage), findsNothing);
    for (final item in identities) {
      expect(find.text(item.$2), findsNothing);
      expect(find.text(item.$3), findsNothing);
    }
    expect(find.byType(ChoiceChip), findsNothing);
    expect(find.byType(AlertDialog), findsNothing);
    expect(find.byType(SnackBar), findsNothing);
  }

  Future<void> navigation(WidgetTester tester, Harness harness) async {
    final semantics = tester.ensureSemantics();
    try {
      final back = find.byTooltip('Volver a Explorar');
      final home = find.bySemanticsLabel('Inicio');
      final homeNode = tester.getSemantics(home);
      expect(homeNode.flagsCollection.isEnabled, ui.Tristate.isTrue);
      expect(homeNode.flagsCollection.isSelected, ui.Tristate.isTrue);
      expect(
        homeNode.getSemanticsData().hasAction(ui.SemanticsAction.tap),
        isTrue,
      );
      for (final label in disabledNav) {
        final target = find.bySemanticsLabel(label);
        expect(target, findsOneWidget);
        final node = tester.getSemantics(target);
        expect(node.label, label);
        expect(node.flagsCollection.isButton, isTrue);
        expect(node.flagsCollection.isEnabled, ui.Tristate.isFalse);
        expect(
          node.getSemanticsData().hasAction(ui.SemanticsAction.tap),
          isFalse,
        );
        await tester.tap(target);
        await tester.pump();
      }
      expect(harness.backs, 0);
      expect(harness.homes, 0);
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.byType(SnackBar), findsNothing);
      await tester.tap(back);
      await tester.tap(home);
      await tester.pump();
      expect(harness.backs, 1);
      expect(harness.homes, 1);
      expect(find.byType(PlantPassportRoutePage), findsOneWidget);
    } finally {
      semantics.dispose();
    }
  }

  for (final entry in identities) {
    testWidgets('RQA01-${entry.$1} exact identity and local callbacks', (
      tester,
    ) async {
      var reads = 0;
      final harness = Harness(entry.$1, (path) async {
        expect(path, plantCatalogAssetPath);
        reads++;
        return json;
      });
      await harness.mount(tester);
      await tester.pumpAndSettle();
      expect(find.text(entry.$2), findsWidgets);
      expect(find.text(entry.$3), findsWidgets);
      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'General'))
            .selected,
        isTrue,
      );
      expect(find.text('No disponible en fuente'), findsNWidgets(2));
      expect(find.text('No aplicable: ficha de planta'), findsOneWidget);
      expect(find.text(notFound), findsNothing);
      await navigation(tester, harness);
      expect(reads, 1);
      expect(tester.takeException(), isNull);
    });
  }

  for (var i = 0; i < invalidIds.length; i++) {
    testWidgets('RQA02-$i invalid ID safely stays inside P05', (tester) async {
      final harness = Harness(invalidIds[i], (_) async => json);
      await harness.mount(tester);
      await tester.pumpAndSettle();
      expect(find.text(notFound), findsOneWidget);
      expect(find.text(failed), findsNothing);
      expect(find.text('Reintentar'), findsNothing);
      noSubstitute();
      await navigation(tester, harness);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('RQA03 known to unknown to known resets General without reload', (
    tester,
  ) async {
    var reads = 0;
    final harness = Harness('544', (_) async {
      reads++;
      return json;
    });
    await harness.mount(tester);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text('Registros tradicionales'), findsOneWidget);
    harness.id.value = 'text';
    await tester.pumpAndSettle();
    expect(find.text(notFound), findsOneWidget);
    noSubstitute();
    harness.id.value = '401';
    await tester.pumpAndSettle();
    expect(find.text('Eucalyptus globulus'), findsWidgets);
    expect(
      tester
          .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'General'))
          .selected,
      isTrue,
    );
    expect(find.text('Registros tradicionales'), findsNothing);
    await tester.tap(find.text('Propiedades'));
    await tester.pumpAndSettle();
    harness.id.value = '619';
    await tester.pumpAndSettle();
    expect(find.text(identities.last.$3), findsWidgets);
    expect(
      tester
          .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'General'))
          .selected,
      isTrue,
    );
    expect(reads, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('RQA04 genuinely deferred first load resolves latest route ID', (
    tester,
  ) async {
    final read = Completer<String>();
    var reads = 0;
    final harness = Harness('544', (_) {
      reads++;
      return read.future;
    });
    await harness.mount(tester);
    await tester.pump();
    expect(find.text(loading), findsOneWidget);
    noSubstitute();
    await navigation(tester, harness);
    harness.id.value = '605';
    await tester.pump();
    expect(find.text(loading), findsOneWidget);
    read.complete(json);
    await tester.pumpAndSettle();
    expect(find.text('Manzanilla'), findsWidgets);
    expect(find.text('Lavanda'), findsNothing);
    expect(reads, 1);
    expect(tester.takeException(), isNull);
  });

  for (final mode in ['read-known', 'invalid-known', 'read-unknown']) {
    testWidgets('RQA05-$mode explicit local retry with no automatic retry', (
      tester,
    ) async {
      var reads = 0;
      final second = Completer<String>();
      final harness = Harness(mode == 'read-unknown' ? '999999' : '873', (_) {
        reads++;
        if (reads == 1) {
          return mode == 'invalid-known'
              ? Future.value('{invalid private-technical-detail')
              : Future.error(StateError('private-technical-detail'));
        }
        return second.future;
      });
      await harness.mount(tester);
      await tester.pumpAndSettle();
      expect(find.text(failed), findsOneWidget);
      expect(find.text(notFound), findsNothing);
      expect(find.textContaining('private-technical-detail'), findsNothing);
      noSubstitute();
      // Virtual time specifically probes retry timers, not a real-time UI wait.
      await tester.pump(const Duration(seconds: 30));
      expect(reads, 1);
      await navigation(tester, harness);
      await tester.tap(find.text('Reintentar'));
      await tester.pump();
      expect(reads, 2);
      expect(find.text(loading), findsOneWidget);
      expect(find.text(failed), findsNothing);
      expect(find.text('Reintentar'), findsNothing);
      noSubstitute();
      second.complete(json);
      await tester.pumpAndSettle();
      if (mode == 'read-unknown') {
        expect(find.text(notFound), findsOneWidget);
        noSubstitute();
      } else {
        expect(find.text('Romero'), findsWidgets);
        expect(find.text('Rosmarinus officinalis'), findsWidgets);
        expect(find.text('Lavanda'), findsNothing);
      }
      expect(reads, 2);
      expect(tester.takeException(), isNull);
    });
  }

  for (final state in ['loading', 'error', 'notfound']) {
    for (final scale in [1.0, 2.0]) {
      testWidgets('RQA06-$state-$scale safe layout glyphs semantics and 48dp', (
        tester,
      ) async {
        final pending = Completer<String>();
        final harness = Harness(
          '999999',
          (_) => switch (state) {
            'loading' => pending.future,
            'error' => Future.error(StateError('private-technical-detail')),
            _ => Future.value(json),
          },
        );
        await harness.mount(tester, scale: scale);
        await tester.pumpAndSettle();
        final title = switch (state) {
          'loading' => loading,
          'error' => failed,
          _ => notFound,
        };
        expect(find.text(title), findsOneWidget);
        noSubstitute();
        final sem = tester.ensureSemantics();
        for (final target in [
          find.byTooltip('Volver a Explorar'),
          find.bySemanticsLabel('Inicio'),
          ...disabledNav.map(find.bySemanticsLabel),
          if (state == 'error') find.widgetWithText(TextButton, 'Reintentar'),
        ]) {
          expect(target.hitTestable(), findsOneWidget);
          final rect = tester.getRect(target);
          expect(rect.shortestSide, greaterThanOrEqualTo(48));
          expect(rect.top, greaterThanOrEqualTo(insets.top));
          expect(rect.bottom, lessThanOrEqualTo(640 - insets.bottom));
          expect(rect.left, greaterThanOrEqualTo(insets.left));
          expect(rect.right, lessThanOrEqualTo(360 - insets.right));
        }
        // Check actual rendered glyph boxes, not merely Text widgets existing.
        for (final element in find.byType(Text).evaluate()) {
          final target = find.byWidget(element.widget);
          final paragraph = tester.renderObject<RenderParagraph>(target);
          final plain = paragraph.text.toPlainText();
          expect(paragraph.didExceedMaxLines, isFalse, reason: plain);
          expect(
            paragraph.overflow,
            isNot(TextOverflow.ellipsis),
            reason: plain,
          );
          final spacing = (paragraph.text.style?.letterSpacing ?? 0).abs() / 2;
          for (final word in RegExp(r'\S+').allMatches(plain)) {
            for (final box in paragraph.getBoxesForSelection(
              TextSelection(baseOffset: word.start, extentOffset: word.end),
            )) {
              expect(box.left, greaterThanOrEqualTo(-0.1), reason: plain);
              expect(
                box.right,
                lessThanOrEqualTo(paragraph.size.width + spacing + 0.1),
                reason: plain,
              );
              final global = box.toRect().shift(
                paragraph.localToGlobal(Offset.zero),
              );
              expect(
                global.top,
                greaterThanOrEqualTo(insets.top - 0.1),
                reason: plain,
              );
              expect(
                global.bottom,
                lessThanOrEqualTo(640 - insets.bottom + 0.1),
                reason: plain,
              );
            }
          }
        }
        sem.dispose();
        await navigation(tester, harness);
        expect(find.text(title), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  }

  testWidgets(
    'RQA07 route content actions inert on three tabs and bounded content',
    (tester) async {
      final harness = Harness('544', (_) async => json);
      await harness.mount(tester);
      await tester.pumpAndSettle();
      final sem = tester.ensureSemantics();
      for (final tab in ['General', 'Propiedades', 'Usos']) {
        final scroll = find.descendant(
          of: find.byType(CustomScrollView),
          matching: find.byType(Scrollable),
        );
        tester.state<ScrollableState>(scroll).position.jumpTo(0);
        await tester.pumpAndSettle();
        await tester.tap(find.text(tab));
        await tester.pumpAndSettle();
        expect(
          tester
              .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, tab))
              .selected,
          isTrue,
        );
        for (final label in [
          'Favorito no disponible',
          'Ver formulaciones relacionadas no disponible',
        ]) {
          final target = find.bySemanticsLabel(label);
          await tester.ensureVisible(target);
          await tester.pumpAndSettle();
          final node = tester.getSemantics(target);
          expect(node.flagsCollection.isEnabled, ui.Tristate.isFalse);
          expect(
            node.getSemanticsData().hasAction(ui.SemanticsAction.tap),
            isFalse,
          );
          await tester.tap(target);
          await tester.pumpAndSettle();
          expect(find.byType(PlantPassportRoutePage), findsOneWidget);
          expect(find.byType(AlertDialog), findsNothing);
          expect(find.byType(SnackBar), findsNothing);
          expect(find.byIcon(Icons.favorite), findsNothing);
          expect(harness.backs, 0);
          expect(harness.homes, 0);
          expect(
            tester
                .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, tab))
                .selected,
            isTrue,
          );
        }
        expect(
          tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
          isNull,
        );
        for (final invented in [
          'Dosis',
          'Recomendaciones',
          'Origen ilustrativo',
          'Descripción ilustrativa',
        ]) {
          expect(find.text(invented), findsNothing);
        }
        if (tab == 'Propiedades') {
          expect(
            find.text('sin propiedades medicinales evaluadas en este catálogo'),
            findsOneWidget,
          );
        }
        if (tab == 'Usos') {
          expect(
            find.text(
              'No es una recomendación de uso ni evidencia de eficacia clínica',
            ),
            findsOneWidget,
          );
        }
      }
      sem.dispose();
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('RQA08 local route and retry require zero HTTP requests', (
    tester,
  ) async {
    final deny = DenyHttp();
    final previous = HttpOverrides.current;
    HttpOverrides.global = deny;
    addTearDown(() => HttpOverrides.global = previous);
    var reads = 0;
    final harness = Harness('544', (_) async {
      if (++reads == 1) throw StateError('local inaccessible');
      return json;
    });
    await harness.mount(tester);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    for (final entry in identities) {
      harness.id.value = entry.$1;
      await tester.pumpAndSettle();
      expect(find.text(entry.$3), findsWidgets);
      expect(find.byType(Image), findsNothing);
    }
    harness.id.value = 'text';
    await tester.pumpAndSettle();
    expect(find.text(notFound), findsOneWidget);
    expect(deny.calls, 0);
    expect(reads, 2);
    expect(tester.takeException(), isNull);
  });

  testWidgets('RQA09 repeated local failure can be retried explicitly again', (
    tester,
  ) async {
    var reads = 0;
    final second = Completer<String>();
    final third = Completer<String>();
    final harness = Harness('619', (_) {
      reads++;
      return switch (reads) {
        1 => Future.error(StateError('private-first-failure')),
        2 => second.future,
        _ => third.future,
      };
    });
    await harness.mount(tester);
    await tester.pumpAndSettle();
    expect(find.text(failed), findsOneWidget);
    await tester.tap(find.text('Reintentar'));
    await tester.pump();
    expect(find.text(loading), findsOneWidget);
    second.completeError(StateError('private-second-failure'));
    await tester.pumpAndSettle();
    expect(find.text(failed), findsOneWidget);
    expect(find.textContaining('private-'), findsNothing);
    noSubstitute();
    await tester.pump(const Duration(seconds: 30));
    expect(reads, 2);
    await tester.tap(find.text('Reintentar'));
    await tester.pump();
    expect(find.text(loading), findsOneWidget);
    expect(reads, 3);
    third.complete(json);
    await tester.pumpAndSettle();
    expect(find.text(identities.last.$3), findsWidgets);
    expect(find.text(failed), findsNothing);
    expect(reads, 3);
    expect(tester.takeException(), isNull);
  });
}
