import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui' as ui;
import 'dart:typed_data';

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_header.dart';
import 'package:boticario_ai/features/passport/presentation/passport_link.dart';
import 'package:boticario_ai/features/passport/presentation/passport_style.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../support/fake_url_launcher.dart';
import 'passport_test_support.dart';

final Uint8List _png = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
  '60e6kgAAAABJRU5ErkJggg==',
);

double _luminance(Color c) {
  double channel(double v) =>
      v <= 0.03928 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
  return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
}

double _contrast(Color a, Color b) {
  final la = _luminance(a);
  final lb = _luminance(b);
  return (math.max(la, lb) + 0.05) / (math.min(la, lb) + 0.05);
}

const _tabs = ['General', 'Propiedades', 'Usos', 'Fuentes'];

/// The vertical scrollable of the sheet (the selectable URLs have their own).
Finder _sheet() => find
    .descendant(
      of: find.byType(CustomScrollView),
      matching: find.byType(Scrollable),
    )
    .first;

/// Scrolls until [finder] is built and then inside the visible viewport (the
/// first step alone can leave it in the cache area, under the bottom bar).
Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(finder, 200, scrollable: _sheet());
  await tester.ensureVisible(finder);
  await tester.pump();
}

/// Pumps the passport at 360x640 dp with the given text [scale] and the tab.
Future<void> _pump(
  WidgetTester tester,
  Plant plant,
  double scale,
  String tab,
) async {
  tester.view.physicalSize = const Size(360, 640);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(const SizedBox.shrink());
  await tester.pumpWidget(
    MaterialApp(
      theme: buildBoticarioTheme(),
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context)
            .copyWith(textScaler: TextScaler.linear(scale)),
        child: child!,
      ),
      home: PlantPassportPage(
        plant: plant,
        onBack: () {},
        onHome: () {},
        imageProviderFor: (_) => MemoryImage(_png),
      ),
    ),
  );
  await tester.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 200)),
  );
  await tester.pump();
  if (tab != 'General') {
    await _scrollTo(tester, find.text(tab));
    await tester.tap(find.text(tab));
    await tester.pumpAndSettle();
  }
}

/// Scrolls the sheet from top to bottom in steps and checks at each step that
/// nothing overflowed and that the tabs keep their 48 dp (links are inline in
/// the text and have no minimum). Returns how many link spans it saw.
Future<int> _scrollThrough(WidgetTester tester) async {
  final scrollable = _sheet();
  var links = 0;
  for (var i = 0; i < 80; i++) {
    expect(tester.takeException(), isNull);
    for (final text in find.byType(PassportLinkedText).evaluate()) {
      links += linkSpansOf(tester, find.byWidget(text.widget)).length;
    }
    for (final chip in find.byType(ChoiceChip).evaluate()) {
      final box = chip.renderObject! as RenderBox;
      expect(box.size.height, greaterThanOrEqualTo(48));
    }
    final position = tester.state<ScrollableState>(scrollable).position;
    if (position.pixels >= position.maxScrollExtent) break;
    await tester.drag(scrollable, const Offset(0, -300));
    await tester.pump();
  }
  expect(tester.takeException(), isNull);
  return links;
}

