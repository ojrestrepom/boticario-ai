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

Finder _link(String text) => find.widgetWithText(PassportInlineLink, text);

/// [text] when it is a real link (it has a touch target), not plain text.
Finder _active(String text) =>
    find.descendant(of: _link(text), matching: find.byType(InkWell));

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

  testWidgets('Fuentes de una planta: nombres y licencias enlazados', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await _openSources(tester, plant);
    expect(find.text(PassportTexts.sourcesIntro), findsOneWidget);
    for (final credit in plant.credits) {
      expect(find.text(credit.name), findsOneWidget, reason: credit.name);
      expect(find.text('Licencia: ${credit.license}'), findsWidgets);
      expect(
        find.text('Atribución: ${attributionWithoutUrls(credit.attribution)}'),
        findsWidgets,
      );
      // The name is a link only when the credit has a page.
      expect(
        _active(credit.name),
        credit.url != null ? findsOneWidget : findsNothing,
        reason: credit.name,
      );
      if (credit.licenseUrl != null) {
        expect(_link('Licencia: ${credit.license}'), findsWidgets);
      }
    }
    final wikipedia = plant.credits.firstWhere(
      (c) => c.name == 'Wikipedia en español',
    );
    expect(wikipedia.license, 'CC BY-SA 4.0');
    expect(wikipedia.url, isNotNull);
    expect(wikipedia.licenseUrl, isNotNull);
    await tester.tap(_link('Wikipedia en español'));
    await tester.pump();
    await tester.tap(_link('Licencia: CC BY-SA 4.0').first);
    await tester.pump();
    expect(launcher.launched, [wikipedia.url, wikipedia.licenseUrl]);
    expect(find.text(PassportTexts.noSources), findsNothing);
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
      expect(find.text('Atribución: $shown'), findsOneWidget);
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

  testWidgets('la pestaña no lleva título ni separador propios', (
    tester,
  ) async {
    await _openSources(tester, consolidatedPlant('lavandula-angustifolia'));
    // `Fuentes` only names the chip.
    expect(find.text(PassportTexts.sourcesTitle), findsOneWidget);
    expect(find.byType(Divider), findsNothing);
  });

  testWidgets('Fuentes solo se ve con su pestaña', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    for (final tab in ['General', 'Propiedades', 'Usos']) {
      await showPassport(tester, plant, tab: tab);
      expect(find.text(PassportTexts.sourcesIntro), findsNothing, reason: tab);
      expect(find.text(plant.credits.first.name), findsNothing, reason: tab);
      expect(find.text(PassportTexts.imageSourceTitle), findsNothing);
      expect(
        find.text('Atribución: ${plant.credits.first.attribution}'),
        findsNothing,
      );
    }
    await showPassport(tester, plant, tab: 'Fuentes');
    expect(find.text(PassportTexts.sourcesIntro), findsOneWidget);
    expect(find.text(plant.credits.first.name), findsOneWidget);
  });

  testWidgets('la atribución es texto secundario, más pequeño y gris', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await _openSources(tester, plant);
    final credit = plant.credits.first;
    final attribution = tester.widget<Text>(
      find.text('Atribución: ${attributionWithoutUrls(credit.attribution)}'),
    );
    final license = tester.widget<RichText>(
      find
          .descendant(
            of: _link('Licencia: ${credit.license}'),
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
        of: find.text(
          'Atribución: ${attributionWithoutUrls(credit.attribution)}',
        ),
        matching: find.byType(PassportInlineLink),
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
      find.text(PassportTexts.imageSourceTitle),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Autor: ${image.author}'), findsOneWidget);
    expect(_link('Licencia: ${image.license}'), findsOneWidget);
    expect(_link(PassportTexts.imageFileLinkLabel), findsOneWidget);
    await tester.ensureVisible(_link(PassportTexts.imageFileLinkLabel));
    await tester.pump();
    await tester.tap(_link(PassportTexts.imageFileLinkLabel));
    await tester.pump();
    expect(launcher.launched, [image.pageUrl]);
  });

  testWidgets('imagen de dominio público sin enlace de licencia', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    expect(plant.image!.licenseUrl, isNull);
    await _openSources(tester, plant);
    await tester.scrollUntilVisible(
      find.text('Licencia: Public domain'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(_active('Licencia: Public domain'), findsNothing);
    expect(_link('Licencia: Public domain'), findsOneWidget);
    expect(find.text(PassportTexts.imageSourceTitle), findsOneWidget);
    // The file link stays.
    expect(_link(PassportTexts.imageFileLinkLabel), findsOneWidget);
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
    expect(find.text('Autor: ${PassportTexts.notAvailable}'), findsOneWidget);
    expect(_link(PassportTexts.imageFileLinkLabel), findsOneWidget);
    expect(find.text(PassportTexts.noSources), findsNothing);
  });

  testWidgets('Sin créditos ni imagen', (tester) async {
    await _openSources(tester, _synthetic());
    expect(find.text(PassportTexts.noSources), findsOneWidget);
    expect(find.text(PassportTexts.sourcesIntro), findsNothing);
    expect(find.text(PassportTexts.imageSourceTitle), findsNothing);
  });

  testWidgets('una planta con imagen y sin créditos muestra solo la imagen', (
    tester,
  ) async {
    final base = consolidatedPlant('blighia-sapida');
    await _openSources(tester, _synthetic(image: base.image));
    expect(find.text(PassportTexts.noSources), findsNothing);
    expect(find.text('Autor: Jerome Walker'), findsOneWidget);
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
      PassportTexts.countriesLabel,
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
                PassportUsesTab(plant: plant),
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
    expect(find.text(PassportTexts.sourcesIntro), findsNothing);
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
    expect(find.text('Fuente sintetica'), findsOneWidget);
    expect(find.text('Licencia: Licencia propia'), findsOneWidget);
    expect(find.text('Atribución: Atribucion sintetica'), findsOneWidget);
    expect(
      find.descendant(
        of: find.byType(PassportSourcesTab),
        matching: find.byType(InkWell),
      ),
      findsNothing,
    );
  });
}
