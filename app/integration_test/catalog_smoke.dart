import 'dart:io';

import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_search_page.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:boticario_ai/main.dart' as app;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Literal smoke oracle. It deliberately does not use the production helper.
const _messages = <HomeAction, String>{
  HomeAction.headerMenu: '[Home] Cabecera: Menú',
  HomeAction.headerProfile: '[Home] Cabecera: Perfil',
  HomeAction.explorePlantsAndOils: '[Home] Explorar plantas y aceites',
  HomeAction.searchByGoal: '[Home] Buscar por objetivo',
  HomeAction.identifyWithCamera: '[Home] Identificar con cámara',
  HomeAction.formulateBlends: '[Home] Formular mezclas',
  HomeAction.askTheBoticario: '[Home] Preguntar al Boticario',
  HomeAction.tabHome: '[Home] Pestaña: Inicio',
  HomeAction.tabFavorites: '[Home] Pestaña: Favoritos',
  HomeAction.tabHistory: '[Home] Pestaña: Historial',
  HomeAction.tabProfile: '[Home] Pestaña: Perfil',
};

const _footerActions = <HomeAction>{
  HomeAction.tabHome,
  HomeAction.tabFavorites,
  HomeAction.tabHistory,
  HomeAction.tabProfile,
};

const _catalogRows = <(String, String)>[
  ('Lavanda', 'Lavandula angustifolia'),
  ('Eucalipto', 'Eucalyptus globulus'),
  ('Romero', 'Rosmarinus officinalis'),
  ('Manzanilla', 'Matricaria recutita'),
  ('Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
];

/// The Android integration test and host preflight exercise this identical
/// real-app UI flow. Host success is preflight evidence only, never Android QA.
Future<void> runCatalogSmoke(
  WidgetTester tester, {
  bool guardApplicationHttp = true,
  bool simulateKeyboardViewport = false,
}) {
  if (!guardApplicationHttp) {
    return _runCatalogSmoke(
      tester,
      guardApplicationHttp: false,
      simulateKeyboardViewport: simulateKeyboardViewport,
    );
  }
  final httpGuard = _DenyHttpClientFactory();
  // A zone-scoped override covers the app and its descendant async work without
  // replacing a process-global override owned by another test.
  return HttpOverrides.runZoned(
    () => _runCatalogSmoke(
      tester,
      guardApplicationHttp: true,
      httpGuard: httpGuard,
      simulateKeyboardViewport: simulateKeyboardViewport,
    ),
    createHttpClient: httpGuard.create,
  );
}

Future<void> _runCatalogSmoke(
  WidgetTester tester, {
  required bool guardApplicationHttp,
  _DenyHttpClientFactory? httpGuard,
  required bool simulateKeyboardViewport,
}) async {
  final previousDebugPrint = debugPrint;
  final originalViewInsets = tester.view.viewInsets;
  final homeLogs = <String>[];
  final semantics = tester.ensureSemantics();

  debugPrint = (String? message, {int? wrapWidth}) {
    if (message != null && message.startsWith('[Home]')) homeLogs.add(message);
    previousDebugPrint(message, wrapWidth: wrapWidth);
  };
  try {
    app.main();
    await _settle(tester);
    final router = GoRouter.of(tester.element(find.byType(HomePage)));

    // P03 is the real scope/router/theme app at its initial route.
    expect(router.state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);
    expect(find.text('Boticario AI'), findsOneWidget);
    expect(
      find.text('Pequeñas esencias, grandes posibilidades'),
      findsOneWidget,
    );
    expect(find.text('Hola, Boticario AI'), findsNothing);
    expect(find.textContaining('Contador'), findsNothing);
    expect(find.text('Incrementar'), findsNothing);
    expect(homeLogs, isEmpty, reason: 'build must not emit Home action logs');
    _expectHomeSelected(tester);

    // The nine inert P03 controls stay on / and each emits its exact literal.
    for (final action in <HomeAction>[
      HomeAction.headerMenu,
      HomeAction.headerProfile,
      HomeAction.identifyWithCamera,
      HomeAction.formulateBlends,
      HomeAction.askTheBoticario,
      HomeAction.tabHome,
      HomeAction.tabFavorites,
      HomeAction.tabHistory,
      HomeAction.tabProfile,
    ]) {
      await _tapAndExpectHomeLog(tester, homeLogs, action);
      _expectPath(router, '/');
      expect(find.byType(HomePage), findsOneWidget);
      _expectHomeSelected(tester);
      expect(find.byType(SnackBar), findsNothing);
      expect(find.byType(Dialog), findsNothing);
      expect(find.byType(Drawer), findsNothing);
    }

    // P06 is visited three times to exercise each return mechanism. Goal rows
    // and the three unavailable footer tabs remain inert on every visit.
    await _tapAndExpectHomeLog(tester, homeLogs, HomeAction.searchByGoal);
    _expectGoalSearch(tester, router);
    await _tapGoalRowsAndDisabledFooter(tester, router);
    await _tapVisible(tester, find.byTooltip('Volver a Inicio'));
    _expectHomeAndCleanStack(tester, router);

    await _tapAndExpectHomeLog(tester, homeLogs, HomeAction.searchByGoal);
    _expectGoalSearch(tester, router);
    await _tapGoalRowsAndDisabledFooter(tester, router);
    await tester.binding.handlePopRoute();
    await _settle(tester);
    _expectHomeAndCleanStack(tester, router);

    await _tapAndExpectHomeLog(tester, homeLogs, HomeAction.searchByGoal);
    _expectGoalSearch(tester, router);
    await _tapGoalRowsAndDisabledFooter(tester, router);
    await _tapVisible(tester, find.text('Inicio').last);
    _expectHomeAndCleanStack(tester, router);

    // Explore activation #1 is explicitly distinct from the nine inert actions.
    await _tapAndExpectHomeLog(
      tester,
      homeLogs,
      HomeAction.explorePlantsAndOils,
    );
    await _waitForCatalog(tester);
    expect(find.byType(ExplorePage), findsOneWidget);
    _expectPath(router, '/explore');
    expect(_selectedChip(tester, 'Todas'), isTrue);
    for (final row in _catalogRows) {
      await _ensureVisible(tester, _catalogRow(row.$1, row.$2));
    }

    // P04 search is local and normalizes scientific/common spelling; filter and
    // clear combine without deriving an oil identity from a plant.
    final query = find.byType(TextField);
    await tester.enterText(query, '  LAVÁNDULA   ANGUSTIFOLIA ');
    await _settle(tester);
    expect(find.text('Lavanda'), findsOneWidget);
    expect(find.text('Manzanilla'), findsNothing);
    await tester.enterText(query, 'MENTA');
    await _settle(tester);
    expect(find.text('Menta'), findsOneWidget);
    await tester.enterText(query, 'sin coincidencias privadas');
    await _settle(tester);
    expect(find.text('No se encontraron plantas'), findsOneWidget);
    await _tapVisible(tester, find.text('Aceites'));
    expect(
      find.text('No hay aceites disponibles en este catálogo'),
      findsOneWidget,
    );
    await _tapVisible(tester, find.byTooltip('Borrar búsqueda'));
    expect(
      find.text('No hay aceites disponibles en este catálogo'),
      findsOneWidget,
    );
    expect(_selectedChip(tester, 'Aceites'), isTrue);
    await _expectCatalogFooterDisabled(tester, ExplorePage, router);

    // P04 Inicio is a real UI activation and clears the stack.
    await _tapCatalogHome(tester, ExplorePage);
    _expectHomeAndCleanStack(tester, router);

    // New P04 session: default filter/query, then preserve a live P04 session
    // across both P05 return mechanisms.
    await _tapAndExpectHomeLog(
      tester,
      homeLogs,
      HomeAction.explorePlantsAndOils,
    );
    await _waitForCatalog(tester);
    _expectFreshExplore(tester, router);
    await _tapVisible(tester, find.text('Plantas'));
    await tester.enterText(find.byType(TextField), 'A');
    await _settle(tester);
    final queryController = tester
        .widget<TextField>(find.byType(TextField))
        .controller!;
    if (simulateKeyboardViewport) {
      await _setViewInsets(tester, const FakeViewPadding(bottom: 1200));
    } else {
      await _closeKeyboardForStableCapture(tester);
    }
    final mint = _catalogRow(
      'Menta',
      'Mentha x piperita subsp. nothosubsp. piperita',
    );
    await _ensureVisible(tester, mint);
    final scrollController = _scrollController(tester);
    final beforePassport = _scrollSnapshot(
      tester,
      stage: simulateKeyboardViewport
          ? 'P04.before-tap.ime-inset'
          : 'P04.before-tap.stable-viewport',
      controller: scrollController,
      queryController: queryController,
    );
    if (beforePassport.maxExtent == 0) {
      expect(beforePassport.offset, 0);
    } else {
      expect(beforePassport.offset, greaterThan(0));
    }
    await _tapPrepared(tester, mint);
    _expectPath(router, '/explore/619');
    if (simulateKeyboardViewport) {
      // Model Android's keyboard closure after the focused P04 field goes
      // offstage. This is a diagnostic viewport transition, not production UI.
      await _setViewInsets(tester, FakeViewPadding.zero);
    }
    _scrollSnapshot(
      tester,
      stage: 'P05.after-navigation',
      controller: scrollController,
      queryController: queryController,
    );
    expect(find.byType(PlantPassportPage), findsOneWidget);
    expect(_selectedChip(tester, 'General'), isTrue);
    expect(find.text('Menta'), findsWidgets);
    expect(
      find.text('Mentha x piperita subsp. nothosubsp. piperita'),
      findsWidgets,
    );
    expect(find.text('No disponible en fuente'), findsWidgets);
    expect(find.text('No aplicable: ficha de planta'), findsOneWidget);
    await _tapVisible(tester, find.text('Propiedades'));
    expect(
      find.text('sin propiedades medicinales evaluadas en este catálogo'),
      findsOneWidget,
    );
    await _tapVisible(tester, find.text('Usos'));
    expect(
      find.text(
        'No hay usos tradicionales con referencia verificable disponibles',
      ),
      findsOneWidget,
    );
    await _expectPassportDisabled(tester, router, homeLogs);

    // First real P05 return: its chevron restores the captured P04 state.
    _scrollSnapshot(
      tester,
      stage: 'P05.before-chevron-return',
      controller: scrollController,
      queryController: queryController,
    );
    await _tapVisible(tester, find.byTooltip('Volver a Explorar'));
    _expectRestoredExplore(
      tester,
      router,
      beforePassport,
      expectExactOffset: !simulateKeyboardViewport,
    );

    // Second real P05 return: framework pop route simulates Android Back; it
    // is intentionally not presented as a physical Back-button observation.
    await _ensureVisible(tester, mint);
    final frameworkBackBefore = _scrollSnapshot(
      tester,
      stage: 'P04.before-framework-tap.stable-viewport',
      controller: scrollController,
      queryController: queryController,
    );
    await _tapPrepared(tester, mint);
    _expectPath(router, '/explore/619');
    _scrollSnapshot(
      tester,
      stage: 'P05.after-framework-navigation',
      controller: scrollController,
      queryController: queryController,
    );
    await tester.binding.handlePopRoute();
    await _settle(tester);
    _expectRestoredExplore(
      tester,
      router,
      frameworkBackBefore,
      expectExactOffset: true,
    );

    // Return from P04, then use P05 Inicio (not an offstage P04 finder).
    await _tapCatalogHome(tester, ExplorePage);
    _expectHomeAndCleanStack(tester, router);
    await _tapAndExpectHomeLog(
      tester,
      homeLogs,
      HomeAction.explorePlantsAndOils,
    );
    await _waitForCatalog(tester);
    _expectFreshExplore(tester, router);

    await tester.enterText(find.byType(TextField), 'Lavanda');
    await _settle(tester);
    final lavender = _catalogRow('Lavanda', 'Lavandula angustifolia');
    await _ensureVisible(tester, lavender);
    await _tapPrepared(tester, lavender);
    _expectPath(router, '/explore/544');
    expect(find.byType(PlantPassportPage), findsOneWidget);
    expect(find.text('Lavanda'), findsWidgets);
    expect(find.text('Lavandula angustifolia'), findsWidgets);
    await _tapVisible(tester, find.text('Usos'));
    expect(find.text('Registros tradicionales'), findsOneWidget);
    expect(find.text('Carminative'), findsOneWidget);
    expect(
      find.text(
        'Steinmetz, E.F. 1957. codex Vegetabilis. Published by the author, Amsterdam.',
      ),
      findsWidgets,
    );
    expect(
      find.text(
        'No es una recomendación de uso ni evidencia de eficacia clínica',
      ),
      findsOneWidget,
    );

    // This finder is evaluated only after asserting P05's route and page.
    await _tapCatalogHome(tester, PlantPassportPage);
    _expectHomeAndCleanStack(tester, router);
    await _tapAndExpectHomeLog(
      tester,
      homeLogs,
      HomeAction.explorePlantsAndOils,
    );
    await _waitForCatalog(tester);
    _expectFreshExplore(tester, router);

    // Framework pop from P04 returns to Home; this is not a physical Back claim.
    await tester.binding.handlePopRoute();
    await _settle(tester);
    _expectHomeAndCleanStack(tester, router);

    // Exact sequence proves all 11 action mappings, repeated route entry
    // counts, and no build logs.
    expect(homeLogs, <String>[
      _messages[HomeAction.headerMenu]!,
      _messages[HomeAction.headerProfile]!,
      _messages[HomeAction.identifyWithCamera]!,
      _messages[HomeAction.formulateBlends]!,
      _messages[HomeAction.askTheBoticario]!,
      _messages[HomeAction.tabHome]!,
      _messages[HomeAction.tabFavorites]!,
      _messages[HomeAction.tabHistory]!,
      _messages[HomeAction.tabProfile]!,
      _messages[HomeAction.searchByGoal]!,
      _messages[HomeAction.searchByGoal]!,
      _messages[HomeAction.searchByGoal]!,
      _messages[HomeAction.explorePlantsAndOils]!,
      _messages[HomeAction.explorePlantsAndOils]!,
      _messages[HomeAction.explorePlantsAndOils]!,
      _messages[HomeAction.explorePlantsAndOils]!,
    ]);
    if (guardApplicationHttp) {
      expect(
        httpGuard!.attempts,
        0,
        reason: 'the application-level guard saw no HttpClient creation; it does not test device radios',
      );
    }
  } finally {
    debugPrint = previousDebugPrint;
    if (simulateKeyboardViewport) tester.view.viewInsets = originalViewInsets;
    semantics.dispose();
  }
}

const _goalLabels = <String>[
  'Relajación / Estrés',
  'Mejorar el sueño',
  'Cuidado de la piel',
  'Alivio respiratorio',
  'Concentración',
  'Otros objetivos',
];

void _expectGoalSearch(WidgetTester tester, GoRouter router) {
  expect(find.byType(GoalSearchPage), findsOneWidget);
  _expectPath(router, '/goals');
  expect(find.text('¿Qué deseas lograr?'), findsOneWidget);
  expect(find.text('Selecciona un objetivo principal'), findsOneWidget);
  for (final label in _goalLabels) {
    expect(find.text(label), findsOneWidget);
  }
}

Future<void> _tapGoalRowsAndDisabledFooter(
  WidgetTester tester,
  GoRouter router,
) async {
  for (final label in _goalLabels) {
    await _tapVisible(tester, find.text(label));
    expect(find.byType(GoalSearchPage), findsOneWidget);
    _expectPath(router, '/goals');
    expect(find.text(label), findsOneWidget);
    expect(find.byType(SnackBar), findsNothing);
    expect(find.byType(Dialog), findsNothing);
  }
  await _expectCatalogFooterDisabled(
    tester,
    GoalSearchPage,
    router,
    expectedPath: '/goals',
  );
}

void _expectPath(GoRouter router, String path) =>
    expect(router.state.uri.path, path);

void _expectHomeSelected(WidgetTester tester) {
  expect(
    tester.getSemantics(find.byKey(const ValueKey(HomeAction.tabHome))),
    isSemantics(isSelected: true),
  );
}

void _expectHomeAndCleanStack(WidgetTester tester, GoRouter router) {
  expect(find.byType(HomePage), findsOneWidget);
  expect(find.byType(ExplorePage), findsNothing);
  expect(find.byType(PlantPassportPage), findsNothing);
  _expectPath(router, '/');
  expect(router.canPop(), isFalse);
}

void _expectFreshExplore(WidgetTester tester, GoRouter router) {
  expect(find.byType(ExplorePage), findsOneWidget);
  _expectPath(router, '/explore');
  expect(_textFieldValue(tester), isEmpty);
  expect(_selectedChip(tester, 'Todas'), isTrue);
  expect(_scrollController(tester).offset, 0);
}

void _expectRestoredExplore(
  WidgetTester tester,
  GoRouter router,
  _ScrollSnapshot beforePassport, {
  required bool expectExactOffset,
}) {
  expect(find.byType(ExplorePage), findsOneWidget);
  _expectPath(router, '/explore');
  final queryController = tester
      .widget<TextField>(find.byType(TextField))
      .controller!;
  expect(queryController.text, 'A');
  expect(_selectedChip(tester, 'Plantas'), isTrue);
  final controller = _scrollController(tester);
  final afterReturn = _scrollSnapshot(
    tester,
    stage: expectExactOffset
        ? 'P04.after-return.stable-viewport'
        : 'P04.after-return.viewport-changed',
    controller: controller,
    queryController: queryController,
  );
  expect(identical(controller, beforePassport.controller), isTrue);
  expect(identical(queryController, beforePassport.queryController), isTrue);
  if (expectExactOffset) {
    expect(afterReturn.viewInset, beforePassport.viewInset);
    expect(afterReturn.viewport, beforePassport.viewport);
    expect(afterReturn.maxExtent, beforePassport.maxExtent);
    expect(afterReturn.offset, beforePassport.offset);
  } else {
    // The controller/state must survive; a changed viewport may legally clamp
    // pixels to the new extent. This assertion identifies that case precisely.
    expect(afterReturn.viewInset, isNot(beforePassport.viewInset));
    expect(
      afterReturn.offset,
      beforePassport.offset.clamp(0, afterReturn.maxExtent).toDouble(),
    );
  }
}

Future<void> _expectCatalogFooterDisabled(
  WidgetTester tester,
  Type pageType,
  GoRouter router, {
  String expectedPath = '/explore',
}) async {
  for (final label in ['Favoritos', 'Historial', 'Perfil']) {
    final disabled = find.bySemanticsLabel('$label no disponible');
    expect(disabled, findsOneWidget);
    expect(
      tester.getSemantics(disabled),
      isSemantics(hasEnabledState: true, isEnabled: false, hasTapAction: false),
    );
    await tester.tap(disabled, warnIfMissed: false);
    await _settle(tester);
    expect(find.byType(pageType), findsOneWidget);
    _expectPath(router, expectedPath);
  }
  final home = _catalogHome(pageType);
  expect(tester.getSemantics(home), isSemantics(isSelected: true));
}

Future<void> _expectPassportDisabled(
  WidgetTester tester,
  GoRouter router,
  List<String> homeLogs,
) async {
  final beforeLogs = homeLogs.length;
  for (final label in [
    'Favorito no disponible',
    'Ver formulaciones relacionadas no disponible',
    'Favoritos no disponible',
    'Historial no disponible',
    'Perfil no disponible',
  ]) {
    final disabled = find.bySemanticsLabel(label);
    expect(disabled, findsOneWidget);
    expect(
      tester.getSemantics(disabled),
      isSemantics(hasEnabledState: true, isEnabled: false, hasTapAction: false),
    );
    await tester.tap(disabled, warnIfMissed: false);
    await _settle(tester);
    expect(find.byType(PlantPassportPage), findsOneWidget);
    _expectPath(router, '/explore/619');
  }
  expect(homeLogs, hasLength(beforeLogs));
  expect(
    tester.getSemantics(_catalogHome(PlantPassportPage)),
    isSemantics(isSelected: true),
  );
}

Finder _catalogHome(Type pageType) => find
    .descendant(of: find.byType(pageType), matching: find.text('Inicio'))
    .first;

Future<void> _tapCatalogHome(WidgetTester tester, Type pageType) async {
  final home = _catalogHome(pageType);
  await _tapVisible(tester, home);
}

Finder _catalogRow(String common, String scientific) =>
    find.bySemanticsLabel('$common, $scientific');

String _textFieldValue(WidgetTester tester) =>
    (tester.widget<TextField>(find.byType(TextField)).controller!).text;

bool _selectedChip(WidgetTester tester, String label) =>
    tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, label)).selected;

