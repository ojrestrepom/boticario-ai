import 'dart:io';

import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_repository.dart';
import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

// Literal oracle from specs/home-screen, never computed by production helper.
const inertMessages = {
  HomeAction.headerMenu: '[Home] Cabecera: Menú',
  HomeAction.headerProfile: '[Home] Cabecera: Perfil',
  HomeAction.searchByGoal: '[Home] Buscar por objetivo',
  HomeAction.identifyWithCamera: '[Home] Identificar con cámara',
  HomeAction.formulateBlends: '[Home] Formular mezclas',
  HomeAction.askTheBoticario: '[Home] Preguntar al Boticario',
  HomeAction.tabHome: '[Home] Pestaña: Inicio',
  HomeAction.tabFavorites: '[Home] Pestaña: Favoritos',
  HomeAction.tabHistory: '[Home] Pestaña: Historial',
  HomeAction.tabProfile: '[Home] Pestaña: Perfil',
};
const exploreMessage = '[Home] Explorar plantas y aceites';
const identities = [
  (544, 'Lavanda', 'Lavandula angustifolia'),
  (401, 'Eucalipto', 'Eucalyptus globulus'),
  (873, 'Romero', 'Rosmarinus officinalis'),
  (605, 'Manzanilla', 'Matricaria recutita'),
  (619, 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
];

Finder inExplore(Finder f) =>
    find.descendant(of: find.byType(ExplorePage), matching: f);
ScrollController scroll(WidgetTester t) => t
    .widget<CustomScrollView>(inExplore(find.byType(CustomScrollView)))
    .controller!;
String query(WidgetTester t) =>
    t.widget<TextField>(inExplore(find.byType(TextField))).controller!.text;
void selected(String name) => expect(
  inExplore(
    find.byWidgetPredicate(
      (w) => w is ChoiceChip && w.selected && (w.label as Text).data == name,
    ),
  ),
  findsOneWidget,
);

Future<GoRouter> mount(WidgetTester t) async {
  t.view.physicalSize = const Size(360, 640);
  t.view.devicePixelRatio = 1;
  addTearDown(t.view.resetPhysicalSize);
  addTearDown(t.view.resetDevicePixelRatio);
  final json = File('assets/data/plant_catalog.json').readAsStringSync();
  await t.pumpWidget(
    ProviderScope(
      overrides: [
        plantCatalogAssetDataSourceProvider.overrideWithValue(
          PlantCatalogAssetDataSource(
            loadAsset: (path) async {
              expect(path, plantCatalogAssetPath);
              return json;
            },
          ),
        ),
      ],
      child: const BoticarioApp(),
    ),
  );
  await t.pumpAndSettle();
  final router = GoRouter.of(t.element(find.byType(HomePage)));
  home(t, router);
  return router;
}

void home(WidgetTester t, GoRouter router) {
  expect(router.state.uri.path, '/');
  expect(router.canPop(), isFalse);
  expect(find.byType(HomePage, skipOffstage: false), findsOneWidget);
  expect(find.byType(ExplorePage, skipOffstage: false), findsNothing);
  expect(
    find.byType(PlantPassportRoutePage, skipOffstage: false),
    findsNothing,
  );
  expect(
    t
        .getSemantics(find.byKey(const ValueKey(HomeAction.tabHome)))
        .flagsCollection
        .isSelected
        .toBoolOrNull(),
    isTrue,
  );
}

Future<void> tap(WidgetTester t, Finder f) async {
  await t.ensureVisible(f);
  await t.pumpAndSettle();
  expect(f.hitTestable(), findsOneWidget);
  await t.tap(f);
  await t.pumpAndSettle();
}

Future<void> openExplore(WidgetTester t, GoRouter router) async {
  // All normal navigation starts at the real Home card, never router.push.
  await tap(t, find.byKey(const ValueKey(HomeAction.explorePlantsAndOils)));
  expect(router.state.uri.path, '/explore');
  expect(find.byType(ExplorePage), findsOneWidget);
}

Future<void> edit(WidgetTester t, String text) async {
  await t.enterText(inExplore(find.byType(TextField)), text);
  t.testTextInput.hide();
  t.binding.focusManager.primaryFocus?.unfocus();
  await t.pumpAndSettle();
}

void fresh(WidgetTester t) {
  expect(query(t), isEmpty);
  selected('Todas');
  expect(scroll(t).offset, 0);
}

void noOverlays() {
  expect(find.byType(SnackBar), findsNothing);
  expect(find.byType(Dialog), findsNothing);
  expect(find.byType(Drawer), findsNothing);
  expect(find.byType(BottomSheet), findsNothing);
}

void qa(String id, Future<void> Function(WidgetTester, List<String>) body) {
  testWidgets(id, (t) async {
    final original = debugPrint;
    final messages = <String>[];
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null) messages.add(message);
    };
    try {
      await body(t, messages);
      noOverlays();
      expect(t.takeException(), isNull);
      print(
        'HOME-FLOW-QA $id debugPrint=${messages.length} messages=$messages',
      );
    } finally {
      // Flutter checks debug globals before addTearDown: restore in body.
      debugPrint = original;
    }
  });
}

