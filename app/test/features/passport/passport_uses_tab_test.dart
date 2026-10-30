import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_style.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:boticario_ai/features/passport/presentation/passport_uses_tab.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../support/fake_catalog_api.dart';
import '../../support/fake_url_launcher.dart';

import 'passport_test_support.dart';

const _line = ValueKey('uses-notice-line');
const _dialog = ValueKey('uses-notice-dialog');

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
  GlossaryEntry? glossary,
}) => UseGroup(
  activity: activity,
  activitySource: activitySource,
  count: count,
  countries: countries,
  references: references,
  glossary: glossary,
);

GlossaryEntry _glossary({
  String term = 'Diurético',
  String text = 'Que aumenta o facilita la producción y excreción de orina.',
  String sourceName = 'Wikcionario',
  String? url = 'https://es.wiktionary.org/w/index.php?title=x&oldid=1',
  bool adapted = false,
}) => GlossaryEntry(
  term: term,
  text: text,
  sourceName: sourceName,
  url: url,
  adapted: adapted,
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
    expect(first.countries, isNotEmpty);
    expect(
      find.text(PassportTexts.useGroupPlaces(first.countries)!),
      findsWidgets,
    );
    expect(find.textContaining(RegExp(r'\d+ registros?')), findsNothing);
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
      find.text('Lugares: China, Otros lugares, Trinidad'),
      findsOneWidget,
    );
    expect(find.textContaining(RegExp(r'\d+ registros?')), findsNothing);
    expect(find.textContaining('·'), findsNothing);
    expect(_toggle('Ver 2 citas'), findsOneWidget);
  });

  testWidgets('2 registros y 1 cita muestran solo Ver 1 cita', (tester) async {
    await showPassport(
      tester,
      _synthetic(
        groups: [
          _group(count: 2, references: [_ref(1)]),
        ],
      ),
      tab: 'Usos',
    );
    expect(_toggle('Ver 1 cita'), findsOneWidget);
    expect(find.textContaining(RegExp(r'\d+ registros?')), findsNothing);
    expect(find.textContaining('Ver 2'), findsNothing);
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
      expect(find.text(PassportTexts.usesNoticeLabel), findsOneWidget);
      await tester.tap(find.byType(TextButton).first);
      await tester.pumpAndSettle();
    }
  });

  testWidgets('Aviso fijo de usos tradicionales en una línea que abre el '
      'diálogo', (tester) async {
    for (final id in [
      'lavandula-angustifolia',
      'acinos-sp',
      'eucalyptus-globulus',
    ]) {
      await showPassport(tester, consolidatedPlant(id), tab: 'Usos');
      expect(
        find.text(PassportTexts.usesNoticeLabel),
        findsOneWidget,
        reason: id,
      );
      // The full text is not in the tab, only in the dialog.
      expect(find.text(PassportTexts.usesNotice), findsNothing, reason: id);
      final line = tester.getTopLeft(find.text(PassportTexts.usesNoticeLabel));
      final below = find.text(
        id == 'acinos-sp'
            ? PassportTexts.noUses
            : consolidatedPlant(id).useGroups.first.activity,
      );
      expect(
        tester.getTopLeft(below.first).dy,
        greaterThan(line.dy),
        reason: id,
      );
    }
    // The line is not shown in the other tabs.
    await showPassport(tester, consolidatedPlant('acinos-sp'));
    expect(find.text(PassportTexts.usesNoticeLabel), findsNothing);
  });

  testWidgets('la línea está también con una planta sin usos', (tester) async {
    await showPassport(tester, _synthetic(), tab: 'Usos');
    expect(find.byKey(_line), findsOneWidget);
    expect(find.text(PassportTexts.noUses), findsOneWidget);
  });

  testWidgets('la línea es un botón de al menos 48 dp con su rótulo', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    await showPassport(
      tester,
      consolidatedPlant('lavandula-angustifolia'),
      tab: 'Usos',
    );
    final size = tester.getSize(find.byKey(_line));
    expect(size.height, greaterThanOrEqualTo(48));
    expect(size.width, greaterThanOrEqualTo(48));
    final buttons = <SemanticsData>[];
    void visit(SemanticsNode node) {
      final data = node.getSemanticsData();
      if (data.label == PassportTexts.usesNoticeLabel) buttons.add(data);
      node.visitChildren((child) {
        visit(child);
        return true;
      });
    }

    // The test binding builds semantics on its own (deprecated) pipeline owner.
    // ignore: deprecated_member_use
    visit(tester.binding.pipelineOwner.semanticsOwner!.rootSemanticsNode!);
    expect(buttons, hasLength(1));
    expect(buttons.single.flagsCollection.isButton, isTrue);
    handle.dispose();
  });

  testWidgets('el diálogo muestra el texto completo y se cierra con '
      '«Entendido»', (tester) async {
    await showPassport(
      tester,
      consolidatedPlant('lavandula-angustifolia'),
      tab: 'Usos',
    );
    await tester.tap(find.byKey(_line));
    await tester.pumpAndSettle();
    expect(find.byKey(_dialog), findsOneWidget);
    expect(find.text(PassportTexts.usesNotice), findsOneWidget);
    expect(find.text(PassportTexts.usesNoticeLabel), findsNWidgets(2));
    await tester.tap(find.text(PassportTexts.usesNoticeClose));
    await tester.pumpAndSettle();
    expect(find.byKey(_dialog), findsNothing);
    expect(find.text(PassportTexts.usesNotice), findsNothing);
  });

  testWidgets('el diálogo se cierra con Atrás y tocando fuera', (tester) async {
    await showPassport(tester, _synthetic(), tab: 'Usos');
    await tester.tap(find.byKey(_line));
    await tester.pumpAndSettle();
    expect(find.byKey(_dialog), findsOneWidget);
    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();
    expect(find.byKey(_dialog), findsNothing);

    await tester.tap(find.byKey(_line));
    await tester.pumpAndSettle();
    expect(find.byKey(_dialog), findsOneWidget);
    await tester.tapAt(const Offset(2, 2));
    await tester.pumpAndSettle();
    expect(find.byKey(_dialog), findsNothing);
  });

  for (final scale in [1.0, 2.0]) {
    testWidgets('la línea y el diálogo a 360x640 al ${(scale * 100).round()} '
        '%, sin truncado', (tester) async {
      tester.view.physicalSize = const Size(360, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        MaterialApp(
          theme: buildBoticarioTheme(),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: TextScaler.linear(scale)),
            child: child!,
          ),
          home: Scaffold(
            body: SingleChildScrollView(
              child: PassportUsesTab(
                plant: _synthetic(),
                expandedGroups: const {},
                onToggleGroup: (_) {},
              ),
            ),
          ),
        ),
      );
      void expectNotTruncated(Finder finder) {
        final paragraph = tester.renderObject<RenderParagraph>(finder);
        expect(paragraph.didExceedMaxLines, isFalse);
        expect(paragraph.overflow, isNot(TextOverflow.ellipsis));
      }

      expectNotTruncated(find.text(PassportTexts.usesNoticeLabel));
      expect(tester.takeException(), isNull);
      await tester.tap(find.byKey(_line));
      await tester.pumpAndSettle();
      expectNotTruncated(find.text(PassportTexts.usesNotice));
      // The text can scroll inside the dialog; the button stays on screen.
      final screen = Offset.zero & const Size(360, 640);
      expect(
        screen.contains(
          tester.getBottomRight(find.text(PassportTexts.usesNoticeClose)),
        ),
        isTrue,
      );
      expect(tester.takeException(), isNull);
      await tester.tap(find.text(PassportTexts.usesNoticeClose));
      await tester.pumpAndSettle();
      expect(find.byKey(_dialog), findsNothing);
    });
  }

  testWidgets('el aviso fijo aclara que las explicaciones son generales', (
    tester,
  ) async {
    expect(
      PassportTexts.usesNotice,
      endsWith(
        'Las explicaciones de términos son definiciones generales de '
        'diccionario o enciclopedia, no afirmaciones sobre esta planta.',
      ),
    );
    expect(PassportTexts.glossaryLabel, 'Significado general del término');
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
      PassportTexts.usesNoticeLabel,
      PassportTexts.usesNoticeClose,
      PassportTexts.glossaryLabel,
      PassportTexts.hideCitations,
      PassportTexts.showCitations(1),
      PassportTexts.showCitations(5),
      PassportTexts.useGroupPlaces(const ['China'])!,
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
    expect(find.textContaining('Lugares'), findsNothing);
    expect(find.textContaining(RegExp(r'\d+ registros?')), findsNothing);
    expect(find.textContaining('·'), findsNothing);
    expect(_toggle('Ver 1 cita'), findsOneWidget);
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
      find.text('Lugares: China, Otros lugares, Trinidad'),
      findsOneWidget,
    );
  });

  testWidgets('Sin registro elegible', (tester) async {
    for (final plant in [consolidatedPlant('acinos-sp'), _synthetic()]) {
      await showPassport(tester, plant, tab: 'Usos');
      expect(find.text(PassportTexts.noUses), findsOneWidget);
      expect(find.byType(TextButton), findsNothing);
      expect(find.text(PassportTexts.usesNoticeLabel), findsOneWidget);
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
    expect(find.textContaining(RegExp(r'\d+ registros?')), findsNothing);
    await tester.tap(_toggle('Ver 1 cita'));
    await tester.pumpAndSettle();
    expect(find.text('Cita antigua'), findsOneWidget);
  });

  group('explicación del término', () {
    late FakeUrlLauncher launcher;

    setUp(() {
      launcher = FakeUrlLauncher();
      UrlLauncherPlatform.instance = launcher;
    });

    Finder line(String text) => plainText(text);

    Future<void> show(WidgetTester tester, List<UseGroup> groups) =>
        showPassport(tester, _synthetic(groups: groups), tab: 'Usos');

    testWidgets('Wikcionario: etiqueta, línea y fuente enlazada', (
      tester,
    ) async {
      final glossary = _glossary();
      await show(tester, [
        _group(
          activity: 'Diurético',
          count: 2,
          countries: const ['China'],
          references: [_ref(1)],
          glossary: glossary,
        ),
      ]);
      expect(find.text('Significado general del término'), findsOneWidget);
      const row =
          'Diurético: «Que aumenta o facilita la producción y excreción de '
          'orina.» (Wikcionario)';
      expect(line(row), findsOneWidget);
      expect(linkSpansOf(tester, line(row)).map((s) => s.text), [
        'Wikcionario',
      ]);
      // Above the data line, below the title.
      final title = tester.getTopLeft(find.text('Diurético')).dy;
      final label = tester
          .getTopLeft(find.text('Significado general del término'))
          .dy;
      final data = tester.getTopLeft(find.text('Lugares: China')).dy;
      expect(title, lessThan(label));
      expect(label, lessThan(tester.getTopLeft(line(row)).dy));
      expect(tester.getTopLeft(line(row)).dy, lessThan(data));
      // The label is secondary text, smaller and gray.
      final labelText = tester.widget<Text>(
        find.text('Significado general del término'),
      );
      expect(labelText.style!.color, passportMuted);
      expect(
        labelText.style!.fontSize!,
        lessThan(tester.widget<Text>(find.text('Diurético')).style!.fontSize!),
      );
    });

    testWidgets('Wikipedia literal', (tester) async {
      await show(tester, [
        _group(
          glossary: _glossary(
            term: 'Tónico',
            text: 'Texto sintético.',
            sourceName: 'Wikipedia',
            url: 'https://es.wikipedia.org/w/index.php?title=T&oldid=1',
          ),
        ),
      ]);
      expect(line('Tónico: «Texto sintético.» (Wikipedia)'), findsOneWidget);
    });

    testWidgets('Wikipedia adaptada dice «adaptado de»', (tester) async {
      await show(tester, [
        _group(
          glossary: _glossary(
            term: 'Tónico',
            text: 'Texto sintético.',
            sourceName: 'Wikipedia',
            adapted: true,
          ),
        ),
      ]);
      const row = 'Tónico: «Texto sintético.» (adaptado de Wikipedia)';
      expect(line(row), findsOneWidget);
      expect(linkSpansOf(tester, line(row)).map((s) => s.text), ['Wikipedia']);
    });

    testWidgets('actividad con calificador conserva el título', (tester) async {
      await show(tester, [
        _group(
          activity: 'Antídoto (escorpión)',
          glossary: _glossary(term: 'Antídoto', text: 'Texto sintético.'),
        ),
      ]);
      expect(find.text('Antídoto (escorpión)'), findsOneWidget);
      expect(
        line('Antídoto: «Texto sintético.» (Wikcionario)'),
        findsOneWidget,
      );
    });

    testWidgets('sin explicación: sin etiqueta ni espacio vacío', (
      tester,
    ) async {
      await show(tester, [
        _group(activity: 'Fiebre', countries: const ['China']),
      ]);
      expect(find.text('Significado general del término'), findsNothing);
      expect(find.textContaining(': «'), findsNothing);
      final title = tester.getBottomLeft(find.text('Fiebre')).dy;
      final data = tester.getTopLeft(find.text('Lugares: China')).dy;
      expect(data - title, lessThanOrEqualTo(4));
    });

    testWidgets('actividad sensible: sin explicación', (tester) async {
      const sensitive = 'Uso tradicional, sin eficacia demostrada: cáncer';
      await show(tester, [_group(activity: sensitive)]);
      expect(find.text(sensitive), findsOneWidget);
      expect(find.text('Significado general del término'), findsNothing);
    });

    testWidgets('el enlace se abre solo si es https y no se ve la URL', (
      tester,
    ) async {
      final glossary = _glossary();
      await show(tester, [_group(glossary: glossary)]);
      expect(find.textContaining('http'), findsNothing);
      expect(
        find.textContaining('wiktionary', findRichText: true),
        findsNothing,
      );
      const row =
          'Diurético: «Que aumenta o facilita la producción y excreción de '
          'orina.» (Wikcionario)';
      await tapSpan(tester, line(row), 'Wikcionario');
      expect(launcher.launched, [glossary.url]);
    });

    testWidgets('URL no https: texto plano sin enlace', (tester) async {
      for (final url in ['http://es.wiktionary.org/x', null, 'javascript:x']) {
        await show(tester, [_group(glossary: _glossary(url: url))]);
        expect(find.textContaining('(Wikcionario)'), findsOneWidget);
        expect(
          linkSpansOf(tester, find.textContaining('Wikcionario')),
          isEmpty,
        );
      }
      expect(launcher.launched, isEmpty);
    });

    testWidgets('el plegado de citas sigue funcionando con explicación', (
      tester,
    ) async {
      await show(tester, [
        _group(references: [_ref(1)], glossary: _glossary()),
        _group(activity: 'Otra', references: [_ref(2)]),
      ]);
      await tester.tap(_toggle('Ver 1 cita').first);
      await tester.pumpAndSettle();
      expect(find.text('Cita sintetica 1'), findsOneWidget);
      expect(find.text('Cita sintetica 2'), findsNothing);
    });

    testWidgets('backend anterior (grupos derivados de uses): sin etiqueta', (
      tester,
    ) async {
      final plant = parsePlant(apiFixture('plant_lavandula-angustifolia.json'));
      await showPassport(tester, plant, tab: 'Usos');
      expect(find.text('Significado general del término'), findsNothing);
    });

    testWidgets(
      'fixture derivada: la etiqueta aparece en los grupos con texto',
      (tester) async {
        final plant = parsePlant(
          apiFixture(
            'consolidated_lavandula-angustifolia_glossary-derived.json',
          ),
        );
        await showPassport(tester, plant, tab: 'Usos');
        final withText = plant.useGroups.where((g) => g.glossary != null);
        expect(withText, hasLength(3));
        expect(
          find.text('Significado general del término', skipOffstage: false),
          findsNWidgets(3),
        );
      },
    );
  });
}
