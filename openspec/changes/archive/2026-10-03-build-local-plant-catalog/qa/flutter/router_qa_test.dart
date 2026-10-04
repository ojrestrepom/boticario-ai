import 'dart:async';
import 'dart:io';

import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_repository.dart';
import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

// Run from app/. All input fixtures are local, versioned, and approved.
const identities = [
  (544, 'Lavanda', 'Lavandula angustifolia'),
  (401, 'Eucalipto', 'Eucalyptus globulus'),
  (873, 'Romero', 'Rosmarinus officinalis'),
  (605, 'Manzanilla', 'Matricaria recutita'),
  (619, 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
];

Finder inExplore(Finder finder) =>
    find.descendant(of: find.byType(ExplorePage), matching: finder);
Finder get list => inExplore(find.byType(Scrollable)).first;
ScrollController scroll(WidgetTester tester) => tester
    .widget<CustomScrollView>(inExplore(find.byType(CustomScrollView)))
    .controller!;
TextEditingController query(WidgetTester tester) =>
    tester.widget<TextField>(inExplore(find.byType(TextField))).controller!;
void selected(String label) => expect(
  inExplore(
    find.byWidgetPredicate(
      (w) => w is ChoiceChip && w.selected && (w.label as Text).data == label,
    ),
  ),
  findsOneWidget,
);

class Harness {
  Harness(this.router);
  final GoRouter router;
  int loads = 0;
}

Future<Harness> mount(
  WidgetTester tester, {
  bool fail = false,
  Completer<String>? pending,
}) async {
  tester.view.physicalSize = const Size(360, 640);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final json = File('assets/data/plant_catalog.json').readAsStringSync();
  late Harness h;
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        plantCatalogAssetDataSourceProvider.overrideWithValue(
          PlantCatalogAssetDataSource(
            loadAsset: (path) async {
              h.loads++;
              expect(path, plantCatalogAssetPath);
              if (fail)
                throw const FormatException('QA persistent local failure');
              return pending == null ? json : await pending.future;
            },
          ),
        ),
      ],
      child: const BoticarioApp(),
    ),
  );
  h = Harness(GoRouter.of(tester.element(find.byType(HomePage))));
  await tester.pumpAndSettle();
  expect(h.router.state.uri.path, '/');
  return h;
}

Future<void> openExplore(WidgetTester tester, Harness h) async {
  // The only programmatic intervention in the normal flow: task 4.2 pending.
  unawaited(h.router.push('/explore'));
  await tester.pumpAndSettle();
  expect(h.router.state.uri.path, '/explore');
}

Future<void> back(WidgetTester tester, bool framework, String tooltip) async {
  if (framework) {
    await tester.binding.handlePopRoute();
  } else {
    final button = find.byTooltip(tooltip);
    await tester.ensureVisible(button);
    await tester.tap(button);
  }
  await tester.pumpAndSettle();
}

Future<void> choose(WidgetTester tester, String name) async {
  final row = inExplore(find.text(name));
  await tester.ensureVisible(row);
  await tester.tap(row);
  await tester.pumpAndSettle();
}

Future<void> editSession(WidgetTester tester) async {
  await tester.tap(inExplore(find.text('Plantas')));
  await tester.enterText(inExplore(find.byType(TextField)), 'a');
  tester.testTextInput.hide();
  tester.binding.focusManager.primaryFocus?.unfocus();
  await tester.pumpAndSettle();
}

void fresh(WidgetTester tester) {
  expect(find.byType(ExplorePage), findsOneWidget);
  expect(query(tester).text, isEmpty);
  selected('Todas');
  expect(scroll(tester).offset, 0);
}

void home(Harness h) {
  expect(h.router.state.uri.path, '/');
  expect(h.router.canPop(), isFalse);
  expect(find.byType(HomePage, skipOffstage: false), findsOneWidget);
  expect(find.byType(ExplorePage, skipOffstage: false), findsNothing);
  expect(
    find.byType(PlantPassportRoutePage, skipOffstage: false),
    findsNothing,
  );
}

