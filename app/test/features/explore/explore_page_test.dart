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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final catalogJson = File('assets/data/plant_catalog.json').readAsStringSync();
  Future<void> pumpExplore(
    WidgetTester tester, {
    required Future<String> Function() loadAsset,
    ValueChanged<int>? selected,
    VoidCallback? back,
    VoidCallback? home,
    TextScaler textScaler = TextScaler.noScaling,
    EdgeInsets padding = EdgeInsets.zero,
    bool settle = true,
  }) async {
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantCatalogRepositoryProvider.overrideWithValue(
            PlantCatalogRepository(
              dataSource: PlantCatalogAssetDataSource(
                loadAsset: (_) => loadAsset(),
              ),
            ),
          ),
        ],
        child: MaterialApp(
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: textScaler,
              padding: padding,
              viewPadding: padding,
            ),
            child: child!,
          ),
          theme: buildBoticarioTheme(),
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

  testWidgets(
    'shows an explicit loading state until the local catalog resolves',
    (tester) async {
      final gate = Completer<String>();
      await pumpExplore(tester, loadAsset: () => gate.future, settle: false);
      await tester.pump();
      expect(find.text('Cargando catálogo...'), findsOneWidget);
      expect(find.text('No se encontraron plantas'), findsNothing);
      gate.complete(catalogJson);
      await tester.pumpAndSettle();
      expect(find.text('Lavanda'), findsOneWidget);
    },
  );

  testWidgets('retry shows loading until the second local load completes', (
    tester,
  ) async {
    final retryGate = Completer<String>();
    var attempts = 0;
    await pumpExplore(
      tester,
      loadAsset: () {
        attempts++;
        if (attempts == 1) return Future.error(StateError('local failure'));
        return retryGate.future;
      },
    );
    expect(find.text('No se pudo cargar el catálogo local.'), findsOneWidget);
    await tester.tap(find.text('Reintentar'));
    await tester.pump();
    expect(find.text('Cargando catálogo...'), findsOneWidget);
    expect(find.text('No se pudo cargar el catálogo local.'), findsNothing);
    expect(find.text('No se encontraron plantas'), findsNothing);
    retryGate.complete(catalogJson);
    await tester.pumpAndSettle();
    expect(find.text('Lavanda'), findsOneWidget);
  });

  testWidgets(
    'loads five catalog plants in stable order and dispatches identity',
    (tester) async {
      int? selected;
      await pumpExplore(
        tester,
        loadAsset: () async => catalogJson,
        selected: (id) => selected = id,
      );
      expect(find.text('Lavanda'), findsOneWidget);
      expect(find.text('Lavandula angustifolia'), findsOneWidget);
      expect(find.text('Eucalipto'), findsOneWidget);
      expect(find.text('Romero'), findsOneWidget);
      expect(find.text('Manzanilla'), findsOneWidget);
      expect(find.byTooltip('Borrar búsqueda'), findsNothing);
      expect(find.text('Menta'), findsOneWidget);
      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Todas'))
            .selected,
        isTrue,
      );
      await tester.ensureVisible(find.text('Romero'));
      await tester.tap(find.text('Romero'));
      expect(selected, 873);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'searches accents and scientific names; clear preserves selected filter',
    (tester) async {
      await pumpExplore(tester, loadAsset: () async => catalogJson);
      await tester.enterText(find.byType(TextField), '  LAVÁNDA ');
      await tester.pump();
      expect(find.text('Lavanda'), findsOneWidget);
      expect(find.text('Eucalipto'), findsNothing);
      await tester.tap(find.text('Plantas'));
      await tester.pump();
      await tester.tap(find.byTooltip('Borrar búsqueda'));
      await tester.pump();
      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Plantas'))
            .selected,
        isTrue,
      );
      await tester.enterText(find.byType(TextField), ' globulus ');
      await tester.pump();
      expect(find.text('Eucalipto'), findsOneWidget);
      expect(find.text('Lavanda'), findsNothing);
    },
  );

  testWidgets(
    'keeps the search field label and editing semantics after text changes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpExplore(tester, loadAsset: () async => catalogJson);
      final searchField = find.byType(EditableText);
      final searchSemantics = find.semantics.byFlag(SemanticsFlag.isTextField);

      void expectSearchSemantics({bool editable = false}) {
        final data = tester.getSemantics(searchField).getSemanticsData();
        expect(data.label, 'Buscar planta o aceite');
        expect(data.flagsCollection.isReadOnly, isFalse);
        if (editable) {
          expect(data.hasAction(SemanticsAction.setText), isTrue);
        }
      }

      expectSearchSemantics();
      await tester.tap(searchField);
      await tester.pumpAndSettle();
      expectSearchSemantics(editable: true);

      tester.semantics.setText(searchSemantics, 'lavanda');
      await tester.pumpAndSettle();
      expectSearchSemantics(editable: true);

      final clearButton = find.byTooltip('Borrar búsqueda');
      expect(clearButton, findsOneWidget);
      final clearData = tester.getSemantics(clearButton).getSemanticsData();
      expect(clearData.tooltip, 'Borrar búsqueda');
      expect(clearData.hasAction(SemanticsAction.tap), isTrue);
      expect(
        tester.getRect(clearButton).size.shortestSide,
        greaterThanOrEqualTo(48),
      );

      await tester.tap(find.text('Explorar'));
      await tester.pumpAndSettle();
      expectSearchSemantics();
      await tester.tap(searchField);
      await tester.pumpAndSettle();
      expectSearchSemantics(editable: true);

      await tester.tap(clearButton);
      await tester.pumpAndSettle();
      expectSearchSemantics();
      semantics.dispose();
    },
  );

  testWidgets('oils empty is distinct from unmatched search', (tester) async {
    await pumpExplore(tester, loadAsset: () async => catalogJson);
    await tester.tap(find.text('Aceites'));
    await tester.pump();
    expect(
      find.text('No hay aceites disponibles en este catálogo'),
      findsOneWidget,
    );
    await tester.tap(find.text('Todas'));
    await tester.enterText(find.byType(TextField), 'zzz');
    await tester.pump();
    expect(find.text('No se encontraron plantas'), findsOneWidget);
    expect(
      find.text('No hay aceites disponibles en este catálogo'),
      findsNothing,
    );
  });

  testWidgets(
    'exposes loading, readable error and retries the local provider',
    (tester) async {
      var attempts = 0;
      await pumpExplore(
        tester,
        loadAsset: () {
          attempts++;
          if (attempts == 1) return Future.error(StateError('private detail'));
          return Future.value(catalogJson);
        },
      );
      expect(find.text('No se pudo cargar el catálogo local.'), findsOneWidget);
      expect(find.textContaining('private detail'), findsNothing);
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(attempts, 2);
      expect(find.text('Lavanda'), findsOneWidget);
    },
  );

  testWidgets('keeps navigation callbacks and layout stable at 200% text', (
    tester,
  ) async {
    var backs = 0, homes = 0;
    await pumpExplore(
      tester,
      loadAsset: () async => catalogJson,
      back: () => backs++,
      home: () => homes++,
      textScaler: const TextScaler.linear(2),
    );
    await tester.tap(find.byTooltip('Volver a Inicio'));
    await tester.tap(find.text('Inicio'));
    expect(backs, 1);
    expect(homes, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'search text remains untruncated at 200% in empty and clear states',
    (tester) async {
      await pumpExplore(
        tester,
        loadAsset: () async => catalogJson,
        textScaler: const TextScaler.linear(2),
      );
      Future<void> checkHint() async {
        final hint = tester.renderObject<RenderParagraph>(
          find.text('Buscar planta o aceite...'),
        );
        expect(hint.didExceedMaxLines, isFalse);
        expect(hint.size.width, lessThanOrEqualTo(360));
      }

      await checkHint();
      await tester.drag(find.byType(CustomScrollView), const Offset(0, -360));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Aceites'));
      await tester.pump();
      expect(
        find.text('No hay aceites disponibles en este catálogo'),
        findsOneWidget,
      );
      await Scrollable.ensureVisible(
        tester.element(find.text('Buscar planta o aceite...')),
      );
      await tester.pumpAndSettle();
      await checkHint();
      await tester.enterText(find.byType(TextField), 'lavanda');
      await tester.pump();
      await Scrollable.ensureVisible(
        tester.element(find.byTooltip('Borrar búsqueda')),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Borrar búsqueda'));
      await tester.pump();
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        isEmpty,
      );
      await Scrollable.ensureVisible(
        tester.element(find.text('Buscar planta o aceite...')),
      );
      await tester.pumpAndSettle();
      await checkHint();
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'filters, rows and catalog tabs expose one actionable semantic target',
    (tester) async {
      final semantics = tester.ensureSemantics();
      int? selected;
      await pumpExplore(
        tester,
        loadAsset: () async => catalogJson,
        selected: (id) => selected = id,
      );
      final plantsFilter = tester.getSemantics(find.text('Plantas'));
      expect(
        plantsFilter.getSemanticsData().hasAction(SemanticsAction.tap),
        isTrue,
      );
      final homeTab = tester.getSemantics(find.text('Inicio').last);
      expect(homeTab.getSemanticsData().hasAction(SemanticsAction.tap), isTrue);
      final unavailable = tester.getSemantics(find.text('Favoritos').last);
      expect(unavailable.label, 'Favoritos no disponible');
      expect(
        unavailable.getSemanticsData().hasAction(SemanticsAction.tap),
        isFalse,
      );
      final lavandaRow = find.bySemanticsLabel(
        'Lavanda, Lavandula angustifolia',
      );
      expect(lavandaRow, findsOneWidget);
      final rowSemantics = tester.getSemantics(lavandaRow);
      expect(
        rowSemantics.getSemanticsData().hasAction(SemanticsAction.tap),
        isTrue,
      );
      await tester.tap(find.text('Lavanda'));
      expect(selected, 544);
      semantics.dispose();
    },
  );

  for (final scale in [1.0, 2.0]) {
    testWidgets('retry is accessible and readable at $scale text scale', (
      tester,
    ) async {
      final retryGate = Completer<String>();
      var attempts = 0;
      await pumpExplore(
        tester,
        textScaler: TextScaler.linear(scale),
        padding: const EdgeInsets.fromLTRB(8, 24, 8, 20),
        loadAsset: () {
          attempts++;
          return attempts == 1
              ? Future.error(StateError('local failure'))
              : retryGate.future;
        },
      );

      final message = find.text('No se pudo cargar el catálogo local.');
      final retry = find.widgetWithText(OutlinedButton, 'Reintentar');
      final scrollable = find
          .descendant(
            of: find.byType(CustomScrollView),
            matching: find.byType(Scrollable),
          )
          .first;
      if (message.evaluate().isEmpty) {
        await tester.scrollUntilVisible(message, 100, scrollable: scrollable);
      }
      await tester.ensureVisible(message);
      await tester.pumpAndSettle();
      final messageParagraph = tester.renderObject<RenderParagraph>(message);
      final viewport = tester.getRect(find.byType(CustomScrollView));
      final messageRect = tester.getRect(message);
      expect(messageParagraph.didExceedMaxLines, isFalse);
      expect(messageRect.left, greaterThanOrEqualTo(8));
      expect(messageRect.right, lessThanOrEqualTo(352));
      expect(messageRect.top, greaterThanOrEqualTo(viewport.top - 0.01));
      expect(messageRect.bottom, lessThanOrEqualTo(viewport.bottom + 0.01));

      if (retry.evaluate().isEmpty) {
        await tester.scrollUntilVisible(retry, 100, scrollable: scrollable);
      }
      await tester.ensureVisible(retry);
      await tester.pumpAndSettle();
      expect(tester.getSize(retry).shortestSide, greaterThanOrEqualTo(48));
      expect(retry.hitTestable(), findsOneWidget);
      final retryData = tester.getSemantics(retry).getSemanticsData();
      expect(retryData.label, 'Reintentar');
      expect(retryData.hasAction(SemanticsAction.tap), isTrue);

      await tester.tap(retry);
      await tester.pump();
      expect(attempts, 2);
      expect(find.text('Cargando catálogo...'), findsOneWidget);
      retryGate.complete(catalogJson);
      await tester.pumpAndSettle();
      expect(find.text('Lavanda'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('keeps controls accessible and safe at $scale text scale', (
      tester,
    ) async {
      final semantics = tester.ensureSemantics();
      try {
        var homes = 0;
        await pumpExplore(
          tester,
          loadAsset: () async => catalogJson,
          textScaler: TextScaler.linear(scale),
          padding: const EdgeInsets.fromLTRB(8, 24, 8, 20),
          home: () => homes++,
        );
        final back = find.widgetWithIcon(IconButton, Icons.chevron_left);
        expect(tester.getRect(back).top, greaterThanOrEqualTo(24));
        final checks = <Finder>[
          back,
          find.byType(TextField),
          for (final label in ['Todas', 'Plantas', 'Aceites'])
            find.widgetWithText(ChoiceChip, label),
          for (final name in [
            'Lavanda',
            'Eucalipto',
            'Romero',
            'Manzanilla',
            'Menta',
          ])
            find.bySemanticsLabel(RegExp('^$name,')),
          for (final tab in ['Inicio', 'Favoritos', 'Historial', 'Perfil'])
            find.bySemanticsLabel(tab == 'Inicio' ? tab : '$tab no disponible'),
        ];
        for (final target in checks) {
          if (target != back) {
            await tester.ensureVisible(target);
            await tester.pumpAndSettle();
          }
          expect(
            tester.getSize(target).shortestSide,
            greaterThanOrEqualTo(48),
            reason: '$target',
          );
          expect(target.hitTestable(), findsOneWidget, reason: '$target');
        }
        for (final label in [
          'Inicio',
          'Favoritos no disponible',
          'Historial no disponible',
          'Perfil no disponible',
        ]) {
          final rect = tester.getRect(find.bySemanticsLabel(label));
          expect(rect.left, greaterThanOrEqualTo(8));
          expect(rect.right, lessThanOrEqualTo(352));
          expect(rect.bottom, lessThanOrEqualTo(620));
        }
        final home = tester
            .getSemantics(find.bySemanticsLabel('Inicio'))
            .getSemanticsData();
        expect(home.flagsCollection.isEnabled, Tristate.isTrue);
        expect(home.flagsCollection.isSelected, Tristate.isTrue);
        for (final name in ['Favoritos', 'Historial', 'Perfil']) {
          final data = tester
              .getSemantics(find.bySemanticsLabel('$name no disponible'))
              .getSemanticsData();
          expect(data.flagsCollection.isEnabled, Tristate.isFalse);
          expect(data.hasAction(SemanticsAction.tap), isFalse);
        }
        await tester.tap(find.bySemanticsLabel('Inicio'));
        expect(homes, 1);
        tester
            .state<ScrollableState>(
              find
                  .descendant(
                    of: find.byType(CustomScrollView),
                    matching: find.byType(Scrollable),
                  )
                  .first,
            )
            .position
            .jumpTo(0);
        await tester.pumpAndSettle();
        await tester.enterText(find.byType(TextField), 'lavanda');
        await tester.pumpAndSettle();
        expect(
          tester.getSemantics(find.byType(EditableText)).label,
          'Buscar planta o aceite',
        );
        await tester.ensureVisible(find.byTooltip('Borrar búsqueda'));
        await tester.pumpAndSettle();
        expect(
          tester.getSize(find.byTooltip('Borrar búsqueda')).shortestSide,
          greaterThanOrEqualTo(48),
        );
      } finally {
        semantics.dispose();
      }
    });

    testWidgets('essential content stays readable and reachable at $scale', (
      tester,
    ) async {
      await pumpExplore(
        tester,
        loadAsset: () async => catalogJson,
        textScaler: TextScaler.linear(scale),
        padding: const EdgeInsets.fromLTRB(8, 24, 8, 20),
      );
      final viewport = tester.getRect(find.byType(CustomScrollView));
      for (final text in [
        'Explorar',
        'Buscar planta o aceite',
        'Buscar planta o aceite...',
        'Todas',
        'Plantas',
        'Aceites',
        'Lavanda',
        'Lavandula angustifolia',
        'Eucalipto',
        'Eucalyptus globulus',
        'Romero',
        'Rosmarinus officinalis',
        'Manzanilla',
        'Matricaria recutita',
        'Menta',
        'Mentha x piperita subsp. nothosubsp. piperita',
      ]) {
        final target = find.text(text);
        if (target.evaluate().isEmpty) {
          await tester.scrollUntilVisible(
            target,
            100,
            scrollable: find
                .descendant(
                  of: find.byType(CustomScrollView),
                  matching: find.byType(Scrollable),
                )
                .first,
          );
        }
        await tester.ensureVisible(target);
        await tester.pumpAndSettle();
        final paragraph = tester.renderObject<RenderParagraph>(target);
        final rect = tester.getRect(target);
        expect(paragraph.didExceedMaxLines, isFalse, reason: text);
        expect(paragraph.text.toPlainText(), text);
        expect(rect.left, greaterThanOrEqualTo(8));
        expect(rect.right, lessThanOrEqualTo(352));
        expect(rect.top, greaterThanOrEqualTo(viewport.top - 0.01));
        expect(
          rect.bottom,
          lessThanOrEqualTo(viewport.bottom + 0.01),
          reason: text,
        );
      }
      expect(tester.takeException(), isNull);
    });
  }
}
