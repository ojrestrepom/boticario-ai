import 'dart:io';
import 'dart:ui' as ui;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_search_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const _labels = <String>[
  'Relajación / Estrés',
  'Mejorar el sueño',
  'Cuidado de la piel',
  'Alivio respiratorio',
  'Concentración',
  'Otros objetivos',
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

  Future<void> show(
    WidgetTester tester, {
    required double scale,
    required EdgeInsets insets,
    required VoidCallback back,
    required VoidCallback home,
    NavigatorObserver? observer,
  }) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBoticarioTheme(),
        navigatorObservers: observer == null ? [] : [observer],
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.linear(scale),
            padding: insets,
            viewPadding: insets,
          ),
          child: child!,
        ),
        home: GoalSearchPage(onBack: back, onHome: home),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
    'renders exact ordered content and inert, single-announcement rows',
    (tester) async {
      var backCalls = 0;
      var homeCalls = 0;
      await show(
        tester,
        scale: 1,
        insets: EdgeInsets.zero,
        back: () => backCalls++,
        home: () => homeCalls++,
      );
      expect(find.text('¿Qué deseas lograr?'), findsOneWidget);
      expect(find.text('Selecciona un objetivo principal'), findsOneWidget);

      final positions = <double>[];
      final scrollable = tester.state<ScrollableState>(
        find.byType(Scrollable).first,
      );
      final viewport = tester.getRect(find.byType(Viewport).first);
      for (final label in _labels) {
        expect(find.bySemanticsLabel(label), findsOneWidget);
        final finder = find.text(label);
        await tester.scrollUntilVisible(
          finder,
          180,
          scrollable: find.byType(Scrollable).first,
        );
        expect(finder, findsOneWidget);
        final semantics = tester.getSemantics(finder);
        expect(semantics.label, label);
        expect(
          semantics.getSemanticsData().hasAction(SemanticsAction.tap),
          isFalse,
        );
        expect(semantics.flagsCollection.isButton, isNot(true));
        expect(semantics.flagsCollection.isSelected, isNot(true));
        final rect = tester.getRect(finder);
        expect(rect.left, greaterThanOrEqualTo(0));
        expect(rect.right, lessThanOrEqualTo(360));
        positions.add(rect.top - viewport.top + scrollable.position.pixels);
        await tester.tap(finder);
        await tester.pumpAndSettle();
        expect(find.text(label), findsOneWidget);
        expect(backCalls, 0);
        expect(homeCalls, 0);
      }
      expect(positions, orderedEquals([...positions]..sort()));
      expect(find.byType(TextField), findsNothing);
      expect(find.text('¿Qué deseas lograr?'), findsOneWidget);
    },
  );

  for (final scale in [1.0, 2.0]) {
    testWidgets('fits and scrolls at ${scale * 100}% with system insets', (
      tester,
    ) async {
      await show(
        tester,
        scale: scale,
        insets: const EdgeInsets.fromLTRB(8, 24, 12, 24),
        back: () {},
        home: () {},
      );
      expect(tester.takeException(), isNull);
      final scrollable = tester.state<ScrollableState>(
        find.byType(Scrollable).first,
      );
      final viewport = tester.getRect(find.byType(Viewport).first);
      final bodyTexts = [
        '¿Qué deseas lograr?',
        'Selecciona un objetivo principal',
        ..._labels,
      ];
      final documentPositions = <double>[];
      for (final text in bodyTexts) {
        final finder = find.text(text);
        await tester.ensureVisible(finder);
        await tester.pumpAndSettle();
        expect(finder, findsOneWidget);
        _expectFullyVisibleText(
          tester,
          finder,
          text,
          tester.getRect(find.byType(Viewport).first),
          const Rect.fromLTRB(8, 24, 348, 616),
        );
        if (_labels.contains(text)) {
          documentPositions.add(
            tester.getRect(finder).top -
                viewport.top +
                scrollable.position.pixels,
          );
        }
        expect(tester.takeException(), isNull);
      }
      // Verify the live document order, independent of the current scroll offset.
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
          const Rect.fromLTRB(8, 24, 348, 616),
        );
      }
      await tester.drag(find.byType(Scrollable).first, const Offset(0, 2000));
      await tester.pumpAndSettle();
      final back = find.byTooltip('Volver a Inicio');
      _expectControlInSafeBounds(
        tester,
        back,
        const Rect.fromLTRB(8, 24, 348, 616),
      );
      expect(find.bySemanticsLabel('Volver a Inicio'), findsOneWidget);
      final home = find.bySemanticsLabel('Inicio');
      _expectControlInSafeBounds(
        tester,
        home,
        const Rect.fromLTRB(8, 24, 348, 616),
      );

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

  testWidgets(
    'goal and inactive-tab taps emit no logs or UI/navigation/overlay changes',
    (tester) async {
      var backCalls = 0;
      var homeCalls = 0;
      final observer = _RecordingNavigatorObserver();
      final logs = <String?>[];
      final originalDebugPrint = debugPrint;
      debugPrint = (message, {wrapWidth}) => logs.add(message);
      try {
        await show(
          tester,
          scale: 1,
          insets: EdgeInsets.zero,
          back: () => backCalls++,
          home: () => homeCalls++,
          observer: observer,
        );
        final pushesAtRest = observer.pushes;
        final popsAtRest = observer.pops;
        expect(logs, isEmpty, reason: 'no log while rendering');
        final contentBefore = _contentSnapshot(tester);
        final modalBarriersAtRest = find.byType(ModalBarrier).evaluate().length;
        await tester.pump(); // Explicit no-input rebuild must remain silent.
        expect(logs, isEmpty, reason: 'no log on rebuild');
        for (final label in _labels) {
          final row = find.text(label);
          await tester.ensureVisible(row);
          await tester.pumpAndSettle();
          await tester.tap(row);
          await tester.pumpAndSettle();
          expect(_contentSnapshot(tester), contentBefore);
          final rowData = tester.getSemantics(row).getSemanticsData();
          expect(rowData.hasAction(ui.SemanticsAction.tap), isFalse);
          expect(rowData.flagsCollection.isSelected, isNot(ui.Tristate.isTrue));
          _expectNoUnexpectedUi(tester, modalBarriersAtRest);
          expect(observer.pushes, pushesAtRest);
          expect(observer.pops, popsAtRest);
          expect(backCalls, 0);
          expect(homeCalls, 0);
          expect(logs, isEmpty, reason: 'tap/rebuild for $label');
        }
        for (final tab in ['Favoritos', 'Historial', 'Perfil']) {
          await tester.tap(find.bySemanticsLabel('$tab no disponible'));
          await tester.pumpAndSettle();
          expect(_contentSnapshot(tester), contentBefore);
          _expectNoUnexpectedUi(tester, modalBarriersAtRest);
          expect(observer.pushes, pushesAtRest);
          expect(observer.pops, popsAtRest);
          expect(backCalls, 0);
          expect(homeCalls, 0);
          expect(logs, isEmpty, reason: 'inert tab $tab');
        }
        expect(backCalls, 0);
      } finally {
        debugPrint = originalDebugPrint;
      }
    },
  );

  testWidgets('back and home callbacks run once each', (tester) async {
    var backCalls = 0;
    var homeCalls = 0;
    await show(
      tester,
      scale: 1,
      insets: EdgeInsets.zero,
      back: () => backCalls++,
      home: () => homeCalls++,
    );
    await tester.tap(find.byTooltip('Volver a Inicio'));
    await tester.tap(find.bySemanticsLabel('Inicio'));
    expect(backCalls, 1);
    expect(homeCalls, 1);
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

List<String> _contentSnapshot(WidgetTester tester) => [
  for (final text in [
    '¿Qué deseas lograr?',
    'Selecciona un objetivo principal',
    ..._labels,
  ])
    '$text:${find.text(text).evaluate().length}',
  'selectedHome:${tester.getSemantics(find.bySemanticsLabel('Inicio')).getSemanticsData().flagsCollection.isSelected}',
  for (final label in ['Favoritos', 'Historial', 'Perfil'])
    'inactive:$label:${tester.getSemantics(find.bySemanticsLabel('$label no disponible')).getSemanticsData().flagsCollection.isEnabled}',
];

void _expectNoUnexpectedUi(WidgetTester tester, int modalBarriersAtRest) {
  expect(find.byType(Dialog), findsNothing);
  expect(find.byType(SnackBar), findsNothing);
  expect(find.byType(Drawer), findsNothing);
  expect(find.byType(ModalBarrier).evaluate().length, modalBarriersAtRest);
}

class _RecordingNavigatorObserver extends NavigatorObserver {
  int pushes = 0;
  int pops = 0;

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    pushes++;
    super.didPush(route, previousRoute);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    pops++;
    super.didPop(route, previousRoute);
  }
}
