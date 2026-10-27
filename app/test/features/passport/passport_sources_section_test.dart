import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:boticario_ai/features/passport/presentation/passport_general_tab.dart';
import 'package:boticario_ai/features/passport/presentation/passport_properties_tab.dart';
import 'package:boticario_ai/features/passport/presentation/passport_uses_tab.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'passport_test_support.dart';

Future<void> _scrollToSources(WidgetTester tester) async {
  await tester.scrollUntilVisible(
    find.text(PassportTexts.sourcesTitle),
    300,
    scrollable: find.byType(Scrollable).first,
  );
}

void main() {
  testWidgets('Fuentes de una planta', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await showPassport(tester, plant);
    await _scrollToSources(tester);
    expect(find.text(PassportTexts.sourcesIntro), findsOneWidget);
    for (final credit in plant.credits) {
      expect(find.text(credit.name), findsOneWidget, reason: credit.name);
      expect(find.text('Licencia: ${credit.license}'), findsWidgets);
      expect(find.text('Atribución: ${credit.attribution}'), findsWidgets);
      if (credit.url != null) {
        expect(find.text(credit.url!), findsWidgets, reason: credit.name);
      }
      if (credit.licenseUrl != null) {
        expect(find.text(credit.licenseUrl!), findsWidgets);
      }
    }
    final wikipedia = plant.credits.firstWhere(
      (c) => c.name == 'Wikipedia en español',
    );
    expect(wikipedia.license, 'CC BY-SA 4.0');
    expect(find.text(wikipedia.licenseUrl!), findsOneWidget);
    expect(find.text(PassportTexts.noSources), findsNothing);
  });

  testWidgets('las URL son texto seleccionable y se pueden abrir', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await showPassport(tester, plant);
    await _scrollToSources(tester);
    expect(find.byType(SelectableText), findsWidgets);
    final url = plant.image!.pageUrl;
    await tester.scrollUntilVisible(
      find.text(url),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      find.ancestor(of: find.text(url), matching: find.byType(SelectableText)),
      findsWidgets,
    );
    expect(
      find.byTooltip(
        PassportTexts.openLinkTooltip(PassportTexts.pageUrlPrefix),
      ),
      findsWidgets,
    );
  });

  testWidgets('Fuentes visibles en cada pestaña', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    for (final tab in ['General', 'Propiedades', 'Usos']) {
      await showPassport(tester, plant, tab: tab);
      await _scrollToSources(tester);
      expect(
        find.text(PassportTexts.sourcesTitle),
        findsOneWidget,
        reason: tab,
      );
      expect(find.text(plant.credits.first.name), findsOneWidget, reason: tab);
    }
  });

  testWidgets('Entrada de la imagen', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    final image = plant.image!;
    await showPassport(tester, plant);
    await _scrollToSources(tester);
    await tester.scrollUntilVisible(
      find.text(PassportTexts.imageSourceTitle),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Autor: ${image.author}'), findsOneWidget);
    expect(find.text('Licencia: ${image.license}'), findsWidgets);
    expect(find.text(image.pageUrl), findsOneWidget);
    expect(find.text(image.licenseUrl!), findsOneWidget);
  });

  testWidgets('imagen de dominio público sin enlace de licencia', (
    tester,
  ) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    expect(plant.image!.licenseUrl, isNull);
    await showPassport(tester, plant);
    await _scrollToSources(tester);
    await tester.scrollUntilVisible(
      find.text('Licencia: Public domain'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text(PassportTexts.imageSourceTitle), findsOneWidget);
  });

  testWidgets('Sin créditos', (tester) async {
    final plant = Plant(
      id: 'planta-sintetica',
      scientificName: 'Planta sintetica',
      family: null,
      names: const [],
      parts: const [],
      uses: const [],
    );
    await showPassport(tester, plant);
    await _scrollToSources(tester);
    expect(find.text(PassportTexts.noSources), findsOneWidget);
    expect(find.text(PassportTexts.sourcesIntro), findsNothing);
    expect(find.text(PassportTexts.imageSourceTitle), findsNothing);
  });

  testWidgets('una planta con imagen y sin créditos muestra solo la imagen', (
    tester,
  ) async {
    final base = consolidatedPlant('blighia-sapida');
    final plant = Plant(
      id: base.id,
      scientificName: base.scientificName,
      family: null,
      names: const [],
      parts: const [],
      uses: const [],
      image: base.image,
    );
    await showPassport(tester, plant);
    await _scrollToSources(tester);
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
    await showPassport(tester, plant);
    await _scrollToSources(tester);
    final sources = find
        .ancestor(
          of: find.text(PassportTexts.sourcesTitle),
          matching: find.byType(Column),
        )
        .first;
    final texts = [
      for (final t in tester.widgetList<Text>(
        find.descendant(of: sources, matching: find.byType(Text)),
      ))
        t.data ?? '',
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
    // And the credits do appear once the section is added.
    expect(find.text(PassportTexts.sourcesTitle), findsNothing);
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
    ]) {
      expect(pattern.hasMatch(text), isFalse, reason: text);
    }
  });

  testWidgets('créditos con licencia y sin URL propia', (tester) async {
    const credit = PlantCredit(
      name: 'Fuente sintetica',
      license: 'Licencia propia',
      licenseUrl: null,
      attribution: 'Atribucion sintetica',
      url: null,
    );
    await showPassport(
      tester,
      Plant(
        id: 'planta-sintetica',
        scientificName: 'Planta sintetica',
        family: null,
        names: const [],
        parts: const [],
        uses: const [],
        credits: const [credit],
      ),
    );
    await _scrollToSources(tester);
    expect(find.text('Fuente sintetica'), findsOneWidget);
    expect(find.text('Licencia: Licencia propia'), findsOneWidget);
    expect(find.text('Atribución: Atribucion sintetica'), findsOneWidget);
    expect(find.text(PassportTexts.licenseUrlPrefix), findsNothing);
    expect(find.text(PassportTexts.pageUrlPrefix), findsNothing);
  });
}