void qaTestWidgets(String name, Future<void> Function(WidgetTester) body) {
  testWidgets(name, (tester) async {
    final original = debugPrint;
    final messages = <String>[];
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null) messages.add(message);
    };
    try {
      await body(tester);
    } finally {
      // Restore before Flutter verifies global debug invariants.
      debugPrint = original;
    }
    expect(messages, isEmpty, reason: 'Navigation generated debugPrint logs');
    print('ROUTER-QA debugPrint=0 (including Home/query logs)');
  });
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final loader = FontLoader('Roboto');
    for (final weight in ['Regular', 'Medium']) {
      final bytes = File('test/fixtures/fonts/Roboto-$weight.ttf')
          .readAsBytesSync();
      loader.addFont(Future.value(ByteData.sublistView(bytes)));
    }
    await loader.load();
  });
  qaTestWidgets('RQ01 five UI rows resolve exact ID and scientific identity', (
    tester,
  ) async {
    final h = await mount(tester);
    await openExplore(tester, h);
    for (final plant in identities) {
      expect(inExplore(find.text(plant.$3)), findsOneWidget);
      await choose(tester, plant.$2);
      expect(h.router.state.uri.path, '/explore/${plant.$1}');
      final page = find.byType(PlantPassportPage);
      expect(page, findsOneWidget);
      expect(
        find.descendant(of: page, matching: find.text(plant.$2)),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.descendant(of: page, matching: find.text(plant.$3)),
        findsAtLeastNWidgets(1),
      );
      await back(tester, false, 'Volver a Explorar');
      expect(h.router.state.uri.path, '/explore');
    }
    expect(h.loads, 1);
  });

  for (final framework in [false, true]) {
    final mode = framework ? 'frameworkBack' : 'chevron';
    qaTestWidgets(
      'RQ02-$mode nonzero scroll and live session survive P05 pop',
      (tester) async {
        final h = await mount(tester);
        await openExplore(tester, h);
        await editSession(tester);
        final oldQuery = query(tester);
        final oldState = tester.state(find.byType(ExplorePage));
        final oldScroll = scroll(tester);
        await tester.drag(list, const Offset(0, -180));
        await tester.pumpAndSettle();
        final offset = oldScroll.offset;
        expect(offset, greaterThan(0));
        // Menta is now reachable; do not change scroll via ensureVisible.
        await tester.tap(inExplore(find.text('Menta')));
        await tester.pumpAndSettle();
        expect(h.router.state.uri.path, '/explore/619');
        await back(tester, framework, 'Volver a Explorar');
        expect(h.router.state.uri.path, '/explore');
        expect(
          identical(tester.state(find.byType(ExplorePage)), oldState),
          isTrue,
        );
        expect(identical(scroll(tester), oldScroll), isTrue);
        expect(scroll(tester).offset, offset);
        expect(oldQuery.text, 'a');
        print('ROUTER-QA restored offset=$offset query=a filter=Plantas');
        await tester.drag(list, const Offset(0, 500));
        await tester.pumpAndSettle();
        expect(identical(query(tester), oldQuery), isTrue);
        selected('Plantas');
        expect(h.loads, 1);
      },
    );

    qaTestWidgets('RQ03-$mode P04 pops to sole Home', (tester) async {
      final h = await mount(tester);
      await openExplore(tester, h);
      await back(tester, framework, 'Volver a Inicio');
      home(h);
    });

    for (final id in ['619', '999999', 'not-a-plant']) {
      qaTestWidgets('RQ04-$id-$mode direct P05 then fresh P04 then Home', (
        tester,
      ) async {
        final h = await mount(tester);
        h.router.go('/explore/$id');
        await tester.pumpAndSettle();
        expect(h.router.state.uri.path, '/explore/$id');
        expect(
          find.text(id == '619' ? identities.last.$3 : 'Planta no encontrada'),
          findsAtLeastNWidgets(1),
        );
        await back(tester, framework, 'Volver a Explorar');
        expect(h.router.state.uri.path, '/explore');
        fresh(tester);
        await back(tester, framework, 'Volver a Inicio');
        home(h);
        expect(h.loads, 1);
      });
    }

    qaTestWidgets(
      'RQ06-$mode persistent loader error retries and pops safely',
      (tester) async {
        final h = await mount(tester, fail: true);
        h.router.go('/explore/619');
        await tester.pumpAndSettle();
        expect(find.text('No se pudo cargar el catálogo'), findsOneWidget);
        await tester.tap(find.text('Reintentar'));
        await tester.pumpAndSettle();
        expect(find.text('No se pudo cargar el catálogo'), findsOneWidget);
        expect(h.loads, 2);
        await back(tester, framework, 'Volver a Explorar');
        fresh(tester);
        expect(
          find.text('No se pudo cargar el catálogo local.'),
          findsOneWidget,
        );
        await back(tester, framework, 'Volver a Inicio');
        home(h);
      },
    );
  }

  for (final destination in ['P04', 'P05', 'unknown', 'error']) {
    qaTestWidgets(
      'RQ05-$destination Inicio clears stack and reentry is fresh',
      (tester) async {
        final h = await mount(tester, fail: destination == 'error');
        if (destination == 'unknown' || destination == 'error') {
          h.router.go(
            '/explore/${destination == 'unknown' ? '999999' : '619'}',
          );
          await tester.pumpAndSettle();
        } else {
          await openExplore(tester, h);
          await editSession(tester);
          if (destination == 'P05') await choose(tester, 'Menta');
        }
        await tester.tap(find.text('Inicio'));
        await tester.pumpAndSettle();
        home(h);
        await openExplore(tester, h);
        fresh(tester);
        await back(tester, false, 'Volver a Inicio');
        home(h);
      },
    );
  }

  qaTestWidgets('RQ07 loading P05 can pop to fresh loading P04 and Home', (
    tester,
  ) async {
    final pending = Completer<String>();
    final h = await mount(tester, pending: pending);
    h.router.go('/explore/619');
    await tester.pumpAndSettle();
    expect(find.text('Cargando catálogo...'), findsOneWidget);
    await back(tester, false, 'Volver a Explorar');
    fresh(tester);
    expect(find.text('Cargando catálogo...'), findsOneWidget);
    await back(tester, true, 'Volver a Inicio');
    home(h);
    pending.complete(File('assets/data/plant_catalog.json').readAsStringSync());
    await tester.pumpAndSettle();
    home(h);
    expect(h.loads, 1);
  });
}
