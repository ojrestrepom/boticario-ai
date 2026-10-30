import 'dart:convert';
import 'dart:typed_data';

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/passport/presentation/passport_header.dart';
import 'package:boticario_ai/features/passport/presentation/passport_link.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../support/fake_url_launcher.dart';
import 'passport_test_support.dart';

/// DEF-01: with the real photo the header is tall (200 dp image plus the full
/// attribution footer). Tabs must stay reachable and visible after a switch.
final Uint8List _png = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
  '60e6kgAAAABJRU5ErkJggg==',
);

const _tabs = ['General', 'Propiedades', 'Usos', 'Fuentes'];
const _firstContent = {
  'General': 'Tipo de aceite',
  'Propiedades': 'Objetivos registrados por la EMA',
  'Usos': PassportTexts.usesNoticeLabel,
  'Fuentes': PassportTexts.sourcesIntro,
};

Finder _sheet() => find
    .descendant(
      of: find.byType(CustomScrollView),
      matching: find.byType(Scrollable),
    )
    .first;

Finder _chip(String tab) => find.widgetWithText(ChoiceChip, tab);

Future<void> _pump(WidgetTester tester, double scale) async {
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
        plant: consolidatedPlant('lavandula-angustifolia'),
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
}

/// Whether [finder] is built and fully inside the sheet's viewport.
bool _inViewport(WidgetTester tester, Finder finder) {
  if (finder.evaluate().isEmpty) return false;
  final viewport = tester.getRect(_sheet());
  final rect = tester.getRect(finder.first);
  return rect.top >= viewport.top - 0.5 && rect.bottom <= viewport.bottom + 0.5;
}

void main() {
  late FakeUrlLauncher launcher;

  setUp(() {
    launcher = FakeUrlLauncher();
    UrlLauncherPlatform.instance = launcher;
  });

  testWidgets('Con imagen, el pie «Foto: autor · licencia» tiene enlaces '
      'abribles y sin URL visible', (tester) async {
    await _pump(tester, 1);
    final plant = consolidatedPlant('lavandula-angustifolia');
    final image = plant.image!;
    final footer = find.descendant(
      of: find.byType(PassportHeader),
      matching: find.byType(PassportLinkedText),
    );
    expect(
      tester
          .widget<Text>(
            find.descendant(of: footer, matching: find.byType(Text)),
          )
          .textSpan!
          .toPlainText(includeSemanticsLabels: false),
      'Foto: ${image.author} · ${image.license}',
    );
    expect(find.textContaining('https'), findsNothing);
    await tapSpan(tester, footer, image.author!);
    expect(launcher.launched, [image.pageUrl]);
    expect(tester.takeException(), isNull);
  });

  for (final scale in [1.0, 2.0]) {
    for (final tab in _tabs.skip(1)) {
      testWidgets('Cambiar a $tab con la cabecera alta al ${scale * 100}%: '
          'pestañas y contenido a la vista', (tester) async {
        await _pump(tester, scale);
        await tester.scrollUntilVisible(_chip(tab), 100, scrollable: _sheet());
        await tester.ensureVisible(_chip(tab));
        await tester.pump();
        await tester.tap(_chip(tab));
        await tester.pumpAndSettle();

        for (final other in _tabs) {
          expect(
            _inViewport(tester, _chip(other)),
            isTrue,
            reason: 'pestaña $other tras elegir $tab',
          );
        }
        expect(tester.widget<ChoiceChip>(_chip(tab)).selected, isTrue);
        // The start of the content is reachable by scrolling down only.
        final start = find.text(_firstContent[tab]!);
        await tester.scrollUntilVisible(start, 100, scrollable: _sheet());
        expect(start, findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('Cambios sucesivos de pestaña al ${scale * 100}%: siempre a '
        'la vista, sin desbordes', (tester) async {
      await _pump(tester, scale);
      for (final tab in [
        'Usos',
        'Fuentes',
        'Propiedades',
        'General',
        'Fuentes',
        'Usos',
      ]) {
        await tester.scrollUntilVisible(_chip(tab), 100, scrollable: _sheet());
        await tester.ensureVisible(_chip(tab));
        await tester.pump();
        await tester.tap(_chip(tab));
        await tester.pumpAndSettle();
        for (final other in _tabs) {
          expect(_inViewport(tester, _chip(other)), isTrue, reason: other);
        }
        expect(tester.takeException(), isNull);
      }
    });

    testWidgets('De Usos (larga) a Fuentes (corta) al ${scale * 100}%: la hoja '
        'no queda en blanco y las cuatro pestañas siguen a la vista', (
      tester,
    ) async {
      await _pump(tester, scale);
      await tester.scrollUntilVisible(_chip('Usos'), 100, scrollable: _sheet());
      await tester.ensureVisible(_chip('Usos'));
      await tester.pump();
      await tester.tap(_chip('Usos'));
      await tester.pumpAndSettle();
      // Go to the end of the long tab, then back up to the chips.
      final position = tester.state<ScrollableState>(_sheet()).position;
      position.jumpTo(position.maxScrollExtent);
      await tester.pumpAndSettle();
      expect(position.pixels, greaterThan(0));
      for (var i = 0; i < 80 && !_inViewport(tester, _chip('Fuentes')); i++) {
        await tester.drag(_sheet(), const Offset(0, 120));
        await tester.pump();
      }
      await tester.ensureVisible(_chip('Fuentes'));
      await tester.pump();
      await tester.tap(_chip('Fuentes'));
      await tester.pumpAndSettle();

      for (final other in _tabs) {
        expect(_inViewport(tester, _chip(other)), isTrue, reason: other);
      }
      final intro = find.text(PassportTexts.sourcesIntro);
      expect(intro, findsOneWidget);
      final viewport = tester.getRect(_sheet());
      expect(tester.getRect(intro).top, lessThan(viewport.bottom));
      expect(tester.getRect(intro).top, greaterThan(viewport.top));
      expect(tester.takeException(), isNull);
    });

    testWidgets('Recorrer las cuatro pestañas en ambos sentidos al '
        '${scale * 100}%', (tester) async {
      await _pump(tester, scale);
      for (final tab in [..._tabs, ..._tabs.reversed]) {
        await tester.scrollUntilVisible(_chip(tab), 100, scrollable: _sheet());
        await tester.ensureVisible(_chip(tab));
        await tester.pump();
        await tester.tap(_chip(tab));
        await tester.pumpAndSettle();
        expect(tester.widget<ChoiceChip>(_chip(tab)).selected, isTrue);
        for (final other in _tabs) {
          expect(_inViewport(tester, _chip(other)), isTrue, reason: other);
        }
        final start = find.text(_firstContent[tab]!);
        await tester.scrollUntilVisible(start, 100, scrollable: _sheet());
        expect(start, findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    });
  }
}
