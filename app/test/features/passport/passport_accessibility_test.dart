import 'dart:convert';
import 'dart:ui' as ui;
import 'dart:typed_data';

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
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

const _tabs = ['General', 'Propiedades', 'Usos'];

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

/// Scrolls the sheet from top to bottom in steps. At each step it checks that
/// nothing overflowed and that every visible "open" button is at least 48 dp.
/// Returns how many buttons it measured.
Future<int> _scrollThrough(WidgetTester tester) async {
  final scrollable = _sheet();
  var buttons = 0;
  for (var i = 0; i < 80; i++) {
    expect(tester.takeException(), isNull);
    for (final button in find.byType(TextButton).evaluate()) {
      final box = button.renderObject! as RenderBox;
      expect(box.size.height, greaterThanOrEqualTo(48));
      expect(box.size.width, greaterThanOrEqualTo(48));
      buttons++;
    }
    final position = tester.state<ScrollableState>(scrollable).position;
    if (position.pixels >= position.maxScrollExtent) break;
    await tester.drag(scrollable, const Offset(0, -300));
    await tester.pump();
  }
  expect(tester.takeException(), isNull);
  return buttons;
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
            'sin desbordes y con botones de 48 dp', (tester) async {
          await _pump(tester, consolidatedPlant(id), scale, tab);
          final measured = await _scrollThrough(tester);
          if (tab == 'General') expect(measured, greaterThan(0));
        });
      }

      testWidgets('$id: Fuentes y pie de imagen visibles al ${scale * 100}%', (
        tester,
      ) async {
        final plant = consolidatedPlant(id);
        await _pump(tester, plant, scale, 'General');
        // Image footer is in the header, at the top.
        expect(find.text('Licencia: ${plant.image!.license}'), findsOneWidget);
        expect(find.text(PassportTexts.imageFilePageLabel), findsOneWidget);
        expect(find.text(PassportTexts.openLink), findsWidgets);
        await _scrollTo(tester, find.text(PassportTexts.sourcesTitle));
        expect(find.text(PassportTexts.sourcesTitle), findsOneWidget);
        expect(find.text(plant.credits.first.name), findsWidgets);
        expect(tester.takeException(), isNull);
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

  testWidgets('El botón Abrir en el navegador expone semántica de botón', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await _pump(
      tester,
      consolidatedPlant('lavandula-angustifolia'),
      2,
      'General',
    );
    final button = find.widgetWithText(TextButton, PassportTexts.openLink);
    expect(button, findsWidgets);
    final data = tester.getSemantics(button.first).getSemanticsData();
    expect(data.flagsCollection.isButton, isTrue);
    expect(data.hasAction(ui.SemanticsAction.tap), isTrue);
    handle.dispose();
  });
}
