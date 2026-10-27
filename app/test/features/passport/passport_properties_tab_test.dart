import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'passport_test_support.dart';

Plant _withSafety(SafetyLevel? level) => Plant(
  id: 'planta-sintetica',
  scientificName: 'Planta sintetica',
  family: null,
  names: const [],
  parts: const [],
  uses: const [],
  safety: PlantSafety(
    level: level,
    text: 'Texto de advertencia sintetico',
    references: const [
      CitedReference(id: 'x:1', citation: 'Cita sintetica', resolved: true),
    ],
  ),
);

/// Effect words searched in the fixed texts (whole words, lowercase). `eficacia`
/// is left out on purpose: the fixed clarification uses it to deny a promise.
const effectWords = <String>[
  'cura',
  'curar',
  'curativo',
  'trata',
  'tratar',
  'tratamiento',
  'sana',
  'sanar',
  'alivia',
  'aliviar',
  'previene',
  'prevenir',
  'calma',
  'calmar',
  'ayuda',
  'ayudar',
  'mejora',
  'mejorar',
  'combate',
  'combatir',
  'elimina',
  'eliminar',
  'remedio',
  'beneficia',
  'fortalece',
  'eficaz',
  'eficaces',
  'efectivo',
  'efectiva',
  'efectivos',
  'efectivas',
];

final _effectPattern = RegExp(
  '(?<![\\p{L}])(${effectWords.join('|')})(?![\\p{L}])',
  caseSensitive: false,
  unicode: true,
);

/// Texts that claim safety (the negated notice is removed before the scan).
final _safePattern = RegExp(
  r'(?<![\p{L}])(segur[oa]s?|inocu[oa]s?|sin riesgos?)(?![\p{L}])',
  caseSensitive: false,
  unicode: true,
);

List<String> _visibleTexts(WidgetTester tester) => [
  for (final widget in tester.widgetList<Text>(find.byType(Text)))
    if (widget.data != null) widget.data!,
];

