// Shared real-app smoke flow: Home, goal search (P06), Explore (P04) backed by
// the catalog API, plant passport (P05) and every return path.
//
// Two callers run this identical flow:
//
// * `integration_test/app_test.dart` on an Android device or emulator. It
//   starts the real `main()` and talks to the real catalog API, so the backend
//   must be running first:
//
//       docker compose up -d                      # from the repository root
//       flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO \
//         --dart-define=API_TOKEN=<uno de los tokens de API_TOKENS>
//
//   The API requires `Authorization: Bearer <token>`, so the real app needs
//   `API_TOKEN` too (the app reads it through `apiTokenFromEnvironment`). Without
//   it the flow fails at once with a message that says so; the message never
//   contains a token value.
//
//   The default base URL is `http://10.0.2.2:8080` (the host machine as seen
//   from the Android emulator). On a physical device pass the address of the
//   machine running the backend:
//
//       flutter test integration_test/app_test.dart -d ID_DEL_DISPOSITIVO \
//         --dart-define=API_BASE_URL=http://192.168.1.20:8080 \
//         --dart-define=API_TOKEN=<token>
//
//   An application-level guard only lets `HttpClient` reach the host and port
//   of that base URL; any other host fails the test with a clear error. It does
//   not test device radios.
//
// * `test/app/catalog_smoke_contract_test.dart` as a widget test, passing
//   [overrides] with a fake HTTP client over fixtures: no network, no backend.
//   Host success is contract evidence only, never Android QA.
//
// The flow never assumes which plants the first page holds nor how many: it
// searches for `lavandula` and expects the "Lavanda" row
// (the seed's display name).
import 'dart:async';
import 'dart:io';

import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/features/catalog/data/catalog_api_config.dart';
import 'package:boticario_ai/features/explore/application/explore_controller.dart';
import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_search_page.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:boticario_ai/main.dart' as app;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
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

/// The row and passport the flow looks for. `lavandula` is stable catalog data
/// both in the API and in the test fixtures.
const _searchTerm = 'lavandula';
const _lavenderCommon = 'Lavanda';
const _lavenderScientific = 'Lavandula angustifolia';
const _lavenderPath = '/explore/lavandula-angustifolia';

/// Shown when the real app runs without `API_TOKEN`. It names the define but
/// never a token value.
const missingApiTokenMessage =
    'Falta API_TOKEN: la API exige un token. Añade '
    '--dart-define=API_TOKEN=<token> con uno de los tokens de API_TOKENS del '
    'backend (para el backend local, el .env de la raíz).';

/// How long a screen may wait for the catalog API before the flow fails.
const _networkTimeout = Duration(seconds: 30);

/// The Android integration test and host contract test exercise this identical
/// real-app UI flow.
///
/// With [overrides] the app is mounted as `ProviderScope(overrides: ...)` over
/// the real [BoticarioApp] (the contract test injects a fake HTTP client this
/// way). Without them `app.main()` runs unchanged.
///
/// With [guardApplicationHttp] every `HttpClient` created inside the flow may
/// only connect to the host and port of the API base URL.
///
/// [requestCount], when given, reports how many API requests were made so the
/// flow can prove that the `Aceites` filter does not call the API.
Future<void> runCatalogSmoke(
  WidgetTester tester, {
  List<Override>? overrides,
  bool guardApplicationHttp = true,
  bool simulateKeyboardViewport = false,
  int Function()? requestCount,
}) {
  // Real app against a real backend: the API needs a token. Fail before any
  // request instead of with a 401 screen. Never print the token itself.
  if (overrides == null && apiTokenFromEnvironment.isEmpty) {
    throw TestFailure(missingApiTokenMessage);
  }
  if (!guardApplicationHttp) {
    return _runCatalogSmoke(
      tester,
      overrides: overrides,
      simulateKeyboardViewport: simulateKeyboardViewport,
      requestCount: requestCount,
    );
  }
  final httpGuard = _AllowOnlyApiHostGuard(
    Uri.parse(normalizeApiBaseUrl(apiBaseUrlFromEnvironment)),
  );
  // A zone-scoped override covers the app and its descendant async work without
  // replacing a process-global override owned by another test.
  return HttpOverrides.runZoned(
    () => _runCatalogSmoke(
      tester,
      overrides: overrides,
      httpGuard: httpGuard,
      simulateKeyboardViewport: simulateKeyboardViewport,
      requestCount: requestCount,
    ),
    createHttpClient: httpGuard.create,
  );
}

