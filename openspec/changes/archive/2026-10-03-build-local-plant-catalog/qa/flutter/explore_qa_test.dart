import 'dart:async';
import 'dart:io';
import 'dart:ui' show Tristate;

import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_repository.dart';
import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:boticario_ai/app/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const plants = [
  ('Lavanda', 'Lavandula angustifolia', 544),
  ('Eucalipto', 'Eucalyptus globulus', 401),
  ('Romero', 'Rosmarinus officinalis', 873),
  ('Manzanilla', 'Matricaria recutita', 605),
  ('Menta', 'Mentha x piperita subsp. nothosubsp. piperita', 619),
];
const noMatch = 'No se encontraron plantas';
const noOils = 'No hay aceites disponibles en este catálogo';
const errorText = 'No se pudo cargar el catálogo local.';
const loadingText = 'Cargando catálogo...';
const safeInsets = EdgeInsets.fromLTRB(8, 24, 8, 20);

class DenyHttp extends HttpOverrides {
  int calls = 0;
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    calls++;
    throw StateError('QA prohibits HTTP');
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final json = File('assets/data/plant_catalog.json').readAsStringSync();

  Future<void> mount(
    WidgetTester tester, {
    Future<String> Function()? loader,
    double scale = 1,
    EdgeInsets padding = EdgeInsets.zero,
    ValueChanged<int>? selected,
    VoidCallback? home,
    VoidCallback? back,
    bool settle = true,
  }) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantCatalogRepositoryProvider.overrideWithValue(
            PlantCatalogRepository(
              dataSource: PlantCatalogAssetDataSource(
                loadAsset: (_) =>
                    loader == null ? Future.value(json) : loader(),
              ),
            ),
          ),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: TextScaler.linear(scale),
              padding: padding,
              viewPadding: padding,
            ),
            child: child!,
          ),
          home: ExplorePage(
            onBack: back ?? () {},
            onHome: home ?? () {},
            onPlantSelected: selected ?? (_) {},
          ),
        ),
      ),
    );
    if (settle) await tester.pumpAndSettle();
  }

  Future<void> reach(WidgetTester tester, Finder finder) async {
    if (finder.evaluate().isEmpty) {
      final scroll = tester.state<ScrollableState>(
        find
            .descendant(
              of: find.byType(CustomScrollView),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      scroll.position.jumpTo(0);
      await tester.pumpAndSettle();
    }
    if (finder.evaluate().isEmpty) {
      await tester.scrollUntilVisible(
        finder,
        100,
        scrollable: find
            .descendant(
              of: find.byType(CustomScrollView),
              matching: find.byType(Scrollable),
            )
            .first,
      );
    }
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
  }

  Future<void> filter(WidgetTester tester, String label) async {
    final chip = find.widgetWithText(ChoiceChip, label);
    await reach(tester, chip);
    await tester.tap(chip);
    await tester.pumpAndSettle();
    expect(tester.widget<ChoiceChip>(chip).selected, isTrue);
  }

  Future<void> query(WidgetTester tester, String value) async {
    await reach(tester, find.byType(TextField));
    await tester.enterText(find.byType(TextField), value);
    await tester.pumpAndSettle();
  }

  testWidgets('QA01 exact source labels, order and all five callback IDs', (
    tester,
  ) async {
    final ids = <int>[];
    await mount(tester, selected: ids.add);
    expect(find.text('Explorar'), findsOneWidget);
    expect(find.text('Buscar planta o aceite...'), findsOneWidget);
    double previous = -1;
    for (final plant in plants) {
      expect(find.text(plant.$1), findsOneWidget);
      expect(find.text(plant.$2), findsOneWidget);
      final y = tester.getTopLeft(find.text(plant.$1)).dy;
      expect(y, greaterThan(previous));
      previous = y;
    }
    for (final plant in plants) {
      await reach(tester, find.text(plant.$1));
      await tester.tap(find.text(plant.$1));
      expect(ids.last, plant.$3);
    }
    expect(ids, plants.map((p) => p.$3).toList());
    for (final alias in [
      'Salvia rosmarinus',
      'Matricaria chamomilla',
      'Mentha piperita',
    ]) {
      expect(find.text(alias), findsNothing);
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('QA02 reactive substring normalization on both visible names', (
    tester,
  ) async {
    await mount(tester);
    for (final item in [
      ('  ÁNZÁ  ', 'Manzanilla'),
      ('  ROSMARÍNUS   OFFICINALIS  ', 'Romero'),
      ('NOTHOSUBSP.', 'Menta'),
    ]) {
      await query(tester, item.$1);
      for (final plant in plants) {
        expect(
          find.text(plant.$1),
          plant.$1 == item.$2 ? findsOneWidget : findsNothing,
        );
      }
    }
    await query(tester, '   \t  ');
    for (final plant in plants) {
      expect(find.text(plant.$1), findsOneWidget);
    }
    await query(tester, '🌿');
    expect(find.text(noMatch), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('QA03 filter-query decisions and clear retain Aceites/Plantas', (
    tester,
  ) async {
    await mount(tester);
    await query(tester, 'lav');
    for (final label in ['Plantas', 'Todas']) {
      await filter(tester, label);
      expect(find.text('Lavanda'), findsOneWidget);
      expect(find.text('Menta'), findsNothing);
    }
    await filter(tester, 'Aceites');
    expect(find.text(noOils), findsOneWidget);
    expect(find.text(noMatch), findsNothing);
    await reach(tester, find.byTooltip('Borrar búsqueda'));
    await tester.tap(find.byTooltip('Borrar búsqueda'));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Aceites'))
          .selected,
      isTrue,
    );
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller!.text,
      isEmpty,
    );
    expect(find.text(noOils), findsOneWidget);
    for (final plant in plants) {
      expect(find.text(plant.$1), findsNothing);
    }
    await filter(tester, 'Plantas');
    await query(tester, 'unknown');
    expect(find.text(noMatch), findsOneWidget);
    await reach(tester, find.byTooltip('Borrar búsqueda'));
    await tester.tap(find.byTooltip('Borrar búsqueda'));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Plantas'))
          .selected,
      isTrue,
    );
    for (final plant in plants) {
      expect(find.text(plant.$1), findsOneWidget);
    }
    await filter(tester, 'Plantas');
    expect(
      tester
          .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Plantas'))
          .selected,
      isTrue,
    );
  });

  testWidgets(
    'QA04 malformed asset, repeated local retry and preserved query/filter',
    (tester) async {
      final recovery = Completer<String>();
      var attempts = 0;
      await mount(
        tester,
        loader: () {
          attempts++;
          return attempts < 3 ? Future.value('{invalid json') : recovery.future;
        },
      );
      expect(attempts, 1);
      expect(find.text(errorText), findsOneWidget);
      expect(find.text(noMatch), findsNothing);
      await query(tester, 'glob');
      await filter(tester, 'Plantas');
      await reach(tester, find.text('Reintentar'));
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(attempts, 2);
      expect(find.text(errorText), findsOneWidget);
      await tester.tap(find.text('Reintentar'));
      await tester.pump();
      expect(attempts, 3);
      expect(find.text(loadingText), findsOneWidget);
      expect(find.text(errorText), findsNothing);
      recovery.complete(json);
      await tester.pumpAndSettle();
      expect(find.text('Eucalipto'), findsOneWidget);
      expect(find.text('Lavanda'), findsNothing);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'glob',
      );
      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Plantas'))
            .selected,
        isTrue,
      );
      expect(find.textContaining('invalid json'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('QA05 loading dominates empty Aceites until resolution', (
    tester,
  ) async {
    final gate = Completer<String>();
    await mount(tester, loader: () => gate.future, settle: false);
    await tester.pump();
    await filter(tester, 'Aceites');
    await query(tester, 'does not exist');
    expect(find.text(loadingText), findsOneWidget);
    expect(find.text(noOils), findsNothing);
    expect(find.text(noMatch), findsNothing);
    gate.complete(json);
    await tester.pumpAndSettle();
    expect(find.text(noOils), findsOneWidget);
    expect(find.text(loadingText), findsNothing);
  });

  for (final scale in [1.0, 2.0]) {
    testWidgets(
      'QA06 scale $scale disabled tab semantics and no mutation/overlays',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          var backs = 0, homes = 0;
          final ids = <int>[];
          await mount(
            tester,
            scale: scale,
            home: () => homes++,
            back: () => backs++,
            selected: ids.add,
          );
          await query(tester, 'lav');
          await filter(tester, 'Plantas');
          for (final label in ['Favoritos', 'Historial', 'Perfil']) {
            final target = find.bySemanticsLabel('$label no disponible');
            expect(target, findsOneWidget);
            final data = tester.getSemantics(target).getSemanticsData();
            expect(data.flagsCollection.isButton, isTrue);
            expect(data.flagsCollection.isEnabled, Tristate.isFalse);
            expect(data.flagsCollection.isSelected, Tristate.isFalse);
            expect(data.hasAction(SemanticsAction.tap), isFalse);
            await tester.tap(target);
            await tester.pumpAndSettle();
            expect(backs + homes + ids.length, 0);
            expect(find.text('Lavanda'), findsOneWidget);
            expect(
              tester.widget<TextField>(find.byType(TextField)).controller!.text,
              'lav',
            );
            expect(
              tester
                  .widget<ChoiceChip>(
                    find.widgetWithText(ChoiceChip, 'Plantas'),
                  )
                  .selected,
              isTrue,
            );
            expect(find.byType(Dialog), findsNothing);
            expect(find.byType(SnackBar), findsNothing);
          }
          final home = tester
              .getSemantics(find.bySemanticsLabel('Inicio'))
              .getSemanticsData();
          expect(home.flagsCollection.isSelected, Tristate.isTrue);
          expect(home.flagsCollection.isEnabled, Tristate.isTrue);
          expect(home.hasAction(SemanticsAction.tap), isTrue);
          await tester.tap(find.text('Inicio'));
          await reach(tester, find.byTooltip('Volver a Inicio'));
          await tester.tap(find.byTooltip('Volver a Inicio'));
          expect(homes, 1);
          expect(backs, 1);
          expect(tester.takeException(), isNull);
        } finally {
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'QA07 scale $scale safe areas, reachable long names, 48dp controls',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          await mount(tester, scale: scale, padding: safeInsets);
          final back = find.widgetWithIcon(IconButton, Icons.chevron_left);
          expect(
            tester.getRect(back).top,
            greaterThanOrEqualTo(safeInsets.top),
          );
          for (final label in [
            'Inicio',
            'Favoritos no disponible',
            'Historial no disponible',
            'Perfil no disponible',
          ]) {
            final target = find.bySemanticsLabel(label);
            final rect = tester.getRect(target);
            expect(rect.left, greaterThanOrEqualTo(safeInsets.left));
            expect(rect.right, lessThanOrEqualTo(360 - safeInsets.right));
            expect(rect.bottom, lessThanOrEqualTo(640 - safeInsets.bottom));
            expect(rect.size.shortestSide, greaterThanOrEqualTo(48));
          }
          final viewport = tester.getRect(find.byType(CustomScrollView));
          final targets = [
            back,
            find.byType(TextField),
            for (final label in ['Todas', 'Plantas', 'Aceites'])
              find.widgetWithText(ChoiceChip, label),
            for (final plant in plants)
              find.bySemanticsLabel('${plant.$1}, ${plant.$2}'),
          ];
          for (final target in targets) {
            await reach(tester, target);
            print(
              'QA07 scale=$scale target=$target widgetSize=${tester.getSize(target)} semanticsRect=${tester.getSemantics(target).rect}',
            );
            expect(
              tester.getSize(target).shortestSide,
              greaterThanOrEqualTo(48),
              reason: target.toString(),
            );
            expect(target.hitTestable(), findsOneWidget);
          }
          for (final text in [
            'Explorar',
            'Buscar planta o aceite',
            'Buscar planta o aceite...',
            'Todas',
            'Plantas',
            'Aceites',
            for (final plant in plants) ...[plant.$1, plant.$2],
          ]) {
            final target = find.text(text);
            await reach(tester, target);
            final paragraph = tester.renderObject<RenderParagraph>(target);
            expect(paragraph.didExceedMaxLines, isFalse, reason: text);
            expect(paragraph.text.toPlainText(), text);
            final rect = tester.getRect(target);
            expect(rect.left, greaterThanOrEqualTo(safeInsets.left));
            expect(rect.right, lessThanOrEqualTo(360 - safeInsets.right));
            expect(rect.top, greaterThanOrEqualTo(viewport.top - 0.01));
            expect(
              rect.bottom,
              lessThanOrEqualTo(viewport.bottom + 0.01),
              reason: text,
            );
          }
          await query(tester, 'lav');
          final clear = find.byTooltip('Borrar búsqueda');
          await reach(tester, clear);
          expect(tester.getSize(clear).shortestSide, greaterThanOrEqualTo(48));
          expect(clear.hitTestable(), findsOneWidget);
          expect(tester.takeException(), isNull);
        } finally {
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'QA08 scale $scale error text and retry reachable within safe viewport',
      (tester) async {
        await mount(
          tester,
          scale: scale,
          padding: safeInsets,
          loader: () => Future.error(StateError('private')),
        );
        await reach(tester, find.text(errorText));
        expect(
          tester
              .renderObject<RenderParagraph>(find.text(errorText))
              .didExceedMaxLines,
          isFalse,
        );
        final retry = find.widgetWithText(OutlinedButton, 'Reintentar');
        await reach(tester, retry);
        expect(tester.getSize(retry).shortestSide, greaterThanOrEqualTo(48));
        expect(retry.hitTestable(), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'QA09 local file source works with HTTP denied and no external Image',
    (tester) async {
      final previous = HttpOverrides.current;
      final deny = DenyHttp();
      HttpOverrides.global = deny;
      addTearDown(() => HttpOverrides.global = previous);
      // The project integration-level asset test covers the real registered bundle.
      // This UI test uses its frozen local contents to avoid real IO in fake time.
      await mount(tester);
      for (final plant in plants) {
        expect(find.text(plant.$1), findsOneWidget);
        expect(find.text(plant.$2), findsOneWidget);
      }
      await query(tester, 'globulus');
      expect(find.text('Eucalipto'), findsOneWidget);
      await filter(tester, 'Aceites');
      expect(find.text(noOils), findsOneWidget);
      expect(find.byType(Image), findsNothing);
      expect(deny.calls, 0);
      expect(tester.takeException(), isNull);
    },
  );

  for (final scale in [1.0, 2.0]) {
    testWidgets(
      'QA10 scale $scale loading and empty messages remain readable',
      (tester) async {
        final gate = Completer<String>();
        await mount(
          tester,
          scale: scale,
          padding: safeInsets,
          loader: () => gate.future,
          settle: false,
        );
        await tester.pump();
        Future<void> checkMessage(String text) async {
          final target = find.text(text);
          await reach(tester, target);
          final paragraph = tester.renderObject<RenderParagraph>(target);
          expect(paragraph.didExceedMaxLines, isFalse);
          final rect = tester.getRect(target);
          final viewport = tester.getRect(find.byType(CustomScrollView));
          expect(rect.left, greaterThanOrEqualTo(safeInsets.left));
          expect(rect.right, lessThanOrEqualTo(360 - safeInsets.right));
          expect(rect.top, greaterThanOrEqualTo(viewport.top - 0.01));
          expect(rect.bottom, lessThanOrEqualTo(viewport.bottom + 0.01));
        }

        await checkMessage(loadingText);
        gate.complete(json);
        await tester.pumpAndSettle();
        await query(tester, 'no match');
        await checkMessage(noMatch);
        await filter(tester, 'Aceites');
        await checkMessage(noOils);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
