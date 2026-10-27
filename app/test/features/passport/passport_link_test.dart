import 'package:boticario_ai/features/passport/presentation/passport_link.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../support/fake_url_launcher.dart';
import 'passport_test_support.dart';

Future<void> _pump(WidgetTester tester, String label, String url) =>
    tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PassportLink(label: label, url: url),
        ),
      ),
    );

void main() {
  late FakeUrlLauncher launcher;

  void install(FakeUrlLauncher l) {
    launcher = l;
    UrlLauncherPlatform.instance = l;
  }

  setUp(() => install(FakeUrlLauncher()));

  testWidgets('abre una URL https en el navegador externo', (tester) async {
    await _pump(tester, 'Página', 'https://commons.wikimedia.org/wiki/File:X');
    await tester.tap(find.text(PassportTexts.openLink));
    await tester.pump();
    expect(launcher.launched, ['https://commons.wikimedia.org/wiki/File:X']);
    expect(launcher.modes, [PreferredLaunchMode.externalApplication]);
    expect(find.byType(SelectableText), findsOneWidget);
  });

  testWidgets('una URL http no se abre ni ofrece botón, y sigue visible', (
    tester,
  ) async {
    await _pump(tester, 'Página', 'http://example.org/a');
    expect(find.text('http://example.org/a'), findsOneWidget);
    expect(find.text(PassportTexts.openLink), findsNothing);
    expect(launcher.launched, isEmpty);
    for (final bad in [
      'javascript:alert(1)',
      'file:///etc/passwd',
      'https://',
      '',
    ]) {
      await _pump(tester, 'Página', bad);
      expect(find.text(PassportTexts.openLink), findsNothing, reason: bad);
    }
  });

  testWidgets('si no se puede abrir no falla y la URL sigue visible', (
    tester,
  ) async {
    for (final l in [
      FakeUrlLauncher(result: false),
      FakeUrlLauncher(throws: true),
    ]) {
      install(l);
      await _pump(tester, 'Página', 'https://example.org/a');
      await tester.tap(find.text(PassportTexts.openLink));
      await tester.pump();
      expect(l.launched, ['https://example.org/a']);
      expect(tester.takeException(), isNull);
      expect(find.text('https://example.org/a'), findsOneWidget);
      expect(find.text(PassportTexts.linkNotOpened), findsOneWidget);
    }
  });

  testWidgets('el botón mide al menos 48 dp', (tester) async {
    await _pump(tester, 'Página', 'https://example.org/a');
    final size = tester.getSize(find.byType(TextButton));
    expect(size.height, greaterThanOrEqualTo(48));
  });

  testWidgets('un enlace de licencia de Fuentes se abre', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    final url = plant.image!.licenseUrl!;
    await showPassport(tester, plant);
    final button = find.descendant(
      of: find.ancestor(
        of: find.text(url),
        matching: find.byType(PassportLink),
      ),
      matching: find.byType(TextButton),
    );
    // The button is built before it is on screen: scroll until it is.
    for (var i = 0; i < 40 && tester.getCenter(button).dy > 2300; i++) {
      await tester.drag(find.byType(CustomScrollView), const Offset(0, -400));
      await tester.pump();
    }
    await tester.tap(button);
    await tester.pump();
    expect(launcher.launched, [url]);
  });
}
