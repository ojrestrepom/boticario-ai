import 'dart:math' as math;

import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_general_tab.dart';
import 'package:boticario_ai/features/passport/presentation/passport_link.dart';
import 'package:boticario_ai/features/passport/presentation/passport_properties_tab.dart';
import 'package:boticario_ai/features/passport/presentation/passport_sources_tab.dart';
import 'package:boticario_ai/features/passport/presentation/passport_style.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:boticario_ai/features/passport/presentation/passport_uses_tab.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../support/fake_url_launcher.dart';
import 'passport_test_support.dart';

/// Opens the `Fuentes` tab and brings its content to the screen.
Future<void> _openSources(WidgetTester tester, Plant plant) async {
  await showPassport(tester, plant, tab: 'Fuentes');
}

/// Whether [text] is a link inside the visible line [row].
bool _isLink(WidgetTester tester, String row, String text) =>
    linkSpansOf(tester, plainText(row)).any((s) => s.text == text);

Plant _synthetic({List<PlantCredit> credits = const [], PlantImage? image}) =>
    Plant(
      id: 'planta-sintetica',
      scientificName: 'Planta sintetica',
      family: null,
      names: const [],
      parts: const [],
      uses: const [],
      credits: credits,
      image: image,
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

void main() {
  late FakeUrlLauncher launcher;

  setUp(() {
    launcher = FakeUrlLauncher();
    UrlLauncherPlatform.instance = launcher;
  });

  testWidgets('Fuentes: créditos de Wikcionario y Wikipedia como los demás', (
    tester,
  ) async {
    const license = 'https://creativecommons.org/licenses/by-sa/4.0/';
    final plant = _synthetic(
      credits: const [
        PlantCredit(
          name: 'Wikcionario en español',
          url: 'https://es.wiktionary.org',
          license: 'CC BY-SA 4.0',
          licenseUrl: license,
          attribution:
              'Colaboradores de Wikcionario en español '
              '(https://es.wiktionary.org). Texto bajo CC BY-SA 4.0.',
        ),
        PlantCredit(
          name: 'Wikipedia en español',
          url: 'https://es.wikipedia.org',
          license: 'CC BY-SA 4.0',
          licenseUrl: license,
          attribution: 'Colaboradores de Wikipedia en español. CC BY-SA 4.0.',
        ),
      ],
    );
    await _openSources(tester, plant);
    for (final name in ['Wikcionario en español', 'Wikipedia en español']) {
      expect(plainText(name), findsOneWidget, reason: name);
      expect(_isLink(tester, name, name), isTrue, reason: name);
    }
    expect(plainText('Licencia: CC BY-SA 4.0'), findsNWidgets(2));
    expect(
      plainText(
        'Atribución: Colaboradores de Wikcionario en español. '
        'Texto bajo CC BY-SA 4.0.',
      ),
      findsOneWidget,
    );
    expect(find.textContaining('http'), findsNothing);
    expect(
      tester
          .widget<Text>(
            plainText(
              'Atribución: Colaboradores de Wikcionario en español. '
              'Texto bajo CC BY-SA 4.0.',
            ),
          )
          .style!
          .color,
      passportMuted,
    );
  });

  testWidgets('Fuentes de una planta: nombres y licencias enlazados', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await _openSources(tester, plant);
    expect(plainText(PassportTexts.sourcesIntro), findsOneWidget);
    for (final credit in plant.credits) {
      expect(plainText(credit.name), findsOneWidget, reason: credit.name);
      expect(plainText('Licencia: ${credit.license}'), findsWidgets);
      expect(
        plainText('Atribución: ${attributionWithoutUrls(credit.attribution)}'),
        findsWidgets,
      );
      // The name is a link only when the credit has a page.
      expect(
        _isLink(tester, credit.name, credit.name),
        credit.url != null,
        reason: credit.name,
      );
      if (credit.licenseUrl != null) {
        expect(
          _isLink(tester, 'Licencia: ${credit.license}', credit.license),
          isTrue,
        );
      }
    }
    final wikipedia = plant.credits.firstWhere(
      (c) => c.name == 'Wikipedia en español',
    );
    expect(wikipedia.license, 'CC BY-SA 4.0');
    expect(wikipedia.url, isNotNull);
    expect(wikipedia.licenseUrl, isNotNull);
    await tapSpan(tester, plainText('Wikipedia en español'), 'Wikipedia');
    await tapSpan(tester, plainText('Licencia: CC BY-SA 4.0').first, 'CC BY');
    expect(launcher.launched, [wikipedia.url, wikipedia.licenseUrl]);
    expect(plainText(PassportTexts.noSources), findsNothing);
  });

  testWidgets('Fuentes no muestra ninguna URL ni el botón retirado', (
    tester,
  ) async {
    for (final id in ['lavandula-angustifolia', 'eucalyptus-globulus']) {
      final plant = consolidatedPlant(id);
      await _openSources(tester, plant);
      final shown = [
        for (final t in tester.widgetList<Text>(
          find.descendant(
            of: find.byType(PassportSourcesTab),
            matching: find.byType(Text),
          ),
        ))
          t.data ?? t.textSpan?.toPlainText() ?? '',
      ];
      for (final text in shown) {
        expect(text, isNot(contains('http')), reason: '$id: $text');
        expect(text, isNot(contains('www.')), reason: '$id: $text');
      }
      expect(find.byType(SelectableText), findsNothing, reason: id);
      expect(find.byType(TextButton), findsNothing, reason: id);
      expect(find.byIcon(Icons.open_in_new), findsNothing, reason: id);
    }
  });

  testWidgets('la atribución se muestra sin URL y el dato no cambia', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    final withUrl = plant.credits.where((c) => c.attribution.contains('http'));
    expect(withUrl, isNotEmpty);
    await _openSources(tester, plant);
    for (final credit in withUrl) {
      final shown = attributionWithoutUrls(credit.attribution);
      expect(shown, isNot(contains('http')), reason: credit.name);
      expect(plainText('Atribución: $shown'), findsOneWidget);
    }
  });

  group('attributionWithoutUrls', () {
    test('URL al final (EFSA)', () {
      expect(
        attributionWithoutUrls(
          "EFSA (2016). EFSA's compendium of botanicals. Zenodo. "
          'https://doi.org/10.5281/zenodo.996024',
        ),
        "EFSA (2016). EFSA's compendium of botanicals. Zenodo.",
      );
    });

    test('URL entre paréntesis (Wikipedia)', () {
      expect(
        attributionWithoutUrls(
          'Colaboradores de Wikipedia en español (https://es.wikipedia.org). '
          'Texto bajo CC BY-SA 4.0; el historial de cada artículo lista a '
          'sus autores.',
        ),
        'Colaboradores de Wikipedia en español. Texto bajo CC BY-SA 4.0; '
        'el historial de cada artículo lista a sus autores.',
      );
      expect(
        attributionWithoutUrls(
          'Colaboradores de Wikidata (https://www.wikidata.org). Datos '
          'estructurados bajo CC0 1.0.',
        ),
        'Colaboradores de Wikidata. Datos estructurados bajo CC0 1.0.',
      );
    });

    test('sin URL no cambia', () {
      const text = 'Autores de la obra (2020). Título. Editorial... Fin.';
      expect(attributionWithoutUrls(text), text);
    });

    test('URL a mitad de frase', () {
      expect(
        attributionWithoutUrls('Datos de http://a.org/x, versión 2 y más.'),
        'Datos de, versión 2 y más.',
      );
      expect(
        attributionWithoutUrls('Ver https://a.org/x. Después sigue.'),
        'Ver. Después sigue.',
      );
    });

    test('punto duplicado, dobles espacios y solo URL', () {
      expect(attributionWithoutUrls('Obra.  https://a.org/.'), 'Obra.');
      expect(attributionWithoutUrls('Obra   (  ) fin'), 'Obra fin');
      expect(attributionWithoutUrls('https://a.org'), '');
    });
  });

  testWidgets('las entradas son compactas: nombre, licencia y atribución '
      'seguidos, sin bandas vacías', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await _openSources(tester, plant);
    final credit = plant.credits.first;
    final name = tester.getRect(plainText(credit.name));
    final license = tester.getRect(plainText('Licencia: ${credit.license}'));
    final attribution = tester.getRect(
      plainText('Atribución: ${attributionWithoutUrls(credit.attribution)}'),
    );
    expect(license.top - name.bottom, lessThanOrEqualTo(8));
    expect(attribution.top - license.bottom, lessThanOrEqualTo(8));
  });

  testWidgets('la pestaña no lleva título ni separador propios', (
    tester,
  ) async {
    await _openSources(tester, consolidatedPlant('lavandula-angustifolia'));
    // `Fuentes` only names the chip.
    expect(plainText(PassportTexts.sourcesTitle), findsOneWidget);
    expect(find.byType(Divider), findsNothing);
  });

  testWidgets('Fuentes solo se ve con su pestaña', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    for (final tab in ['General', 'Propiedades', 'Usos']) {
      await showPassport(tester, plant, tab: tab);
      expect(plainText(PassportTexts.sourcesIntro), findsNothing, reason: tab);
      expect(plainText(plant.credits.first.name), findsNothing, reason: tab);
      expect(plainText(PassportTexts.imageSourceTitle), findsNothing);
      expect(
        plainText('Atribución: ${plant.credits.first.attribution}'),
        findsNothing,
      );
    }
    await showPassport(tester, plant, tab: 'Fuentes');
    expect(plainText(PassportTexts.sourcesIntro), findsOneWidget);
    expect(plainText(plant.credits.first.name), findsOneWidget);
  });

  testWidgets('la atribución es texto secundario, más pequeño y gris', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await _openSources(tester, plant);
    final credit = plant.credits.first;
    final attribution = tester.widget<Text>(
      plainText('Atribución: ${attributionWithoutUrls(credit.attribution)}'),
    );
    final license = tester.widget<RichText>(
      find
          .descendant(
            of: plainText('Licencia: ${credit.license}'),
            matching: find.byType(RichText),
          )
          .first,
    );
    expect(
      attribution.style!.fontSize!,
      lessThan(license.text.style!.fontSize!),
    );
    expect(attribution.style!.color, passportMuted);
    expect(
      _contrast(passportMuted, passportBackground),
      greaterThanOrEqualTo(4.5),
    );
    // No link on the attribution.
    expect(
      find.ancestor(
        of: plainText(
          'Atribución: ${attributionWithoutUrls(credit.attribution)}',
        ),
        matching: find.byType(PassportLinkedText),
      ),
      findsNothing,
    );
  });

  testWidgets('Entrada de la imagen con autor, licencia y archivo enlazados', (
    tester,
  ) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    final image = plant.image!;
    await _openSources(tester, plant);
    await tester.scrollUntilVisible(
      plainText(PassportTexts.imageSourceTitle),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(plainText('Autor: ${image.author}'), findsOneWidget);
    expect(
      _isLink(tester, 'Licencia: ${image.license}', image.license),
      image.licenseUrl != null,
    );
    final file = plainText(PassportTexts.imageFileLinkLabel);
    expect(
      _isLink(
        tester,
        PassportTexts.imageFileLinkLabel,
        PassportTexts.imageFileLinkLabel,
      ),
      isTrue,
    );
    await tester.ensureVisible(file);
    await tester.pump();
    await tapSpan(tester, file, 'Archivo');
    expect(launcher.launched, [image.pageUrl]);
  });

  testWidgets('imagen de dominio público sin enlace de licencia', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    expect(plant.image!.licenseUrl, isNull);
    await _openSources(tester, plant);
    await tester.scrollUntilVisible(
      plainText('Licencia: Public domain'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      _isLink(tester, 'Licencia: Public domain', 'Public domain'),
      isFalse,
    );
    expect(plainText(PassportTexts.imageSourceTitle), findsOneWidget);
    // The file link stays.
    expect(
      _isLink(
        tester,
        PassportTexts.imageFileLinkLabel,
        PassportTexts.imageFileLinkLabel,
      ),
      isTrue,
    );
  });

  testWidgets('imagen sin autor: no disponible en fuente y archivo enlazado', (
    tester,
  ) async {
    final image = PlantImage(
      url: 'https://upload.wikimedia.org/wikipedia/commons/a/ab/X.jpg',
      pageUrl: 'https://commons.wikimedia.org/wiki/File:X.jpg',
      author: null,
      license: 'CC0 1.0',
      licenseUrl: null,
      attributionRequired: false,
    );
    await _openSources(tester, _synthetic(image: image));
    expect(plainText('Autor: ${PassportTexts.notAvailable}'), findsOneWidget);
    expect(
      _isLink(
        tester,
        PassportTexts.imageFileLinkLabel,
        PassportTexts.imageFileLinkLabel,
      ),
      isTrue,
    );
    expect(plainText(PassportTexts.noSources), findsNothing);
  });

  testWidgets('Sin créditos ni imagen', (tester) async {
    await _openSources(tester, _synthetic());
    expect(plainText(PassportTexts.noSources), findsOneWidget);
    expect(plainText(PassportTexts.sourcesIntro), findsNothing);
    expect(plainText(PassportTexts.imageSourceTitle), findsNothing);
  });

  testWidgets('una planta con imagen y sin créditos muestra solo la imagen', (
    tester,
  ) async {
    final base = consolidatedPlant('blighia-sapida');
    await _openSources(tester, _synthetic(image: base.image));
    expect(plainText(PassportTexts.noSources), findsNothing);
    expect(plainText('Autor: Jerome Walker'), findsOneWidget);
  });

  testWidgets('Sin procedencia por campo', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    final fieldLabels = [
      PassportTexts.commonNameLabel,
      PassportTexts.synonymsLabel,
      PassportTexts.familyLabel,
      PassportTexts.originLabel,
      PassportTexts.partLabel,
      PassportTexts.oilLabel,
      PassportTexts.descriptionLabel,
      PassportTexts.goalsTitle,
      PassportTexts.safetyTitle,
    ];
    await _openSources(tester, plant);
    final texts = [
      for (final t in tester.widgetList<Text>(
        find.descendant(
          of: find.byType(PassportSourcesTab),
          matching: find.byType(Text),
        ),
      ))
        t.data ?? t.textSpan?.toPlainText() ?? '',
    ];
    for (final label in fieldLabels) {
      expect(texts, isNot(contains(label)), reason: label);
    }
  });

  testWidgets('Atribución sin procedencia por campo', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    // The tab bodies are built eagerly here, so nothing is left unbuilt.
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Column(
              children: [
                PassportGeneralTab(plant: plant),
                PassportPropertiesTab(plant: plant),
                PassportUsesTab(
                  plant: plant,
                  expandedGroups: const {},
                  onToggleGroup: (_) {},
                  expandedGlossaries: const {},
                  onToggleGlossary: (_) {},
                ),
              ],
            ),
          ),
        ),
      ),
    );
    final shown = [
      for (final t in tester.widgetList<Text>(find.byType(Text))) t.data ?? '',
    ].join('\n');
    for (final credit in plant.credits) {
      // Citations of goals and precautions may name a work; credits do not.
      expect(shown, isNot(contains(credit.attribution)), reason: credit.name);
    }
    expect(shown, isNot(contains(PassportTexts.attributionPrefix)));
    expect(shown, isNot(contains(PassportTexts.licensePrefix)));
    expect(plainText(PassportTexts.sourcesIntro), findsNothing);
  });

  testWidgets('los textos fijos de Fuentes no tienen lenguaje de eficacia', (
    tester,
  ) async {
    final pattern = RegExp(
      r'(?<![\p{L}])(cura|trata|alivia|calma|ayuda|mejora|previene|remedio)'
      r'(?![\p{L}])',
      caseSensitive: false,
      unicode: true,
    );
    for (final text in [
      PassportTexts.sourcesIntro,
      PassportTexts.noSources,
      PassportTexts.sourcesTitle,
      PassportTexts.imageFileLinkLabel,
      PassportTexts.linkCopied,
      PassportTexts.linkNotOpened,
    ]) {
      expect(pattern.hasMatch(text), isFalse, reason: text);
    }
  });

  testWidgets('créditos sin URL propia: nombre y licencia en texto plano', (
    tester,
  ) async {
    const credit = PlantCredit(
      name: 'Fuente sintetica',
      license: 'Licencia propia',
      licenseUrl: null,
      attribution: 'Atribucion sintetica',
      url: null,
    );
    await _openSources(tester, _synthetic(credits: const [credit]));
    expect(plainText('Fuente sintetica'), findsOneWidget);
    expect(plainText('Licencia: Licencia propia'), findsOneWidget);
    expect(plainText('Atribución: Atribucion sintetica'), findsOneWidget);
    for (final row in ['Fuente sintetica', 'Licencia: Licencia propia']) {
      expect(linkSpansOf(tester, plainText(row)), isEmpty, reason: row);
    }
  });
}
