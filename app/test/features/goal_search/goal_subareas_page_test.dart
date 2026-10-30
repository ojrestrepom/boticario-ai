import 'dart:io';
import 'dart:ui' as ui;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_subareas_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

const _subareas = <String>[
  'Digestión',
  'Vías urinarias y genitales',
  'Dolor e inflamación',
  'Boca y garganta',
  'Circulación',
  'Molestias oculares',
];

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
    String goalId = 'otros-objetivos',
    double scale = 1,
    FakeCatalogApi? api,
    VoidCallback? back,
    VoidCallback? home,
    void Function(String, String)? onPlants,
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
          apiTokenProvider.overrideWithValue(testApiToken),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: TextScaler.linear(scale)),
            child: child!,
          ),
          home: GoalSubareasPage(
            goalId: goalId,
            onBack: back ?? () {},
            onHome: home ?? () {},
            onOpenPlants: onPlants ?? (_, _) {},
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

  testWidgets('lists the subareas of the API in order under the goal title', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await show(tester);
    expect(find.text('Otros objetivos'), findsOneWidget);
    final tops = <double>[];
    final scrollable = tester.state<ScrollableState>(
      find.byType(Scrollable).first,
    );
    for (final label in _subareas) {
      final finder = find.bySemanticsLabel(label);
      await tester.ensureVisible(finder);
      await tester.pumpAndSettle();
      expect(finder, findsOneWidget);
      final data = tester.getSemantics(finder).getSemanticsData();
      expect(data.flagsCollection.isButton, isTrue);
      expect(tester.getRect(finder).height, greaterThanOrEqualTo(48));
      tops.add(tester.getRect(finder).top + scrollable.position.pixels);
    }
    expect(tops, orderedEquals([...tops]..sort()));
    // Counts are never shown.
    for (final count in ['68', '42', '22', '20', '17']) {
      expect(find.textContaining(count), findsNothing);
    }
    handle.dispose();
  });

  testWidgets('opens the plants of the chosen subarea', (tester) async {
    final opened = <(String, String)>[];
    await show(tester, onPlants: (goal, sub) => opened.add((goal, sub)));
    await tester.tap(find.text('Digestión'));
    await tester.pumpAndSettle();
    expect(opened, [('otros-objetivos', 'digestion')]);
  });

  testWidgets('an empty subarea is not listed', (tester) async {
    final goals = syntheticGoals();
    final other = goals.last;
    final subs = (other['subareas']! as List<Map<String, Object?>>)
        .map((s) => s['id'] == 'circulacion' ? {...s, 'plantCount': 0} : s)
        .toList();
    goals.last = {...other, 'subareas': subs};
    await show(
      tester,
      api: FakeCatalogApi(requiredToken: testApiToken, goals: goals),
    );
    await tester.ensureVisible(find.text('Molestias oculares'));
    expect(find.text('Circulación'), findsNothing);
    expect(find.text('Boca y garganta'), findsOneWidget);
  });

  testWidgets('back and home callbacks run once each', (tester) async {
    var back = 0;
    var home = 0;
    await show(tester, back: () => back++, home: () => home++);
    await tester.tap(find.byTooltip('Volver a objetivos'));
    await tester.tap(find.bySemanticsLabel('Inicio'));
    expect(back, 1);
    expect(home, 1);
  });

  testWidgets('loading shows a label and error offers Reintentar', (
    tester,
  ) async {
    final api = FakeCatalogApi(
      requiredToken: testApiToken,
      failure: FakeApiFailure.timeout,
    );
    await show(tester, api: api, settle: false);
    expect(find.byKey(const ValueKey('goals-loading')), findsOneWidget);
    expect(find.text('Digestión'), findsNothing);
    await tester.pump(const Duration(seconds: 11));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('goals-error')), findsOneWidget);

    api.failure = FakeApiFailure.none;
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(find.text('Digestión'), findsOneWidget);
    expect(find.text('Otros objetivos'), findsOneWidget);
  });

  testWidgets('a goal that the API does not know says so', (tester) async {
    await show(tester, goalId: 'no-existe');
    expect(find.text('Objetivo no encontrado'), findsOneWidget);
  });

  for (final scale in [1.0, 2.0]) {
    testWidgets('fits 360x640 at ${scale * 100}% text', (tester) async {
      await show(tester, scale: scale);
      expect(tester.takeException(), isNull);
      for (final label in ['Otros objetivos', ..._subareas]) {
        final finder = find.text(label);
        await tester.ensureVisible(finder);
        await tester.pumpAndSettle();
        final paragraph = tester.renderObject<RenderParagraph>(finder);
        expect(paragraph.didExceedMaxLines, isFalse, reason: label);
        final rect = tester.getRect(finder);
        expect(rect.left, greaterThanOrEqualTo(0), reason: label);
        expect(rect.right, lessThanOrEqualTo(360), reason: label);
        if (label != 'Otros objetivos') {
          final row = tester.getRect(
            find.ancestor(of: finder, matching: find.byType(InkWell)).first,
          );
          expect(row.height, greaterThanOrEqualTo(48), reason: label);
        }
      }
      expect(tester.takeException(), isNull);
      await tester.drag(find.byType(Scrollable).first, const Offset(0, 3000));
      await tester.pumpAndSettle();
      final back = tester.getRect(find.byTooltip('Volver a objetivos'));
      expect(back.shortestSide, greaterThanOrEqualTo(48));
      final home = find.bySemanticsLabel('Inicio');
      expect(home, findsOneWidget);
      expect(tester.getRect(home).height, greaterThanOrEqualTo(48));
      expect(
        tester.getSemantics(home).getSemanticsData().flagsCollection.isSelected,
        ui.Tristate.isTrue,
      );
    });
  }
}
