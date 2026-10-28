import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/catalog/data/plant_image_policy.dart';
import 'package:boticario_ai/features/goal_search/application/goal_results_controller.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_results_page.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_results_texts.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

/// A 1x1 transparent PNG: stands in for a downloaded photo.
final Uint8List _png = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
  '60e6kgAAAABJRU5ErkJggg==',
);

ImageProvider? _loads(String? url) => MemoryImage(_png);
ImageProvider? _never(String? url) => const _Never();

class _Never extends ImageProvider<_Never> {
  const _Never();

  @override
  Future<_Never> obtainKey(ImageConfiguration configuration) =>
      Future.value(this);

  @override
  ImageStreamCompleter loadImage(_Never key, ImageDecoderCallback decode) =>
      OneFrameImageStreamCompleter(Completer<ImageInfo>().future);
}

class _Failing extends ImageProvider<_Failing> {
  const _Failing();

  @override
  Future<_Failing> obtainKey(ImageConfiguration configuration) =>
      Future.value(this);

  @override
  ImageStreamCompleter loadImage(_Failing key, ImageDecoderCallback decode) =>
      OneFrameImageStreamCompleter(Future.error(Exception('sin conexión')));
}

ImageProvider? _fails(String? url) => const _Failing();

/// Lets the in-memory image decode (real async work) and shows its frame.
Future<void> _settleImage(WidgetTester tester) async {
  await tester.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 200)),
  );
  await tester.pump();
}

Map<String, Object?> _copy(Map<String, Object?> item) =>
    jsonDecode(jsonEncode(item)) as Map<String, Object?>;

/// A real item of [fixture] (by [id], or the first) with [changes] applied.
Map<String, Object?> _item(
  String fixture, {
  String? id,
  Map<String, Object?> changes = const {},
}) {
  final items = goalFixtureItems(fixture);
  final found = id == null
      ? items.first
      : items.firstWhere((i) => i['id'] == id);
  return {..._copy(found), ...changes};
}

Map<String, Object?> _image(Map<String, Object?> item) =>
    item['image']! as Map<String, Object?>;

Finder _card(String id) => find.byKey(ValueKey('plant-card-$id'));

Finder _merged(String id) =>
    find.descendant(of: _card(id), matching: find.byType(MergeSemantics));

Finder _in(String id, String text) =>
    find.descendant(of: _card(id), matching: find.text(text));

