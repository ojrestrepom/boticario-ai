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
  String? activitySource,
  int count = 1,
  List<String> countries = const [],
  List<CitedReference> references = const [],
}) => UseGroup(
  activity: activity,
  activitySource: activitySource,
  count: count,
  countries: countries,
  references: references,
);

CitedReference _ref(int i, {bool resolved = true}) => CitedReference(
  id: resolved ? 'ref:$i' : null,
  citation: resolved ? 'Cita sintetica $i' : 'Clave $i (sin resolver)',
  resolved: resolved,
);

String _showLabel(UseGroup group) =>
    PassportTexts.showCitations(group.references.length);

Finder _toggle(String label) => find.widgetWithText(TextButton, label);

void main() {
  testWidgets('Registro tradicional elegible', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await showPassport(tester, plant, tab: 'Usos');
    expect(plant.useGroups, hasLength(11));
    final first = plant.useGroups.first;
    expect(find.text(first.activity), findsOneWidget);
    expect(
      find.text(PassportTexts.useGroupSummary(first.count, first.countries)),
      findsWidgets,
    );
    expect(first.countries, isNotEmpty);
    expect(_toggle(_showLabel(first)), findsWidgets);
    expect(find.text(PassportTexts.noUses), findsNothing);
  });

  testWidgets('línea de datos con tres países y control Ver 2 citas', (
    tester,
  ) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(
            count: 12,
            countries: const ['China', 'Otros lugares', 'Trinidad'],
            references: [_ref(1), _ref(2)],
          ),
        ],
      ),
      tab: 'Usos',
    );
    expect(find.text('Actividad sintetica'), findsOneWidget);
    expect(
      find.text('12 registros · China, Otros lugares, Trinidad'),
      findsOneWidget,
    );
    expect(_toggle('Ver 2 citas'), findsOneWidget);
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

  testWidgets('Citas plegadas por defecto', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await showPassport(tester, plant, tab: 'Usos');
    for (final group in plant.useGroups) {
      for (final reference in group.references) {
        expect(find.text(reference.citation), findsNothing);
      }
    }
    final controls = find.byWidgetPredicate(
      (w) => w is Text && RegExp(r'^Ver \d+ citas?$').hasMatch(w.data ?? ''),
    );
    expect(controls, findsNWidgets(plant.useGroups.length));
  });

  testWidgets('Desplegar y plegar citas sin tocar los demás grupos', (
    tester,
  ) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(activity: 'Primera', references: [_ref(1), _ref(2), _ref(3)]),
          _group(activity: 'Segunda', references: [_ref(4), _ref(5)]),
        ],
      ),
      tab: 'Usos',
    );
    final before = tester.getTopLeft(_toggle('Ver 3 citas'));
    await tester.tap(_toggle('Ver 3 citas'));
    await tester.pumpAndSettle();
    expect(tester.getTopLeft(_toggle('Ocultar citas')), before);
    for (final i in [1, 2, 3]) {
      expect(find.text('Cita sintetica $i'), findsOneWidget);
    }
    expect(find.text('Cita sintetica 4'), findsNothing);
    expect(_toggle('Ver 2 citas'), findsOneWidget);
    await tester.tap(_toggle('Ocultar citas'));
    await tester.pumpAndSettle();
    expect(find.text('Cita sintetica 1'), findsNothing);
    expect(_toggle('Ver 3 citas'), findsOneWidget);
    expect(_toggle('Ver 2 citas'), findsOneWidget);
  });

  testWidgets('dos grupos con la misma actividad se pliegan por separado', (
    tester,
  ) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(
            activity: 'Hidropesía',
            activitySource: 'Dropsy',
            references: [_ref(1)],
          ),
          _group(
            activity: 'Hidropesía',
            activitySource: 'Edema',
            references: [_ref(2), _ref(3)],
          ),
        ],
      ),
      tab: 'Usos',
    );
    await tester.tap(_toggle('Ver 2 citas'));
    await tester.pumpAndSettle();
    expect(find.text('Cita sintetica 1'), findsNothing);
    expect(find.text('Cita sintetica 2'), findsOneWidget);
    expect(_toggle('Ver 1 cita'), findsOneWidget);
    await tester.tap(_toggle('Ver 1 cita'));
    await tester.pumpAndSettle();
    expect(find.text('Cita sintetica 1'), findsOneWidget);
    await tester.tap(_toggle('Ocultar citas').first);
    await tester.pumpAndSettle();
    expect(find.text('Cita sintetica 1'), findsNothing);
    expect(find.text('Cita sintetica 2'), findsOneWidget);
  });

  testWidgets('Grupo con una sola cita', (tester) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(references: [_ref(1)]),
        ],
      ),
      tab: 'Usos',
    );
    expect(find.text('Cita sintetica 1'), findsNothing);
    await tester.tap(_toggle('Ver 1 cita'));
    await tester.pumpAndSettle();
    expect(find.text('Cita sintetica 1'), findsOneWidget);
  });

  testWidgets('Sin etiqueta ni aclaración por grupo', (tester) async {
    await showPassport(
      tester,
      consolidatedPlant('lavandula-angustifolia'),
      tab: 'Usos',
    );
    for (var i = 0; i < 2; i++) {
      expect(find.text('Registro tradicional'), findsNothing);
      expect(find.text('Países'), findsNothing);
      expect(find.text('Es un registro, no un consejo de uso.'), findsNothing);
      expect(find.text(PassportTexts.usesNotice), findsOneWidget);
      await tester.tap(find.byType(TextButton).first);
      await tester.pumpAndSettle();
    }
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

  testWidgets('el aviso fijo y los textos de grupo no tienen lenguaje de '
      'eficacia', (tester) async {
    final pattern = RegExp(
      r'(?<![\p{L}])(cura|curar|trata|tratar|alivia|calma|ayuda|mejora|'
      r'previene|remedio|eficaz|efectivo)(?![\p{L}])',
      caseSensitive: false,
      unicode: true,
    );
    for (final text in [
      PassportTexts.usesNotice,
      PassportTexts.hideCitations,
      PassportTexts.showCitations(1),
      PassportTexts.showCitations(5),
      PassportTexts.useGroupSummary(3, const ['China']),
    ]) {
      expect(pattern.hasMatch(text), isFalse, reason: text);
    }
  });

  testWidgets('Cita sin resolver visible al desplegar', (tester) async {
    final plant = consolidatedPlant('capsella-bursa-pastoris');
    await showPassport(tester, plant, tab: 'Usos');
    expect(find.text('Woi.Syria (sin resolver)'), findsNothing);
    final hemorrhage = plant.useGroups.firstWhere(
      (g) => g.activity == 'Hemorragia',
    );
    expect(hemorrhage.references.any((r) => !r.resolved), isTrue);
    final index = plant.useGroups.indexOf(hemorrhage);
    final control = find.byType(TextButton).at(index);
    await tester.ensureVisible(control);
    await tester.tap(control);
    await tester.pumpAndSettle();
    final unresolved = find.textContaining('(sin resolver)');
    expect(unresolved, findsWidgets);
    final dimmed = tester.widget<Text>(unresolved.first);
    final resolvedRef = hemorrhage.references.firstWhere((r) => r.resolved);
    final resolved = tester.widget<Text>(find.text(resolvedRef.citation));
    expect(dimmed.style!.fontStyle, FontStyle.italic);
    expect(dimmed.style!.color, isNot(resolved.style!.color));
    expect(resolved.style!.fontStyle, isNot(FontStyle.italic));
    expect(find.text('Hemorragia'), findsOneWidget);
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
    await tester.tap(_toggle('Ver 1 cita'));
    await tester.pumpAndSettle();
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
          _group(count: 3, references: [_ref(1)]),
        ],
      ),
      tab: 'Usos',
    );
    expect(find.text('Actividad sintetica'), findsOneWidget);
    expect(find.text('3 registros'), findsOneWidget);
    expect(find.textContaining('·'), findsNothing);
  });

  testWidgets('Países tal como llegan', (tester) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(
            count: 5,
            countries: const ['China', 'Otros lugares', 'Trinidad'],
            references: [_ref(1)],
          ),
        ],
      ),
      tab: 'Usos',
    );
    expect(
      find.text('5 registros · China, Otros lugares, Trinidad'),
      findsOneWidget,
    );
  });

  testWidgets('Sin registro elegible', (tester) async {
    for (final plant in [consolidatedPlant('acinos-sp'), _synthetic()]) {
      await showPassport(tester, plant, tab: 'Usos');
      expect(find.text(PassportTexts.noUses), findsOneWidget);
      expect(find.byType(TextButton), findsNothing);
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
    await tester.ensureVisible(find.byType(TextButton).last);
    await tester.pump();
    await tester.tap(find.byType(TextButton).last);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text(last.references.last.citation));
    expect(find.text(last.references.last.citation), findsOneWidget);
    for (final text in tester.widgetList<Text>(find.byType(Text))) {
      expect(text.overflow, isNot(TextOverflow.ellipsis));
      expect(text.maxLines, isNull);
    }
  });

  testWidgets('Muchos usos: desplegar en medio conserva la posición', (
    tester,
  ) async {
    final groups = [
      for (var i = 0; i < 46; i++)
        _group(activity: 'Actividad $i', references: [_ref(i), _ref(i + 100)]),
    ];
    await showPassport(tester, _synthetic(groups: groups), tab: 'Usos');
    final scrollable = find
        .descendant(
          of: find.byType(CustomScrollView),
          matching: find.byType(Scrollable),
        )
        .first;
    await tester.scrollUntilVisible(
      find.text('Actividad 23'),
      300,
      scrollable: scrollable,
    );
    final position = tester.state<ScrollableState>(scrollable).position;
    // The built range is lazy: the control of the group is the one inside the
    // column that holds its activity.
    final below = find.descendant(
      of: find
          .ancestor(
            of: find.text('Actividad 23'),
            matching: find.byType(Column),
          )
          .first,
      matching: find.byType(TextButton),
    );
    expect(below, findsOneWidget);
    await tester.ensureVisible(below);
    await tester.pump();
    final offset = position.pixels;
    final controlTop = tester.getTopLeft(below).dy;
    final activityTop = tester.getTopLeft(find.text('Actividad 23')).dy;
    final nextTop = tester.getTopLeft(find.text('Actividad 24')).dy;
    await tester.tap(below);
    await tester.pumpAndSettle();
    expect(position.pixels, offset);
    expect(tester.getTopLeft(find.text('Actividad 23')).dy, activityTop);
    expect(tester.getTopLeft(below).dy, controlTop);
    expect(find.text('Cita sintetica 23'), findsOneWidget);
    expect(
      tester.getTopLeft(find.text('Actividad 24')).dy,
      greaterThan(nextTop),
    );
    await tester.tap(below);
    await tester.pumpAndSettle();
    expect(position.pixels, offset);
    expect(tester.getTopLeft(find.text('Actividad 24')).dy, nextTop);
    expect(find.text('Cita sintetica 23'), findsNothing);
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
    expect(find.text('Cita antigua'), findsNothing);
    expect(find.text('1 registro'), findsOneWidget);
    await tester.tap(_toggle('Ver 1 cita'));
    await tester.pumpAndSettle();
    expect(find.text('Cita antigua'), findsOneWidget);
  });
}
