import 'dart:ui' as ui;

import 'package:boticario_ai/features/passport/presentation/passport_link.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../support/fake_url_launcher.dart';
import 'passport_test_support.dart';

Future<void> _pump(
  WidgetTester tester,
  String? url, {
  String text = 'CC0',
  String prefix = '',
}) => tester.pumpWidget(
  MaterialApp(
    home: Scaffold(
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PassportInlineLink(
            text: text,
            url: url,
            prefix: prefix,
            destination: PassportTexts.licenseTextDestination,
          ),
        ],
      ),
    ),
  ),
);

/// Replaces the platform clipboard; returns what was copied.
List<String?> _mockClipboard(WidgetTester tester, {bool fails = false}) {
  final copied = <String?>[];
  tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
    SystemChannels.platform,
    (call) async {
      if (call.method == 'Clipboard.setData') {
        if (fails) throw PlatformException(code: 'sin portapapeles');
        copied.add((call.arguments as Map)['text'] as String?);
      }
      return null;
    },
  );
  addTearDown(
    () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      null,
    ),
  );
  return copied;
}

void main() {
  late FakeUrlLauncher launcher;

  void install(FakeUrlLauncher l) {
    launcher = l;
    UrlLauncherPlatform.instance = l;
  }

  setUp(() => install(FakeUrlLauncher()));

  testWidgets('abre una URL https en el navegador externo', (tester) async {
    await _pump(tester, 'https://creativecommons.org/publicdomain/zero/1.0/');
    await tester.tap(find.text('CC0'));
    await tester.pump();
    expect(launcher.launched, [
      'https://creativecommons.org/publicdomain/zero/1.0/',
    ]);
    expect(launcher.modes, [PreferredLaunchMode.externalApplication]);
    expect(find.byType(SnackBar), findsNothing);
  });

  testWidgets('el texto enlazado va subrayado y el prefijo no', (tester) async {
    await _pump(tester, 'https://example.org/a', prefix: 'Licencia: ');
    final rich = tester.widget<RichText>(
      find.descendant(
        of: find.byType(PassportInlineLink),
        matching: find.byType(RichText),
      ),
    );
    final spans = <TextSpan>[];
    rich.text.visitChildren((span) {
      if (span is TextSpan && span.text != null) spans.add(span);
      return true;
    });
    final prefixSpan = spans.firstWhere((s) => s.text == 'Licencia: ');
    final linkSpan = spans.firstWhere((s) => s.text == 'CC0');
    expect(linkSpan.style?.decoration, TextDecoration.underline);
    expect(prefixSpan.style?.decoration, isNot(TextDecoration.underline));
  });

  testWidgets('pulsación larga copia la URL, avisa y no abre', (tester) async {
    final copied = _mockClipboard(tester);
    await _pump(tester, '  https://example.org/a%20b  ');
    await tester.longPress(find.text('CC0'));
    await tester.pump();
    expect(copied, ['https://example.org/a%20b']);
    expect(find.text(PassportTexts.linkCopied), findsOneWidget);
    expect(launcher.launched, isEmpty);
  });

  testWidgets('si falla el portapapeles no hay cierre inesperado', (
    tester,
  ) async {
    _mockClipboard(tester, fails: true);
    await _pump(tester, 'https://example.org/a');
    await tester.longPress(find.text('CC0'));
    await tester.pump();
    expect(tester.takeException(), isNull);
    expect(find.text(PassportTexts.linkCopied), findsNothing);
  });

  testWidgets('una URL que no es https es texto plano sin acciones', (
    tester,
  ) async {
    final copied = _mockClipboard(tester);
    for (final bad in [
      'http://example.org/a',
      'javascript:alert(1)',
      'file:///etc/passwd',
      'https://',
      '',
      null,
    ]) {
      await _pump(tester, bad);
      expect(find.text('CC0'), findsOneWidget, reason: '$bad');
      expect(find.byType(InkWell), findsNothing, reason: '$bad');
      await tester.tap(find.text('CC0'));
      await tester.longPress(find.text('CC0'));
      await tester.pump();
    }
    expect(launcher.launched, isEmpty);
    expect(copied, isEmpty);
    expect(find.byType(SnackBar), findsNothing);
  });

  testWidgets('el texto plano no tiene subrayado ni semántica de enlace', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await _pump(tester, null);
    final rich = tester.widget<RichText>(
      find.descendant(
        of: find.byType(PassportInlineLink),
        matching: find.byType(RichText),
      ),
    );
    expect(rich.text.style?.decoration, isNot(TextDecoration.underline));
    final data = tester.getSemantics(find.text('CC0')).getSemanticsData();
    expect(data.flagsCollection.isLink, isFalse);
    handle.dispose();
  });

  testWidgets('si no se puede abrir no falla y avisa', (tester) async {
    for (final l in [
      FakeUrlLauncher(result: false),
      FakeUrlLauncher(throws: true),
    ]) {
      install(l);
      await _pump(tester, 'https://example.org/a');
      await tester.tap(find.text('CC0'));
      await tester.pump();
      expect(l.launched, ['https://example.org/a']);
      expect(tester.takeException(), isNull);
      expect(find.text(PassportTexts.linkNotOpened), findsOneWidget);
      expect(find.text('https://example.org/a'), findsNothing);
    }
  });

  testWidgets('la URL no se muestra como texto', (tester) async {
    const url = 'https://commons.wikimedia.org/wiki/File:K%C3%B6hler.jpg';
    await _pump(tester, url);
    expect(find.textContaining('https'), findsNothing);
    expect(find.textContaining('wikimedia'), findsNothing);
    expect(find.byType(SelectableText), findsNothing);
    expect(find.byType(TextButton), findsNothing);
    // And it opens as given, without decoding.
    await tester.tap(find.text('CC0'));
    await tester.pump();
    expect(launcher.launched, [url]);
  });

  testWidgets('canOpen solo acepta https con host', (tester) async {
    expect(PassportInlineLink.canOpen('https://example.org'), isTrue);
    expect(PassportInlineLink.canOpen(' https://example.org/a '), isTrue);
    for (final bad in [
      'http://example.org',
      'https://',
      'ftp://a.b',
      '',
      null,
    ]) {
      expect(PassportInlineLink.canOpen(bad), isFalse, reason: '$bad');
    }
  });

  group('semántica y áreas de toque', () {
    testWidgets('se anuncia como enlace con texto, destino y gestos', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await _pump(tester, 'https://example.org/a', prefix: 'Licencia: ');
      final node = tester.getSemantics(find.bySemanticsLabel('Licencia: CC0'));
      final data = node.getSemanticsData();
      expect(data.flagsCollection.isLink, isTrue);
      expect(data.label, 'Licencia: CC0');
      expect(data.hint, PassportTexts.linkHint('el texto de la licencia'));
      expect(data.hint, contains('copiar'));
      expect(data.hasAction(ui.SemanticsAction.tap), isTrue);
      expect(data.hasAction(ui.SemanticsAction.longPress), isTrue);
      // The URL is not read, and the visible text is not read twice.
      expect(data.label, isNot(contains('https')));
      expect(data.hint, isNot(contains('https')));
      expect(find.bySemanticsLabel(RegExp('CC0')), findsOneWidget);
      handle.dispose();
    });

    testWidgets('un nombre corto mide al menos 48 dp de alto y de ancho', (
      tester,
    ) async {
      await _pump(tester, 'https://example.org/a', text: 'A');
      final size = tester.getSize(find.byType(InkWell));
      expect(size.height, greaterThanOrEqualTo(48));
      expect(size.width, greaterThanOrEqualTo(48));
    });

    testWidgets('cumple las guías de toque y de etiquetas', (tester) async {
      final handle = tester.ensureSemantics();
      await _pump(tester, 'https://example.org/a', prefix: 'Licencia: ');
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      handle.dispose();
    });
  });

  testWidgets('un enlace de licencia de Fuentes se abre', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    final url = plant.image!.licenseUrl!;
    await showPassport(tester, plant, tab: 'Fuentes');
    final link = find.widgetWithText(
      PassportInlineLink,
      'Licencia: ${plant.image!.license}',
    );
    await tester.ensureVisible(link);
    await tester.pump();
    await tester.tap(link);
    await tester.pump();
    expect(launcher.launched, [url]);
  });
}