void main() {
  setUpAll(() async {
    final fonts = FontLoader('Roboto');
    for (final weight in ['Regular', 'Medium']) {
      final bytes = File('test/fixtures/fonts/Roboto-$weight.ttf')
          .readAsBytesSync();
      fonts.addFont(Future.value(ByteData.sublistView(bytes)));
    }
    await fonts.load();
  });

  qa('HQ01 ten inert actions twice: literal logs, immutable Home, no overlays', (
    t,
    logs,
  ) async {
    final router = await mount(t);
    expect(logs, isEmpty);
    final expected = <String>[];
    for (var round = 0; round < 2; round++) {
      for (final entry in inertMessages.entries) {
        final before = find
            .byType(Text)
            .evaluate()
            .map((e) => (e.widget as Text).data)
            .toList();
        await tap(t, find.byKey(ValueKey(entry.key)));
        expected.add(entry.value);
        expect(logs, expected);
        home(t, router);
        expect(
          find
              .byType(Text)
              .evaluate()
              .map((e) => (e.widget as Text).data)
              .toList(),
          before,
        );
        noOverlays();
      }
    }
    t.element(find.byType(HomePage)).markNeedsBuild();
    await t.pumpAndSettle();
    // Host subtree reassembly, not an actual IDE/VM hot reload. Waiting on
    // binding.reassembleApplication without driving frames deadlocks FakeAsync.
    t.element(find.byType(HomePage)).reassemble();
    await t.pumpAndSettle();
    expect(logs, expected);
    home(t, router);
  });

  qa('HQ02 Home card to all five correct passports, pop and rebuild silent', (
    t,
    logs,
  ) async {
    final router = await mount(t);
    await openExplore(t, router);
    expect(logs, [exploreMessage]);
    for (final identity in identities) {
      await tap(t, inExplore(find.text(identity.$2)));
      expect(router.state.uri.path, '/explore/${identity.$1}');
      final page = find.byType(PlantPassportPage);
      expect(
        find.descendant(of: page, matching: find.text(identity.$3)),
        findsAtLeastNWidgets(1),
      );
      await tap(t, find.byTooltip('Volver a Explorar'));
      expect(router.state.uri.path, '/explore');
      expect(logs, [exploreMessage]);
    }
    await tap(t, find.byTooltip('Volver a Inicio'));
    home(t, router);
    t.element(find.byType(HomePage)).markNeedsBuild();
    await t.pumpAndSettle();
    expect(logs, [exploreMessage]);
  });

  for (final frameworkBack in [false, true]) {
    final mode = frameworkBack ? 'frameworkBack-P05Home' : 'chevron-P04Home';
    qa('HQ03-$mode session restores and Home clears stack; reentry fresh', (
      t,
      logs,
    ) async {
      final router = await mount(t);
      await openExplore(t, router);
      await tap(t, inExplore(find.text('Plantas')));
      await edit(t, 'a');
      await t.drag(
        inExplore(find.byType(Scrollable)).first,
        const Offset(0, -180),
      );
      await t.pumpAndSettle();
      final offset = scroll(t).offset;
      expect(offset, greaterThan(0));
      await tap(t, inExplore(find.text('Menta')));
      expect(router.state.uri.path, '/explore/619');
      if (frameworkBack) {
        await t.binding.handlePopRoute();
        await t.pumpAndSettle();
      } else {
        await tap(t, find.byTooltip('Volver a Explorar'));
      }
      expect(router.state.uri.path, '/explore');
      expect(scroll(t).offset, offset);
      expect(query(t), 'a');
      selected('Plantas');
      print(
        'HOME-FLOW-QA restored $mode offset=$offset -> ${scroll(t).offset}',
      );
      if (frameworkBack) await tap(t, inExplore(find.text('Menta')));
      await tap(t, find.text('Inicio').last);
      home(t, router);
      expect(logs, [exploreMessage]);
      await openExplore(t, router);
      fresh(t);
      await t.binding.handlePopRoute();
      await t.pumpAndSettle();
      home(t, router);
      expect(logs, [exploreMessage, exploreMessage]);
    });
  }

  qa(
    'HQ04 catalog negative actions and private query never emit Home or data logs',
    (t, logs) async {
      final router = await mount(t);
      await openExplore(t, router);
      for (final label in ['Favoritos', 'Historial', 'Perfil']) {
        final semantics = find.byWidgetPredicate(
          (w) => w is Semantics && w.properties.label == '$label no disponible',
        );
        expect(
          t.getSemantics(semantics).flagsCollection.isEnabled.toBoolOrNull(),
          isFalse,
        );
        await tap(t, inExplore(find.text(label)));
        expect(router.state.uri.path, '/explore');
      }
      await edit(t, 'QA-private-no-match-4.2');
      expect(find.text('No se encontraron plantas'), findsOneWidget);
      await tap(t, inExplore(find.text('Aceites')));
      expect(
        find.text('No hay aceites disponibles en este catálogo'),
        findsOneWidget,
      );
      await tap(t, find.byTooltip('Borrar búsqueda'));
      selected('Aceites');
      expect(query(t), isEmpty);
      await tap(t, find.text('Inicio').last);
      home(t, router);
      expect(logs, [exploreMessage]);
    },
  );
}