ScrollController _scrollController(WidgetTester tester) =>
    tester.widget<CustomScrollView>(find.byType(CustomScrollView)).controller!;

class _ScrollSnapshot {
  const _ScrollSnapshot({
    required this.stage,
    required this.controller,
    required this.queryController,
    required this.offset,
    required this.maxExtent,
    required this.viewport,
    required this.viewInset,
  });

  final String stage;
  final ScrollController controller;
  final TextEditingController queryController;
  final double offset;
  final double maxExtent;
  final double viewport;
  final double viewInset;
}

_ScrollSnapshot _scrollSnapshot(
  WidgetTester tester, {
  required String stage,
  required ScrollController controller,
  required TextEditingController queryController,
}) {
  expect(
    controller.hasClients,
    isTrue,
    reason: '$stage must retain P04 scroll',
  );
  final position = controller.position;
  final snapshot = _ScrollSnapshot(
    stage: stage,
    controller: controller,
    queryController: queryController,
    offset: controller.offset,
    maxExtent: position.maxScrollExtent,
    viewport: position.viewportDimension,
    viewInset: tester.view.viewInsets.bottom / tester.view.devicePixelRatio,
  );
  debugPrint(
    '[CatalogSmoke metrics] stage=${snapshot.stage} '
    'inset=${snapshot.viewInset} viewport=${snapshot.viewport} '
    'maxExtent=${snapshot.maxExtent} offset=${snapshot.offset} '
    'scrollController=${identityHashCode(snapshot.controller)} '
    'queryController=${identityHashCode(snapshot.queryController)} '
    'query=${snapshot.queryController.text}',
  );
  return snapshot;
}

