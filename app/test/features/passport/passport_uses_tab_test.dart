import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'passport_test_support.dart';

Plant _synthetic({
  List<UseGroup> groups = const [],
  List<PlantUse> uses = const [],
}) => Plant(
  id: 'planta-sintetica',
  scientificName: 'Planta sintetica',
  family: null,
  names: const [],
  parts: const [],
  uses: uses,
  useGroups: groups,
);

UseGroup _group({
  String activity = 'Actividad sintetica',
  int count = 1,
  List<String> countries = const [],
  List<CitedReference> references = const [],
}) => UseGroup(
  activity: activity,
  activitySource: null,
  count: count,
  countries: countries,
  references: references,
);

CitedReference _ref(int i, {bool resolved = true}) => CitedReference(
  id: resolved ? 'ref:$i' : null,
  citation: resolved ? 'Cita sintetica $i' : 'Clave $i (sin resolver)',
  resolved: resolved,
);

void main() {
  testWidgets('Registro tradicional elegible', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await showPassport(tester, plant, tab: 'Usos');
    expect(plant.useGroups, hasLength(11));
    final first = plant.useGroups.first;
    expect(find.text(first.activity), findsOneWidget);
    expect(find.text('Registro tradicional'), findsNWidgets(11));
    expect(find.text('2 registros'), findsWidgets);
    expect(find.text('Países'), findsWidgets);
    expect(find.text(first.countries.join(', ')), findsWidgets);
    for (final reference in first.references) {
      expect(find.text(reference.citation), findsWidgets);
    }
    expect(find.text(PassportTexts.useGroupClarification), findsNWidgets(11));
    expect(find.text(PassportTexts.noUses), findsNothing);
  });

  testWidgets('un registro se escribe en singular', (tester) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(count: 1, references: [_ref(1)]),
        ],
      ),
      tab: 'Usos',
    );
    expect(find.text('1 registro'), findsOneWidget);
  });

  testWidgets('Aviso fijo de usos tradicionales', (tester) async {
    for (final id in [
      'lavandula-angustifolia',
      'acinos-sp',
      'eucalyptus-globulus',
    ]) {
      await showPassport(tester, consolidatedPlant(id), tab: 'Usos');
      expect(find.text(PassportTexts.usesNotice), findsOneWidget, reason: id);
      final notice = tester.getTopLeft(find.text(PassportTexts.usesNotice));
      final below = find.text(
        id == 'acinos-sp'
            ? PassportTexts.noUses
            : consolidatedPlant(id).useGroups.first.activity,
      );
      expect(
        tester.getTopLeft(below.first).dy,
        greaterThan(notice.dy),
        reason: id,
      );
    }
    // The notice is not shown in the other tabs.
    await showPassport(tester, consolidatedPlant('acinos-sp'));
    expect(find.text(PassportTexts.usesNotice), findsNothing);
  });

  testWidgets('el aviso fijo no contiene lenguaje de eficacia', (tester) async {
    final pattern = RegExp(
      r'(?<![\p{L}])(cura|curar|trata|tratar|alivia|calma|ayuda|mejora|'
      r'previene|remedio|eficaz|efectivo)(?![\p{L}])',
      caseSensitive: false,
      unicode: true,
    );
    for (final text in [
      PassportTexts.usesNotice,
      PassportTexts.useGroupClarification,
    ]) {
      expect(pattern.hasMatch(text), isFalse, reason: text);
    }
  });

  testWidgets('Cita sin resolver visible', (tester) async {
    final plant = consolidatedPlant('capsella-bursa-pastoris');
    await showPassport(tester, plant, tab: 'Usos');
    final unresolved = find.text('Woi.Syria (sin resolver)');
    expect(unresolved, findsWidgets);
    final dimmed = tester.widget<Text>(unresolved.first);
    final resolved = tester.widget<Text>(
      find.text(plant.useGroups.first.references.first.citation).first,
    );
    expect(dimmed.style!.fontStyle, FontStyle.italic);
    expect(dimmed.style!.color, isNot(resolved.style!.color));
    expect(resolved.style!.fontStyle, isNot(FontStyle.italic));
    // The group with a resolved and an unresolved citation shows both.
    expect(find.text('Hemorragia'), findsOneWidget);
    expect(
      find.text('Al-Rawi, Ali. 1964. Medicinal Plants of Iraq.'),
      findsNothing,
    );
    expect(find.textContaining('Al-Rawi, Ali. 1964'), findsOneWidget);
  });

  testWidgets('una cita sin resolver sin el sufijo lo recibe', (tester) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(
            references: const [
              CitedReference(id: null, citation: 'Clave x', resolved: false),
            ],
          ),
        ],
      ),
      tab: 'Usos',
    );
    expect(find.text('Clave x (sin resolver)'), findsOneWidget);
  });

  testWidgets('Actividades sensibles tal como llegan', (tester) async {
    final plant = consolidatedPlant('capsella-bursa-pastoris');
    await showPassport(tester, plant, tab: 'Usos');
    expect(
      find.text('Uso tradicional, sin eficacia demostrada: cáncer'),
      findsOneWidget,
    );
    final activities = [for (final g in plant.useGroups) g.activity];
    for (final activity in activities) {
      expect(find.text(activity), findsOneWidget, reason: activity);
    }
  });

  testWidgets('Grupo sin países', (tester) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(references: [_ref(1)]),
        ],
      ),
      tab: 'Usos',
    );
    expect(find.text('Actividad sintetica'), findsOneWidget);
    expect(find.text('Países'), findsNothing);
    expect(find.text('Cita sintetica 1'), findsOneWidget);
  });

  testWidgets('Sin registro elegible', (tester) async {
    for (final plant in [consolidatedPlant('acinos-sp'), _synthetic()]) {
      await showPassport(tester, plant, tab: 'Usos');
      expect(find.text(PassportTexts.noUses), findsOneWidget);
      expect(find.text('Registro tradicional'), findsNothing);
      expect(find.text(PassportTexts.usesNotice), findsOneWidget);
    }
  });

  testWidgets('Muchos usos', (tester) async {
    final plant = consolidatedPlant('eucalyptus-globulus');
    expect(plant.useGroups.length, greaterThanOrEqualTo(20));
    await showPassport(tester, plant, tab: 'Usos');
    final last = plant.useGroups.last;
    await tester.scrollUntilVisible(
      find.text(last.activity),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text(last.activity), findsOneWidget);
    for (final reference in last.references) {
      expect(find.text(reference.citation), findsWidgets);
    }
    for (final text in tester.widgetList<Text>(find.byType(Text))) {
      expect(text.overflow, isNot(TextOverflow.ellipsis));
      expect(text.maxLines, isNull);
    }
  });

  testWidgets('respaldo de un backend anterior sin useGroups', (tester) async {
    final plant = Plant(
      id: 'planta-sintetica',
      scientificName: 'Planta sintetica',
      family: null,
      names: const [],
      parts: const [],
      uses: const [
        PlantUse(
          activity: 'Carminative',
          language: 'en',
          reference: UseReference(id: 'r:1', citation: 'Cita antigua'),
        ),
      ],
    );
    await showPassport(tester, plant, tab: 'Usos');
    expect(find.text('Carminative'), findsOneWidget);
    expect(find.text('Cita antigua'), findsOneWidget);
    expect(find.text('1 registro'), findsOneWidget);
    expect(find.text('Países'), findsNothing);
  });
}
