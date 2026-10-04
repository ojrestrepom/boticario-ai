import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' show Tristate;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/plant_catalog_asset_data_source.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_catalog_provenance.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const identities = [
  (544, 'Lavanda', 'Lavandula angustifolia', 10),
  (401, 'Eucalipto', 'Eucalyptus globulus', 51),
  (873, 'Romero', 'Rosmarinus officinalis', 60),
  (605, 'Manzanilla', 'Matricaria recutita', 0),
  (619, 'Menta', 'Mentha x piperita subsp. nothosubsp. piperita', 0),
];
const insets = EdgeInsets.fromLTRB(8, 24, 8, 20);
const noProperties = 'sin propiedades medicinales evaluadas en este catálogo';
const noUses =
    'No hay usos tradicionales con referencia verificable disponibles';
const disclaimer =
    'No es una recomendación de uso ni evidencia de eficacia clínica';
const unavailable = [
  'Favorito no disponible',
  'Ver formulaciones relacionadas no disponible',
  'Favoritos no disponible',
  'Historial no disponible',
  'Perfil no disponible',
];

class PassportDenyHttp extends HttpOverrides {
  int calls = 0;
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    calls++;
    throw StateError('Passport QA denies HTTP');
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  // Read once outside fake async. Registered bundle IO already has project tests.
  final catalog = PlantCatalogAssetDataSource.parse(
    File('assets/data/plant_catalog.json').readAsStringSync(),
  );

  // Use existing SDK Roboto for representative Android text metrics, not
  // Flutter tests' deliberately square Ahem glyphs. No download/product edit.
  // Ahem remains opt-in for harness characterization, with unchanged assertions.
  final sdk =
      Platform.environment['QA_FLUTTER_SDK'] ?? '/opt/homebrew/share/flutter';
  final fontDirectory =
      Platform.environment['QA_PASSPORT_ROBOTO_DIR'] ??
      '$sdk/engine/src/flutter/txt/third_party/fonts';
  if (Platform.environment['QA_PASSPORT_USE_AHEM'] != '1') {
    setUpAll(() async {
      final loader = FontLoader('Roboto');
      for (final name in ['Roboto-Regular.ttf', 'Roboto-Medium.ttf']) {
        loader.addFont(
          Future.value(
            ByteData.sublistView(
              File('$fontDirectory/$name').readAsBytesSync(),
            ),
          ),
        );
      }
      await loader.load();
      print('Passport QA: SDK Roboto fonts loaded (host, not Android device)');
    });
  }