Future<void> _setViewInsets(
  WidgetTester tester,
  FakeViewPadding viewInsets,
) async {
  tester.view.viewInsets = viewInsets;
  await _settle(tester);
}

Future<void> _closeKeyboardForStableCapture(WidgetTester tester) async {
  // This is limited to the session-offset capture. The synthetic-inset test
  // below separately verifies how a viewport change clamps a retained scroll.
  tester.binding.focusManager.primaryFocus?.unfocus();
  await SystemChannels.textInput.invokeMethod<void>('TextInput.hide');
  const maxFrames = 60;
  for (
    var frame = 0;
    frame < maxFrames && tester.view.viewInsets.bottom != 0;
    frame++
  ) {
    await tester.pump(const Duration(milliseconds: 16));
  }
  expect(
    tester.view.viewInsets.bottom,
    0,
    reason: 'keyboard must close before capturing a stable P04 viewport',
  );
  await _settle(tester);
}

Future<void> _settle(WidgetTester tester) =>
    tester.pumpAndSettle(const Duration(milliseconds: 100));

Future<void> _waitForCatalog(WidgetTester tester) async {
  // Completes the same bundled asset through the real bundle channel; unlike a
  // timed delay, this is deterministic and lets its completion reach FakeAsync.
  await tester.runAsync(
    () => rootBundle.loadString('assets/data/plant_catalog.json'),
  );
  const maxFrames = 30;
  for (
    var frame = 0;
    frame < maxFrames && find.text('Lavanda').evaluate().isEmpty;
    frame++
  ) {
    await tester.pump(const Duration(milliseconds: 16));
  }
  expect(
    find.text('Lavanda'),
    findsOneWidget,
    reason:
        'catalog state: loading=${find.text("Cargando catálogo...").evaluate().length}, '
        'error=${find.text("No se pudo cargar el catálogo local.").evaluate().length}',
  );
}