void main() {
  testWidgets('Planta con objetivos de la EMA', (tester) async {
    await showPassport(
      tester,
      consolidatedPlant('lavandula-angustifolia'),
      tab: 'Propiedades',
    );
    expect(find.text('Objetivos registrados por la EMA'), findsOneWidget);
    expect(find.text('Mejorar el sueño'), findsOneWidget);
    expect(
      find.text('Trastornos del sueño e insomnio pasajero'),
      findsOneWidget,
    );
    expect(
      find.text(
        'La EMA tiene una monografía de la flor y otra del aceite esencial '
        'en esta área.',
      ),
      findsNWidgets(2),
    );
    expect(find.text('Tipo de documento'), findsNWidgets(2));
    expect(find.text('EMA: Lavandulae flos'), findsNWidgets(2));
    expect(find.text(PassportTexts.goalDisclaimer), findsNWidgets(2));
    expect(find.text('Subárea'), findsNothing);
  });

  testWidgets('Objetivo de otros objetivos', (tester) async {
    await showPassport(
      tester,
      consolidatedPlant('agrimonia-eupatoria'),
      tab: 'Propiedades',
    );
    expect(find.text('Otros objetivos'), findsNWidgets(2));
    expect(find.text('Subárea'), findsNWidgets(2));
    expect(find.text('Digestión'), findsOneWidget);
    expect(find.text('Boca y garganta'), findsOneWidget);
  });

  testWidgets('Plantas sin evaluación respaldada', (tester) async {
    for (final id in ['blighia-sapida', 'acinos-sp']) {
      await showPassport(tester, consolidatedPlant(id), tab: 'Propiedades');
      expect(
        find.text('No hay objetivos registrados por la EMA para esta planta'),
        findsOneWidget,
        reason: id,
      );
      expect(find.text(PassportTexts.goalDisclaimer), findsNothing);
    }
  });

  testWidgets('Precauciones de nivel alto', (tester) async {
    final plant = consolidatedPlant('blighia-sapida');
    await showPassport(tester, plant, tab: 'Propiedades');
    expect(find.text('Precauciones'), findsOneWidget);
    expect(find.text('Nivel'), findsOneWidget);
    expect(find.text('Alto'), findsOneWidget);
    expect(find.text(plant.safety!.text), findsOneWidget);
    expect(find.text('USDA Dr. Duke: uso etnobotánico 23667'), findsOneWidget);
    expect(find.text('USDA Dr. Duke: uso etnobotánico 37710'), findsOneWidget);
  });

  testWidgets('Precauciones sin nivel', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    expect(plant.safety!.level, isNull);
    await showPassport(tester, plant, tab: 'Propiedades');
    expect(find.text(plant.safety!.text), findsOneWidget);
    expect(find.text(plant.safety!.references.first.citation), findsOneWidget);
    expect(find.text('Nivel'), findsNothing);
    for (final label in ['Alto', 'Medio', 'Bajo']) {
      expect(find.text(label), findsNothing, reason: label);
    }
    expect(find.text(PassportTexts.noSafety), findsNothing);
  });

  testWidgets('Precauciones sin datos', (tester) async {
    await showPassport(
      tester,
      consolidatedPlant('acinos-sp'),
      tab: 'Propiedades',
    );
    expect(
      find.text(
        'No hay precauciones registradas en las fuentes consultadas. '
        'Esto no significa que la planta sea segura.',
      ),
      findsOneWidget,
    );
    expect(find.text('Nivel'), findsNothing);
  });

  testWidgets('Nivel de precauciones como texto', (tester) async {
    for (final (level, label) in [
      (SafetyLevel.high, 'Alto'),
      (SafetyLevel.medium, 'Medio'),
      (SafetyLevel.low, 'Bajo'),
    ]) {
      await showPassport(tester, _withSafety(level), tab: 'Propiedades');
      expect(find.text(label), findsOneWidget, reason: label);
    }
  });

  testWidgets('Ninguna planta se presenta como segura', (tester) async {
    final negated = PassportTexts.noSafety;
    final plants = <Plant>[
      _withSafety(SafetyLevel.high),
      _withSafety(SafetyLevel.medium),
      _withSafety(SafetyLevel.low),
      _withSafety(null),
      consolidatedPlant('acinos-sp'),
    ];
    for (final plant in plants) {
      await showPassport(tester, plant, tab: 'Propiedades');
      for (final text in _visibleTexts(tester)) {
        final scanned = text.replaceAll(negated, '');
        expect(_safePattern.hasMatch(scanned), isFalse, reason: text);
      }
    }
    // The no-data text is the only one that mentions it, and it denies it.
    expect(
      PassportTexts.noSafety.replaceAll(
        'Esto no significa que la planta sea segura.',
        '',
      ),
      isNot(contains('segura')),
    );
    // Fixed texts never claim safety apart from that denial.
    for (final text in PassportTexts.all) {
      expect(
        _safePattern.hasMatch(text.replaceAll(negated, '')),
        isFalse,
        reason: text,
      );
    }
  });

  test('Sin lenguaje de eficacia en los textos fijos', () {
    expect(PassportTexts.all, isNotEmpty);
    for (final text in PassportTexts.all) {
      expect(_effectPattern.hasMatch(text), isFalse, reason: text);
    }
  });

  testWidgets('Sin lenguaje de eficacia en los textos fijos mostrados', (
    tester,
  ) async {
    // Plant without data: every visible text of the tab is a fixed text.
    await showPassport(
      tester,
      consolidatedPlant('acinos-sp'),
      tab: 'Propiedades',
    );
    final empty = _visibleTexts(tester);
    expect(empty, contains(PassportTexts.noGoals));
    for (final text in empty) {
      expect(_effectPattern.hasMatch(text), isFalse, reason: text);
    }
    // With goals, the fixed labels and clarification are scanned; API data
    // (goal names, areas and citations) comes from the seed and is not.
    await showPassport(
      tester,
      consolidatedPlant('agrimonia-eupatoria'),
      tab: 'Propiedades',
    );
    final fixed = PassportTexts.all.toSet();
    final shown = _visibleTexts(tester).where(fixed.contains).toList();
    expect(shown, contains(PassportTexts.goalDisclaimer));
    for (final text in shown) {
      expect(_effectPattern.hasMatch(text), isFalse, reason: text);
    }
  });

  test('Las palabras de efecto detectan los verbos esperados', () {
    for (final sample in ['Calma el estres', 'ayuda a dormir', 'Es eficaz']) {
      expect(_effectPattern.hasMatch(sample), isTrue, reason: sample);
    }
    expect(_effectPattern.hasMatch('promesa de eficacia'), isFalse);
  });

  testWidgets('Nivel de texto no depende del color', (tester) async {
    await showPassport(
      tester,
      _withSafety(SafetyLevel.high),
      tab: 'Propiedades',
    );
    final level = tester.widget<Text>(find.text('Alto'));
    expect(level.data, 'Alto');
    expect(find.byType(Text), findsWidgets);
  });
}