  Future<void> mount(
    WidgetTester tester,
    Plant plant, {
    double scale = 1,
    VoidCallback? back,
    VoidCallback? home,
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
            padding: insets,
            viewPadding: insets,
          ),
          child: child!,
        ),
        home: PlantPassportPage(
          plant: plant,
          provenance: catalog.provenance,
          onBack: back ?? () {},
          onHome: home ?? () {},
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Finder scrollable() => find.descendant(
    of: find.byType(CustomScrollView),
    matching: find.byType(Scrollable),
  );

  Future<void> top(WidgetTester tester) async {
    tester.state<ScrollableState>(scrollable()).position.jumpTo(0);
    await tester.pumpAndSettle();
  }

  Future<void> reach(WidgetTester tester, Finder target) async {
    if (target.evaluate().isEmpty) await top(tester);
    if (target.evaluate().isEmpty) {
      await tester.scrollUntilVisible(target, 100, scrollable: scrollable());
    }
    await tester.ensureVisible(target);
    await tester.pumpAndSettle();
  }

  Future<void> tab(WidgetTester tester, String label) async {
    await top(tester);
    final target = find.widgetWithText(ChoiceChip, label);
    await reach(tester, target);
    expect(target.hitTestable(), findsOneWidget);
    await tester.tap(target);
    await tester.pumpAndSettle();
    await reach(tester, find.widgetWithText(ChoiceChip, label));
    for (final name in ['General', 'Propiedades', 'Usos']) {
      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, name))
            .selected,
        name == label,
      );
    }
  }

  List<String> scrollText(WidgetTester tester) => tester
      .widgetList<Text>(
        find.descendant(
          of: find.byType(CustomScrollView),
          matching: find.byType(Text),
        ),
      )
      .map((text) => text.data ?? text.textSpan!.toPlainText())
      .toList();

  // Assert actual rendered lines, not just Text existence. A paragraph taller
  // than the viewport must be readable in overlapping scroll segments.
  Future<void> readParagraph(WidgetTester tester, Finder target) async {
    await reach(tester, target);
    final paragraph = tester.renderObject<RenderParagraph>(target);
    final plain = paragraph.text.toPlainText();
    expect(paragraph.didExceedMaxLines, isFalse, reason: plain);
    expect(paragraph.overflow, isNot(TextOverflow.ellipsis), reason: plain);
    // Selection boxes include hanging whitespace and half of letterSpacing
    // after the last glyph: measure non-whitespace text, not invisible space.
    final boxes = [
      for (final word in RegExp(r'\S+').allMatches(plain))
        ...paragraph.getBoxesForSelection(
          TextSelection(baseOffset: word.start, extentOffset: word.end),
        ),
    ];
    final spacing = (paragraph.text.style?.letterSpacing ?? 0).abs() / 2;
    expect(boxes, isNotEmpty, reason: plain);
    for (final box in boxes) {
      expect(box.left, greaterThanOrEqualTo(-0.1), reason: plain);
      expect(
        box.right,
        lessThanOrEqualTo(paragraph.size.width + spacing + 0.1),
        reason: plain,
      );
      expect(
        box.bottom,
        lessThanOrEqualTo(paragraph.size.height + 0.1),
        reason: plain,
      );
    }
    final viewport = tester.getRect(find.byType(CustomScrollView));
    final rect = tester.getRect(target);
    expect(rect.left, greaterThanOrEqualTo(insets.left - 0.1), reason: plain);
    expect(
      rect.right,
      lessThanOrEqualTo(360 - insets.right + 0.1),
      reason: plain,
    );
    final seen = <int>{};
    final maxSteps =
        (paragraph.size.height / (viewport.height * 0.5)).ceil() + 10;
    for (var step = 0; step < maxSteps; step++) {
      final origin = paragraph.localToGlobal(Offset.zero);
      for (var i = 0; i < boxes.length; i++) {
        final line = boxes[i].toRect().shift(origin);
        if (line.top >= viewport.top - 0.1 &&
            line.bottom <= viewport.bottom + 0.1) {
          seen.add(i);
        }
      }
      if (seen.length == boxes.length) break;
      final position = tester.state<ScrollableState>(scrollable()).position;
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
      reason: 'Every rendered line reachable: $plain',
    );
    expect(tester.takeException(), isNull);
  }

  Future<void> readScroll(WidgetTester tester) async {
    await top(tester);
    // At 200% the long header can place the next sliver outside cache extent.
    final plant = tester
        .widget<PlantPassportPage>(find.byType(PlantPassportPage))
        .plant;
    for (final value in [
      plant.editorialCommonName,
      plant.sourceScientificName,
    ]) {
      await readParagraph(tester, find.text(value).first);
    }
    await reach(tester, find.widgetWithText(ChoiceChip, 'General'));
    final texts = tester
        .widgetList<Text>(
          find.descendant(
            of: find.byType(CustomScrollView),
            matching: find.byType(Text),
          ),
        )
        .toList();
    for (final text in texts) {
      // PQA08 checks tab text separately so a tab defect cannot block the
      // traversal of all General/Properties/Uses paragraphs.
      if (find
          .ancestor(of: find.byWidget(text), matching: find.byType(ChoiceChip))
          .evaluate()
          .isNotEmpty)
        continue;
      await readParagraph(tester, find.byWidget(text));
    }
  }

  for (final entry in identities) {
    testWidgets(
      'PQA01-${entry.$1} General identity, absences, provenance and tabs',
      (tester) async {
        final plant = catalog.findById(entry.$1)!;
        await mount(tester, plant);
        expect(find.text(entry.$2), findsNWidgets(2));
        expect(find.text(entry.$3), findsNWidgets(2));
        expect(
          tester
              .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'General'))
              .selected,
          isTrue,
        );
        expect(find.text('No disponible en fuente'), findsNWidgets(2));
        expect(find.text('No aplicable: ficha de planta'), findsOneWidget);
        expect(find.text('Partes registradas en fuente'), findsOneWidget);
        expect(
          find.text(
            plant.parts.map((p) => '${p.name} (${p.sourceCode})').join(', '),
          ),
          findsOneWidget,
        );
        for (final value in [
          catalog.provenance.sourceName,
          'CC0',
          '1',
          '24660351',
          'Duke-Source-CSV.zip (ID 43363335)',
          catalog.provenance.sourceUrl,
          'Fecha de inspección (no cobertura temporal)',
          '2026-10-01',
          catalog.provenance.recommendedCitation,
        ]) {
          expect(find.text(value), findsOneWidget);
        }
        final refs = <String, String>{};
        for (final use in plant.traditionalUses) {
          for (final ref in use.references) {
            refs[ref.id] = ref.citation;
          }
        }
        for (final ref in refs.entries) {
          expect(find.text(ref.key), findsOneWidget);
          expect(find.text(ref.value), findsOneWidget);
        }
        for (final invented in [
          'Mediterráneo',
          'Esencial',
          'Salvia rosmarinus',
          'Matricaria chamomilla',
          'Mentha piperita',
        ]) {
          expect(find.text(invented), findsNothing);
        }
        await tab(tester, 'Propiedades');
        expect(find.text(noProperties), findsOneWidget);
        await tab(tester, 'Usos');
        expect(
          find.text(plant.traditionalUses.isEmpty ? noUses : disclaimer),
          findsOneWidget,
        );
        await tab(tester, 'General');
        expect(find.text('Nombre común editorial'), findsOneWidget);
        await tab(tester, 'General');
        expect(find.text('Nombre común editorial'), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );

    testWidgets(
      'PQA02-${entry.$1} every eligible row has exact activity and resolved LONGREF',
      (tester) async {
        final plant = catalog.findById(entry.$1)!;
        await mount(tester, plant);
        await tab(tester, 'Usos');
        expect(plant.traditionalUses.length, entry.$4);
        final visible = scrollText(tester);
        if (entry.$4 == 0) {
          expect(visible.skip(visible.indexOf('Usos tradicionales')).toList(), [
            'Usos tradicionales',
            noUses,
          ]);
          expect(find.text('Registro tradicional'), findsNothing);
        } else {
          final expected = <String>['Registros tradicionales', disclaimer];
          for (final use in plant.traditionalUses) {
            expect(use.activity, use.source.selectors['ACTIVITY']);
            expect(use.source.table, 'ETHNOBOT');
            expected.addAll(['Registro tradicional', use.activity]);
            for (final ref in use.references) {
              expect(ref.source.table, 'REFERENCES');
              expect(ref.id, ref.source.selectors['REFERENCE']);
              expect(ref.citation, ref.source.selectors['LONGREF']);
              expected.addAll(['Fuente: ${ref.id}', ref.citation]);
            }
          }
          expect(
            visible.skip(visible.indexOf('Registros tradicionales')).toList(),
            expected,
          );
          expect(find.text('Registro tradicional'), findsNWidgets(entry.$4));
          await readParagraph(
            tester,
            find.text(plant.traditionalUses.last.references.last.citation).last,
          );
        }
        expect(
          find
              .bySemanticsLabel('Ver formulaciones relacionadas no disponible')
              .hitTestable(),
          findsOneWidget,
        );
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'PQA03 identity update resets General but same identity retains tab',
    (tester) async {
      await mount(tester, catalog.findById(544)!);
      await tab(tester, 'Usos');
      await mount(tester, catalog.findById(544)!);
      expect(find.text(disclaimer), findsOneWidget);
      await mount(tester, catalog.findById(619)!);
      expect(find.text('Nombre común editorial'), findsOneWidget);
      expect(find.text(noUses), findsNothing);
      expect(
        tester
            .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'General'))
            .selected,
        isTrue,
      );
      await tab(tester, 'Propiedades');
      await mount(tester, catalog.findById(401)!);
      expect(find.text('Nombre común editorial'), findsOneWidget);
      expect(find.text(noProperties), findsNothing);
    },
  );

  for (final scale in [1.0, 2.0]) {
    testWidgets('PQA08-$scale complete tab labels with no clipped glyphs', (
      tester,
    ) async {
      await mount(tester, catalog.findById(544)!, scale: scale);
      for (final label in ['General', 'Propiedades', 'Usos']) {
        await tab(tester, label);
        final target = find.descendant(
          of: find.widgetWithText(ChoiceChip, label),
          matching: find.text(label),
        );
        final paragraph = tester.renderObject<RenderParagraph>(target);
        print(
          'PQA08 scale=$scale label=$label size=${paragraph.size} softWrap=${paragraph.softWrap} overflow=${paragraph.overflow}',
        );
        await readParagraph(tester, target);
      }
    });

    testWidgets(
      'PQA04-$scale disabled semantics, no actions, persistent CTA, callbacks',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          var backs = 0, homes = 0;
          await mount(
            tester,
            catalog.findById(544)!,
            scale: scale,
            back: () => backs++,
            home: () => homes++,
          );
          for (final name in ['General', 'Propiedades', 'Usos']) {
            await tab(tester, name);
            for (final label in unavailable) {
              if (label == 'Favorito no disponible') await top(tester);
              final target = find.bySemanticsLabel(label);
              expect(target, findsOneWidget);
              final data = tester.getSemantics(target).getSemanticsData();
              expect(data.label, label);
              expect(data.flagsCollection.isButton, isTrue);
              expect(data.flagsCollection.isEnabled, Tristate.isFalse);
              expect(data.hasAction(SemanticsAction.tap), isFalse);
              await tester.ensureVisible(target);
              await tester.pumpAndSettle();
              await tester.tap(target);
              await tester.pumpAndSettle();
              expect(backs + homes, 0);
              await reach(tester, find.widgetWithText(ChoiceChip, name));
              expect(
                tester
                    .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, name))
                    .selected,
                isTrue,
              );
              expect(find.byType(Dialog), findsNothing);
              expect(find.byType(SnackBar), findsNothing);
              expect(find.byType(PlantPassportPage), findsOneWidget);
            }
            expect(
              find
                  .bySemanticsLabel(
                    'Ver formulaciones relacionadas no disponible',
                  )
                  .hitTestable(),
              findsOneWidget,
            );
          }
          final home = tester
              .getSemantics(find.bySemanticsLabel('Inicio'))
              .getSemanticsData();
          expect(home.flagsCollection.isSelected, Tristate.isTrue);
          expect(home.flagsCollection.isEnabled, Tristate.isTrue);
          expect(home.hasAction(SemanticsAction.tap), isTrue);
          expect(
            tester.widget<Text>(find.text('Inicio')).style!.color,
            const Color(0xFF236335),
          );
          await tester.tap(find.text('Inicio'));
          await top(tester);
          await tester.tap(find.byTooltip('Volver a Explorar'));
          expect(homes, 1);
          expect(backs, 1);
          expect(tester.takeException(), isNull);
        } finally {
          semantics.dispose();
        }
      },
    );

    for (final entry in identities) {
      testWidgets(
        'PQA05-${entry.$1}-$scale safe areas, 48dp and complete scroll reading all tabs',
        (tester) async {
          final semantics = tester.ensureSemantics();
          try {
            await mount(tester, catalog.findById(entry.$1)!, scale: scale);
            final viewport = tester.getRect(find.byType(CustomScrollView));
            expect(viewport.left, greaterThanOrEqualTo(insets.left));
            expect(viewport.top, greaterThanOrEqualTo(insets.top));
            expect(viewport.right, lessThanOrEqualTo(360 - insets.right));
            final back = find.widgetWithIcon(IconButton, Icons.chevron_left);
            expect(tester.getSize(back).shortestSide, greaterThanOrEqualTo(48));
            expect(tester.getRect(back).top, greaterThanOrEqualTo(insets.top));
            for (final label in ['Inicio', ...unavailable]) {
              final target = find.bySemanticsLabel(label);
              expect(
                tester.getSize(target).shortestSide,
                greaterThanOrEqualTo(48),
                reason: label,
              );
              if (label != 'Favorito no disponible') {
                final rect = tester.getRect(target);
                expect(rect.left, greaterThanOrEqualTo(insets.left));
                expect(rect.right, lessThanOrEqualTo(360 - insets.right));
                expect(rect.bottom, lessThanOrEqualTo(640 - insets.bottom));
                expect(target.hitTestable(), findsOneWidget);
              }
            }
            for (final name in ['General', 'Propiedades', 'Usos']) {
              await tab(tester, name);
              for (final chip in ['General', 'Propiedades', 'Usos']) {
                expect(
                  tester
                      .getSize(find.widgetWithText(ChoiceChip, chip))
                      .shortestSide,
                  greaterThanOrEqualTo(48),
                );
              }
              await readScroll(tester);
              expect(
                find
                    .bySemanticsLabel(
                      'Ver formulaciones relacionadas no disponible',
                    )
                    .hitTestable(),
                findsOneWidget,
              );
            }
            for (final text in [
              'Ver formulaciones relacionadas',
              'Inicio',
              'Favoritos',
              'Historial',
              'Perfil',
            ]) {
              final paragraph = tester.renderObject<RenderParagraph>(
                find.text(text),
              );
              expect(paragraph.didExceedMaxLines, isFalse);
              expect(paragraph.overflow, isNot(TextOverflow.ellipsis));
            }
            print(
              'PQA05 ID=${entry.$1} scale=$scale: all texts/lines traversed; footer persists',
            );
          } finally {
            semantics.dispose();
          }
        },
      );
    }

    testWidgets(
      'PQA06-$scale unusually long citation readable in scroll segments, absent parts explicit',
      (tester) async {
        final base = catalog.findById(544)!;
        final citation = List.generate(
          90,
          (i) => 'Segmento $i: referencia bibliográfica extensa verificable.',
        ).join(' ');
        final plant = Plant(
          usdaPlantId: base.usdaPlantId,
          editorialCommonName: base.editorialCommonName,
          sourceScientificName: base.sourceScientificName,
          identitySource: base.identitySource,
          traditionalUses: [
            TraditionalUse(
              activity: 'QA activity',
              source: SourceRecord(
                table: 'ETHNOBOT',
                selectors: const {'ACTIVITY': 'QA activity'},
              ),
              references: [
                PlantReference(
                  id: 'QA long reference',
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
        await mount(tester, plant, scale: scale);
        await reach(tester, find.text('No hay partes registradas en fuente'));
        expect(
          find.text('No hay partes registradas en fuente'),
          findsOneWidget,
        );
        await readParagraph(tester, find.text(citation));
        await tab(tester, 'Usos');
        expect(find.text(disclaimer), findsOneWidget);
        expect(find.text(citation), findsOneWidget);
        expect(
          tester.getSize(find.text(citation)).height,
          greaterThan(tester.getSize(find.byType(CustomScrollView)).height),
        );
        await readParagraph(tester, find.text(citation));
        expect(
          find
              .bySemanticsLabel('Ver formulaciones relacionadas no disponible')
              .hitTestable(),
          findsOneWidget,
        );
      },
    );
  }

  testWidgets(
    'PQA07 all five local passports and tabs with HTTP denied, provisional icons only',
    (tester) async {
      final previous = HttpOverrides.current;
      final deny = PassportDenyHttp();
      HttpOverrides.global = deny;
      addTearDown(() => HttpOverrides.global = previous);
      for (final entry in identities) {
        await mount(tester, catalog.findById(entry.$1)!);
        for (final name in ['General', 'Propiedades', 'Usos']) {
          await tab(tester, name);
          expect(find.byType(Image), findsNothing);
          await top(tester);
          expect(find.byIcon(Icons.local_florist), findsOneWidget);
        }
      }
      expect(deny.calls, 0);
      expect(tester.takeException(), isNull);
    },
  );
}
