import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import '../../support/fake_catalog_api.dart';
import 'passport_test_support.dart' show consolidatedPlant, plainText;

const _tabNames = ['General', 'Propiedades', 'Usos', 'Fuentes'];
const _lavender = 'lavandula-angustifolia';
const _rosemary = 'rosmarinus-officinalis';
const _noCommonNames = 'abies-spectabilis';
const _noFamily = 'chondrus-crispus';
const _noUses = 'abies-sachalinensis';

/// Visible names (primary, secondary) of each fixture plant.
const _names = <String, (String, String?)>{
  _lavender: ('English Lavender', 'Lavandula angustifolia'),
  _rosemary: ('Rosemary', 'Rosmarinus officinalis'),
  _noCommonNames: ('Abies spectabilis', null),
  _noFamily: ('Irish Moss', 'Chondrus crispus'),
  _noUses: ('Japanese Fir', 'Abies sachalinensis'),
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Map<String, Plant> plants;
  const insets = EdgeInsets.fromLTRB(8, 24, 8, 20);

  setUpAll(() async {
    plants = {
      for (final id in FakeCatalogApi.plantIds)
        id: parsePlant(apiFixture('plant_$id.json')),
    };
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

  Widget pageFor(
    Object plantOrId, {
    VoidCallback? onBack,
    VoidCallback? onHome,
  }) => PlantPassportPage(
    plant: plantOrId is Plant ? plantOrId : plants[plantOrId]!,
    onBack: onBack ?? () {},
    onHome: onHome ?? () {},
  );

  Future<void> show(
    WidgetTester tester,
    Object plantOrId, {
    VoidCallback? onBack,
    VoidCallback? onHome,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBoticarioTheme(),
        home: pageFor(plantOrId, onBack: onBack, onHome: onHome),
      ),
    );
  }

  /// Route entry backed by a fake API (or any client).
  Widget route(
    String id, {
    required http.Client client,
    Key? key,
    VoidCallback? onBack,
    VoidCallback? onHome,
  }) => ProviderScope(
    overrides: [
      httpClientProvider.overrideWithValue(client),
      apiTokenProvider.overrideWithValue(testApiToken),
    ],
    child: MaterialApp(
      theme: buildBoticarioTheme(),
      home: PlantPassportRoutePage(
        key: key,
        plantId: id,
        onBack: onBack ?? () {},
        onHome: onHome ?? () {},
      ),
    ),
  );

  Future<void> setCompactViewport(
    WidgetTester tester, {
    double scale = 1,
  }) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBoticarioTheme(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.linear(scale),
            viewPadding: insets,
            padding: insets,
          ),
          child: child!,
        ),
        home: pageFor(_lavender),
      ),
    );
  }

  Finder passportScroll() => find.descendant(
    of: find.byType(CustomScrollView),
    matching: find.byType(Scrollable),
  );

  Future<void> scrollTop(WidgetTester tester) async {
    tester.state<ScrollableState>(passportScroll()).position.jumpTo(0);
    await tester.pumpAndSettle();
  }

  Future<void> reach(WidgetTester tester, Finder target) async {
    if (target.evaluate().isEmpty) await scrollTop(tester);
    if (target.evaluate().isEmpty) {
      await tester.scrollUntilVisible(
        target,
        100,
        scrollable: passportScroll(),
      );
    }
    await tester.ensureVisible(target);
    await tester.pumpAndSettle();
  }

  /// Opens the citations of the `Usos` group titled [activity].
  Future<void> openCitations(WidgetTester tester, String activity) async {
    await reach(tester, find.text(activity).first);
    final control = find.descendant(
      of: find
          .ancestor(
            of: find.text(activity).first,
            matching: find.byType(Column),
          )
          .first,
      matching: find.byType(TextButton),
    );
    await reach(tester, control);
    await tester.tap(control);
    await tester.pumpAndSettle();
  }

  Future<void> selectTab(WidgetTester tester, String name) async {
    await scrollTop(tester);
    final target = find.widgetWithText(ChoiceChip, name);
    await reach(tester, target);
    expect(target.hitTestable(), findsOneWidget, reason: name);
    await tester.tap(target);
    await tester.pumpAndSettle();
    expect(tester.widget<ChoiceChip>(target).selected, isTrue);
  }

  Future<void> assertParagraphReadable(
    WidgetTester tester,
    Finder target,
  ) async {
    await reach(tester, target);
    final paragraph = tester.renderObject<RenderParagraph>(target);
    final text = paragraph.text.toPlainText();
    expect(paragraph.didExceedMaxLines, isFalse, reason: text);
    expect(paragraph.overflow, isNot(TextOverflow.ellipsis), reason: text);
    final boxes = [
      for (final word in RegExp(r'\S+').allMatches(text))
        ...paragraph.getBoxesForSelection(
          TextSelection(baseOffset: word.start, extentOffset: word.end),
        ),
    ];
    expect(boxes, isNotEmpty, reason: text);
    final spacing = (paragraph.text.style?.letterSpacing ?? 0).abs() / 2;
    for (final box in boxes) {
      expect(box.left, greaterThanOrEqualTo(-0.1), reason: text);
      expect(
        box.right,
        lessThanOrEqualTo(paragraph.size.width + spacing + 0.1),
        reason: text,
      );
      expect(box.bottom, lessThanOrEqualTo(paragraph.size.height + 0.1));
    }

    final viewport = tester.getRect(find.byType(CustomScrollView));
    expect(viewport.top, greaterThanOrEqualTo(insets.top));
    expect(viewport.bottom, lessThanOrEqualTo(640 - insets.bottom));
    final paragraphRect = tester.getRect(target);
    expect(
      paragraphRect.left,
      greaterThanOrEqualTo(insets.left - 0.1),
      reason: text,
    );
    expect(
      paragraphRect.right,
      lessThanOrEqualTo(360 - insets.right + 0.1),
      reason: text,
    );
    final seen = <int>{};
    final limit = (paragraph.size.height / (viewport.height * 0.5)).ceil() + 12;
    for (var step = 0; step < limit && seen.length < boxes.length; step++) {
      final origin = paragraph.localToGlobal(Offset.zero);
      for (var i = 0; i < boxes.length; i++) {
        final box = boxes[i].toRect().shift(origin);
        expect(box.left, greaterThanOrEqualTo(insets.left - 0.1), reason: text);
        expect(
          box.right,
          lessThanOrEqualTo(360 - insets.right + 0.1),
          reason: text,
        );
        if (box.top >= viewport.top - 0.1 &&
            box.bottom <= viewport.bottom + 0.1) {
          seen.add(i);
        }
      }
      if (seen.length == boxes.length) break;
      final position = tester.state<ScrollableState>(passportScroll()).position;
      final previous = position.pixels;
      await tester.dragFrom(
        viewport.center,
        Offset(0, -viewport.height * 0.65),
      );
      await tester.pumpAndSettle();
      if ((position.pixels - previous).abs() < 0.1) break;
    }
    expect(
      seen.length,
      boxes.length,
      reason: 'Texto completo alcanzable: $text',
    );
  }

  void assertLabelFitsWithin(
    WidgetTester tester,
    Finder target,
    Rect ownerRect,
  ) {
    final paragraph = tester.renderObject<RenderParagraph>(target);
    final text = paragraph.text.toPlainText();
    expect(paragraph.didExceedMaxLines, isFalse, reason: text);
    expect(paragraph.overflow, isNot(TextOverflow.ellipsis), reason: text);
    final targetRect = tester.getRect(target);
    expect(targetRect.left, greaterThanOrEqualTo(ownerRect.left), reason: text);
    expect(targetRect.top, greaterThanOrEqualTo(ownerRect.top), reason: text);
    expect(targetRect.right, lessThanOrEqualTo(ownerRect.right), reason: text);
    expect(
      targetRect.bottom,
      lessThanOrEqualTo(ownerRect.bottom),
      reason: text,
    );
    final spacing = (paragraph.text.style?.letterSpacing ?? 0).abs() / 2;
    final boxes = [
      for (final word in RegExp(r'\S+').allMatches(text))
        ...paragraph.getBoxesForSelection(
          TextSelection(baseOffset: word.start, extentOffset: word.end),
        ),
    ];
    expect(boxes, isNotEmpty, reason: text);
    final origin = paragraph.localToGlobal(Offset.zero);
    for (final box in boxes) {
      expect(box.left, greaterThanOrEqualTo(-0.1), reason: text);
      expect(
        box.right,
        lessThanOrEqualTo(paragraph.size.width + spacing + 0.1),
        reason: text,
      );
      expect(box.bottom, lessThanOrEqualTo(paragraph.size.height + 0.1));
      final glyph = box.toRect().shift(origin);
      expect(glyph.left, greaterThanOrEqualTo(ownerRect.left), reason: text);
      expect(glyph.top, greaterThanOrEqualTo(ownerRect.top), reason: text);
      expect(glyph.right, lessThanOrEqualTo(ownerRect.right), reason: text);
      expect(glyph.bottom, lessThanOrEqualTo(ownerRect.bottom), reason: text);
    }
  }

  const emptyUses =
      'No hay usos tradicionales con referencia verificable disponibles';

  testWidgets('General muestra identidad, familia, nombres, partes y sin '
      'procedencia', (tester) async {
    await setCompactViewport(tester);
    expect(find.text('English Lavender'), findsNWidgets(2));
    expect(find.text('Lavandula angustifolia'), findsOneWidget);
    expect(find.text('Familia'), findsOneWidget);
    expect(find.text('Lamiaceae'), findsOneWidget);
    expect(find.text('Otros nombres comunes'), findsOneWidget);
    // The older backend has no display name: the first common name is the
    // `Nombre común` and is not repeated among the others.
    expect(find.text('English Lavender (en)'), findsNothing);
    expect(find.text('Flower, Leaf, Plant, Seed'), findsOneWidget);
    expect(find.text('Tipo de aceite'), findsOneWidget);
    for (final removed in [
      'No aplicable: ficha de planta',
      'Procedencia',
      'Licencia',
      'Versión',
      'Dataset',
      'Archivo',
      'URL de fuente',
      'Nombre común editorial',
      'Nombre científico de fuente',
      'Fecha de inspección (no cobertura temporal)',
      'Cita recomendada de la fuente',
    ]) {
      expect(find.text(removed), findsNothing, reason: removed);
    }
    expect(find.textContaining('CC0'), findsNothing);
    expect(find.textContaining('MD5'), findsNothing);
    // `General` has no reference list: citations live in `Usos`.
    expect(find.text('Referencias bibliográficas'), findsNothing);
    expect(find.text('Steinmetz'), findsNothing);
    expect(find.textContaining('codex Vegetabilis'), findsNothing);
  });

  testWidgets('a null family is stated as not available in the source', (
    tester,
  ) async {
    await show(tester, _noFamily);
    expect(find.text('Familia'), findsOneWidget);
    // Familia, origen, tipo de aceite and descripción.
    expect(find.text('No disponible en fuente'), findsNWidgets(4));
    expect(find.text('Referencias bibliográficas'), findsNothing);
  });

  testWidgets('a plant without common names has the scientific name as the '
      'only name', (tester) async {
    await show(tester, _noCommonNames);
    expect(find.text('Abies spectabilis'), findsOneWidget);
    expect(find.text('Otros nombres comunes'), findsOneWidget);
    expect(find.text('No hay nombres comunes registrados'), findsOneWidget);
    expect(find.text('Leaf, Plant, Wood'), findsOneWidget);
  });

  testWidgets('common names keep their text and language code', (tester) async {
    await show(tester, _noUses);
    expect(find.text('Shin-Yo-Yu (en)'), findsOneWidget);
    // Header and `Nombre común`: the primary name is not repeated in the list.
    expect(find.text('Japanese Fir'), findsNWidgets(2));
    expect(find.text('Japanese Fir (en)'), findsNothing);
    expect(find.text('Abies sachalinensis'), findsOneWidget);
  });

  testWidgets('Propiedades no afirma eficacia medicinal', (tester) async {
    await show(tester, _lavender);
    await tester.tap(find.text('Propiedades'));
    await tester.pumpAndSettle();
    expect(
      find.bySemanticsLabel('Ver formulaciones relacionadas no disponible'),
      findsOneWidget,
    );
    expect(
      find.text('No hay objetivos registrados por la EMA para esta planta'),
      findsOneWidget,
    );
    expect(find.textContaining('eficaz'), findsNothing);
  });

  testWidgets('empty parts and common names are stated explicitly', (
    tester,
  ) async {
    final bare = Plant(
      id: 'bare-plant',
      scientificName: 'Bare plant',
      family: 'Familia X',
      names: const [],
      parts: const [],
      uses: const [],
    );
    await show(tester, bare);
    expect(find.text('No hay partes registradas en fuente'), findsOneWidget);
    expect(find.text('No hay nombres comunes registrados'), findsOneWidget);
    expect(find.text('Familia X'), findsOneWidget);
    expect(find.text('Bare plant'), findsOneWidget);
  });

  /// Opens every `Ver N citas` control, tapping the first one still closed.
  Future<void> expandAllCitations(WidgetTester tester) async {
    final closed = find.byWidgetPredicate(
      (w) => w is Text && RegExp(r'^Ver \d+ citas?$').hasMatch(w.data ?? ''),
    );
    while (closed.evaluate().isNotEmpty) {
      await tester.tap(closed.first);
      await tester.pumpAndSettle();
    }
  }

  void useTallViewport(WidgetTester tester, double height) {
    tester.view.physicalSize = Size(360, height);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets('Usos conserva actividad y cita de cada registro al desplegar', (
    tester,
  ) async {
    useTallViewport(tester, 4000);
    await show(tester, _lavender);
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text(PassportTexts.usesNoticeLabel), findsOneWidget);
    expect(find.text('Carminative'), findsOneWidget);
    final lavender = plants[_lavender]!;
    expect(lavender.uses, hasLength(10));
    expect(find.text('Registro tradicional'), findsNothing);
    final controls = find.byWidgetPredicate(
      (w) => w is Text && RegExp(r'^Ver \d+ citas?$').hasMatch(w.data ?? ''),
    );
    expect(controls, findsNWidgets(lavender.useGroups.length));
    // Closed by default: no citation is in the tree.
    for (final use in lavender.uses) {
      expect(find.text(use.reference.citation), findsNothing);
    }
    await expandAllCitations(tester);
    for (final use in lavender.uses) {
      expect(find.text(use.activity), findsWidgets);
      expect(find.text(use.reference.citation), findsWidgets);
    }
    expect(find.text(emptyUses), findsNothing);
  });

  testWidgets('Romero presenta todos sus usos sin truncar y sin usos queda '
      'vacío explícito', (tester) async {
    await show(tester, _rosemary);
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    final rosemary = plants[_rosemary]!;
    expect(rosemary.uses, hasLength(59));
    // The older backend sends `uses` only: one derived group per activity.
    expect(rosemary.useGroups, hasLength(46));
    expect(find.text('Registro tradicional'), findsNothing);
    expect(
      find.bySemanticsLabel('Ver formulaciones relacionadas no disponible'),
      findsOneWidget,
    );
    // The last group is reachable by scrolling and opens its citations.
    final last = rosemary.useGroups.last;
    await tester.scrollUntilVisible(find.text(last.activity), 200);
    final control = find.descendant(
      of: find
          .ancestor(of: find.text(last.activity), matching: find.byType(Column))
          .first,
      matching: find.byType(TextButton),
    );
    await tester.ensureVisible(control);
    await tester.pump();
    await tester.tap(control);
    await tester.pumpAndSettle();
    for (final reference in last.references) {
      await tester.ensureVisible(find.text(reference.citation).last);
      expect(find.text(reference.citation), findsWidgets);
    }

    for (final id in [_noUses, _noFamily]) {
      await show(tester, id);
      await tester.tap(find.text('Usos'));
      await tester.pumpAndSettle();
      expect(find.text(emptyUses), findsOneWidget, reason: id);
      expect(find.byType(TextButton), findsNothing);
      expect(
        find.bySemanticsLabel('Ver formulaciones relacionadas no disponible'),
        findsOneWidget,
      );
    }
  });

  testWidgets('el plegado de Usos sobrevive al cambio de pestaña y se '
      'reinicia con otra planta o al reabrir', (tester) async {
    useTallViewport(tester, 4000);
    final lavender = plants[_lavender]!;
    final groups = lavender.useGroups;
    expect(groups.length, greaterThan(2));
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(_lavender)),
    );
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    await tester.tap(
      find.text('Ocultar citas').evaluate().isEmpty
          ? find.byType(TextButton).at(1)
          : find.text('Ocultar citas'),
    );
    await tester.pumpAndSettle();
    expect(find.text('Ocultar citas'), findsOneWidget);
    await tester.tap(find.text('General'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text('Ocultar citas'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (w) => w is Text && RegExp(r'^Ver \d+ citas?$').hasMatch(w.data ?? ''),
      ),
      findsNWidgets(groups.length - 1),
    );
    // Another plant: everything closed.
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(_rosemary)),
    );
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text('Ocultar citas'), findsNothing);
    // Back to the first one with a new page: still closed.
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(_lavender)),
    );
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text('Ocultar citas'), findsNothing);
  });

  testWidgets('Back/Home callbacks and unavailable actions are inert', (
    tester,
  ) async {
    var backs = 0;
    var homes = 0;
    await show(tester, _lavender, onBack: () => backs++, onHome: () => homes++);
    await tester.tap(find.byTooltip('Volver a Explorar'));
    expect(
      tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
      isNull,
    );
    await tester.tap(find.text('Inicio'));
    await tester.pumpAndSettle();
    expect(backs, 1);
    expect(homes, 1);
  });

  testWidgets('cuatro pestañas con General inicial y Fuentes como cuarta', (
    tester,
  ) async {
    await show(tester, _lavender);
    final chips = tester.widgetList<ChoiceChip>(find.byType(ChoiceChip));
    expect([for (final chip in chips) (chip.label as Text).data], _tabNames);
    expect(
      [for (final chip in chips) chip.selected],
      [true, false, false, false],
    );
  });

  testWidgets('las pestañas no se mueven ni cambian de tamaño al elegir una', (
    tester,
  ) async {
    for (final scale in [1.0, 2.0]) {
      await setCompactViewport(tester, scale: scale);
      await scrollTop(tester);
      Map<String, Rect> rects() => {
        for (final tab in _tabNames)
          tab: tester.getRect(find.widgetWithText(ChoiceChip, tab)),
      };
      final before = rects();
      for (final tab in [..._tabNames, ..._tabNames.reversed]) {
        await selectTab(tester, tab);
        await scrollTop(tester);
        expect(rects(), before, reason: 'tras elegir $tab al $scale');
        final chip = tester.widget<ChoiceChip>(
          find.widgetWithText(ChoiceChip, tab),
        );
        expect(chip.selected, isTrue);
        expect(chip.showCheckmark, isFalse);
        // The selection is not only a fill: the border turns green.
        expect((chip.side as BorderSide).color, const Color(0xFF236335));
        expect(
          tester
              .getSemantics(find.widgetWithText(ChoiceChip, tab))
              .flagsCollection
              .isSelected,
          ui.Tristate.isTrue,
        );
      }
      // Selected and not selected chips are told apart by border and fill.
      final others = tester.widgetList<ChoiceChip>(find.byType(ChoiceChip));
      expect(others.where((c) => c.selected), hasLength(1));
      expect(
        others
            .where((c) => !c.selected)
            .every((c) => c.side!.color != const Color(0xFF236335)),
        isTrue,
      );
    }
  });

  testWidgets('Fuentes solo aparece con su pestaña y no bajo las otras tres', (
    tester,
  ) async {
    // The `plant_*` fixtures predate credits: use a consolidated plant.
    final plant = consolidatedPlant(_lavender);
    final credit = plant.credits.first;
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(plant)),
    );
    Future<void> expectSourcesAbsent(String tab) async {
      // Scroll the whole tab so lazily built rows cannot hide a section.
      final scroll = passportScroll();
      final position = tester.state<ScrollableState>(scroll).position;
      for (var i = 0; i < 60; i++) {
        expect(
          find.text(PassportTexts.sourcesIntro),
          findsNothing,
          reason: tab,
        );
        expect(plainText(credit.name), findsNothing, reason: tab);
        expect(find.text('Licencia: ${credit.license}'), findsNothing);
        expect(find.text(PassportTexts.imageSourceTitle), findsNothing);
        if (position.pixels >= position.maxScrollExtent) break;
        await tester.drag(scroll, const Offset(0, -300));
        await tester.pump();
      }
    }

    await expectSourcesAbsent('General');
    for (final tab in ['Propiedades', 'Usos']) {
      await selectTab(tester, tab);
      await expectSourcesAbsent(tab);
    }
    await selectTab(tester, 'Fuentes');
    expect(find.text(PassportTexts.sourcesIntro), findsOneWidget);
    expect(plainText(credit.name), findsOneWidget);
  });

  testWidgets('identity change resets selected tab to General', (tester) async {
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(_lavender)),
    );
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text(PassportTexts.usesNoticeLabel), findsOneWidget);
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(_noFamily)),
    );
    await tester.pumpAndSettle();
    expect(find.text('Familia'), findsOneWidget);
    expect(find.text(emptyUses), findsNothing);
  });

  testWidgets('route entry resolves a known catalog identity by slug', (
    tester,
  ) async {
    final api = FakeCatalogApi();
    await tester.pumpWidget(route(_lavender, client: api.client));
    expect(find.text('Cargando planta...'), findsOneWidget);
    await tester.pumpAndSettle();
    expect(find.text('English Lavender'), findsWidgets);
    expect(find.text('Lavandula angustifolia'), findsWidgets);
    expect(api.requests.single.url.path, '/v1/plants/$_lavender');
    expect(find.text('Cargando planta...'), findsNothing);
  });

  testWidgets('route entry resolves every fixture id and handles unknown ids '
      'safely', (tester) async {
    var backs = 0;
    var homes = 0;
    final api = FakeCatalogApi();
    Widget entry(String id) => route(
      id,
      client: api.client,
      onBack: () => backs++,
      onHome: () => homes++,
    );

    for (final item in _names.entries) {
      await tester.pumpWidget(entry(item.key));
      await tester.pumpAndSettle();
      expect(find.text(item.value.$1), findsWidgets, reason: 'ID ${item.key}');
      if (item.value.$2 != null) {
        expect(find.text(item.value.$2!), findsWidgets);
      }
      expect(tester.takeException(), isNull);
    }

    for (final id in [
      '999999',
      'not-an-id',
      '-544',
      'a' * 300,
      'lavandula-angustifolia-x',
    ]) {
      await tester.pumpWidget(entry(id));
      await tester.pumpAndSettle();
      expect(find.text('Planta no encontrada'), findsOneWidget, reason: id);
      expect(find.text('No se pudo cargar la planta'), findsNothing);
      for (final names in _names.values) {
        expect(find.text(names.$1), findsNothing, reason: 'unexpected for $id');
      }
      await tester.tap(find.byTooltip('Volver a Explorar'));
      await tester.tap(find.bySemanticsLabel('Inicio'));
      expect(tester.takeException(), isNull);
    }
    expect(backs, 5);
    expect(homes, 5);
  });

  testWidgets('route ID changes known → unknown → known and resets General', (
    tester,
  ) async {
    const key = ValueKey('route-entry');
    final api = FakeCatalogApi();
    Widget entry(String id) => route(id, client: api.client, key: key);

    await tester.pumpWidget(entry(_lavender));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text(PassportTexts.usesNoticeLabel), findsOneWidget);

    await tester.pumpWidget(entry('999999'));
    await tester.pumpAndSettle();
    expect(find.text('Planta no encontrada'), findsOneWidget);
    await tester.pumpWidget(entry(_noUses));
    await tester.pumpAndSettle();
    expect(find.text('Japanese Fir'), findsWidgets);
    expect(find.text('Familia'), findsOneWidget);
    expect(find.text(PassportTexts.usesNoticeLabel), findsNothing);
  });

  testWidgets('a 401 shows unauthorized, not "not found", with retry', (
    tester,
  ) async {
    final api = FakeCatalogApi(failure: FakeApiFailure.unauthorized);
    await tester.pumpWidget(route(_rosemary, client: api.client));
    await tester.pumpAndSettle();
    expect(find.text('No se pudo cargar la planta'), findsOneWidget);
    expect(find.textContaining('no está autorizada'), findsOneWidget);
    expect(find.textContaining(testApiToken), findsNothing);
    expect(find.text('Planta no encontrada'), findsNothing);
    expect(find.text('Reintentar'), findsOneWidget);
    expect(api.requests, hasLength(1), reason: 'no automatic retry');
    expect(tester.takeException(), isNull);

    api.failure = FakeApiFailure.none;
    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();
    expect(api.requests, hasLength(2));
    expect(find.text('No se pudo cargar la planta'), findsNothing);
  });

  testWidgets('retry waits for the request and actions work in loading/error', (
    tester,
  ) async {
    var backs = 0;
    var homes = 0;
    var attempts = 0;
    final second = Completer<http.Response>();
    final fake = FakeCatalogApi();
    final client = MockClient((request) {
      attempts++;
      if (attempts == 1) {
        return Future.value(http.Response('{"title":"x","status":500}', 500));
      }
      if (attempts == 2) return second.future;
      return fake.client.get(request.url).then((r) => r);
    });
    await tester.pumpWidget(
      route(
        _rosemary,
        client: client,
        onBack: () => backs++,
        onHome: () => homes++,
      ),
    );
    expect(find.text('Cargando planta...'), findsOneWidget);
    await tester.pumpAndSettle();
    expect(find.text('No se pudo cargar la planta'), findsOneWidget);
    expect(find.textContaining('HTTP 500'), findsOneWidget);
    expect(find.text('Planta no encontrada'), findsNothing);
    expect(attempts, 1, reason: 'there must be no automatic retry');
    await tester.tap(find.byTooltip('Volver a Explorar'));
    await tester.tap(find.bySemanticsLabel('Inicio'));
    expect(backs, 1);
    expect(homes, 1);

    await tester.tap(find.text('Reintentar'));
    await tester.pump();
    expect(attempts, 2);
    expect(find.text('Cargando planta...'), findsOneWidget);
    expect(find.text('Planta no encontrada'), findsNothing);
    await tester.tap(find.byTooltip('Volver a Explorar'));
    await tester.tap(find.bySemanticsLabel('Inicio'));
    expect(backs, 2);
    expect(homes, 2);
    expect(find.text('No se pudo cargar la planta'), findsNothing);

    second.complete(
      http.Response(
        apiFixture('plant_$_rosemary.json'),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Rosemary'), findsWidgets);
    expect(find.text('English Lavender'), findsNothing);
    expect(attempts, 2);
  });

  testWidgets(
    'disabled actions stay inert on every tab and evidence stays bounded',
    (tester) async {
      var backs = 0;
      var homes = 0;
      await show(
        tester,
        _lavender,
        onBack: () => backs++,
        onHome: () => homes++,
      );
      for (final tab in _tabNames) {
        await tester.tap(find.text(tab));
        await tester.pumpAndSettle();
        Finder chip() => find
            .ancestor(of: find.text(tab), matching: find.byType(ChoiceChip))
            .first;
        expect(tester.widget<ChoiceChip>(chip()).selected, isTrue);
        for (final action in [
          find.bySemanticsLabel('Favorito no disponible'),
          find.bySemanticsLabel('Ver formulaciones relacionadas no disponible'),
        ]) {
          final node = tester.getSemantics(action);
          expect(
            node.getSemanticsData().hasAction(ui.SemanticsAction.tap),
            isFalse,
          );
          await tester.ensureVisible(action);
          await tester.tap(action, warnIfMissed: false);
          await tester.pump();
          expect(backs, 0);
          expect(homes, 0);
          expect(find.byType(AlertDialog), findsNothing);
          expect(find.byType(SnackBar), findsNothing);
        }
        expect(tester.widget<ChoiceChip>(chip()).selected, isTrue);
      }

      await show(tester, _lavender);
      for (final label in [
        'Dosis',
        'Recomendación',
        'Recomendaciones',
        'Origen ilustrativo',
        'Descripción ilustrativa',
      ]) {
        expect(find.text(label), findsNothing);
      }
      await tester.tap(find.text('Propiedades'));
      await tester.pumpAndSettle();
      expect(
        find.text('No hay objetivos registrados por la EMA para esta planta'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'loading, error retry, and not-found expose safe parent actions',
    (tester) async {
      var backs = 0;
      var homes = 0;
      final api = FakeCatalogApi(failure: FakeApiFailure.connection);
      await tester.pumpWidget(
        route(
          '123456',
          client: api.client,
          onBack: () => backs++,
          onHome: () => homes++,
        ),
      );
      expect(find.text('Cargando planta...'), findsOneWidget);
      await tester.pumpAndSettle();
      expect(find.text('No se pudo cargar la planta'), findsOneWidget);
      expect(find.textContaining('No se pudo conectar'), findsOneWidget);
      expect(find.textContaining('Connection refused'), findsNothing);
      api.failure = FakeApiFailure.none;
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(api.requests, hasLength(2));
      expect(find.text('Planta no encontrada'), findsOneWidget);
      expect(find.text('Reintentar'), findsNothing);
      await tester.tap(find.byTooltip('Volver a Explorar'));
      await tester.tap(find.text('Inicio'));
      expect(backs, 1);
      expect(homes, 1);
    },
  );

  testWidgets(
    'all fixture identities, parts and 200% layouts remain readable',
    (tester) async {
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      for (final entry in _names.entries) {
        final plant = plants[entry.key]!;
        expect((plant.primaryName, plant.secondaryName), entry.value);
        for (final scale in [1.0, 2.0]) {
          tester.view.physicalSize = const Size(360, 640);
          tester.view.devicePixelRatio = 1;
          await tester.pumpWidget(
            MaterialApp(
              key: ValueKey('layout-${plant.id}-$scale'),
              theme: buildBoticarioTheme(),
              builder: (context, child) => MediaQuery(
                data: MediaQuery.of(context).copyWith(
                  textScaler: TextScaler.linear(scale),
                  viewPadding: const EdgeInsets.only(top: 24, bottom: 24),
                  padding: const EdgeInsets.only(top: 24, bottom: 24),
                ),
                child: child!,
              ),
              home: pageFor(plant),
            ),
          );
          expect(find.text(entry.value.$1), findsWidgets);
          if (entry.value.$2 != null) {
            expect(find.text(entry.value.$2!), findsWidgets);
          }
          expect(
            tester.getRect(find.byTooltip('Volver a Explorar')).top,
            greaterThanOrEqualTo(24),
          );
          expect(
            tester.getRect(find.bySemanticsLabel('Inicio')).bottom,
            lessThanOrEqualTo(616),
          );
          await tester.scrollUntilVisible(find.text('Familia'), 100);
          expect(tester.takeException(), isNull);
          expect(
            find.bySemanticsLabel(
              'Ver formulaciones relacionadas no disponible',
            ),
            findsOneWidget,
          );
          if (scale == 1) {
            final expectedParts = plant.parts.isEmpty
                ? 'No hay partes registradas en fuente'
                : plant.parts.join(', ');
            await tester.scrollUntilVisible(find.text(expectedParts), 100);
            expect(find.text(expectedParts), findsOneWidget);
          }
        }
      }
    },
  );

  testWidgets('bottom bar lays out 2x2 without splitting labels at 200%', (
    tester,
  ) async {
    await setCompactViewport(tester, scale: 2);
    final tops = <String, double>{};
    for (final label in ['Inicio', 'Favoritos', 'Historial', 'Perfil']) {
      final finder = find.text(label);
      final paragraph = tester.renderObject<RenderParagraph>(finder);
      final lines = paragraph.getBoxesForSelection(
        TextSelection(baseOffset: 0, extentOffset: label.length),
      );
      expect(lines, hasLength(1), reason: '$label must stay on one line');
      tops[label] = tester.getTopLeft(finder).dy;
    }
    expect(tops['Favoritos'], tops['Inicio']);
    expect(tops['Perfil'], tops['Historial']);
    expect(tops['Historial']!, greaterThan(tops['Inicio']!));
  });

  testWidgets(
    'disabled controls have a single accessible label and 48dp targets',
    (tester) async {
      await setCompactViewport(tester, scale: 2);
      for (final label in [
        'Favorito no disponible',
        'Ver formulaciones relacionadas no disponible',
        'Favoritos no disponible',
        'Historial no disponible',
        'Perfil no disponible',
      ]) {
        final semantics = tester.getSemantics(find.bySemanticsLabel(label));
        expect(semantics.label, label);
        expect(semantics.flagsCollection.isButton, isTrue);
        expect(semantics.flagsCollection.isEnabled, ui.Tristate.isFalse);
      }
      final home = tester.getSemantics(find.bySemanticsLabel('Inicio'));
      expect(home.flagsCollection.isEnabled, ui.Tristate.isTrue);
      expect(home.flagsCollection.isSelected, ui.Tristate.isTrue);
      expect(
        tester.widget<Text>(find.text('Inicio')).style!.color,
        const Color(0xFF236335),
      );
      expect(
        tester.widget<Text>(find.text('Favoritos')).style!.color,
        Colors.grey,
      );
      expect(
        tester.getRect(find.byTooltip('Volver a Explorar')).shortestSide,
        greaterThanOrEqualTo(48),
      );
      expect(
        tester
            .getRect(find.bySemanticsLabel('Favorito no disponible'))
            .shortestSide,
        greaterThanOrEqualTo(48),
      );
      expect(
        tester
            .getRect(
              find.bySemanticsLabel(
                'Ver formulaciones relacionadas no disponible',
              ),
            )
            .height,
        greaterThanOrEqualTo(48),
      );
      final generalChip = find.ancestor(
        of: find.text('General'),
        matching: find.byType(ChoiceChip),
      );
      expect(tester.getRect(generalChip).height, greaterThanOrEqualTo(48));
      for (final finder in [
        find.bySemanticsLabel('Favoritos no disponible'),
        find.bySemanticsLabel('Historial no disponible'),
        find.bySemanticsLabel('Perfil no disponible'),
      ]) {
        final rect = tester.getRect(finder);
        expect(rect.height, greaterThanOrEqualTo(48));
        expect(rect.width, greaterThanOrEqualTo(48));
      }
    },
  );

  for (final scale in [1.0, 2.0]) {
    testWidgets(
      'P05 controls expose complete semantics and 48dp targets at $scale',
      (tester) async {
        var backCount = 0;
        var homeCount = 0;
        await setCompactViewport(tester, scale: scale);
        await tester.pumpWidget(
          MaterialApp(
            theme: buildBoticarioTheme(),
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(context).copyWith(
                textScaler: TextScaler.linear(scale),
                padding: insets,
                viewPadding: insets,
              ),
              child: child!,
            ),
            home: pageFor(
              _lavender,
              onBack: () => backCount++,
              onHome: () => homeCount++,
            ),
          ),
        );

        final viewport = tester.getRect(find.byType(CustomScrollView));
        expect(viewport.left, greaterThanOrEqualTo(insets.left));
        expect(viewport.top, greaterThanOrEqualTo(insets.top));
        expect(viewport.right, lessThanOrEqualTo(360 - insets.right));
        final back = find.byTooltip('Volver a Explorar');
        expect(tester.getRect(back).shortestSide, greaterThanOrEqualTo(48));
        expect(tester.getRect(back).top, greaterThanOrEqualTo(insets.top));
        expect(back.hitTestable(), findsOneWidget);
        await tester.tap(back);
        expect(backCount, 1);

        for (final tabName in _tabNames) {
          await selectTab(tester, tabName);
          final tab = find.widgetWithText(ChoiceChip, tabName);
          final tabSemantics = tester.getSemantics(tab);
          expect(tabSemantics.label, tabName);
          expect(tabSemantics.flagsCollection.isEnabled, ui.Tristate.isTrue);
          expect(tabSemantics.flagsCollection.isSelected, ui.Tristate.isTrue);
          expect(
            tabSemantics.getSemanticsData().hasAction(ui.SemanticsAction.tap),
            isTrue,
          );
          expect(tester.getRect(tab).height, greaterThanOrEqualTo(48));
          expect(tab.hitTestable(), findsOneWidget);

          await scrollTop(tester);
          final favorite = find.bySemanticsLabel('Favorito no disponible');
          final favoriteData = tester.getSemantics(favorite).getSemanticsData();
          expect(favoriteData.label, 'Favorito no disponible');
          expect(favoriteData.flagsCollection.isEnabled, ui.Tristate.isFalse);
          expect(favoriteData.hasAction(ui.SemanticsAction.tap), isFalse);
          expect(
            tester.getRect(favorite).shortestSide,
            greaterThanOrEqualTo(48),
          );
          expect(favorite.hitTestable(), findsOneWidget);

          final cta = find.bySemanticsLabel(
            'Ver formulaciones relacionadas no disponible',
          );
          final ctaData = tester.getSemantics(cta).getSemanticsData();
          expect(ctaData.label, 'Ver formulaciones relacionadas no disponible');
          expect(ctaData.flagsCollection.isButton, isTrue);
          expect(ctaData.flagsCollection.isEnabled, ui.Tristate.isFalse);
          expect(ctaData.hasAction(ui.SemanticsAction.tap), isFalse);
          expect(tester.getRect(cta).height, greaterThanOrEqualTo(48));
          expect(cta.hitTestable(), findsOneWidget);

          for (final label in [
            'Favoritos no disponible',
            'Historial no disponible',
            'Perfil no disponible',
          ]) {
            final target = find.bySemanticsLabel(label);
            final data = tester.getSemantics(target).getSemanticsData();
            expect(data.label, label);
            expect(data.flagsCollection.isButton, isTrue);
            expect(data.flagsCollection.isEnabled, ui.Tristate.isFalse);
            expect(data.hasAction(ui.SemanticsAction.tap), isFalse);
            final rect = tester.getRect(target);
            expect(rect.shortestSide, greaterThanOrEqualTo(48), reason: label);
            expect(rect.left, greaterThanOrEqualTo(insets.left));
            expect(rect.right, lessThanOrEqualTo(360 - insets.right));
            expect(rect.bottom, lessThanOrEqualTo(640 - insets.bottom));
            expect(target.hitTestable(), findsOneWidget);
          }
          final home = find.bySemanticsLabel('Inicio');
          final homeData = tester.getSemantics(home).getSemanticsData();
          expect(homeData.label, 'Inicio');
          expect(homeData.flagsCollection.isEnabled, ui.Tristate.isTrue);
          expect(homeData.flagsCollection.isSelected, ui.Tristate.isTrue);
          expect(homeData.hasAction(ui.SemanticsAction.tap), isTrue);
          expect(tester.getRect(home).shortestSide, greaterThanOrEqualTo(48));
          expect(home.hitTestable(), findsOneWidget);
          await tester.tap(home);
          expect(homeCount, _tabNames.indexOf(tabName) + 1);
        }
        expect(tester.takeException(), isNull);
      },
    );

    testWidgets(
      'P05 essential content and citations remain readable at $scale',
      (tester) async {
        await setCompactViewport(tester, scale: scale);
        for (final entry in _names.entries) {
          final plant = plants[entry.key]!;
          await tester.pumpWidget(
            MaterialApp(
              theme: buildBoticarioTheme(),
              builder: (context, child) => MediaQuery(
                data: MediaQuery.of(context).copyWith(
                  textScaler: TextScaler.linear(scale),
                  padding: insets,
                  viewPadding: insets,
                ),
                child: child!,
              ),
              home: pageFor(plant),
            ),
          );
          for (final tabName in _tabNames) {
            await selectTab(tester, tabName);
            final chip = find.widgetWithText(ChoiceChip, tabName);
            final renderedLabel = find.descendant(
              of: chip,
              matching: find.text(tabName),
            );
            assertLabelFitsWithin(tester, renderedLabel, tester.getRect(chip));
            expect(chip.hitTestable(), findsOneWidget);
          }
          await selectTab(tester, 'General');

          final footerRow = find
              .ancestor(
                of: find.text('Inicio'),
                matching: find.byType(Material),
              )
              .first;
          final footerRect = tester.getRect(footerRow);
          expect(footerRect.left, greaterThanOrEqualTo(insets.left));
          expect(footerRect.right, lessThanOrEqualTo(360 - insets.right));
          expect(footerRect.bottom, lessThanOrEqualTo(640 - insets.bottom));
          for (final label in ['Inicio', 'Favoritos', 'Historial', 'Perfil']) {
            final renderedLabel = find.text(label);
            expect(renderedLabel, findsOneWidget);
            expect(renderedLabel.hitTestable(), findsOneWidget);
            assertLabelFitsWithin(tester, renderedLabel, footerRect);
          }
          final cta = find.text('Ver formulaciones relacionadas');
          expect(cta.hitTestable(), findsOneWidget);
          final ctaRect = tester.getRect(find.byType(OutlinedButton));
          expect(ctaRect.left, greaterThanOrEqualTo(insets.left));
          expect(ctaRect.right, lessThanOrEqualTo(360 - insets.right));
          expect(ctaRect.bottom, lessThanOrEqualTo(640 - insets.bottom));
          assertLabelFitsWithin(tester, cta, ctaRect);

          for (final text in [
            entry.value.$1,
            ?entry.value.$2,
            'Familia',
            plant.family ?? 'No disponible en fuente',
            'Otros nombres comunes',
            if (plant.commonNames
                .skip(plant.primaryName == plant.scientificName ? 0 : 1)
                .isEmpty)
              'No hay nombres comunes registrados'
            else
              for (final name in plant.commonNames.skip(
                plant.primaryName == plant.scientificName ? 0 : 1,
              ))
                '${name.text} (${name.language})',
            'Parte utilizada',
            plant.parts.isEmpty
                ? 'No hay partes registradas en fuente'
                : plant.parts.join(', '),
            'Tipo de aceite',
          ]) {
            final target = find.text(text);
            // Rows are built lazily: scroll until the text exists.
            if (target.evaluate().isEmpty) await scrollTop(tester);
            for (var i = 0; i < 80 && target.evaluate().isEmpty; i++) {
              await tester.drag(passportScroll(), const Offset(0, -150));
              await tester.pump();
            }
            expect(target, findsWidgets, reason: 'Texto esencial: $text');
            await assertParagraphReadable(tester, target.first);
          }

          await selectTab(tester, 'Propiedades');
          await assertParagraphReadable(
            tester,
            find.text(
              'No hay objetivos registrados por la EMA para esta planta',
            ),
          );
          await selectTab(tester, 'Usos');
          if (plant.uses.isEmpty) {
            await assertParagraphReadable(tester, find.text(emptyUses));
          } else {
            await assertParagraphReadable(
              tester,
              find.text(PassportTexts.usesNoticeLabel),
            );
            final opened = <String>{};
            for (final use in plant.uses) {
              if (opened.add(use.activity)) {
                await openCitations(tester, use.activity);
              }
              await assertParagraphReadable(
                tester,
                find.text(use.activity).first,
              );
              await assertParagraphReadable(
                tester,
                find.text(use.reference.citation).first,
              );
            }
          }
          expect(tester.takeException(), isNull);
        }
      },
    );

    testWidgets(
      'P05 very long citation is readable in overlapping segments at $scale',
      (tester) async {
        tester.view.physicalSize = const Size(360, 640);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final base = plants[_lavender]!;
        final citation = List.generate(
          90,
          (index) =>
              'Segmento $index: referencia bibliográfica extensa verificable.',
        ).join(' ');
        final plant = Plant(
          id: base.id,
          scientificName: base.scientificName,
          family: base.family,
          names: base.names,
          parts: const [],
          uses: [
            PlantUse(
              activity: 'QA uso tradicional',
              language: 'en',
              reference: UseReference(
                id: 'QA referencia larga',
                citation: citation,
              ),
            ),
          ],
        );
        await tester.pumpWidget(
          MaterialApp(
            theme: buildBoticarioTheme(),
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(context).copyWith(
                textScaler: TextScaler.linear(scale),
                padding: insets,
                viewPadding: insets,
              ),
              child: child!,
            ),
            home: pageFor(plant),
          ),
        );
        await assertParagraphReadable(
          tester,
          find.text('No hay partes registradas en fuente'),
        );
        // `General` has no reference list: the citation is in `Usos` only.
        expect(find.text(citation), findsNothing);
        await selectTab(tester, 'Usos');
        expect(find.text(citation), findsNothing);
        await openCitations(tester, 'QA uso tradicional');
        await assertParagraphReadable(tester, find.text(citation));
        expect(
          tester.getSize(find.text(citation)).height,
          greaterThan(tester.getSize(find.byType(CustomScrollView)).height),
        );
        expect(tester.takeException(), isNull);
      },
    );

    for (final state in ['loading', 'error', 'notfound']) {
      testWidgets('P05 route $state semantics and safe targets at $scale', (
        tester,
      ) async {
        tester.view.physicalSize = const Size(360, 640);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        var backCount = 0;
        var homeCount = 0;
        var reads = 0;
        final pending = Completer<http.Response>();
        final fake = FakeCatalogApi();
        final client = MockClient((request) {
          reads++;
          if (state == 'loading') return pending.future;
          if (state == 'error') {
            return reads == 1
                ? Future.value(http.Response('{"status":500}', 500))
                : pending.future;
          }
          return fake.client.get(request.url);
        });
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              httpClientProvider.overrideWithValue(client),
              apiTokenProvider.overrideWithValue(testApiToken),
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
              home: PlantPassportRoutePage(
                plantId: state == 'notfound' ? '999999' : _lavender,
                onBack: () => backCount++,
                onHome: () => homeCount++,
              ),
            ),
          ),
        );
        if (state != 'loading') await tester.pumpAndSettle();
        final title = switch (state) {
          'loading' => 'Cargando planta...',
          'error' => 'No se pudo cargar la planta',
          _ => 'Planta no encontrada',
        };
        expect(find.text(title), findsOneWidget);
        expect(find.textContaining('private error'), findsNothing);
        if (state == 'error') {
          expect(find.textContaining('HTTP 500'), findsOneWidget);
        }
        final titleParagraph = tester.renderObject<RenderParagraph>(
          find.text(title),
        );
        expect(titleParagraph.didExceedMaxLines, isFalse, reason: title);
        expect(
          titleParagraph.overflow,
          isNot(TextOverflow.ellipsis),
          reason: title,
        );
        for (final text in tester.widgetList<Text>(find.byType(Text))) {
          final textValue = text.data ?? text.textSpan!.toPlainText();
          final paragraph = tester.renderObject<RenderParagraph>(
            find.byWidget(text),
          );
          expect(paragraph.didExceedMaxLines, isFalse, reason: textValue);
          expect(
            paragraph.overflow,
            isNot(TextOverflow.ellipsis),
            reason: textValue,
          );
          for (final word in RegExp(r'\S+').allMatches(textValue)) {
            for (final box in paragraph.getBoxesForSelection(
              TextSelection(baseOffset: word.start, extentOffset: word.end),
            )) {
              expect(box.left, greaterThanOrEqualTo(-0.1), reason: textValue);
              expect(
                box.right,
                lessThanOrEqualTo(paragraph.size.width + 0.1),
                reason: textValue,
              );
              final global = box.toRect().shift(
                paragraph.localToGlobal(Offset.zero),
              );
              expect(global.top, greaterThanOrEqualTo(insets.top - 0.1));
              expect(
                global.bottom,
                lessThanOrEqualTo(640 - insets.bottom + 0.1),
              );
            }
          }
        }

        final controls = <Finder>[
          find.byTooltip('Volver a Explorar'),
          find.bySemanticsLabel('Inicio'),
          for (final label in [
            'Favoritos no disponible',
            'Historial no disponible',
            'Perfil no disponible',
          ])
            find.bySemanticsLabel(label),
          if (state == 'error')
            find.widgetWithText(OutlinedButton, 'Reintentar'),
        ];
        for (final control in controls) {
          expect(
            control.hitTestable(),
            findsOneWidget,
            reason: '$state $control',
          );
          final rect = tester.getRect(control);
          expect(rect.shortestSide, greaterThanOrEqualTo(48));
          expect(rect.top, greaterThanOrEqualTo(insets.top));
          expect(rect.bottom, lessThanOrEqualTo(640 - insets.bottom));
          expect(rect.left, greaterThanOrEqualTo(insets.left));
          expect(rect.right, lessThanOrEqualTo(360 - insets.right));
        }
        final retryRect = state == 'error'
            ? tester.getRect(find.widgetWithText(OutlinedButton, 'Reintentar'))
            : null;
        final homeSemantics = tester
            .getSemantics(find.bySemanticsLabel('Inicio'))
            .getSemanticsData();
        expect(homeSemantics.flagsCollection.isSelected, ui.Tristate.isTrue);
        expect(homeSemantics.flagsCollection.isEnabled, ui.Tristate.isTrue);
        for (final label in [
          'Favoritos no disponible',
          'Historial no disponible',
          'Perfil no disponible',
        ]) {
          final data = tester
              .getSemantics(find.bySemanticsLabel(label))
              .getSemanticsData();
          expect(data.flagsCollection.isEnabled, ui.Tristate.isFalse);
          expect(data.hasAction(ui.SemanticsAction.tap), isFalse);
        }
        await tester.tap(find.byTooltip('Volver a Explorar'));
        await tester.tap(find.bySemanticsLabel('Inicio'));
        expect(backCount, 1);
        expect(homeCount, 1);
        if (state == 'error') {
          await tester.tap(find.text('Reintentar'));
          await tester.pump();
          expect(reads, 2);
          expect(find.text('Cargando planta...'), findsOneWidget);
          expect(retryRect!.shortestSide, greaterThanOrEqualTo(48));
          pending.complete(
            http.Response(
              apiFixture('plant_$_lavender.json'),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            ),
          );
          await tester.pumpAndSettle();
          expect(find.text('English Lavender'), findsWidgets);
        }
        if (!pending.isCompleted) {
          // Lets the repository's 10 s timeout timer end with the request.
          pending.complete(
            http.Response(
              apiFixture('plant_$_lavender.json'),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            ),
          );
          await tester.pumpAndSettle();
        }
        expect(tester.takeException(), isNull);
      });
    }
  }
}
