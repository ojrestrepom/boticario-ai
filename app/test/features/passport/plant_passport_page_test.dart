import 'dart:async';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_repository.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_catalog_provenance.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late PlantCatalog catalog;
  late String catalogJson;
  const insets = EdgeInsets.fromLTRB(8, 24, 8, 20);

  setUpAll(() async {
    catalogJson = await rootBundle.loadString(plantCatalogAssetPath);
    catalog = PlantCatalogAssetDataSource.parse(catalogJson);
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

  Widget pageFor(int id, {VoidCallback? onBack, VoidCallback? onHome}) =>
      PlantPassportPage(
        plant: catalog.findById(id)!,
        provenance: catalog.provenance,
        onBack: onBack ?? () {},
        onHome: onHome ?? () {},
      );

  Future<void> show(
    WidgetTester tester,
    int id, {
    VoidCallback? onBack,
    VoidCallback? onHome,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBoticarioTheme(),
        home: pageFor(id, onBack: onBack, onHome: onHome),
      ),
    );
  }

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
        home: pageFor(544),
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

  testWidgets('General muestra identidad, ausencias y procedencia', (
    tester,
  ) async {
    await setCompactViewport(tester);
    expect(find.text('Lavanda'), findsNWidgets(2));
    expect(find.text('Lavandula angustifolia'), findsNWidgets(2));
    expect(find.text('Nombre común editorial'), findsOneWidget);
    expect(find.text('No disponible en fuente'), findsNWidgets(2));
    expect(find.textContaining('Flower (FL)'), findsOneWidget);
    expect(find.text('No aplicable: ficha de planta'), findsOneWidget);
    expect(find.text(catalog.provenance.sourceName), findsOneWidget);
    expect(find.text(catalog.provenance.license), findsOneWidget);
    expect(find.text(catalog.provenance.version), findsOneWidget);
    expect(find.text(catalog.provenance.datasetId), findsOneWidget);
    expect(
      find.textContaining(
        '${catalog.provenance.fileName} (ID ${catalog.provenance.fileId})',
      ),
      findsOneWidget,
    );
    expect(find.text(catalog.provenance.sourceUrl), findsOneWidget);
    expect(find.text(catalog.provenance.recommendedCitation), findsOneWidget);
    expect(
      find.textContaining('45ae44a0544586b8ac22a232beaac344'),
      findsNothing,
    );
  });

  testWidgets('Propiedades no afirma eficacia medicinal', (tester) async {
    await show(tester, 544);
    await tester.tap(find.text('Propiedades'));
    await tester.pumpAndSettle();
    expect(
      find.bySemanticsLabel('Ver formulaciones relacionadas no disponible'),
      findsOneWidget,
    );
    expect(
      find.text('sin propiedades medicinales evaluadas en este catálogo'),
      findsOneWidget,
    );
    expect(find.textContaining('eficaz'), findsNothing);
  });

  testWidgets('an empty parts collection is stated explicitly', (tester) async {
    final lavender = catalog.findById(544)!;
    final withoutParts = Plant(
      usdaPlantId: lavender.usdaPlantId,
      editorialCommonName: lavender.editorialCommonName,
      sourceScientificName: lavender.sourceScientificName,
      identitySource: lavender.identitySource,
      parts: const [],
      traditionalUses: lavender.traditionalUses,
    );
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBoticarioTheme(),
        home: PlantPassportPage(
          plant: withoutParts,
          provenance: catalog.provenance,
          onBack: () {},
          onHome: () {},
        ),
      ),
    );
    await tester.scrollUntilVisible(
      find.text('No hay partes registradas en fuente'),
      100,
    );
    expect(find.text('No hay partes registradas en fuente'), findsOneWidget);
  });

  testWidgets('Usos conserva actividad y cita en cada registro', (
    tester,
  ) async {
    await show(tester, 544);
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text('Registros tradicionales'), findsOneWidget);
    expect(
      find.text(
        'No es una recomendación de uso ni evidencia de eficacia clínica',
      ),
      findsOneWidget,
    );
    expect(find.text('Carminative'), findsOneWidget);
    final lavender = catalog.findById(544)!;
    expect(lavender.traditionalUses, hasLength(10));
    for (final use in lavender.traditionalUses) {
      expect(find.text(use.activity), findsWidgets);
      for (final reference in use.references) {
        expect(find.text(reference.citation), findsWidgets);
      }
    }
    expect(find.textContaining('no disponible'), findsNothing);
  });

  testWidgets(
    'Romero presenta usos sin limitar la lista y menta/manzanilla vacías',
    (tester) async {
      await show(tester, 873);
      await tester.tap(find.text('Usos'));
      await tester.pumpAndSettle();
      expect(find.text('Registro tradicional'), findsNWidgets(60));
      expect(
        find.bySemanticsLabel('Ver formulaciones relacionadas no disponible'),
        findsOneWidget,
      );
      await show(tester, 605);
      await tester.tap(find.text('Usos'));
      await tester.pumpAndSettle();
      expect(
        find.text(
          'No hay usos tradicionales con referencia verificable disponibles',
        ),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel('Ver formulaciones relacionadas no disponible'),
        findsOneWidget,
      );
      await show(tester, 619);
      await tester.tap(find.text('Usos'));
      await tester.pumpAndSettle();
      expect(
        find.text(
          'No hay usos tradicionales con referencia verificable disponibles',
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets('Back/Home callbacks and unavailable actions are inert', (
    tester,
  ) async {
    var backs = 0;
    var homes = 0;
    await show(tester, 544, onBack: () => backs++, onHome: () => homes++);
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

  testWidgets('identity change resets selected tab to General', (tester) async {
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(544)),
    );
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text('Registros tradicionales'), findsOneWidget);
    await tester.pumpWidget(
      MaterialApp(theme: buildBoticarioTheme(), home: pageFor(619)),
    );
    await tester.pumpAndSettle();
    expect(find.text('Nombre común editorial'), findsOneWidget);
    expect(
      find.text(
        'No hay usos tradicionales con referencia verificable disponibles',
      ),
      findsNothing,
    );
  });

  testWidgets('route entry resolves a known catalog identity', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantCatalogAssetDataSourceProvider.overrideWithValue(
            PlantCatalogAssetDataSource(loadAsset: (_) async => catalogJson),
          ),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          home: PlantPassportRoutePage(
            plantId: '544',
            onBack: () {},
            onHome: () {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Lavanda'), findsWidgets);
  });

  testWidgets(
    'route entry resolves five valid IDs and handles all bad IDs safely',
    (tester) async {
      var backs = 0;
      var homes = 0;
      const expected = <String, String>{
        '544': 'Lavanda',
        '401': 'Eucalipto',
        '873': 'Romero',
        '605': 'Manzanilla',
        '619': 'Menta',
      };
      Widget route(String id) => ProviderScope(
        overrides: [
          plantCatalogAssetDataSourceProvider.overrideWithValue(
            PlantCatalogAssetDataSource(loadAsset: (_) async => catalogJson),
          ),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          home: PlantPassportRoutePage(
            plantId: id,
            onBack: () => backs++,
            onHome: () => homes++,
          ),
        ),
      );

      await tester.pumpWidget(route('544'));
      await tester.pumpAndSettle();
      for (final item in expected.entries) {
        await tester.pumpWidget(route(item.key));
        await tester.pumpAndSettle();
        expect(find.text(item.value), findsWidgets, reason: 'ID ${item.key}');
        expect(tester.takeException(), isNull);
      }

      for (final id in [
        '999999',
        'not-an-id',
        '-544',
        '99999999999999999999999999999999999999999999999999',
      ]) {
        await tester.pumpWidget(route(id));
        await tester.pumpAndSettle();
        expect(find.text('Planta no encontrada'), findsOneWidget, reason: id);
        for (final name in expected.values) {
          expect(
            find.text(name),
            findsNothing,
            reason: 'unexpected plant for $id',
          );
        }
        await tester.tap(find.byTooltip('Volver a Explorar'));
        await tester.tap(find.bySemanticsLabel('Inicio'));
        expect(tester.takeException(), isNull);
      }
      expect(backs, 4);
      expect(homes, 4);
    },
  );

  testWidgets('route ID changes known → unknown → known and resets General', (
    tester,
  ) async {
    const key = ValueKey('route-entry');
    Widget route(String id) => ProviderScope(
      overrides: [
        plantCatalogAssetDataSourceProvider.overrideWithValue(
          PlantCatalogAssetDataSource(loadAsset: (_) async => catalogJson),
        ),
      ],
      child: MaterialApp(
        theme: buildBoticarioTheme(),
        home: PlantPassportRoutePage(
          key: key,
          plantId: id,
          onBack: () {},
          onHome: () {},
        ),
      ),
    );

    await tester.pumpWidget(route('544'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Usos'));
    await tester.pumpAndSettle();
    expect(find.text('Registros tradicionales'), findsOneWidget);

    await tester.pumpWidget(route('999999'));
    await tester.pumpAndSettle();
    expect(find.text('Planta no encontrada'), findsOneWidget);
    await tester.pumpWidget(route('401'));
    await tester.pumpAndSettle();
    expect(find.text('Eucalipto'), findsWidgets);
    expect(find.text('Nombre común editorial'), findsOneWidget);
    expect(find.text('Registros tradicionales'), findsNothing);
  });

  testWidgets('retry waits for Completer and actions work in loading/error', (
    tester,
  ) async {
    var backs = 0;
    var homes = 0;
    var attempts = 0;
    final secondRead = Completer<String>();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          plantCatalogAssetDataSourceProvider.overrideWithValue(
            PlantCatalogAssetDataSource(
              loadAsset: (_) {
                attempts++;
                if (attempts == 1) {
                  return Future<String>.error(StateError('private raw error'));
                }
                return secondRead.future;
              },
            ),
          ),
        ],
        child: MaterialApp(
          theme: buildBoticarioTheme(),
          home: PlantPassportRoutePage(
            plantId: '401',
            onBack: () => backs++,
            onHome: () => homes++,
          ),
        ),
      ),
    );
    expect(find.text('Cargando catálogo...'), findsOneWidget);
    await tester.pumpAndSettle();
    expect(find.text('No se pudo cargar el catálogo'), findsOneWidget);
    expect(find.textContaining('private raw error'), findsNothing);
    expect(attempts, 1, reason: 'there must be no automatic retry');
    await tester.tap(find.byTooltip('Volver a Explorar'));
    await tester.tap(find.bySemanticsLabel('Inicio'));
    expect(backs, 1);
    expect(homes, 1);

    await tester.tap(find.text('Reintentar'));
    await tester.pump();
    expect(attempts, 2);
    expect(find.text('Cargando catálogo...'), findsOneWidget);
    await tester.tap(find.byTooltip('Volver a Explorar'));
    await tester.tap(find.bySemanticsLabel('Inicio'));
    expect(backs, 2);
    expect(homes, 2);
    expect(find.text('No se pudo cargar el catálogo'), findsNothing);

    secondRead.complete(catalogJson);
    await tester.pumpAndSettle();
    expect(find.text('Eucalipto'), findsWidgets);
    expect(find.text('Lavanda'), findsNothing);
    expect(attempts, 2);
  });

  testWidgets(
    'disabled actions stay inert on every tab and evidence stays bounded',
    (tester) async {
      var backs = 0;
      var homes = 0;
      await show(tester, 544, onBack: () => backs++, onHome: () => homes++);
      for (final tab in ['General', 'Propiedades', 'Usos']) {
        await tester.tap(find.text(tab));
        await tester.pumpAndSettle();
        expect(
          tester
              .widget<ChoiceChip>(
                find
                    .ancestor(
                      of: find.text(tab),
                      matching: find.byType(ChoiceChip),
                    )
                    .first,
              )
              .selected,
          isTrue,
        );
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
        expect(
          tester
              .widget<ChoiceChip>(
                find
                    .ancestor(
                      of: find.text(tab),
                      matching: find.byType(ChoiceChip),
                    )
                    .first,
              )
              .selected,
          isTrue,
        );
      }

      await show(tester, 544);
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
        find.text('sin propiedades medicinales evaluadas en este catálogo'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'loading, error retry, and not-found expose safe parent actions',
    (tester) async {
      var backs = 0;
      var homes = 0;
      var attempts = 0;
      final loaded = rootBundle.loadString(plantCatalogAssetPath);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            plantCatalogAssetDataSourceProvider.overrideWithValue(
              PlantCatalogAssetDataSource(
                loadAsset: (_) async {
                  attempts++;
                  if (attempts == 1) throw StateError('private raw error');
                  return loaded;
                },
              ),
            ),
          ],
          child: MaterialApp(
            theme: buildBoticarioTheme(),
            home: PlantPassportRoutePage(
              plantId: '123456',
              onBack: () => backs++,
              onHome: () => homes++,
            ),
          ),
        ),
      );
      expect(find.text('Cargando catálogo...'), findsOneWidget);
      await tester.pumpAndSettle();
      expect(find.text('No se pudo cargar el catálogo'), findsOneWidget);
      expect(find.text('private raw error'), findsNothing);
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(attempts, 2);
      expect(find.text('Planta no encontrada'), findsOneWidget);
      await tester.tap(find.byTooltip('Volver a Explorar'));
      await tester.tap(find.text('Inicio'));
      expect(backs, 1);
      expect(homes, 1);
    },
  );

  testWidgets(
    'all five source identities, parts and 200% layouts remain readable',
    (tester) async {
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final expected = <int, (String, String)>{
        544: ('Lavanda', 'Lavandula angustifolia'),
        401: ('Eucalipto', 'Eucalyptus globulus'),
        873: ('Romero', 'Rosmarinus officinalis'),
        605: ('Manzanilla', 'Matricaria recutita'),
        619: ('Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
      };
      for (final entry in expected.entries) {
        final plant = catalog.findById(entry.key)!;
        expect((
          plant.editorialCommonName,
          plant.sourceScientificName,
        ), entry.value);
        for (final scale in [1.0, 2.0]) {
          tester.view.physicalSize = const Size(360, 640);
          tester.view.devicePixelRatio = 1;
          await tester.pumpWidget(
            MaterialApp(
              key: ValueKey('layout-${plant.usdaPlantId}-$scale'),
              theme: buildBoticarioTheme(),
              builder: (context, child) => MediaQuery(
                data: MediaQuery.of(context).copyWith(
                  textScaler: TextScaler.linear(scale),
                  viewPadding: const EdgeInsets.only(top: 24, bottom: 24),
                  padding: const EdgeInsets.only(top: 24, bottom: 24),
                ),
                child: child!,
              ),
              home: PlantPassportPage(
                plant: plant,
                provenance: catalog.provenance,
                onBack: () {},
                onHome: () {},
              ),
            ),
          );
          expect(find.text(entry.value.$1), findsWidgets);
          expect(find.text(entry.value.$2), findsWidgets);
          expect(
            tester.getRect(find.byTooltip('Volver a Explorar')).top,
            greaterThanOrEqualTo(24),
          );
          expect(
            tester.getRect(find.bySemanticsLabel('Inicio')).bottom,
            lessThanOrEqualTo(616),
          );
          await tester.scrollUntilVisible(
            find.text('Nombre común editorial'),
            100,
          );
          expect(find.text(entry.value.$1), findsWidgets);
          expect(find.text(entry.value.$2), findsWidgets);
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
                : plant.parts
                      .map((part) => '${part.name} (${part.sourceCode})')
                      .join(', ');
            await tester.scrollUntilVisible(
              find.textContaining(expectedParts),
              100,
            );
            expect(find.text(expectedParts), findsOneWidget);
          }
        }
      }
    },
  );

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
              544,
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

        for (final tabName in ['General', 'Propiedades', 'Usos']) {
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
          expect(
            homeCount,
            ['General', 'Propiedades', 'Usos'].indexOf(tabName) + 1,
          );
        }
        expect(tester.takeException(), isNull);
      },
    );

    testWidgets(
      'P05 essential content and citations remain readable at $scale',
      (tester) async {
        await setCompactViewport(tester, scale: scale);
        const expected = <int, (String, String)>{
          544: ('Lavanda', 'Lavandula angustifolia'),
          401: ('Eucalipto', 'Eucalyptus globulus'),
          873: ('Romero', 'Rosmarinus officinalis'),
          605: ('Manzanilla', 'Matricaria recutita'),
          619: ('Menta', 'Mentha x piperita subsp. nothosubsp. piperita'),
        };
        for (final entry in expected.entries) {
          final plant = catalog.findById(entry.key)!;
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
              home: PlantPassportPage(
                plant: plant,
                provenance: catalog.provenance,
                onBack: () {},
                onHome: () {},
              ),
            ),
          );
          for (final tabName in ['General', 'Propiedades', 'Usos']) {
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
              .ancestor(of: find.text('Inicio'), matching: find.byType(Row))
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
            entry.value.$2,
            'Nombre común editorial',
            'Nombre científico de fuente',
            'Origen',
            'Descripción',
            'No disponible en fuente',
            'Partes registradas en fuente',
            plant.parts.isEmpty
                ? 'No hay partes registradas en fuente'
                : plant.parts
                      .map((part) => '${part.name} (${part.sourceCode})')
                      .join(', '),
            'Tipo de aceite',
            'No aplicable: ficha de planta',
            'Procedencia',
            'Fuente',
            catalog.provenance.sourceName,
            'Licencia',
            catalog.provenance.license,
            'Versión',
            catalog.provenance.version,
            'Dataset',
            catalog.provenance.datasetId,
            'Archivo',
            '${catalog.provenance.fileName} (ID ${catalog.provenance.fileId})',
            'URL de fuente',
            catalog.provenance.sourceUrl,
            'Fecha de inspección (no cobertura temporal)',
            '2026-10-01',
            'Cita recomendada de la fuente',
            catalog.provenance.recommendedCitation,
          ]) {
            final target = find.text(text);
            expect(target, findsWidgets, reason: 'Texto esencial: $text');
            await assertParagraphReadable(tester, target.first);
          }

          await selectTab(tester, 'Propiedades');
          await assertParagraphReadable(
            tester,
            find.text('sin propiedades medicinales evaluadas en este catálogo'),
          );
          await selectTab(tester, 'Usos');
          if (plant.traditionalUses.isEmpty) {
            await assertParagraphReadable(
              tester,
              find.text(
                'No hay usos tradicionales con referencia verificable disponibles',
              ),
            );
          } else {
            await assertParagraphReadable(
              tester,
              find.text(
                'No es una recomendación de uso ni evidencia de eficacia clínica',
              ),
            );
            for (final use in plant.traditionalUses) {
              await assertParagraphReadable(
                tester,
                find.text(use.activity).first,
              );
              for (final reference in use.references) {
                await assertParagraphReadable(
                  tester,
                  find.text(reference.citation).first,
                );
              }
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
        final base = catalog.findById(544)!;
        final citation = List.generate(
          90,
          (index) =>
              'Segmento $index: referencia bibliográfica extensa verificable.',
        ).join(' ');
        final plant = Plant(
          usdaPlantId: base.usdaPlantId,
          editorialCommonName: base.editorialCommonName,
          sourceScientificName: base.sourceScientificName,
          identitySource: base.identitySource,
          traditionalUses: [
            TraditionalUse(
              activity: 'QA uso tradicional',
              source: SourceRecord(
                table: 'ETHNOBOT',
                selectors: const {'ACTIVITY': 'QA uso tradicional'},
              ),
              references: [
                PlantReference(
                  id: 'QA referencia larga',
                  citation: citation,
                  source: SourceRecord(
                    table: 'REFERENCES',
                    selectors: {'LONGREF': citation},
                  ),
                ),
              ],
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
            home: PlantPassportPage(
              plant: plant,
              provenance: catalog.provenance,
              onBack: () {},
              onHome: () {},
            ),
          ),
        );
        await assertParagraphReadable(
          tester,
          find.text('No hay partes registradas en fuente'),
        );
        await assertParagraphReadable(tester, find.text(citation));
        expect(
          tester.getSize(find.text(citation)).height,
          greaterThan(tester.getSize(find.byType(CustomScrollView)).height),
        );
        await selectTab(tester, 'Usos');
        await assertParagraphReadable(tester, find.text(citation));
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
        final pending = Completer<String>();
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              plantCatalogAssetDataSourceProvider.overrideWithValue(
                PlantCatalogAssetDataSource(
                  loadAsset: (_) {
                    reads++;
                    if (state == 'loading') return pending.future;
                    if (state == 'error') {
                      return reads == 1
                          ? Future<String>.error(StateError('private error'))
                          : pending.future;
                    }
                    return Future.value(catalogJson);
                  },
                ),
              ),
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
                plantId: state == 'notfound' ? '999999' : '544',
                onBack: () => backCount++,
                onHome: () => homeCount++,
              ),
            ),
          ),
        );
        if (state != 'loading') await tester.pumpAndSettle();
        final title = switch (state) {
          'loading' => 'Cargando catálogo...',
          'error' => 'No se pudo cargar el catálogo',
          _ => 'Planta no encontrada',
        };
        expect(find.text(title), findsOneWidget);
        expect(find.textContaining('private error'), findsNothing);
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
          if (state == 'error') find.widgetWithText(TextButton, 'Reintentar'),
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
            ? tester.getRect(find.widgetWithText(TextButton, 'Reintentar'))
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
          expect(find.text('Cargando catálogo...'), findsOneWidget);
          expect(retryRect!.shortestSide, greaterThanOrEqualTo(48));
          pending.complete(catalogJson);
          await tester.pumpAndSettle();
          expect(find.text('Lavanda'), findsWidgets);
        }
        expect(tester.takeException(), isNull);
      });
    }
  }
}