Future<void> _tapAndExpectHomeLog(
  WidgetTester tester,
  List<String> logs,
  HomeAction action,
) async {
  final before = logs.length;
  await _tapHome(tester, action);
  expect(logs, hasLength(before + 1));
  expect(logs.last, _messages[action]);
}

Future<void> _tapHome(WidgetTester tester, HomeAction action) async {
  final control = find.byKey(ValueKey<HomeAction>(action));
  if (!_footerActions.contains(action)) await _ensureVisible(tester, control);
  await _tapPrepared(tester, control);
}

Future<void> _ensureVisible(WidgetTester tester, Finder finder) async {
  final catalogOrPassportScroll = find.byType(CustomScrollView);
  if (catalogOrPassportScroll.evaluate().isEmpty) {
    await tester.ensureVisible(finder);
  } else {
    await tester.scrollUntilVisible(
      finder,
      120,
      scrollable: find
          .descendant(
            of: catalogOrPassportScroll,
            matching: find.byType(Scrollable),
          )
          .first,
    );
  }
  await _settle(tester);
  expect(finder, findsOneWidget);
  expect(finder.hitTestable(), findsOneWidget);
}

Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  await _ensureVisible(tester, finder);
  await _tapPrepared(tester, finder);
}

Future<void> _tapPrepared(WidgetTester tester, Finder finder) async {
  expect(finder, findsOneWidget);
  expect(finder.hitTestable(), findsOneWidget);
  await tester.tap(finder);
  await _settle(tester);
}

class _DenyHttpClientFactory {
  var attempts = 0;

  HttpClient create(SecurityContext? context) {
    attempts++;
    throw StateError('HTTP forbidden by offline integration harness');
  }
}