void main() {
  setUp(() => UrlLauncherPlatform.instance = FakeUrlLauncher());

  for (final scale in [1.0, 2.0]) {
    for (final id in [
      'lavandula-angustifolia',
      'blighia-sapida',
      'eucalyptus-globulus',
    ]) {
      for (final tab in _tabs) {
        testWidgets('$id, $tab a 360x640 con texto al ${scale * 100}%: '
            'sin desbordes y con pestañas de 48 dp', (tester) async {
          await _pump(tester, consolidatedPlant(id), scale, tab);
          final measured = await _scrollThrough(tester);
          // The photo footer is always in the header; `Fuentes` has more.
          if (tab == 'General' || tab == 'Fuentes') {
            expect(measured, greaterThan(0));
          }
        });
      }

      testWidgets(
        '$id: pie de imagen sin truncar y sin URL al ${scale * 100}%',
        (tester) async {
          final plant = consolidatedPlant(id);
          final image = plant.image!;
          await _pump(tester, plant, scale, 'General');
          final footer = find.descendant(
            of: find.byType(PassportHeader),
            matching: find.byType(PassportLinkedText),
          );
          final text = tester
              .widget<Text>(
                find.descendant(of: footer, matching: find.byType(Text)),
              )
              .textSpan!
              .toPlainText(includeSemanticsLabels: false);
          expect(
            text,
            'Foto: ${image.author ?? PassportTexts.commonsName} · '
            '${image.license}',
          );
          expect(text, isNot(contains('http')));
          final rich = tester.widget<RichText>(
            find.descendant(of: footer, matching: find.byType(RichText)),
          );
          expect(rich.maxLines, isNull);
          expect(rich.overflow, isNot(TextOverflow.ellipsis));
          expect(tester.takeException(), isNull);
        },
      );

      testWidgets(
        '$id: pestaña Fuentes completa y legible al ${scale * 100}%',
        (tester) async {
          final plant = consolidatedPlant(id);
          await _pump(tester, plant, scale, 'Fuentes');
          expect(find.text(PassportTexts.sourcesIntro), findsOneWidget);
          await _scrollTo(tester, plainText(plant.credits.first.name));
          expect(plainText(plant.credits.first.name), findsOneWidget);
          await _scrollTo(tester, find.text(PassportTexts.imageSourceTitle));
          await _scrollTo(tester, plainText(PassportTexts.imageFileLinkLabel));
          for (final text in tester.widgetList<RichText>(
            find.byType(RichText),
          )) {
            expect(text.maxLines, isNull);
            expect(text.overflow, isNot(TextOverflow.ellipsis));
          }
          expect(tester.takeException(), isNull);
        },
      );

      testWidgets('$id: las cuatro pestañas miden 48 dp y tienen etiqueta '
          'al ${scale * 100}%', (tester) async {
        final handle = tester.ensureSemantics();
        await _pump(tester, consolidatedPlant(id), scale, 'General');
        for (final tab in _tabs) {
          final chip = find.widgetWithText(ChoiceChip, tab);
          await _scrollTo(tester, chip);
          expect(tester.getRect(chip).height, greaterThanOrEqualTo(48));
          expect(tester.getSemantics(chip).label, tab);
        }
        handle.dispose();
      });
    }

    for (final entry in {
      'blighia-sapida': PassportTexts.levelHigh,
      'lavandula-angustifolia': PassportTexts.levelMedium,
    }.entries) {
      testWidgets(
        'Nivel de precauciones sin depender del color: ${entry.key} al '
        '${scale * 100}%',
        (tester) async {
          await _pump(
            tester,
            consolidatedPlant(entry.key),
            scale,
            'Propiedades',
          );
          await _scrollTo(tester, find.text(PassportTexts.safetyLevelLabel));
          expect(find.text(PassportTexts.safetyLevelLabel), findsOneWidget);
          expect(find.text(entry.value), findsOneWidget);
          expect(tester.takeException(), isNull);
        },
      );
    }

    testWidgets('eucalipto sin nivel: no hay etiqueta de nivel al '
        '${scale * 100}%', (tester) async {
      await _pump(
        tester,
        consolidatedPlant('eucalyptus-globulus'),
        scale,
        'Propiedades',
      );
      await _scrollTo(tester, find.text(PassportTexts.safetyTitle));
      expect(find.text(PassportTexts.safetyLevelLabel), findsNothing);
    });
  }

  testWidgets(
    'Imagen descrita: nodo de imagen con descripción y sin duplicar',
    (tester) async {
      final handle = tester.ensureSemantics();
      final plant = consolidatedPlant('lavandula-angustifolia');
      await _pump(tester, plant, 2, 'General');
      final finder = find.bySemanticsLabel(
        PassportTexts.imageDescription(plant.primaryName),
      );
      expect(finder, findsOneWidget);
      final data = tester.getSemantics(finder).getSemanticsData();
      expect(data.flagsCollection.isImage, isTrue);
      expect(tester.getSize(finder).height, greaterThan(0));
      handle.dispose();
    },
  );

  for (final scale in [1.0, 2.0]) {
    testWidgets('Los enlaces del pie y de Fuentes se anuncian como enlace con '
        'destino al ${scale * 100}%', (tester) async {
      final handle = tester.ensureSemantics();
      final plant = consolidatedPlant('eucalyptus-globulus');
      final image = plant.image!;
      await _pump(tester, plant, scale, 'General');
      // Footer: author -> file page, license -> license text.
      await _scrollTo(
        tester,
        find.descendant(
          of: find.byType(PassportHeader),
          matching: find.byType(PassportLinkedText),
        ),
      );
      // Footer: author -> file page, license -> license text.
      await _scrollTo(
        tester,
        find.descendant(
          of: find.byType(PassportHeader),
          matching: find.byType(PassportLinkedText),
        ),
      );
      final announced = {
        for (final data in linkSemantics(tester)) data.label: data,
      };
      for (final entry in {
        image.author ?? PassportTexts.commonsName:
            PassportTexts.imageFileDestination,
        if (image.licenseUrl != null)
          image.license: PassportTexts.licenseTextDestination,
      }.entries) {
        final data =
            announced[PassportTexts.linkSemantics(entry.key, entry.value)];
        expect(data, isNotNull, reason: '${entry.key}: ${announced.keys}');
        expect(data!.flagsCollection.isLink, isTrue);
        expect(data.hasAction(ui.SemanticsAction.tap), isTrue);
      }
      // Sources tab: credit name -> source page, license -> license text.
      await _scrollTo(tester, find.text('Fuentes'));
      await tester.tap(find.text('Fuentes'));
      await tester.pumpAndSettle();
      final credit = plant.credits.firstWhere(
        (c) => c.url != null && c.licenseUrl != null,
      );
      await _scrollTo(tester, plainText(credit.name));
      final labels = [for (final data in linkSemantics(tester)) data.label];
      expect(
        labels,
        contains(
          PassportTexts.linkSemantics(
            credit.name,
            PassportTexts.sourcePageDestination,
          ),
        ),
      );
      await _scrollTo(tester, plainText('Licencia: ${credit.license}'));
      expect(
        [for (final data in linkSemantics(tester)) data.label],
        contains(
          PassportTexts.linkSemantics(
            credit.license,
            PassportTexts.licenseTextDestination,
          ),
        ),
      );
      // No URL is announced.
      for (final label in labels) {
        expect(label, isNot(contains('http')));
      }
      handle.dispose();
    });

    testWidgets('Los enlaces se distinguen por el subrayado, no solo por el '
        'color, al ${scale * 100}%', (tester) async {
      final plant = consolidatedPlant('eucalyptus-globulus');
      await _pump(tester, plant, scale, 'Fuentes');
      await _scrollTo(tester, plainText(plant.credits.first.name));
      var links = 0;
      for (final text in find.byType(PassportLinkedText).evaluate()) {
        for (final span in linkSpansOf(tester, find.byWidget(text.widget))) {
          links++;
          expect(span.style?.decoration, TextDecoration.underline);
        }
      }
      expect(links, greaterThan(0));
    });

    testWidgets('Guía de etiquetas en el pie y en Fuentes, y pestañas de 48 dp '
        'al ${scale * 100}%', (tester) async {
      final handle = tester.ensureSemantics();
      final plant = consolidatedPlant('eucalyptus-globulus');
      await _pump(tester, plant, scale, 'General');
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      await _scrollTo(tester, find.text('Fuentes'));
      await tester.tap(find.text('Fuentes'));
      await tester.pumpAndSettle();
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      handle.dispose();
    });
  }

  for (final scale in [1.0, 2.0]) {
    testWidgets('Control de citas accesible, plegado y desplegado, al '
        '${scale * 100}%', (tester) async {
      final handle = tester.ensureSemantics();
      const activity =
          'Actividad tradicional con un nombre muy largo que ocupa varias '
          'líneas en una pantalla estrecha de 360 dp';
      final plant = Plant(
        id: 'planta-sintetica',
        scientificName: 'Planta sintetica',
        family: null,
        names: const [],
        parts: const [],
        uses: const [],
        useGroups: [
          UseGroup(
            activity: activity,
            activitySource: null,
            count: 12,
            countries: const ['China', 'Otros lugares', 'Trinidad y Tobago'],
            references: [
              for (var i = 1; i <= 5; i++)
                CitedReference(
                  id: i == 5 ? null : 'ref:$i',
                  citation: i == 5
                      ? 'Clave larga $i (sin resolver)'
                      : 'Cita sintetica $i, con un título bastante largo '
                            'para que ocupe varias líneas.',
                  resolved: i != 5,
                ),
            ],
          ),
        ],
      );
      await _pump(tester, plant, scale, 'Usos');
      final control = find.widgetWithText(TextButton, 'Ver 5 citas');
      await _scrollTo(tester, control);

      final closedData = tester.getSemantics(control).getSemanticsData();
      expect(closedData.label, 'Ver 5 citas de $activity');
      expect(closedData.flagsCollection.isButton, isTrue);
      expect(closedData.flagsCollection.isExpanded, ui.Tristate.isFalse);
      expect(tester.getSize(control).height, greaterThanOrEqualTo(48));
      expect(tester.getSize(control).width, greaterThanOrEqualTo(48));
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));

      await tester.tap(control);
      await tester.pumpAndSettle();
      final opened = find.widgetWithText(TextButton, 'Ocultar citas');
      await _scrollTo(tester, opened);
      expect(tester.getSemantics(opened).label, 'Ocultar citas de $activity');
      final openData = tester.getSemantics(opened).getSemanticsData();
      expect(openData.flagsCollection.isButton, isTrue);
      expect(openData.flagsCollection.isExpanded, ui.Tristate.isTrue);
      expect(tester.getSize(opened).height, greaterThanOrEqualTo(48));
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));

      // Nothing is truncated: data line, control and citations.
      for (final text in [
        'Cita sintetica 1, con un título bastante largo para que ocupe '
            'varias líneas.',
        'Clave larga 5 (sin resolver)',
        activity,
        'Lugares: China, Otros lugares, Trinidad y Tobago',
        'Ocultar citas',
      ]) {
        await _scrollTo(tester, find.text(text));
        final widget = tester.widget<Text>(find.text(text));
        expect(widget.maxLines, isNull, reason: text);
        expect(widget.overflow, isNot(TextOverflow.ellipsis), reason: text);
        final rect = tester.getRect(find.text(text));
        expect(rect.left, greaterThanOrEqualTo(0));
        expect(rect.right, lessThanOrEqualTo(360));
      }
      expect(tester.takeException(), isNull);
      handle.dispose();
    });
  }

  for (final scale in [1.0, 2.0]) {
    testWidgets('Explicación del término legible, en orden y con enlace '
        'accionable al ${scale * 100}%', (tester) async {
      final handle = tester.ensureSemantics();
      final launcher = FakeUrlLauncher();
      UrlLauncherPlatform.instance = launcher;
      const text =
          'Que aumenta o facilita la producción y excreción de orina, con un '
          'texto sintético bastante largo para ocupar varias líneas.';
      const row = 'Diurético: «$text» (adaptado de Wikipedia)';
      final plant = Plant(
        id: 'planta-sintetica',
        scientificName: 'Planta sintetica',
        family: null,
        names: const [],
        parts: const [],
        uses: const [],
        useGroups: [
          UseGroup(
            activity: 'Diurético',
            activitySource: null,
            count: 12,
            countries: const ['China', 'Otros lugares', 'Trinidad y Tobago'],
            references: const [],
            glossary: const GlossaryEntry(
              term: 'Diurético',
              text: text,
              sourceName: 'Wikipedia',
              url: 'https://es.wikipedia.org/w/index.php?title=D&oldid=1',
              adapted: true,
            ),
          ),
        ],
      );
      await _pump(tester, plant, scale, 'Usos');
      const data = 'Lugares: China, Otros lugares, Trinidad y Tobago';
      final label = find.text(PassportTexts.glossaryLabel);
      final line = plainText(row);
      for (final finder in [
        find.text('Diurético'),
        label,
        line,
        find.text(data),
      ]) {
        await _scrollTo(tester, finder);
        final rect = tester.getRect(finder);
        expect(rect.left, greaterThanOrEqualTo(0));
        expect(rect.right, lessThanOrEqualTo(360));
      }
      for (final widget in [
        tester.widget<Text>(label),
        tester.widget<Text>(line),
      ]) {
        expect(widget.maxLines, isNull);
        expect(widget.overflow, isNot(TextOverflow.ellipsis));
      }
      // Reading order: title, meaning, data.
      expect(
        tester.getTopLeft(find.text('Diurético')).dy,
        lessThan(tester.getTopLeft(label).dy),
      );
      expect(tester.getTopLeft(label).dy, lessThan(tester.getTopLeft(line).dy));
      expect(
        tester.getTopLeft(line).dy,
        lessThan(tester.getTopLeft(find.text(data)).dy),
      );
      // The source is announced as a link with its destination, never a URL.
      final announced = [for (final d in linkSemantics(tester)) d.label];
      expect(
        announced,
        contains(
          PassportTexts.linkSemantics(
            'Wikipedia',
            PassportTexts.glossarySourceDestination,
          ),
        ),
      );
      for (final d in linkSemantics(tester)) {
        expect(d.label, isNot(contains('http')));
      }
      // Secondary text keeps 4.5:1 on the background.
      expect(
        _contrast(passportMuted, passportBackground),
        greaterThanOrEqualTo(4.5),
      );
      expect(tester.takeException(), isNull);
      handle.dispose();
    });
  }
}
