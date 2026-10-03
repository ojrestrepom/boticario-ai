import 'dart:async';

import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_repository.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_catalog_provenance.dart';
import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Router real de la app a través de su API pública, sin tocar campos privados.
GoRouter _currentRouter(WidgetTester tester) {
  return GoRouter.of(tester.element(find.byType(HomePage)));
}

final _testCatalog = PlantCatalog(
  provenance: PlantCatalogProvenance(
    sourceName: 'test',
    license: 'CC0',
    version: 'test',
    sourceUrl: '',
    datasetId: '',
    downloadUrl: '',
    fileId: '',
    fileName: '',
    fileSizeBytes: 0,
    md5: '',
    inspectedOn: DateTime(2026),
    recommendedCitation: '',
  ),
  plants: [
    for (final item in [
      (544, 'Lavanda', 'Lavandula angustifolia'),
      (401, 'Eucalipto', 'Eucalyptus globulus'),
      (873, 'Romero', 'Rosmarinus officinalis'),
      (605, 'Manzanilla', 'Matricaria recutita'),
      (619, 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
    ])
      Plant(
        usdaPlantId: item.$1,
        editorialCommonName: item.$2,
        sourceScientificName: item.$3,
      ),
  ],
);

Future<void> _mount(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        plantCatalogProvider.overrideWith((ref) async => _testCatalog),
      ],
      child: const BoticarioApp(),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('arranca en / con HomePage, la marca y sin el demo', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    // Ruta inicial y pantalla renderizada vía API pública de go_router.
    expect(_currentRouter(tester).state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);

    // Contrato de Home: marca, banner y ausencia del saludo/contador demo.
    expect(find.text('Boticario AI'), findsOneWidget);
    expect(
      find.text('Pequeñas esencias, grandes posibilidades'),
      findsOneWidget,
    );
    expect(find.text('Hola, Boticario AI'), findsNothing);
    expect(find.textContaining('Contador'), findsNothing);
    expect(find.text('Incrementar'), findsNothing);

    // Se aplica el tema real de la app, no uno genérico del harness.
    final theme = Theme.of(tester.element(find.byType(HomePage)));
    expect(theme.colorScheme, buildBoticarioTheme().colorScheme);
  });

  testWidgets('activar controles de Home no cambia la ruta /', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    final router = _currentRouter(tester);
    expect(router.state.uri.path, '/');

    // Cabecera y barra inferior están visibles sin scroll.
    await tester.tap(find.byIcon(Icons.person));
    await tester.pump();
    await tester.tap(find.text('Favoritos'));
    await tester.pump();
    await tester.tap(find.text('Perfil'));
    await tester.pump();

    // La interacción emite su acción, pero la ruta y la pantalla no mutan.
    expect(router.state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);
  });

  testWidgets('Explorar navega por el flujo real y emite un único log', (
    tester,
  ) async {
    final logs = <String>[];
    final original = debugPrint;
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null && message.startsWith('[Home]')) {
        logs.add(message);
      } else {
        original(message, wrapWidth: wrapWidth);
      }
    };
    try {
      await _mount(tester);
      final router = _currentRouter(tester);
      expect(router.state.uri.path, '/');
      expect(logs, isEmpty);

      await tester.tap(
        find.byKey(const ValueKey(HomeAction.explorePlantsAndOils)),
      );
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/explore');
      expect(find.byType(ExplorePage), findsOneWidget);
      expect(logs, ['[Home] Explorar plantas y aceites']);

      await tester.tap(find.text('Lavanda').last);
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/explore/544');
      expect(find.byType(PlantPassportPage), findsOneWidget);
      await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/explore');
      await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/');
      expect(find.byType(HomePage), findsOneWidget);
      expect(
        tester
            .getSemantics(find.byKey(const ValueKey(HomeAction.tabHome)))
            .flagsCollection
            .isSelected
            .toBoolOrNull(),
        isTrue,
      );
      expect(logs, ['[Home] Explorar plantas y aceites']);
    } finally {
      debugPrint = original;
    }
  });

  testWidgets('dos ProviderScope no comparten el GoRouter', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    final firstRouter = _currentRouter(tester);

    // Montar un scope nuevo desmonta el anterior: el router del primer scope
    // se libera y el segundo scope queda operativo e independiente.
    await tester.pumpWidget(
      ProviderScope(key: UniqueKey(), child: const BoticarioApp()),
    );
    await tester.pumpAndSettle();

    final secondRouter = _currentRouter(tester);

    expect(identical(firstRouter, secondRouter), isFalse);
    expect(secondRouter.state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);
    expect(find.text('Boticario AI'), findsOneWidget);

    // El router del scope nuevo sigue respondiendo tras el disposal del previo.
    await tester.tap(find.text('Favoritos'));
    await tester.pump();
    expect(secondRouter.state.uri.path, '/');
  });

  testWidgets('cada fila abre su ficha y pop retorna a Explorar', (
    tester,
  ) async {
    await _mount(tester);
    final router = _currentRouter(tester);
    unawaited(router.push('/explore'));
    await tester.pumpAndSettle();
    for (final item in [
      (544, 'Lavanda'),
      (401, 'Eucalipto'),
      (873, 'Romero'),
      (605, 'Manzanilla'),
      (619, 'Menta'),
    ]) {
      final plantRow = find.descendant(
        of: find.byType(ExplorePage),
        matching: find.text(item.$2),
      );
      await tester.ensureVisible(plantRow.last);
      await tester.tap(plantRow.last);
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/explore/${item.$1}');
      expect(find.byType(PlantPassportPage), findsOneWidget);
      expect(
        find.descendant(
          of: find.byType(PlantPassportPage),
          matching: find.text(item.$2),
        ),
        findsAtLeastNWidgets(1),
      );
      await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();
      expect(router.state.uri.path, '/explore');
      expect(find.byType(ExplorePage), findsOneWidget);
    }
  });

  testWidgets(
    'consulta, filtro y scroll restauran al volver por chevron y Back',
    (tester) async {
      tester.view.physicalSize = const Size(360, 640);
      tester.view.devicePixelRatio = 1;
      final originalViewInsets = tester.view.viewInsets;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(() => tester.view.viewInsets = originalViewInsets);
      await _mount(tester);
      final router = _currentRouter(tester);
      unawaited(router.push('/explore'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Plantas'));
      await tester.enterText(find.byType(TextField), 'a');
      tester.testTextInput.hide();
      tester.binding.focusManager.primaryFocus?.unfocus();
      tester.view.viewInsets = FakeViewPadding.zero;
      await tester.pumpAndSettle();
      final queryController = tester
          .widget<TextField>(find.byType(TextField))
          .controller!;
      await tester.pumpAndSettle();
      expect(queryController.text, 'a');
      expect(
        find.byWidgetPredicate(
          (w) =>
              w is ChoiceChip &&
              w.selected &&
              (w.label as Text).data == 'Plantas',
        ),
        findsOneWidget,
      );

      for (final useFrameworkBack in [false, true]) {
        final mentaRow = find.descendant(
          of: find.byType(ExplorePage),
          matching: find.text('Menta'),
        );
        final listScroll = find
            .descendant(
              of: find.byType(ExplorePage),
              matching: find.byType(Scrollable),
            )
            .first;
        await tester.drag(listScroll, const Offset(0, -180));
        await tester.pumpAndSettle();
        final currentExploreScroll = tester
            .widget<CustomScrollView>(
              find.descendant(
                of: find.byType(ExplorePage),
                matching: find.byType(CustomScrollView),
              ),
            )
            .controller!;
        final offset = currentExploreScroll.offset;
        expect(offset, greaterThan(0));
        await tester.tap(mentaRow.last);
        await tester.pumpAndSettle();
        expect(router.state.uri.path, '/explore/619');
        expect(find.byType(PlantPassportPage), findsOneWidget);
        expect(
          find.descendant(
            of: find.byType(PlantPassportPage),
            matching: find.text('Menta'),
          ),
          findsAtLeastNWidgets(1),
        );
        if (useFrameworkBack) {
          await tester.binding.handlePopRoute();
        } else {
          await tester.tap(find.byTooltip('Volver a Explorar'));
        }
        await tester.pumpAndSettle();
        expect(router.state.uri.path, '/explore');
        expect(find.byType(ExplorePage), findsOneWidget);
        final restoredController = tester
            .widget<CustomScrollView>(
              find.descendant(
                of: find.byType(ExplorePage),
                matching: find.byType(CustomScrollView),
              ),
            )
            .controller!;
        expect(restoredController.offset, offset);
        await tester.drag(
          find
              .descendant(
                of: find.byType(ExplorePage),
                matching: find.byType(Scrollable),
              )
              .first,
          const Offset(0, 500),
        );
        await tester.pumpAndSettle();
        final currentQuery = tester
            .widget<TextField>(
              find.descendant(
                of: find.byType(ExplorePage),
                matching: find.byType(TextField),
              ),
            )
            .controller!;
        expect(currentQuery.text, 'a');
        expect(identical(currentQuery, queryController), isTrue);
        expect(
          find.byWidgetPredicate(
            (w) =>
                w is ChoiceChip &&
                w.selected &&
                (w.label as Text).data == 'Plantas',
          ),
          findsOneWidget,
        );
      }
    },
  );

  testWidgets('rutas directas de P05 permiten retornos seguros', (
    tester,
  ) async {
    for (final entry in [
      ('/explore/619', 'Menta'),
      ('/explore/not-a-plant', 'Planta no encontrada'),
    ]) {
      for (final useFrameworkBack in [false, true]) {
        await _mount(tester);
        final router = _currentRouter(tester);
        router.go(entry.$1);
        await tester.pumpAndSettle();
        expect(find.text(entry.$2), findsAtLeastNWidgets(1));
        if (useFrameworkBack) {
          await tester.binding.handlePopRoute();
        } else {
          await tester.tap(find.byTooltip('Volver a Explorar'));
        }
        await tester.pumpAndSettle();
        expect(router.state.uri.path, '/explore');
        expect(find.byType(ExplorePage), findsOneWidget);
        expect(
          find.byWidgetPredicate(
            (w) =>
                w is ChoiceChip &&
                w.selected &&
                (w.label as Text).data == 'Todas',
          ),
          findsOneWidget,
        );
        expect(
          tester
              .widget<TextField>(
                find.descendant(
                  of: find.byType(ExplorePage),
                  matching: find.byType(TextField),
                ),
              )
              .controller!
              .text,
          isEmpty,
        );
        expect(
          tester
              .state<ScrollableState>(
                find
                    .descendant(
                      of: find.byType(ExplorePage),
                      matching: find.byType(Scrollable),
                    )
                    .first,
              )
              .position
              .pixels,
          0,
        );
        await tester.binding.handlePopRoute();
        await tester.pumpAndSettle();
        expect(router.state.uri.path, '/');
        expect(find.byType(HomePage), findsOneWidget);
        await tester.pumpWidget(const SizedBox.shrink());
      }
    }
  });

  testWidgets('Inicio desde P04 y P05 limpia la pila', (tester) async {
    await _mount(tester);
    final router = _currentRouter(tester);
    unawaited(router.push('/explore'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Inicio').last);
    await tester.pumpAndSettle();
    expect(router.state.uri.path, '/');
    expect(router.canPop(), isFalse);
    unawaited(router.push('/explore'));
    await tester.pumpAndSettle();
    unawaited(router.push('/explore/619'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Inicio').last);
    await tester.pumpAndSettle();
    expect(router.state.uri.path, '/');
    expect(router.canPop(), isFalse);
    expect(find.byType(HomePage), findsOneWidget);
  });
}
