import 'dart:io';
import 'dart:ui' as ui;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_list_shell.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_search_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

const _labels = <String>[
  'Relajación / Estrés',
  'Mejorar el sueño',
  'Cuidado de la piel',
  'Alivio respiratorio',
  'Cansancio y fatiga',
  'Otros objetivos',
];

const _unauthorizedMessage =
    'La app no está autorizada para usar el servidor. Inténtalo de nuevo más tarde.';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    final loader = FontLoader('Roboto');
    for (final name in ['Roboto-Regular.ttf', 'Roboto-Medium.ttf']) {
      loader.addFont(
        Future.value(
          ByteData.sublistView(
            File('test/fixtures/fonts/$name').readAsBytesSync(),
          ),
        ),
      );
    }
    await loader.load();
  });

  Future<FakeCatalogApi> show(
    WidgetTester tester, {
    double scale = 1,
    EdgeInsets insets = EdgeInsets.zero,
    FakeCatalogApi? api,
    bool withToken = true,
    VoidCallback? back,
    VoidCallback? home,
    ValueChanged<String>? onSubareas,
    ValueChanged<String>? onPlants,
    bool settle = true,
  }) async {
    final fake = api ?? FakeCatalogApi(requiredToken: testApiToken);
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          httpClientProvider.overrideWithValue(fake.client),
          if (withToken) apiTokenProvider.overrideWithValue(testApiToken),
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
          home: GoalSearchPage(
            onBack: back ?? () {},
            onHome: home ?? () {},
            onOpenSubareas: onSubareas ?? (_) {},
            onOpenPlants: onPlants ?? (_) {},
          ),
        ),
      ),
    );
    if (settle) {
      await tester.pumpAndSettle();
    } else {
      await tester.pump();
    }
    return fake;
  }

  testWidgets('shows the goals of the API in order, without counts or '
      'Concentración', (tester) async {
    final api = await show(tester);
    expect(find.text('¿Qué deseas lograr?'), findsOneWidget);
    expect(find.text('Selecciona un objetivo principal'), findsOneWidget);
    expect(api.requests.map((r) => r.url.path), ['/v1/goals']);

    final scrollable = tester.state<ScrollableState>(
      find.byType(Scrollable).first,
    );
    final viewport = tester.getRect(find.byType(Viewport).first);
    final positions = <double>[];
    for (final label in _labels) {
      final finder = find.text(label);
      await tester.scrollUntilVisible(
        finder,
        180,
        scrollable: find.byType(Scrollable).first,
      );
      expect(finder, findsOneWidget);
      positions.add(
        tester.getRect(finder).top - viewport.top + scrollable.position.pixels,
      );
    }
    expect(positions, orderedEquals([...positions]..sort()));
    expect(find.text('Concentración'), findsNothing);
    expect(find.byType(TextField), findsNothing);
    // plantCount (17, 8, 32, 52, 135) never reaches the rows.
    for (final count in ['17', '8', '32', '52', '135']) {
      expect(find.textContaining(count), findsNothing);
    }
  });

  testWidgets('takes names and order from the API without code changes', (
    tester,
  ) async {
    final goals = syntheticGoals().reversed.toList();
    goals[0] = {...goals[0], 'name': 'Otros asuntos'};
    await show(
      tester,
      api: FakeCatalogApi(requiredToken: testApiToken, goals: goals),
    );
    expect(find.text('Otros asuntos'), findsOneWidget);
    expect(find.text('Otros objetivos'), findsNothing);
    expect(
      tester.getRect(find.text('Otros asuntos')).top,
      lessThan(tester.getRect(find.text('Relajación / Estrés')).top),
    );
  });

  testWidgets('a goal with an unknown id gets the generic icon and works', (
    tester,
  ) async {
    final opened = <String>[];
    await show(
      tester,
      api: FakeCatalogApi(
        requiredToken: testApiToken,
        goals: [
          {
            'id': 'meta-nueva',
            'name': 'Meta nueva',
            'plantCount': 3,
            'subareas': <Object?>[],
          },
        ],
      ),
      onPlants: opened.add,
    );
    final row = find.byKey(const ValueKey('goal-meta-nueva'));
    expect(
      find.descendant(of: row, matching: find.byIcon(Icons.eco_outlined)),
      findsOneWidget,
    );
    await tester.tap(find.text('Meta nueva'));
    expect(opened, ['meta-nueva']);
  });

  testWidgets('each row is one 48 dp button announced once, icons excluded', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await show(tester);
    for (final label in _labels) {
      final finder = find.bySemanticsLabel(label);
      await tester.ensureVisible(finder);
      await tester.pumpAndSettle();
      expect(finder, findsOneWidget);
      final data = tester.getSemantics(finder).getSemanticsData();
      expect(data.label, label);
      expect(data.flagsCollection.isButton, isTrue);
      expect(data.hasAction(ui.SemanticsAction.tap), isTrue);
      expect(data.flagsCollection.isSelected, isNot(ui.Tristate.isTrue));
      final rect = tester.getRect(find.text(label));
      expect(tester.getRect(finder).height, greaterThanOrEqualTo(48));
      expect(rect.left, greaterThanOrEqualTo(0));
      expect(rect.right, lessThanOrEqualTo(360));
    }
    handle.dispose();
  });

  testWidgets('a row with subareas opens subareas, the others open plants, '
      'and nothing stays selected', (tester) async {
    final subareas = <String>[];
    final plants = <String>[];
    await show(tester, onSubareas: subareas.add, onPlants: plants.add);
    await tester.tap(find.text('Mejorar el sueño'));
    await tester.pumpAndSettle();
    expect(plants, ['mejorar-el-sueno']);
    expect(subareas, isEmpty);

    final other = find.text('Otros objetivos');
    await tester.ensureVisible(other);
    await tester.pumpAndSettle();
    await tester.tap(other);
    await tester.pumpAndSettle();
    expect(subareas, ['otros-objetivos']);
    expect(plants, ['mejorar-el-sueno']);

    final handle = tester.ensureSemantics();
    for (final label in _labels) {
      final finder = find.bySemanticsLabel(label);
      await tester.ensureVisible(finder);
      await tester.pumpAndSettle();
      final data = tester.getSemantics(finder).getSemanticsData();
      expect(data.flagsCollection.isSelected, isNot(ui.Tristate.isTrue));
    }
    handle.dispose();
  });

  testWidgets('shows a labelled loading indicator, the header and no rows', (
    tester,
  ) async {
    final api = FakeCatalogApi(
      requiredToken: testApiToken,
      failure: FakeApiFailure.timeout,
    );
    await show(tester, api: api, settle: false);
    expect(find.byKey(const ValueKey('goals-loading')), findsOneWidget);
    expect(find.bySemanticsLabel('Cargando objetivos'), findsOneWidget);
    expect(find.text('¿Qué deseas lograr?'), findsOneWidget);
    for (final label in _labels) {
      expect(find.text(label), findsNothing);
    }
    // The 10 s timeout ends the request: no timer is left pending.
    await tester.pump(const Duration(seconds: 11));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('goals-error')), findsOneWidget);
  });

  testWidgets('a server error shows Reintentar and a retry shows the rows', (
    tester,
  ) async {
    final api = FakeCatalogApi(
      requiredToken: testApiToken,
      failure: FakeApiFailure.serverError,
    );
    await show(tester, api: api);
    expect(find.byKey(const ValueKey('goals-error')), findsOneWidget);
    expect(find.textContaining('HTTP 500'), findsOneWidget);
    expect(find.text('Mejorar el sueño'), findsNothing);

    api.failure = FakeApiFailure.none;
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('goals-error')), findsNothing);
    expect(find.text('Mejorar el sueño'), findsOneWidget);
    expect(api.requests, hasLength(2));
  });

  testWidgets('a connection failure is retryable too', (tester) async {
    final api = FakeCatalogApi(
      requiredToken: testApiToken,
      failure: FakeApiFailure.connection,
    );
    await show(tester, api: api);
    expect(find.text('Reintentar'), findsOneWidget);
    api.failure = FakeApiFailure.none;
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(find.text('Relajación / Estrés'), findsOneWidget);
  });

  testWidgets('a 401 shows the unauthorized error without any token', (
    tester,
  ) async {
    await show(tester, withToken: false);
    expect(find.text(_unauthorizedMessage), findsOneWidget);
    expect(find.textContaining(testApiToken), findsNothing);
    expect(find.text('Reintentar'), findsOneWidget);
    expect(find.text('Mejorar el sueño'), findsNothing);
  });

  for (final scale in [1.0, 2.0]) {
    testWidgets('fits and scrolls at ${scale * 100}% with system insets', (
      tester,
    ) async {
      const safe = Rect.fromLTRB(8, 24, 348, 616);
      await show(
        tester,
        scale: scale,
        insets: const EdgeInsets.fromLTRB(8, 24, 12, 24),
      );
      expect(tester.takeException(), isNull);
      final scrollable = tester.state<ScrollableState>(
        find.byType(Scrollable).first,
      );
      final viewport = tester.getRect(find.byType(Viewport).first);
      final documentPositions = <double>[];
      for (final text in [
        '¿Qué deseas lograr?',
        'Selecciona un objetivo principal',
        ..._labels,
      ]) {
        final finder = find.text(text);
        await tester.ensureVisible(finder);
        await tester.pumpAndSettle();
        expect(finder, findsOneWidget);
        _expectFullyVisibleText(
          tester,
          finder,
          text,
          tester.getRect(find.byType(Viewport).first),
          safe,
        );
        if (_labels.contains(text)) {
          documentPositions.add(
            tester.getRect(finder).top -
                viewport.top +
                scrollable.position.pixels,
          );
          final row = tester.getRect(
            find.ancestor(of: finder, matching: find.byType(InkWell)).first,
          );
          expect(row.height, greaterThanOrEqualTo(48));
          expect(row.left, greaterThanOrEqualTo(safe.left));
          expect(row.right, lessThanOrEqualTo(safe.right));
        }
        expect(tester.takeException(), isNull);
      }
      expect(documentPositions, orderedEquals([...documentPositions]..sort()));

      for (final label in ['Inicio', 'Favoritos', 'Historial', 'Perfil']) {
        final finder = find.bySemanticsLabel(
          label == 'Inicio' ? 'Inicio' : '$label no disponible',
        );
        expect(finder, findsOneWidget);
        _expectFullyVisibleText(
          tester,
          find.text(label).last,
          label,
          tester.getRect(find.byType(Scaffold)),
          safe,
        );
      }
      await tester.drag(find.byType(Scrollable).first, const Offset(0, 2000));
      await tester.pumpAndSettle();
      _expectControlInSafeBounds(
        tester,
        find.byTooltip('Volver a Inicio'),
        safe,
      );
      expect(find.bySemanticsLabel('Volver a Inicio'), findsOneWidget);
      final home = find.bySemanticsLabel('Inicio');
      _expectControlInSafeBounds(tester, home, safe);

      final homeData = tester.getSemantics(home).getSemanticsData();
      expect(homeData.flagsCollection.isSelected, ui.Tristate.isTrue);
      expect(homeData.hasAction(ui.SemanticsAction.tap), isTrue);
      for (final label in ['Favoritos', 'Historial', 'Perfil']) {
        final data = tester
            .getSemantics(find.bySemanticsLabel('$label no disponible'))
            .getSemanticsData();
        expect(data.flagsCollection.isEnabled, ui.Tristate.isFalse);
        expect(data.flagsCollection.isSelected, ui.Tristate.isFalse);
        expect(data.hasAction(ui.SemanticsAction.tap), isFalse);
      }
    });
  }

  testWidgets('the other tabs do nothing and the bottom bar stays intact', (
    tester,
  ) async {
    var calls = 0;
    await show(
      tester,
      back: () => calls++,
      home: () => calls++,
      onSubareas: (_) => calls++,
      onPlants: (_) => calls++,
    );
    for (final tab in ['Favoritos', 'Historial', 'Perfil']) {
      await tester.tap(find.bySemanticsLabel('$tab no disponible'));
      await tester.pumpAndSettle();
      expect(calls, 0);
      expect(find.byType(Dialog), findsNothing);
      expect(find.byType(SnackBar), findsNothing);
    }
    expect(find.text('Relajación / Estrés'), findsOneWidget);
  });

  testWidgets('back and home callbacks run once each', (tester) async {
    var backCalls = 0;
    var homeCalls = 0;
    await show(tester, back: () => backCalls++, home: () => homeCalls++);
    await tester.tap(find.byTooltip('Volver a Inicio'));
    await tester.tap(find.bySemanticsLabel('Inicio'));
    expect(backCalls, 1);
    expect(homeCalls, 1);
  });

  testWidgets('the last row ends above the bottom bar at the end of the scroll '
      '(360x640, 100 %)', (tester) async {
    await show(tester);
    await tester.scrollUntilVisible(
      find.bySemanticsLabel('Otros objetivos'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.drag(find.byType(Scrollable).first, const Offset(0, -2000));
    await tester.pumpAndSettle();
    final row = tester.getRect(
      find.byKey(const ValueKey('goal-otros-objetivos')),
    );
    final bar = tester.getRect(find.byType(GoalBottomBar));
    expect(row.bottom, lessThanOrEqualTo(bar.top - 16));
  });
}

void _expectFullyVisibleText(
  WidgetTester tester,
  Finder finder,
  String text,
  Rect viewport,
  Rect safeRect,
) {
  final paragraph = tester.renderObject<RenderParagraph>(finder);
  final paragraphRect = tester.getRect(finder);
  expect(
    paragraphRect.left,
    greaterThanOrEqualTo(safeRect.left - 0.1),
    reason: '$text $paragraphRect',
  );
  expect(
    paragraphRect.right,
    lessThanOrEqualTo(safeRect.right + 0.1),
    reason: '$text $paragraphRect',
  );
  expect(paragraph.didExceedMaxLines, isFalse, reason: text);
  expect(paragraph.overflow, isNot(TextOverflow.ellipsis), reason: text);
  for (final match in RegExp(r'\S+').allMatches(text)) {
    final boxes = paragraph.getBoxesForSelection(
      TextSelection(baseOffset: match.start, extentOffset: match.end),
    );
    expect(boxes, isNotEmpty, reason: 'glyph bounds for $text');
    for (final box in boxes) {
      expect(box.left, greaterThanOrEqualTo(-0.1), reason: text);
      expect(
        box.right,
        lessThanOrEqualTo(paragraph.size.width + 0.1),
        reason: text,
      );
      final rect = box.toRect().shift(paragraph.localToGlobal(Offset.zero));
      expect(
        rect.left,
        greaterThanOrEqualTo(safeRect.left - 0.1),
        reason: text,
      );
      expect(rect.right, lessThanOrEqualTo(safeRect.right + 0.1), reason: text);
      expect(rect.top, greaterThanOrEqualTo(viewport.top - 0.1), reason: text);
      expect(
        rect.bottom,
        lessThanOrEqualTo(viewport.bottom + 0.1),
        reason: text,
      );
    }
  }
}

void _expectControlInSafeBounds(
  WidgetTester tester,
  Finder finder,
  Rect safeRect,
) {
  expect(finder.hitTestable(), findsOneWidget);
  final rect = tester.getRect(finder);
  expect(rect.width, greaterThanOrEqualTo(48));
  expect(rect.height, greaterThanOrEqualTo(48));
  expect(rect.left, greaterThanOrEqualTo(safeRect.left));
  expect(rect.right, lessThanOrEqualTo(safeRect.right));
  expect(rect.top, greaterThanOrEqualTo(safeRect.top));
  expect(rect.bottom, lessThanOrEqualTo(safeRect.bottom));
}
