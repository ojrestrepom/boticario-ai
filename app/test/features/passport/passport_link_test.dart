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
          PassportLinkedText(
            parts: [
              if (prefix.isNotEmpty) PassportLinkPart(prefix),
              PassportLinkPart(
                text,
                url: url,
                destination: PassportTexts.licenseTextDestination,
              ),
            ],
          ),
        ],
      ),
    ),
  ),
);

final _root = find.byType(PassportLinkedText);

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

  testWidgets('un toque abre una URL https en el navegador externo', (
    tester,
  ) async {
    _mockClipboard(tester);
    await _pump(tester, 'https://creativecommons.org/publicdomain/zero/1.0/');
    await tapSpan(tester, _root, 'CC0');
    expect(launcher.launched, [
      'https://creativecommons.org/publicdomain/zero/1.0/',
    ]);
    expect(launcher.modes, [PreferredLaunchMode.externalApplication]);
    expect(find.byType(SnackBar), findsNothing);
  });

  testWidgets('solo el texto enlazado va subrayado y es un enlace', (
    tester,
  ) async {
    await _pump(tester, 'https://example.org/a', prefix: 'Licencia: ');
    final links = linkSpansOf(tester, _root);
    expect(links.map((s) => s.text), ['CC0']);
    expect(links.single.style?.decoration, TextDecoration.underline);
    final prefix = textSpansOf(
      tester,
      _root,
    ).firstWhere((s) => s.text == 'Licencia: ');
    expect(prefix.recognizer, isNull);
    expect(prefix.style?.decoration, isNot(TextDecoration.underline));
  });

  testWidgets('pulsación larga copia la URL, avisa y no abre', (tester) async {
    final copied = _mockClipboard(tester);
    await _pump(tester, '  https://example.org/a%20b  ');
    await longPressSpan(tester, _root, 'CC0');
    expect(copied, ['https://example.org/a%20b']);
    expect(find.text(PassportTexts.linkCopied), findsOneWidget);
    expect(launcher.launched, isEmpty);
  });

  testWidgets('si falla el portapapeles no hay cierre inesperado', (
    tester,
  ) async {
    _mockClipboard(tester, fails: true);
    await _pump(tester, 'https://example.org/a');
    await longPressSpan(tester, _root, 'CC0');
    expect(tester.takeException(), isNull);
    expect(find.text(PassportTexts.linkCopied), findsNothing);
    expect(launcher.launched, isEmpty);
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
      expect(linkSpansOf(tester, _root), isEmpty, reason: '$bad');
      await tapSpan(tester, _root, 'CC0');
      await longPressSpan(tester, _root, 'CC0');
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
    expect(
      textSpansOf(tester, _root).single.style?.decoration,
      isNot(TextDecoration.underline),
    );
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
      await tapSpan(tester, _root, 'CC0');
      expect(l.launched, ['https://example.org/a']);
      expect(tester.takeException(), isNull);
      expect(find.text(PassportTexts.linkNotOpened), findsOneWidget);
      expect(find.textContaining('https://example.org/a'), findsNothing);
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
    await tapSpan(tester, _root, 'CC0');
    expect(launcher.launched, [url]);
  });

  testWidgets('canOpen solo acepta https con host', (tester) async {
    expect(PassportLinkedText.canOpen('https://example.org'), isTrue);
    expect(PassportLinkedText.canOpen(' https://example.org/a '), isTrue);
    for (final bad in [
      'http://example.org',
      'https://',
      'ftp://a.b',
      '',
      null,
    ]) {
      expect(PassportLinkedText.canOpen(bad), isFalse, reason: '$bad');
    }
  });

  testWidgets('el enlace va en el texto corrido: sin mínimo de 48 dp', (
    tester,
  ) async {
    await _pump(tester, 'https://example.org/a', text: 'A');
    expect(find.byType(InkWell), findsNothing);
    expect(tester.getSize(_root).height, lessThan(48));
  });

  testWidgets('se anuncia como enlace con su texto y destino, sin URL', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await _pump(tester, 'https://example.org/a', prefix: 'Licencia: ');
    final links = linkSemantics(tester);
    expect(links, hasLength(1));
    final data = links.single;
    expect(data.flagsCollection.isLink, isTrue);
    expect(
      data.label,
      PassportTexts.linkSemantics('CC0', 'el texto de la licencia'),
    );
    expect(data.label, isNot(contains('https')));
    expect(data.hasAction(ui.SemanticsAction.tap), isTrue);
    handle.dispose();
  });

  testWidgets('el texto enlazado y el plano se leen en el mismo párrafo', (
    tester,
  ) async {
    await _pump(tester, 'https://example.org/a', prefix: 'Licencia: ');
    expect(plainText('Licencia: CC0'), findsOneWidget);
  });

  testWidgets('un enlace de licencia de Fuentes se abre', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    final url = plant.image!.licenseUrl!;
    await showPassport(tester, plant, tab: 'Fuentes');
    final row = plainText('Licencia: ${plant.image!.license}');
    await tester.ensureVisible(row);
    await tester.pump();
    await tapSpan(tester, row, plant.image!.license);
    expect(launcher.launched, [url]);
  });
}
