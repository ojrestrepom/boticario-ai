import 'dart:async';
import 'dart:convert';
import 'dart:ui' show Tristate;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/explore/presentation/explore_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import '../../support/fake_catalog_api.dart';

const _debounce = Duration(milliseconds: 300);

/// Catalog API with `total` generated plants, served `limit` at a time (or
/// `perPage` at a time to simulate a first page that does not fill the
/// screen). Requests can be gated or made to fail per offset.
class _PagedApi {
  _PagedApi({required this.total, this.perPage}) {
    client = MockClient(_handle);
  }

  final int total;
  final int? perPage;
  late final http.Client client;
  final requests = <Uri>[];
  final gates = <int, Completer<void>>{};
  final failOffsets = <int>{};

  List<int> get offsets => [
    for (final uri in requests) int.parse(uri.queryParameters['offset']!),
  ];

  Future<http.Response> _handle(http.Request request) async {
    requests.add(request.url);
    final limit = int.parse(request.url.queryParameters['limit']!);
    final offset = int.parse(request.url.queryParameters['offset']!);
    final gate = gates[offset];
    if (gate != null) await gate.future;
    if (failOffsets.contains(offset)) {
      return http.Response('{"title":"error","status":500}', 500);
    }
    final count = (perPage ?? limit).clamp(0, limit);
    final end = (offset + count).clamp(0, total);
    return http.Response.bytes(
      utf8.encode(
        jsonEncode({
          'items': [
            for (var i = offset; i < end; i++)
              {
                'id': 'plant-$i',
                'scientificName': 'Genus species $i',
                'commonNames': [
                  {'text': 'Common $i', 'language': 'en'},
                ],
                'family': 'Family',
              },
          ],
          'total': total,
          'limit': limit,
          'offset': offset,
        }),
      ),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> pumpExplore(
    WidgetTester tester, {
    required http.Client client,
    ValueChanged<String>? selected,
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
        overrides: [httpClientProvider.overrideWithValue(client)],
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

  Finder listScrollable() => find
      .descendant(
        of: find.byType(CustomScrollView),
        matching: find.byType(Scrollable),
      )
      .first;

  Finder filterChip(String label) => find.widgetWithText(ChoiceChip, label);

  bool isSelected(WidgetTester tester, String label) =>
      tester.widget<ChoiceChip>(filterChip(label)).selected;

  /// The list builds rows lazily: scrolls until [target] exists, then shows it.
  Future<void> reveal(WidgetTester tester, Finder target) async {
    for (var i = 0; i < 80 && target.evaluate().isEmpty; i++) {
      await tester.drag(listScrollable(), const Offset(0, -150));
      await tester.pump();
    }
    expect(target, findsWidgets, reason: 'never built: $target');
    await tester.ensureVisible(target.first);
    await tester.pumpAndSettle();
  }

  /// Scrolls until the list footer is built and visible, then lets any page
  /// request it triggered run (without waiting for spinners to settle).
  Future<void> scrollToEnd(WidgetTester tester) async {
    final footer = find.byWidgetPredicate(
      (w) => w is Padding && '${w.key}'.contains('explore-footer'),
    );
    for (var i = 0; i < 80 && footer.evaluate().isEmpty; i++) {
      await tester.drag(listScrollable(), const Offset(0, -400));
      await tester.pump();
    }
    expect(footer, findsOneWidget);
    await tester.ensureVisible(footer);
    await tester.pump(const Duration(milliseconds: 50));
  }

  testWidgets('shows an explicit loading state until the first page resolves', (
    tester,
  ) async {
    final api = _PagedApi(total: 3)..gates[0] = Completer<void>();
    await pumpExplore(tester, client: api.client, settle: false);
    await tester.pump();
    expect(find.byKey(const ValueKey('catalog-loading')), findsOneWidget);
    expect(find.text('Cargando catálogo...'), findsOneWidget);
    expect(find.text('No se encontraron plantas'), findsNothing);
    expect(find.text('Reintentar'), findsNothing);
    api.gates[0]!.complete();
    await tester.pumpAndSettle();
    expect(find.text('Common 0'), findsOneWidget);
    expect(find.text('Cargando catálogo...'), findsNothing);
  });

  testWidgets('retry shows loading until the second request completes', (
    tester,
  ) async {
    final api = _PagedApi(total: 3)..failOffsets.add(0);
    await pumpExplore(tester, client: api.client);
    expect(find.textContaining('HTTP 500'), findsOneWidget);
    expect(find.byKey(const ValueKey('catalog-loading')), findsNothing);
    expect(find.text('No se encontraron plantas'), findsNothing);
    expect(api.requests, hasLength(1), reason: 'no automatic retry');

    api.failOffsets.clear();
    api.gates[0] = Completer<void>();
    await tester.tap(find.text('Reintentar'));
    await tester.pump();
    expect(find.text('Cargando catálogo...'), findsOneWidget);
    expect(find.textContaining('HTTP 500'), findsNothing);
    expect(find.text('No se encontraron plantas'), findsNothing);
    api.gates[0]!.complete();
    await tester.pumpAndSettle();
    expect(api.requests, hasLength(2));
    expect(find.text('Common 0'), findsOneWidget);
  });

  testWidgets('loads the first page in API order and dispatches the id', (
    tester,
  ) async {
    final api = FakeCatalogApi();
    String? selected;
    await pumpExplore(
      tester,
      client: api.client,
      selected: (id) => selected = id,
    );
    expect(api.requests, hasLength(1));
    final first = api.requests.single.url;
    expect(first.path, '/v1/plants');
    expect(first.queryParameters, {'limit': '50', 'offset': '0'});

    expect(find.text('English Lavender'), findsOneWidget);
    expect(find.text('Lavandula angustifolia'), findsOneWidget);
    expect(find.text('Aspic'), findsOneWidget);
    expect(find.text('Lavandula latifolia'), findsOneWidget);
    expect(find.byTooltip('Borrar búsqueda'), findsNothing);
    expect(isSelected(tester, 'Todas'), isTrue);
    expect(find.text('Cargando catálogo...'), findsNothing);

    final dy = [
      for (final name in ['English Lavender', 'Aspic', 'Lavender'])
        tester.getTopLeft(find.text(name).first).dy,
    ];
    expect(dy, orderedEquals([...dy]..sort()), reason: 'API order is kept');

    await reveal(tester, find.text('Lavender Rosemary'));
    await tester.tap(find.text('Lavender Rosemary'));
    expect(selected, 'rosmarinus-x-lavandulaceus');
    expect(tester.takeException(), isNull);
  });

  testWidgets('a plant without common names shows only its scientific name', (
    tester,
  ) async {
    final api = FakeCatalogApi();
    await pumpExplore(tester, client: api.client);
    // `Lavandula spica` has no common names in the fixture.
    final semantics = tester.ensureSemantics();
    await reveal(tester, find.text('Lavandula spica'));
    expect(find.bySemanticsLabel('Lavandula spica'), findsOneWidget);
    expect(find.text('Lavandula spica'), findsOneWidget);
    expect(find.bySemanticsLabel(RegExp('^Lavandula spica,')), findsNothing);
    semantics.dispose();
  });

  testWidgets(
    'searches remotely after the debounce, trimmed; clear keeps the filter',
    (tester) async {
      final api = FakeCatalogApi();
      await pumpExplore(tester, client: api.client);
      await tester.enterText(find.byType(TextField), '  LAVANDULA ');
      await tester.pump(_debounce - const Duration(milliseconds: 1));
      expect(api.requests, hasLength(1), reason: 'still inside the debounce');
      await tester.pump(const Duration(milliseconds: 1));
      await tester.pumpAndSettle();
      expect(api.requests, hasLength(2));
      expect(api.requests.last.url.queryParameters['q'], 'LAVANDULA');
      expect(find.text('English Lavender'), findsOneWidget);

      await tester.tap(filterChip('Plantas'));
      await tester.pump();
      await tester.tap(find.byTooltip('Borrar búsqueda'));
      await tester.pump(_debounce);
      await tester.pumpAndSettle();
      expect(isSelected(tester, 'Plantas'), isTrue);
      expect(api.requests, hasLength(3));
      expect(api.requests.last.url.queryParameters.containsKey('q'), isFalse);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        '',
      );

      await tester.enterText(find.byType(TextField), 'zzz');
      await tester.pump(_debounce);
      await tester.pumpAndSettle();
      expect(find.text('No se encontraron plantas'), findsOneWidget);
      expect(isSelected(tester, 'Plantas'), isTrue);
    },
  );

  testWidgets('several keystrokes with short pauses send a single request', (
    tester,
  ) async {
    final api = FakeCatalogApi();
    await pumpExplore(tester, client: api.client);
    for (final text in ['l', 'la', 'lav', 'lavan']) {
      await tester.enterText(find.byType(TextField), text);
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(api.requests, hasLength(1));
    await tester.pump(_debounce);
    await tester.pumpAndSettle();
    expect(api.requests, hasLength(2));
    expect(api.requests.last.url.queryParameters['q'], 'lavan');
  });

  testWidgets('a long query is cut to 200 characters', (tester) async {
    final api = FakeCatalogApi();
    await pumpExplore(tester, client: api.client);
    await tester.enterText(find.byType(TextField), 'x' * 250);
    await tester.pump(_debounce);
    await tester.pumpAndSettle();
    expect(api.requests.last.url.queryParameters['q'], 'x' * 200);
  });

  testWidgets('a late response of an older query is discarded', (tester) async {
    final late = Completer<http.Response>();
    const headers = {'content-type': 'application/json; charset=utf-8'};
    final client = MockClient((request) {
      if (request.url.queryParameters['q'] == 'lav') return late.future;
      return Future.value(
        http.Response(
          '{"items":[],"total":0,"limit":50,"offset":0}',
          200,
          headers: headers,
        ),
      );
    });
    await pumpExplore(tester, client: client);
    await tester.enterText(find.byType(TextField), 'lav');
    await tester.pump(_debounce);
    await tester.enterText(find.byType(TextField), 'zzz');
    await tester.pump(_debounce);
    await tester.pumpAndSettle();
    expect(find.text('No se encontraron plantas'), findsOneWidget);
    late.complete(
      http.Response.bytes(
        utf8.encode(apiFixture('list_lavandula.json')),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('No se encontraron plantas'), findsOneWidget);
    expect(find.text('English Lavender'), findsNothing);
  });

  testWidgets(
    'keeps the search field label and editing semantics after text changes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpExplore(tester, client: FakeCatalogApi().client);
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

      tester.semantics.setText(searchSemantics, 'lavandula');
      await tester.pump(_debounce);
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
      await tester.pump(_debounce);
      await tester.pumpAndSettle();
      expectSearchSemantics();
      semantics.dispose();
    },
  );

  testWidgets('oils empty is distinct from unmatched search and needs no '
      'request', (tester) async {
    final api = FakeCatalogApi();
    await pumpExplore(tester, client: api.client);
    expect(api.requests, hasLength(1));
    await tester.tap(filterChip('Aceites'));
    await tester.pump();
    expect(find.byKey(const ValueKey('empty-oils')), findsOneWidget);
    expect(
      find.text('No hay aceites disponibles en este catálogo'),
      findsOneWidget,
    );
    expect(find.text('English Lavender'), findsNothing);
    expect(api.requests, hasLength(1));

    await tester.tap(filterChip('Plantas'));
    await tester.pump();
    expect(find.text('English Lavender'), findsOneWidget);
    await tester.tap(filterChip('Todas'));
    await tester.pump();
    expect(find.text('English Lavender'), findsOneWidget);
    expect(api.requests, hasLength(1), reason: 'filters are local');

    await tester.enterText(find.byType(TextField), 'zzz');
    await tester.pump(_debounce);
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('empty-search')), findsOneWidget);
    expect(find.text('No se encontraron plantas'), findsOneWidget);
    expect(
      find.text('No hay aceites disponibles en este catálogo'),
      findsNothing,
    );
  });

  testWidgets('a query combined with Aceites is fetched only when leaving it', (
    tester,
  ) async {
    final api = FakeCatalogApi();
    await pumpExplore(tester, client: api.client);
    await tester.tap(filterChip('Aceites'));
    await tester.enterText(find.byType(TextField), 'lavandula');
    await tester.pump(_debounce);
    await tester.pumpAndSettle();
    expect(api.requests, hasLength(1));
    expect(find.byKey(const ValueKey('empty-oils')), findsOneWidget);
    await tester.tap(filterChip('Todas'));
    await tester.pumpAndSettle();
    expect(api.requests, hasLength(2));
    expect(api.requests.last.url.queryParameters['q'], 'lavandula');
    expect(find.text('English Lavender'), findsOneWidget);
  });

  testWidgets('exposes a readable error without raw details and retries', (
    tester,
  ) async {
    final api = FakeCatalogApi(failure: FakeApiFailure.connection);
    await pumpExplore(tester, client: api.client);
    expect(find.textContaining('No se pudo conectar'), findsOneWidget);
    expect(find.textContaining('Connection refused'), findsNothing);
    expect(find.textContaining('local'), findsNothing);
    api.failure = FakeApiFailure.none;
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(api.requests, hasLength(2));
    expect(find.text('English Lavender'), findsOneWidget);
    expect(find.textContaining('No se pudo conectar'), findsNothing);
  });

  testWidgets('keeps navigation callbacks and layout stable at 200% text', (
    tester,
  ) async {
    var backs = 0, homes = 0;
    await pumpExplore(
      tester,
      client: FakeCatalogApi().client,
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
        client: FakeCatalogApi().client,
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
      await tester.tap(filterChip('Aceites'));
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
      String? selected;
      await pumpExplore(
        tester,
        client: FakeCatalogApi().client,
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
      final lavenderRow = find.bySemanticsLabel(
        'English Lavender, Lavandula angustifolia',
      );
      expect(lavenderRow, findsOneWidget);
      expect(
        tester
            .getSemantics(lavenderRow)
            .getSemanticsData()
            .hasAction(SemanticsAction.tap),
        isTrue,
      );
      await tester.tap(find.text('English Lavender'));
      expect(selected, 'lavandula-angustifolia');
      semantics.dispose();
    },
  );

  group('infinite scroll', () {
    testWidgets('asks for the next page near the end and appends it', (
      tester,
    ) async {
      final api = _PagedApi(total: 120);
      await pumpExplore(tester, client: api.client);
      expect(api.offsets, [0]);
      expect(find.text('Common 0'), findsOneWidget);

      api.gates[50] = Completer<void>();
      await scrollToEnd(tester);
      expect(api.offsets, [0, 50]);
      expect(api.requests.last.queryParameters['limit'], '50');
      expect(
        find.byKey(const ValueKey('explore-footer-loading')),
        findsOneWidget,
      );
      final offsetBefore = tester
          .state<ScrollableState>(listScrollable())
          .position
          .pixels;
      expect(offsetBefore, greaterThan(0));

      api.gates[50]!.complete();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      expect(
        tester.state<ScrollableState>(listScrollable()).position.pixels,
        closeTo(offsetBefore, 5),
        reason: 'the position is kept when items are appended',
      );
      expect(api.offsets, [0, 50]);
      await tester.drag(listScrollable(), const Offset(0, -200));
      await tester.pump();
      expect(find.text('Common 51'), findsOneWidget);
    });

    testWidgets('marks the end of the list and stops requesting', (
      tester,
    ) async {
      final api = _PagedApi(total: 60);
      await pumpExplore(tester, client: api.client);
      await scrollToEnd(tester);
      await tester.pumpAndSettle();
      expect(api.offsets, [0, 50]);
      await scrollToEnd(tester);
      await tester.pumpAndSettle();
      expect(find.text('Common 59'), findsOneWidget);
      expect(find.text('No hay más resultados'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsNothing);
      await scrollToEnd(tester);
      expect(api.offsets, [0, 50], reason: 'no request after the end');
    });

    testWidgets('a single page that fits shows the end text at once', (
      tester,
    ) async {
      final api = FakeCatalogApi();
      await pumpExplore(tester, client: api.client);
      expect(find.text('No hay más resultados'), findsNothing);
      await scrollToEnd(tester);
      expect(find.text('No hay más resultados'), findsOneWidget);
      expect(api.requests, hasLength(1));
    });

    testWidgets('loads on its own when the first page does not fill the '
        'screen', (tester) async {
      final api = _PagedApi(total: 40, perPage: 3);
      await pumpExplore(tester, client: api.client);
      expect(api.requests.length, greaterThan(1));
      expect(find.text('Common 0'), findsOneWidget);
      expect(
        find.text('Common 3'),
        findsOneWidget,
        reason: 'the second page is already on screen',
      );
    });

    testWidgets('a failed page shows a retry in the footer and keeps the '
        'loaded items', (tester) async {
      final api = _PagedApi(total: 120)..failOffsets.add(50);
      await pumpExplore(tester, client: api.client);
      await scrollToEnd(tester);
      await tester.pumpAndSettle();
      expect(api.offsets, [0, 50]);
      expect(
        find.byKey(const ValueKey('explore-footer-error')),
        findsOneWidget,
      );
      expect(find.textContaining('HTTP 500'), findsOneWidget);
      expect(find.text('Reintentar'), findsOneWidget);
      expect(find.text('Common 49'), findsOneWidget);
      expect(find.byKey(const ValueKey('catalog-loading')), findsNothing);

      await tester.pump(const Duration(seconds: 1));
      expect(api.offsets, [0, 50], reason: 'no automatic retry');

      api.failOffsets.clear();
      await tester.ensureVisible(find.text('Reintentar'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(api.offsets, [0, 50, 50], reason: 'only that page is requested');
      expect(find.byKey(const ValueKey('explore-footer-error')), findsNothing);
      await tester.drag(listScrollable(), const Offset(0, -200));
      await tester.pump();
      expect(find.text('Common 51'), findsOneWidget);
    });
  });

  for (final scale in [1.0, 2.0]) {
    testWidgets('retry is accessible and readable at $scale text scale', (
      tester,
    ) async {
      final api = _PagedApi(total: 3)..failOffsets.add(0);
      await pumpExplore(
        tester,
        client: api.client,
        textScaler: TextScaler.linear(scale),
        padding: const EdgeInsets.fromLTRB(8, 24, 8, 20),
      );

      final message = find.textContaining('HTTP 500');
      final retry = find.widgetWithText(OutlinedButton, 'Reintentar');
      if (message.evaluate().isEmpty) {
        await tester.scrollUntilVisible(
          message,
          100,
          scrollable: listScrollable(),
        );
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
        await tester.scrollUntilVisible(
          retry,
          100,
          scrollable: listScrollable(),
        );
      }
      await tester.ensureVisible(retry);
      await tester.pumpAndSettle();
      expect(tester.getSize(retry).shortestSide, greaterThanOrEqualTo(48));
      expect(retry.hitTestable(), findsOneWidget);
      final retryData = tester.getSemantics(retry).getSemanticsData();
      expect(retryData.label, 'Reintentar');
      expect(retryData.hasAction(SemanticsAction.tap), isTrue);

      api.failOffsets.clear();
      api.gates[0] = Completer<void>();
      await tester.tap(retry);
      await tester.pump();
      expect(api.requests, hasLength(2));
      expect(find.text('Cargando catálogo...'), findsOneWidget);
      api.gates[0]!.complete();
      await tester.pumpAndSettle();
      expect(find.text('Common 0'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('footer states are accessible and readable at $scale', (
      tester,
    ) async {
      final semantics = tester.ensureSemantics();
      try {
        final api = _PagedApi(total: 60);
        await pumpExplore(
          tester,
          client: api.client,
          textScaler: TextScaler.linear(scale),
          padding: const EdgeInsets.fromLTRB(8, 24, 8, 20),
        );
        final viewport = tester.getRect(find.byType(CustomScrollView));

        // Loading footer.
        api.gates[50] = Completer<void>();
        await scrollToEnd(tester);
        final spinner = find.byKey(const ValueKey('explore-footer-loading'));
        expect(spinner, findsOneWidget);
        expect(tester.getSize(spinner).height, greaterThanOrEqualTo(48));
        expect(
          tester
              .getSemantics(find.bySemanticsLabel('Cargando más resultados'))
              .label,
          'Cargando más resultados',
        );

        // Error footer: the pending request now fails.
        api.failOffsets.add(50);
        api.gates[50]!.complete();
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));
        await scrollToEnd(tester);
        await tester.pumpAndSettle();
        final retry = find.widgetWithText(OutlinedButton, 'Reintentar');
        await tester.ensureVisible(retry);
        await tester.pumpAndSettle();
        final message = find.textContaining('HTTP 500');
        final paragraph = tester.renderObject<RenderParagraph>(message);
        expect(paragraph.didExceedMaxLines, isFalse);
        final rect = tester.getRect(message);
        expect(rect.left, greaterThanOrEqualTo(8));
        expect(rect.right, lessThanOrEqualTo(352));
        expect(tester.getSize(retry).shortestSide, greaterThanOrEqualTo(48));
        expect(retry.hitTestable(), findsOneWidget);
        final data = tester.getSemantics(retry).getSemanticsData();
        expect(data.label, 'Reintentar');
        expect(data.hasAction(SemanticsAction.tap), isTrue);
        expect(
          tester.getRect(retry).bottom,
          lessThanOrEqualTo(viewport.bottom + 0.01),
        );

        // End-of-list footer.
        api.failOffsets.clear();
        await tester.tap(retry);
        await tester.pumpAndSettle();
        await scrollToEnd(tester);
        await tester.pumpAndSettle();
        expect(api.offsets, [0, 50, 50]);
        final end = find.text('No hay más resultados');
        expect(end, findsOneWidget);
        await tester.ensureVisible(end);
        await tester.pumpAndSettle();
        final endParagraph = tester.renderObject<RenderParagraph>(end);
        expect(endParagraph.didExceedMaxLines, isFalse);
        final endRect = tester.getRect(end);
        expect(endRect.left, greaterThanOrEqualTo(8));
        expect(endRect.right, lessThanOrEqualTo(352));
        expect(endRect.bottom, lessThanOrEqualTo(viewport.bottom + 0.01));
        expect(tester.takeException(), isNull);
      } finally {
        semantics.dispose();
      }
    });

    testWidgets('keeps controls accessible and safe at $scale text scale', (
      tester,
    ) async {
      final semantics = tester.ensureSemantics();
      try {
        var homes = 0;
        await pumpExplore(
          tester,
          client: FakeCatalogApi().client,
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
            filterChip(label),
          for (final name in [
            'English Lavender',
            'Aspic',
            'Lavandula spica',
            'Hybrid Lavender',
            'Dutch Lavender',
            'Lavender Rosemary',
          ])
            find.bySemanticsLabel(RegExp('^$name')),
          for (final tab in ['Inicio', 'Favoritos', 'Historial', 'Perfil'])
            find.bySemanticsLabel(tab == 'Inicio' ? tab : '$tab no disponible'),
        ];
        for (final target in checks) {
          if (target != back) await reveal(tester, target);
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
        tester.state<ScrollableState>(listScrollable()).position.jumpTo(0);
        await tester.pumpAndSettle();
        await tester.enterText(find.byType(TextField), 'lavandula');
        await tester.pump(_debounce);
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
        client: FakeCatalogApi().client,
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
        'English Lavender',
        'Lavandula angustifolia',
        'Aspic',
        'Lavandula spica',
        'Rosmarinus x lavandulaceus',
        'No hay más resultados',
      ]) {
        final target = find.text(text);
        await reveal(tester, target);
        final paragraph = tester.renderObject<RenderParagraph>(target.first);
        final rect = tester.getRect(target.first);
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