Future<void> _runCatalogSmoke(
  WidgetTester tester, {
  List<Override>? overrides,
  _AllowOnlyApiHostGuard? httpGuard,
  required bool simulateKeyboardViewport,
  int Function()? requestCount,
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
    if (overrides == null) {
      app.main();
    } else {
      await tester.pumpWidget(
        ProviderScope(overrides: overrides, child: const BoticarioApp()),
      );
    }
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
    // The first page comes from the API: only assert that it has rows.
    await _tapAndExpectHomeLog(
      tester,
      homeLogs,
      HomeAction.explorePlantsAndOils,
    );
    await _waitForFirstPage(tester);
    expect(find.byType(ExplorePage), findsOneWidget);
    _expectPath(router, '/explore');
    expect(_selectedChip(tester, 'Todas'), isTrue);

    // The query goes to the API after the debounce; the rows come from it.
    final query = find.byType(TextField);
    await _search(tester, _searchTerm);
    await _waitForLavenderRow(tester);
    await _search(tester, 'zzzz sin coincidencias privadas');
    await _waitFor(
      tester,
      find.text('No se encontraron plantas'),
      reason: 'empty search result',
    );
    await _search(tester, _searchTerm);
    await _waitForLavenderRow(tester);

    // Oils are not in the catalog: the filter shows its empty state without
    // asking the API, and Todas brings the list back with the query kept.
    final requestsBeforeOils = requestCount?.call();
    await _tapVisible(tester, find.text('Aceites'));
    expect(
      find.text('No hay aceites disponibles en este catálogo'),
      findsOneWidget,
    );
    expect(_selectedChip(tester, 'Aceites'), isTrue);
    if (requestCount != null) {
      expect(
        requestCount(),
        requestsBeforeOils,
        reason: 'the Aceites filter must not call the API',
      );
    }
    await _tapVisible(tester, find.text('Todas'));
    await _waitForLavenderRow(tester);
    expect(_selectedChip(tester, 'Todas'), isTrue);
    expect(_textFieldValue(tester), _searchTerm);
    expect(query, findsOneWidget);
    await _tapVisible(tester, find.byTooltip('Borrar búsqueda'));
    await _waitForFirstPage(tester);
    expect(_textFieldValue(tester), isEmpty);
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
    await _waitForFirstPage(tester);
    _expectFreshExplore(tester, router);
    await _tapVisible(tester, find.text('Plantas'));
    await _search(tester, _searchTerm);
    await _waitForLavenderRow(tester);
    final queryController = tester
        .widget<TextField>(find.byType(TextField))
        .controller!;
    if (simulateKeyboardViewport) {
      await _setViewInsets(tester, const FakeViewPadding(bottom: 1200));
      // Popping back refocuses the field and Flutter scrolls the caret into
      // view, which would mask the clamp this diagnostic wants to observe.
      tester.binding.focusManager.primaryFocus?.unfocus();
      await _settle(tester);
    } else {
      await _closeKeyboardForStableCapture(tester);
    }
    final lavender = _lavenderRow();
    await _ensureVisible(tester, lavender);
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
    await _tapPrepared(tester, lavender);
    await _waitForPassport(tester);
    _expectPath(router, _lavenderPath);
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
    expect(find.text(_lavenderCommon), findsWidgets);
    expect(find.text(_lavenderScientific), findsWidgets);
    for (final tab in ['General', 'Propiedades', 'Usos']) {
      expect(find.widgetWithText(ChoiceChip, tab), findsOneWidget);
    }
    expect(_selectedChip(tester, 'General'), isTrue);
    expect(find.text('Lamiaceae'), findsOneWidget);
    expect(find.text('No aplicable: ficha de planta'), findsOneWidget);
    await _tapVisible(tester, find.text('Propiedades'));
    expect(_selectedChip(tester, 'Propiedades'), isTrue);
    expect(
      find.textContaining(
        'sin propiedades medicinales evaluadas en este catálogo',
      ),
      findsOneWidget,
    );
    await _tapVisible(tester, find.text('Usos'));
    expect(_selectedChip(tester, 'Usos'), isTrue);
    expect(find.text('Registros tradicionales'), findsOneWidget);
    expect(
      find.text(
        'No es una recomendación de uso ni evidencia de eficacia clínica',
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
    await _ensureVisible(tester, lavender);
    final frameworkBackBefore = _scrollSnapshot(
      tester,
      stage: 'P04.before-framework-tap.stable-viewport',
      controller: scrollController,
      queryController: queryController,
    );
    await _tapPrepared(tester, lavender);
    await _waitForPassport(tester);
    _expectPath(router, _lavenderPath);
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
    await _waitForFirstPage(tester);
    _expectFreshExplore(tester, router);

    await _search(tester, _searchTerm);
    await _waitForLavenderRow(tester);
    await _ensureVisible(tester, _lavenderRow());
    await _tapPrepared(tester, _lavenderRow());
    await _waitForPassport(tester);
    _expectPath(router, _lavenderPath);
    expect(find.byType(PlantPassportPage), findsOneWidget);
    expect(find.text(_lavenderCommon), findsWidgets);
    expect(find.text(_lavenderScientific), findsWidgets);

    // This finder is evaluated only after asserting P05's route and page.
    await _tapCatalogHome(tester, PlantPassportPage);
    _expectHomeAndCleanStack(tester, router);
    await _tapAndExpectHomeLog(
      tester,
      homeLogs,
      HomeAction.explorePlantsAndOils,
    );
    await _waitForFirstPage(tester);
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
    if (httpGuard != null) {
      expect(
        httpGuard.denied,
        isEmpty,
        reason:
            'the application-level guard only allows ${httpGuard.allowed}; '
            'it does not test device radios',
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
  // The field and chips may be scrolled out of the built range, so the
  // retained session is read from the captured controller and the provider.
  final queryController = beforePassport.queryController;
  expect(queryController.text, _searchTerm);
  final state = ProviderScope.containerOf(
    tester.element(find.byType(ExplorePage)),
  ).read(exploreControllerProvider);
  expect(state.query, _searchTerm);
  expect(state.filter, ExploreFilter.plants);
  expect(_lavenderRow(), findsOneWidget);
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
    _expectPath(router, _lavenderPath);
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

Finder _lavenderRow() =>
    find.bySemanticsLabel('$_lavenderCommon, $_lavenderScientific');

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

/// Types [text] and waits past the debounce so the request is sent.
Future<void> _search(WidgetTester tester, String text) async {
  // The field is the first item of the scroll view; an earlier tap may have
  // scrolled it out of the built range.
  final scroll = find.byType(CustomScrollView);
  if (scroll.evaluate().isNotEmpty) {
    final controller = _scrollController(tester);
    if (controller.hasClients && controller.offset != 0) {
      controller.jumpTo(0);
      await tester.pump();
    }
  }
  await tester.enterText(find.byType(TextField), text);
  await tester.pump(exploreDebounce + const Duration(milliseconds: 50));
}

/// Pumps frames until [finder] matches. The wait is real time on a device
/// (the API takes a while) and fake time in a widget test.
Future<void> _waitFor(
  WidgetTester tester,
  Finder finder, {
  required String reason,
  Duration timeout = _networkTimeout,
}) async {
  const step = Duration(milliseconds: 100);
  for (
    var waited = Duration.zero;
    finder.evaluate().isEmpty && waited < timeout;
    waited += step
  ) {
    await tester.pump(step);
  }
  expect(
    finder,
    findsWidgets,
    reason:
        'timed out waiting for $reason; '
        'loading=${find.byKey(const ValueKey('catalog-loading')).evaluate().length}, '
        'error=${find.byKey(const ValueKey('catalog-error')).evaluate().length}, '
        'passportLoading=${find.text('Cargando planta...').evaluate().length}',
  );
  await _settle(tester);
}

/// The first page has at least one plant row; it never assumes which ones.
Future<void> _waitForFirstPage(WidgetTester tester) async {
  await _waitFor(
    tester,
    find.descendant(
      of: find.byType(ExplorePage),
      matching: find.byIcon(Icons.local_florist),
    ),
    reason: 'the first catalog page',
  );
  expect(find.byKey(const ValueKey('catalog-loading')), findsNothing);
  expect(find.byKey(const ValueKey('catalog-error')), findsNothing);
}

Future<void> _waitForLavenderRow(WidgetTester tester) async {
  await _waitFor(
    tester,
    find.text(_lavenderCommon),
    reason: 'the "$_lavenderCommon" row for "$_searchTerm"',
  );
  expect(find.text(_lavenderScientific), findsWidgets);
}

Future<void> _waitForPassport(WidgetTester tester) => _waitFor(
  tester,
  find.byType(PlantPassportPage),
  reason: 'the plant passport',
);

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

/// Lets `HttpClient` connect only to the API base URL host and port. Any other
/// destination is recorded in [denied] and fails with a clear error.
class _AllowOnlyApiHostGuard {
  _AllowOnlyApiHostGuard(this._base);

  final Uri _base;
  final denied = <String>[];

  String get allowed => '${_base.host}:${_base.port}';

  HttpClient create(SecurityContext? context) {
    // The root zone has no HttpOverrides, so this builds the real client
    // instead of recursing into this factory.
    final client = Zone.root.run(() => HttpClient(context: context));
    client.connectionFactory = (uri, proxyHost, proxyPort) async {
      if (uri.host != _base.host || uri.port != _base.port) {
        final target = '${uri.host}:${uri.port}';
        denied.add(target);
        throw StateError(
          'HTTP to $target forbidden by the smoke harness: only $allowed '
          '(API_BASE_URL) is allowed',
        );
      }
      // For https the client upgrades this plain socket itself.
      return Socket.startConnect(proxyHost ?? uri.host, proxyPort ?? uri.port);
    };
    return client;
  }
}