const _goalKey = 'relajacion-estres||0';

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

  /// Shows P07 for the plants in [items] (a goal page with `total` equal to
  /// their count) or, without [items], for what [api] serves.
  Future<FakeCatalogApi> show(
    WidgetTester tester, {
    List<Map<String, Object?>>? items,
    String goalId = 'relajacion-estres',
    String? subareaId,
    double scale = 1,
    FakeCatalogApi? api,
    ImageProvider? Function(String? url) imageProviderFor = _never,
    ValueChanged<String>? onPlant,
    VoidCallback? back,
    VoidCallback? home,
    String token = testApiToken,
    bool settle = true,
  }) async {
    final fake = api ?? FakeCatalogApi.real();
    if (items != null) fake.goalPageBodies[_goalKey] = goalPageJson(items);
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          httpClientProvider.overrideWithValue(fake.client),
          apiTokenProvider.overrideWithValue(token),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: TextScaler.linear(scale)),
            child: child!,
          ),
          home: GoalResultsPage(
            goalId: goalId,
            subareaId: subareaId,
            imageProviderFor: imageProviderFor,
            onBack: back ?? () {},
            onHome: home ?? () {},
            onPlantSelected: onPlant ?? (_) {},
          ),
        ),
      ),
    );
    if (settle) await tester.pumpAndSettle();
    return fake;
  }

  group('composition', () {
    testWidgets('title, subtitle from the response, cards, notice and bar', (
      tester,
    ) async {
      await show(tester);
      expect(find.text('Recomendaciones'), findsOneWidget);
      expect(find.text('Para: Relajación / Estrés'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('plant-card-crataegus-azarolus')),
        findsOneWidget,
      );
      await tester.scrollUntilVisible(
        find.text(GoalResultsTexts.notice),
        400,
        scrollable: find.byType(Scrollable).first,
      );
      expect(
        find.text(
          'Estas recomendaciones se basan en información especializada. '
          'Consulta detalles y precauciones.',
        ),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.info_outline), findsOneWidget);
      for (final tab in ['Inicio', 'Favoritos', 'Historial', 'Perfil']) {
        expect(find.text(tab), findsOneWidget);
      }
      // «Ver más detalles» belongs to task 5.4.
      expect(find.text('Ver más detalles'), findsNothing);
    });

    testWidgets('the subarea gives the subtitle and the request', (
      tester,
    ) async {
      final api = await show(
        tester,
        goalId: 'otros-objetivos',
        subareaId: 'digestion',
      );
      expect(find.text('Para: Digestión'), findsOneWidget);
      expect(find.text('Para: Otros objetivos'), findsNothing);
      final request = api.requests.last.url;
      expect(request.path, '/v1/goals/otros-objetivos/plants');
      expect(request.queryParameters, {
        'subarea': 'digestion',
        'limit': '20',
        'offset': '0',
      });
    });

    testWidgets('Atrás and Inicio call back; the other tabs do nothing', (
      tester,
    ) async {
      var backs = 0;
      var homes = 0;
      await show(tester, back: () => backs++, home: () => homes++);
      await tester.tap(find.byTooltip('Volver'));
      await tester.tap(find.text('Inicio'));
      await tester.tap(find.text('Favoritos'));
      await tester.tap(find.text('Historial'));
      await tester.tap(find.text('Perfil'));
      expect((backs, homes), (1, 1));
    });

    testWidgets('a card opens the passport of its plant', (tester) async {
      final opened = <String>[];
      await show(tester, onPlant: opened.add);
      await tester.tap(_card('leonurus-cardiaca'));
      expect(opened, ['leonurus-cardiaca']);
    });

    test('the default image provider is the 500 px thumbnail policy', () {
      final page = GoalResultsPage(
        goalId: 'x',
        onBack: () {},
        onHome: () {},
        onPlantSelected: (_) {},
      );
      expect(page.imageProviderFor, PlantImagePolicy.thumbnailProviderFor);
    });
  });

  group('card text', () {
    testWidgets('one area', (tester) async {
      final item = _item('goal_plants_relajacion-estres.json');
      await show(tester, items: [item]);
      expect(_in('crataegus-azarolus', 'Acerolo'), findsOneWidget);
      expect(_in('crataegus-azarolus', 'Crataegus azarolus'), findsOneWidget);
      expect(
        _in(
          'crataegus-azarolus',
          'La EMA la registra en: Estrés mental y trastornos del ánimo',
        ),
        findsOneWidget,
      );
    });

    testWidgets('two areas are listed, four show two and "y 2 más"', (
      tester,
    ) async {
      final two = _item(
        'goal_plants_relajacion-estres.json',
        changes: {
          'areas': ['A uno', 'A dos'],
        },
      );
      final four = _item(
        'goal_plants_relajacion-estres.json',
        id: 'leonurus-cardiaca',
        changes: {
          'areas': ['A uno', 'A dos', 'A tres', 'A cuatro'],
        },
      );
      await show(tester, items: [two, four]);
      expect(
        _in('crataegus-azarolus', 'La EMA la registra en: A uno, A dos'),
        findsOneWidget,
      );
      expect(
        _in('leonurus-cardiaca', 'La EMA la registra en: A uno, A dos y 2 más'),
        findsOneWidget,
      );
      expect(find.textContaining('A tres'), findsNothing);
    });

    testWidgets('three areas say "y 1 más"', (tester) async {
      final three = _item(
        'goal_plants_relajacion-estres.json',
        changes: {
          'areas': ['A', 'B', 'C'],
        },
      );
      await show(tester, items: [three]);
      expect(find.text('La EMA la registra en: A, B y 1 más'), findsOneWidget);
    });

    testWidgets(
      'a scientific display name shows once, even with English names',
      (tester) async {
        final item = _item(
          'goal_plants_relajacion-estres.json',
          id: 'crataegus-pentagyna',
        );
        expect(item['displayName'], item['scientificName']);
        expect(item['commonNames'], isNotEmpty);
        await show(tester, items: [item]);
        expect(
          _in('crataegus-pentagyna', 'Crataegus pentagyna'),
          findsOneWidget,
        );
        expect(find.textContaining('Hawthorn'), findsNothing);
      },
    );

    testWidgets('a scientific display name without common names', (
      tester,
    ) async {
      final item = _item(
        'goal_plants_relajacion-estres.json',
        id: 'tilia-x-europaea',
      );
      await show(tester, items: [item]);
      expect(_in('tilia-x-europaea', 'Tilia × europaea'), findsOneWidget);
    });

    testWidgets('an area joining two values with "; " is shown as it is', (
      tester,
    ) async {
      final item = _item(
        'goal_plants_otros-objetivos_page1.json',
        id: 'cichorium-intybus',
      );
      expect(item['areas'], [
        'Pérdida de apetito; Trastornos gastrointestinales',
      ]);
      await show(tester, items: [item]);
      expect(
        _in(
          'cichorium-intybus',
          'La EMA la registra en: '
              'Pérdida de apetito; Trastornos gastrointestinales',
        ),
        findsOneWidget,
      );
      expect(find.textContaining(' y 1 más'), findsNothing);
    });

    testWidgets('no efficacy language anywhere on screen', (tester) async {
      await show(tester, goalId: 'relajacion-estres');
      final texts = [
        for (final widget in tester.widgetList<Text>(find.byType(Text)))
          widget.data ?? '',
      ].join('\n').toLowerCase();
      for (final forbidden in [
        'efecto calmante',
        'ayuda a',
        'promueve',
        'calma',
        'dosis',
        'más recomendada',
      ]) {
        expect(texts, isNot(contains(forbidden)), reason: forbidden);
      }
      expect(find.textContaining(RegExp(r'\d+ ?%|puntos?\b')), findsNothing);
    });
  });

  group('photo', () {
    testWidgets('a loaded photo shows author and license', (tester) async {
      final item = _item('goal_plants_relajacion-estres.json');
      expect(_image(item)['author'], 'Cillas');
      await show(tester, items: [item], imageProviderFor: _loads);
      await _settleImage(tester);
      expect(
        _in('crataegus-azarolus', 'Foto: Cillas · CC BY-SA 4.0'),
        findsOneWidget,
      );
      expect(find.byType(Image), findsOneWidget);
    });

    testWidgets('credit is shown also without attributionRequired', (
      tester,
    ) async {
      final item = _item('goal_plants_relajacion-estres.json');
      _image(item)
        ..['attributionRequired'] = false
        ..['license'] = 'CC0 1.0'
        ..['author'] = 'J. Pérez';
      await show(tester, items: [item], imageProviderFor: _loads);
      await _settleImage(tester);
      expect(find.text('Foto: J. Pérez · CC0 1.0'), findsOneWidget);
    });

    testWidgets('a null author reads "autor no disponible"', (tester) async {
      final item = _item('goal_plants_no_author.json');
      await show(tester, items: [item], imageProviderFor: _loads);
      await _settleImage(tester);
      final license = _image(item)['license'];
      expect(find.text('Foto: autor no disponible · $license'), findsOneWidget);
    });

    testWidgets('asks for the 500 px thumbnail and never the original', (
      tester,
    ) async {
      final item = _item('goal_plants_relajacion-estres.json');
      final original = _image(item)['url']! as String;
      expect(original, endsWith('Crataegus_azarolus_HRM.jpg'));
      final urls = <String>[];
      await show(
        tester,
        items: [item],
        imageProviderFor: (url) {
          final provider = PlantImagePolicy.thumbnailProviderFor(url);
          urls.add((provider! as NetworkImage).url);
          return _never(url);
        },
      );
      expect(urls, [
        'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/'
            'Crataegus_azarolus_HRM.jpg/500px-Crataegus_azarolus_HRM.jpg',
      ]);
      expect(urls.single, isNot(original));
    });

    testWidgets('no image: local art, no credit, no provider asked', (
      tester,
    ) async {
      final item = _item('goal_plants_no_image.json');
      expect(item['image'], isNull);
      var asked = 0;
      await show(
        tester,
        items: [item],
        imageProviderFor: (url) {
          asked++;
          return _loads(url);
        },
      );
      await _settleImage(tester);
      expect(asked, 0);
      expect(find.byType(Image), findsNothing);
      expect(find.textContaining('Foto:'), findsNothing);
      expect(find.byIcon(Icons.local_florist), findsOneWidget);
    });

    for (final entry in {
      'host not allowed': 'https://evil.example.com/a/ab/X.jpg',
      'http': 'http://upload.wikimedia.org/wikipedia/commons/a/ab/X.jpg',
      'TIFF (no thumbnail)':
          'https://upload.wikimedia.org/wikipedia/commons/a/ab/X.tif',
    }.entries) {
      testWidgets('${entry.key}: local art, no credit, no original', (
        tester,
      ) async {
        final item = _item('goal_plants_relajacion-estres.json');
        _image(item)['url'] = entry.value;
        final asked = <ImageProvider?>[];
        await show(
          tester,
          items: [item],
          imageProviderFor: (url) {
            final provider = PlantImagePolicy.thumbnailProviderFor(url);
            asked.add(provider);
            return provider == null ? null : _never(url);
          },
        );
        expect(asked, [null]);
        expect(find.byType(Image), findsNothing);
        expect(find.textContaining('Foto:'), findsNothing);
        expect(find.byIcon(Icons.local_florist), findsOneWidget);
      });
    }

    testWidgets('while loading: local art and no credit', (tester) async {
      final item = _item('goal_plants_relajacion-estres.json');
      await show(tester, items: [item], imageProviderFor: _never);
      expect(find.byType(Image), findsOneWidget);
      expect(find.textContaining('Foto:'), findsNothing);
      expect(find.byIcon(Icons.local_florist), findsOneWidget);
    });

    testWidgets('failed: local art, no credit, list still usable', (
      tester,
    ) async {
      final item = _item('goal_plants_relajacion-estres.json');
      final opened = <String>[];
      await show(
        tester,
        items: [item],
        imageProviderFor: _fails,
        onPlant: opened.add,
      );
      await _settleImage(tester);
      expect(find.textContaining('Foto:'), findsNothing);
      expect(find.byIcon(Icons.local_florist), findsOneWidget);
      await tester.tap(_card('crataegus-azarolus'));
      expect(opened, ['crataegus-azarolus']);
    });

    testWidgets('the photo is not read twice: credit is part of the card', (
      tester,
    ) async {
      final item = _item('goal_plants_relajacion-estres.json');
      final handle = tester.ensureSemantics();
      await show(tester, items: [item], imageProviderFor: _loads);
      await _settleImage(tester);
      final label = tester
          .getSemantics(_merged('crataegus-azarolus'))
          .getSemanticsData()
          .label;
      expect(label, contains('Foto: Cillas · CC BY-SA 4.0'));
      expect(RegExp('Acerolo').allMatches(label), hasLength(1));
      handle.dispose();
    });
  });

  group('precaution mark', () {
    Future<void> showWith(WidgetTester tester, String? level, bool hasSafety) =>
        show(
          tester,
          items: [
            _item(
              'goal_plants_relajacion-estres.json',
              changes: {'safetyLevel': level, 'hasSafety': hasSafety},
            ),
          ],
        );

    for (final level in ['alto', 'medio']) {
      testWidgets('$level shows Precaución', (tester) async {
        await showWith(tester, level, true);
        expect(find.text('Precaución'), findsOneWidget);
        expect(find.textContaining('Sin datos'), findsNothing);
      });
    }

    testWidgets('bajo shows no mark', (tester) async {
      await showWith(tester, 'bajo', true);
      expect(find.text('Precaución'), findsNothing);
      expect(find.textContaining('Sin datos'), findsNothing);
    });

    testWidgets('no level with precautions (eucalyptus) shows no mark', (
      tester,
    ) async {
      final item = _item('goal_plants_safety_without_level.json');
      expect(item['safetyLevel'], isNull);
      expect(item['hasSafety'], isTrue);
      await show(tester, items: [item]);
      expect(find.text('Precaución'), findsNothing);
      expect(find.textContaining('Sin datos'), findsNothing);
    });

    testWidgets('without safety data it says so and not that it is safe', (
      tester,
    ) async {
      final item = _item('goal_plants_no_safety_synthetic.json');
      await show(tester, items: [item]);
      expect(
        find.text(
          'Sin datos de precauciones (esto no significa que sea segura)',
        ),
        findsOneWidget,
      );
      expect(find.text('Precaución'), findsNothing);
      expect(find.textContaining(RegExp('segura(?!\\))')), findsNothing);
    });

    testWidgets('the mark is part of the accessible name of the card', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await showWith(tester, 'alto', true);
      final node = tester
          .getSemantics(_merged('crataegus-azarolus'))
          .getSemanticsData();
      expect(node.label, contains('Acerolo'));
      expect(node.label, contains('La EMA la registra en: Estrés mental'));
      expect(node.label, contains('Precaución'));
      expect(node.flagsCollection.isButton, isTrue);
      handle.dispose();
    });

    testWidgets('a real high-level plant shows the mark', (tester) async {
      final item = _item('goal_plants_no_author.json');
      expect(item['safetyLevel'], 'alto');
      await show(tester, items: [item]);
      expect(find.text('Precaución'), findsOneWidget);
    });
  });

  group('states', () {
    testWidgets('loading: indicator with label and no cards', (tester) async {
      await show(tester, settle: false);
      expect(find.bySemanticsLabel('Cargando recomendaciones'), findsOneWidget);
      expect(find.byKey(const ValueKey('results-loading')), findsOneWidget);
      expect(find.byType(Card), findsNothing);
      expect(find.byKey(const ValueKey('results-notice')), findsOneWidget);
      expect(find.text('Inicio'), findsOneWidget);
      await tester.pumpAndSettle();
    });

    testWidgets('empty', (tester) async {
      final api = FakeCatalogApi.real();
      api.goalPageBodies[_goalKey] = goalPageJson(const [], total: 0);
      await show(tester, api: api);
      expect(
        find.text(
          'Aún no hay plantas con información registrada para este objetivo',
        ),
        findsOneWidget,
      );
      expect(find.text('Para: Relajación / Estrés'), findsOneWidget);
      expect(find.byKey(const ValueKey('results-notice')), findsOneWidget);
    });

    testWidgets('an unknown goal says "Objetivo no encontrado" without retry', (
      tester,
    ) async {
      await show(tester, goalId: 'no-existe');
      expect(find.text('Objetivo no encontrado'), findsOneWidget);
      expect(find.text('Reintentar'), findsNothing);
      expect(find.byKey(const ValueKey('results-notice')), findsOneWidget);
      expect(find.text('Inicio'), findsOneWidget);
    });

    testWidgets('error with Reintentar, then the cards appear', (tester) async {
      final api = FakeCatalogApi.real(failure: FakeApiFailure.serverError);
      await show(tester, api: api);
      expect(find.byKey(const ValueKey('results-error')), findsOneWidget);
      expect(find.byType(OutlinedButton), findsOneWidget);
      expect(find.byKey(const ValueKey('results-notice')), findsOneWidget);
      api.failure = FakeApiFailure.none;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('results-error')), findsNothing);
      expect(_card('crataegus-azarolus'), findsOneWidget);
    });

    testWidgets('401 shows the unauthorized error, without the token', (
      tester,
    ) async {
      const wrong = 'wrong-token-wrong-token-wrong-token-1';
      await show(tester, token: wrong);
      expect(find.byKey(const ValueKey('results-error')), findsOneWidget);
      expect(find.textContaining('no está autorizada'), findsOneWidget);
      expect(find.textContaining(wrong), findsNothing);
      expect(find.textContaining(testApiToken), findsNothing);
      expect(find.text('Reintentar'), findsOneWidget);
    });
  });

  group('pagination', () {
    Future<void> scrollToEnd(WidgetTester tester, {int times = 40}) async {
      for (var i = 0; i < times; i++) {
        await tester.drag(find.byType(CustomScrollView), const Offset(0, -600));
        await tester.pump(const Duration(milliseconds: 50));
      }
    }

    bool asked(FakeCatalogApi api, int offset) =>
        api.requests.any((r) => r.url.queryParameters['offset'] == '$offset');

    testWidgets('loads 20, then the next 20 near the end of the scroll', (
      tester,
    ) async {
      final api = await show(tester, goalId: 'otros-objetivos');
      expect(asked(api, 0), isTrue);
      expect(asked(api, 20), isFalse);
      expect(api.requests.first.url.queryParameters['limit'], '20');

      await scrollToEnd(tester, times: 12);
      await tester.pumpAndSettle();
      expect(asked(api, 20), isTrue);
      final container = ProviderScope.containerOf(
        tester.element(find.byType(GoalResultsPage)),
      );
      final state = container.read(
        goalResultsControllerProvider((
          goalId: 'otros-objetivos',
          subareaId: null,
        )),
      );
      expect(state.items, hasLength(40));
      expect(state.items.toSet(), hasLength(40));
      expect(state.total, 135);
      // Real API order, no ranking.
      final page1 = goalFixtureItems('goal_plants_otros-objetivos_page1.json');
      final page2 = goalFixtureItems('goal_plants_otros-objetivos_page2.json');
      expect(
        [for (final plant in state.items) plant.id],
        [
          for (final item in [...page1, ...page2]) item['id'],
        ],
      );
    });

    testWidgets('the end of the list shows the end marker, no more requests', (
      tester,
    ) async {
      final api = await show(tester);
      await scrollToEnd(tester, times: 12);
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('results-footer-end')), findsOneWidget);
      expect(find.text('No hay más resultados'), findsOneWidget);
      expect(
        api.requests.where((r) => r.url.path.endsWith('/plants')).length,
        1,
      );
    });

    testWidgets('while the next page loads the footer shows an indicator', (
      tester,
    ) async {
      final api = await show(tester, goalId: 'otros-objetivos');
      api.failure = FakeApiFailure.timeout;
      await scrollToEnd(tester, times: 12);
      expect(
        find.byKey(const ValueKey('results-footer-loading')),
        findsOneWidget,
      );
      expect(find.bySemanticsLabel('Cargando más resultados'), findsOneWidget);
      // Let the repository timeout end the pending request.
      await tester.pump(const Duration(seconds: 11));
      await tester.pumpAndSettle();
    });

    testWidgets('a failed next page keeps the cards and offers Reintentar', (
      tester,
    ) async {
      final api = await show(tester, goalId: 'otros-objetivos');
      api.failure = FakeApiFailure.serverError;
      await scrollToEnd(tester, times: 12);
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('results-footer-error')),
        findsOneWidget,
      );
      expect(find.text('Reintentar'), findsOneWidget);
      final container = ProviderScope.containerOf(
        tester.element(find.byType(GoalResultsPage)),
      );
      const query = (goalId: 'otros-objetivos', subareaId: null);
      expect(
        container.read(goalResultsControllerProvider(query)).items,
        hasLength(20),
      );
      expect(find.byKey(const ValueKey('results-error')), findsNothing);

      api.failure = FakeApiFailure.none;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(
        container.read(goalResultsControllerProvider(query)).items,
        hasLength(40),
      );
    });
  });

  group('accessibility', () {
    for (final scale in [1.0, 2.0]) {
      testWidgets('cards, marks and notice at 360x640 and ${scale * 100} %', (
        tester,
      ) async {
        final items = [
          _item(
            'goal_plants_relajacion-estres.json',
            changes: {
              'safetyLevel': 'alto',
              'areas': ['A uno largo', 'A dos largo', 'A tres', 'A cuatro'],
            },
          ),
          _item('goal_plants_no_safety_synthetic.json'),
        ];
        await show(
          tester,
          items: items,
          scale: scale,
          imageProviderFor: _loads,
        );
        await _settleImage(tester);
        expect(tester.takeException(), isNull);
        final cardHeight = tester.getSize(_card('crataegus-azarolus')).height;
        expect(cardHeight, greaterThanOrEqualTo(48));
        await tester.scrollUntilVisible(
          find.text(GoalResultsTexts.notice),
          300,
          scrollable: find.byType(Scrollable).first,
        );
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('Atrás, cards and Reintentar are at least 48 dp', (
      tester,
    ) async {
      final api = FakeCatalogApi.real(failure: FakeApiFailure.serverError);
      await show(tester, api: api);
      expect(
        tester.getSize(find.byType(OutlinedButton)).height,
        greaterThanOrEqualTo(48),
      );
      expect(
        tester.getSize(find.byTooltip('Volver')).shortestSide,
        greaterThanOrEqualTo(48),
      );
    });
  });
}
