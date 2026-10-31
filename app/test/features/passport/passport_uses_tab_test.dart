import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_consolidated.dart';
import 'package:boticario_ai/features/passport/presentation/passport_style.dart';
import 'package:boticario_ai/features/passport/presentation/passport_texts.dart';
import 'package:boticario_ai/features/passport/presentation/passport_uses_tab.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart' show FontLoader;
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

/// Icon button of the citations control whose tooltip is [label].
Finder _toggle(String label) =>
    find.byWidgetPredicate((w) => w is IconButton && w.tooltip == label);

/// Every collapsed `Ver N citas` control, in the order of the groups.
Finder _controls() => find.byWidgetPredicate(
  (w) =>
      w is IconButton && RegExp(r'^Ver \d+ citas?$').hasMatch(w.tooltip ?? ''),
);

const _diureticoRow =
    'Diurético: «Que aumenta o facilita la producción y excreción de '
    'orina.» (Wikcionario)';

/// Icon buttons of the explanation control, shown or hidden.
Finder _glossaryControls() => find.byWidgetPredicate(
  (w) =>
      w is IconButton &&
      (w.tooltip == PassportTexts.showGlossary ||
          w.tooltip == PassportTexts.hideGlossary),
);

/// The row of a group's title, with its icons on the right.
Finder _titleRow() =>
    find.byWidgetPredicate((w) => w.runtimeType.toString() == '_TitleRow');

/// Loads the icon font of the Flutter SDK running the tests: without it the
/// icons are drawn as squares.
Future<void> _loadMaterialIcons(WidgetTester tester) async {
  // The test environment draws icons as squares unless the font is loaded:
  // use the one that ships with the Flutter SDK running the tests.
  final root = Platform.environment['FLUTTER_ROOT'];
  expect(root, isNotNull, reason: 'FLUTTER_ROOT no está definido');
  final font = File(
    '$root/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf',
  );
  expect(font.existsSync(), isTrue, reason: font.path);
  final loader = FontLoader('MaterialIcons')
    ..addFont(Future.value(ByteData.sublistView(font.readAsBytesSync())));
  await tester.runAsync(loader.load);
}

/// Raw pixels of [icon] drawn at 20 dp in the passport green.
Future<List<int>> _iconPixels(WidgetTester tester, IconData icon) async {
  final key = GlobalKey();
  await tester.pumpWidget(
    Directionality(
      textDirection: TextDirection.ltr,
      child: Center(
        child: RepaintBoundary(
          key: key,
          child: Icon(icon, size: 20, color: passportGreen),
        ),
      ),
    ),
  );
  await tester.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 100)),
  );
  await tester.pumpAndSettle();
  final boundary =
      key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
  return (await tester.runAsync(() async {
    final image = await boundary.toImage(pixelRatio: 4);
    final data = await image.toByteData();
    return data!.buffer.asUint8List().toList();
  }))!;
}

void main() {
  testWidgets('Registro tradicional elegible', (tester) async {
    final plant = consolidatedPlant('lavandula-angustifolia');
    await showPassport(tester, plant, tab: 'Usos');
    expect(plant.useGroups, hasLength(11));
    final first = plant.useGroups.first;
    expect(find.text(first.activity), findsOneWidget);
    expect(first.countries, isNotEmpty);
    expect(find.textContaining('Lugares'), findsNothing);
    expect(find.textContaining(RegExp(r'\d+ registros?')), findsNothing);
    expect(_toggle(_showLabel(first)), findsWidgets);
    expect(find.text(PassportTexts.noUses), findsNothing);
  });

  testWidgets('sin línea de datos aunque el grupo trae tres países', (
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
    expect(find.textContaining('Lugares'), findsNothing);
    expect(find.textContaining('China'), findsNothing);
    expect(find.textContaining('Otros lugares'), findsNothing);
    expect(find.textContaining('Trinidad'), findsNothing);
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
      (w) =>
          w is IconButton &&
          RegExp(r'^Ver \d+ citas?$').hasMatch(w.tooltip ?? ''),
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
      await tester.tap(_controls().first);
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
                expandedGlossaries: const {},
                onToggleGlossary: (_) {},
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
    final control = _controls().at(index);
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

  testWidgets('Países tal como llegan no se muestran en el grupo', (
    tester,
  ) async {
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
    expect(find.textContaining('Lugares'), findsNothing);
    expect(find.textContaining('Otros lugares'), findsNothing);
    expect(_toggle('Ver 1 cita'), findsOneWidget);
  });

  testWidgets('Sin registro elegible', (tester) async {
    for (final plant in [consolidatedPlant('acinos-sp'), _synthetic()]) {
      await showPassport(tester, plant, tab: 'Usos');
      expect(find.text(PassportTexts.noUses), findsOneWidget);
      expect(_controls(), findsNothing);
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
    await tester.ensureVisible(_controls().last);
    await tester.pump();
    await tester.tap(_controls().last);
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
      matching: find.byType(IconButton),
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

    Finder label() => find.text(PassportTexts.glossaryLabel);

    Future<void> show(WidgetTester tester, List<UseGroup> groups) =>
        showPassport(tester, _synthetic(groups: groups), tab: 'Usos');

    /// Taps the explanation control number [index] and lets the list settle.
    Future<void> tapGlossary(WidgetTester tester, [int index = 0]) async {
      await tester.tap(_glossaryControls().at(index));
      await tester.pumpAndSettle();
    }

    testWidgets('sin explicación no hay icono de información', (tester) async {
      await show(tester, [
        _group(activity: 'Fiebre', countries: const ['China']),
      ]);
      expect(_glossaryControls(), findsNothing);
      expect(find.byIcon(Icons.info_outline), findsNothing);
      expect(find.byIcon(Icons.info), findsNothing);
      expect(label(), findsNothing);
      expect(_toggle('Ver 0 citas'), findsOneWidget);
    });

    testWidgets('la explicación empieza oculta, se muestra y se oculta al '
        'tocar el icono', (tester) async {
      await show(tester, [_group(glossary: _glossary())]);
      expect(_glossaryControls(), findsOneWidget);
      expect(label(), findsNothing);
      expect(line(_diureticoRow), findsNothing);
      expect(find.byTooltip('Ver significado'), findsOneWidget);

      await tapGlossary(tester);
      expect(label(), findsOneWidget);
      expect(line(_diureticoRow), findsOneWidget);
      expect(find.byTooltip('Ocultar significado'), findsOneWidget);
      expect(find.byTooltip('Ver significado'), findsNothing);

      await tapGlossary(tester);
      expect(label(), findsNothing);
      expect(line(_diureticoRow), findsNothing);
      expect(find.byTooltip('Ver significado'), findsOneWidget);
    });

    testWidgets('Wikcionario: etiqueta, línea y fuente enlazada al abrir', (
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
      await tapGlossary(tester);
      expect(label(), findsOneWidget);
      expect(line(_diureticoRow), findsOneWidget);
      expect(linkSpansOf(tester, line(_diureticoRow)).map((s) => s.text), [
        'Wikcionario',
      ]);
      // Below the title; the icons stay on the title row, above the label.
      final title = tester.getTopLeft(find.text('Diurético')).dy;
      final labelTop = tester.getTopLeft(label()).dy;
      expect(title, lessThan(labelTop));
      expect(labelTop, lessThan(tester.getTopLeft(line(_diureticoRow)).dy));
      expect(tester.getTopLeft(_toggle('Ver 1 cita')).dy, lessThan(labelTop));
      expect(find.textContaining('Lugares'), findsNothing);
      expect(
        (tester.getCenter(find.text('Diurético')).dy -
                tester.getCenter(_toggle('Ver 1 cita')).dy)
            .abs(),
        lessThan(2),
      );
      // The label is secondary text, smaller and gray.
      final labelText = tester.widget<Text>(label());
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
      await tapGlossary(tester);
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
      await tapGlossary(tester);
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
      expect(_glossaryControls(), findsOneWidget);
      await tapGlossary(tester);
      expect(
        line('Antídoto: «Texto sintético.» (Wikcionario)'),
        findsOneWidget,
      );
    });

    testWidgets('actividad sensible: sin explicación ni icono', (tester) async {
      const sensitive = 'Uso tradicional, sin eficacia demostrada: cáncer';
      await show(tester, [_group(activity: sensitive)]);
      expect(find.text(sensitive), findsOneWidget);
      expect(_glossaryControls(), findsNothing);
      expect(label(), findsNothing);
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
      await tapGlossary(tester);
      expect(find.textContaining('http'), findsNothing);
      await tapSpan(tester, line(_diureticoRow), 'Wikcionario');
      expect(launcher.launched, [glossary.url]);
    });

    testWidgets('URL no https: texto plano sin enlace', (tester) async {
      for (final url in ['http://es.wiktionary.org/x', null, 'javascript:x']) {
        await show(tester, [_group(glossary: _glossary(url: url))]);
        await tapGlossary(tester);
        expect(find.textContaining('(Wikcionario)'), findsOneWidget);
        expect(
          linkSpansOf(tester, find.textContaining('Wikcionario')),
          isEmpty,
        );
      }
      expect(launcher.launched, isEmpty);
    });

    testWidgets('la explicación es independiente de las citas', (tester) async {
      await show(tester, [
        _group(references: [_ref(1)], glossary: _glossary()),
      ]);
      // Opening the citations does not open the explanation.
      await tester.tap(_toggle('Ver 1 cita'));
      await tester.pumpAndSettle();
      expect(find.text('Cita sintetica 1'), findsOneWidget);
      expect(label(), findsNothing);
      // Opening the explanation keeps the citations open.
      await tapGlossary(tester);
      expect(label(), findsOneWidget);
      expect(find.text('Cita sintetica 1'), findsOneWidget);
      // Closing the citations keeps the explanation open.
      await tester.tap(_toggle('Ocultar citas'));
      await tester.pumpAndSettle();
      expect(find.text('Cita sintetica 1'), findsNothing);
      expect(label(), findsOneWidget);
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

    testWidgets('el estado de la explicación se conserva al cambiar de '
        'pestaña', (tester) async {
      await show(tester, [_group(glossary: _glossary())]);
      await tapGlossary(tester);
      expect(label(), findsOneWidget);
      await tester.tap(find.text('General'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Usos'));
      await tester.pumpAndSettle();
      expect(label(), findsOneWidget);
      expect(find.byTooltip('Ocultar significado'), findsOneWidget);
    });

    testWidgets('backend anterior (grupos derivados de uses): sin control', (
      tester,
    ) async {
      final plant = parsePlant(apiFixture('plant_lavandula-angustifolia.json'));
      await showPassport(tester, plant, tab: 'Usos');
      expect(_glossaryControls(), findsNothing);
      expect(find.text(PassportTexts.glossaryLabel), findsNothing);
    });

    testWidgets(
      'fixture derivada: el control aparece en los grupos con texto',
      (tester) async {
        final plant = parsePlant(
          apiFixture(
            'consolidated_lavandula-angustifolia_glossary-derived.json',
          ),
        );
        await showPassport(tester, plant, tab: 'Usos');
        final withText = plant.useGroups.where((g) => g.glossary != null);
        expect(withText, hasLength(3));
        expect(_glossaryControls(), findsNWidgets(3));
        expect(find.text(PassportTexts.glossaryLabel), findsNothing);
        for (var i = 0; i < 3; i++) {
          await tapGlossary(tester, i);
        }
        expect(find.text(PassportTexts.glossaryLabel), findsNWidgets(3));
      },
    );

    testWidgets('el control se anuncia como botón con su estado y el '
        'término', (tester) async {
      final handle = tester.ensureSemantics();
      await show(tester, [_group(glossary: _glossary())]);
      final closed = tester
          .getSemantics(_glossaryControls())
          .getSemanticsData();
      expect(closed.label, 'Ver significado de Diurético');
      expect(closed.flagsCollection.isButton, isTrue);
      expect(closed.flagsCollection.isExpanded, ui.Tristate.isFalse);
      await tapGlossary(tester);
      final opened = tester
          .getSemantics(_glossaryControls())
          .getSemanticsData();
      expect(opened.label, 'Ocultar significado de Diurético');
      expect(opened.flagsCollection.isExpanded, ui.Tristate.isTrue);
      handle.dispose();
    });

    testWidgets('el icono de información mide 20 dp, es verde y cambia', (
      tester,
    ) async {
      await show(tester, [_group(glossary: _glossary())]);
      final closedIcon = find.descendant(
        of: _glossaryControls(),
        matching: find.byIcon(Icons.info_outline),
      );
      expect(closedIcon, findsOneWidget);
      expect(tester.widget<Icon>(closedIcon).size, 20);
      expect(tester.widget<Icon>(closedIcon).color, passportGreen);
      await tapGlossary(tester);
      expect(
        find.descendant(
          of: _glossaryControls(),
          matching: find.byIcon(Icons.info),
        ),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: _glossaryControls(),
          matching: find.byIcon(Icons.info_outline),
        ),
        findsNothing,
      );
    });

    testWidgets('el área táctil mide 48 dp y responde cerca de los bordes', (
      tester,
    ) async {
      await show(tester, [_group(glossary: _glossary())]);
      final rect = tester.getRect(_glossaryControls());
      expect(rect.size, const Size(48, 48));
      const inset = 3.0;
      final points = {
        'superior': Offset(rect.center.dx, rect.top + inset),
        'inferior': Offset(rect.center.dx, rect.bottom - inset),
        'izquierdo': Offset(rect.left + inset, rect.center.dy),
        'derecho': Offset(rect.right - inset, rect.center.dy),
        'esquina superior izquierda': rect.topLeft + const Offset(inset, inset),
        'esquina inferior derecha':
            rect.bottomRight - const Offset(inset, inset),
      };
      for (final entry in points.entries) {
        await tester.tapAt(entry.value);
        await tester.pumpAndSettle();
        expect(label(), findsOneWidget, reason: 'mostrar, borde ${entry.key}');
        await tester.tapAt(entry.value);
        await tester.pumpAndSettle();
        expect(label(), findsNothing, reason: 'ocultar, borde ${entry.key}');
      }
    });

    testWidgets('el icono de información va a la izquierda del libro, en la '
        'misma fila', (tester) async {
      await show(tester, [
        _group(
          activity: 'Diurético',
          references: [_ref(1)],
          glossary: _glossary(),
        ),
      ]);
      final info = tester.getRect(_glossaryControls());
      final book = tester.getRect(_toggle('Ver 1 cita'));
      expect(info.right, lessThanOrEqualTo(book.left));
      expect((info.center.dy - book.center.dy).abs(), lessThan(2));
      expect(
        (tester.getCenter(find.text('Diurético')).dy - info.center.dy).abs(),
        lessThan(2),
      );
    });

    testWidgets('los iconos de información plegado y desplegado se dibujan '
        'distintos', (tester) async {
      await _loadMaterialIcons(tester);
      final closed = await _iconPixels(tester, Icons.info_outline);
      final open = await _iconPixels(tester, Icons.info);
      expect(closed.any((b) => b != 0), isTrue, reason: 'glifo cerrado vacío');
      expect(open.any((b) => b != 0), isTrue, reason: 'glifo abierto vacío');
      expect(closed, isNot(equals(open)));
    });

    for (final scale in [1.0, 2.0]) {
      testWidgets('a 360 dp y ${(scale * 100).round()} % de texto con '
          'explicación: sin desbordes, dos iconos a la derecha y primera línea '
          'centrada', (tester) async {
        tester.view.physicalSize = const Size(360, 640);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        const long =
            'Actividad con un nombre bastante largo que ocupa '
            'varias líneas en pantallas angostas';
        for (final name in ['Actividad corta', long]) {
          await tester.pumpWidget(const SizedBox.shrink());
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
                    plant: _synthetic(
                      groups: [
                        _group(
                          activity: name,
                          references: [_ref(1)],
                          glossary: _glossary(),
                        ),
                      ],
                    ),
                    expandedGroups: const {},
                    onToggleGroup: (_) {},
                    expandedGlossaries: const {},
                    onToggleGlossary: (_) {},
                  ),
                ),
              ),
            ),
          );
          expect(tester.takeException(), isNull);
          final row = tester.getRect(_titleRow());
          final info = tester.getRect(_glossaryControls());
          final book = tester.getRect(_toggle('Ver 1 cita'));
          expect(row.height, greaterThanOrEqualTo(48));
          expect(info.size, const Size(48, 48));
          expect(book.size, const Size(48, 48));
          expect(info.top, row.top);
          expect(book.top, row.top);
          expect(book.right, row.right);
          expect(info.right, lessThanOrEqualTo(book.left));
          final text = tester.getRect(find.text(name));
          expect(text.right, lessThanOrEqualTo(info.left));
          // First line of the title centered on the two icons.
          final paragraph = tester.renderObject<RenderParagraph>(
            find.text(name),
          );
          final firstLine = paragraph
              .getBoxesForSelection(
                const TextSelection(baseOffset: 0, extentOffset: 1),
              )
              .first;
          final lineCenter = text.top + (firstLine.top + firstLine.bottom) / 2;
          expect(
            (lineCenter - info.center.dy).abs(),
            lessThan(2),
            reason: '$name a $scale',
          );
          expect(
            (lineCenter - book.center.dy).abs(),
            lessThan(2),
            reason: '$name a $scale',
          );
        }
      });
    }
  });

  group('icono de citas junto al título', () {
    const activity = 'Actividad con icono';

    testWidgets('el icono va a la derecha del título, en su misma fila', (
      tester,
    ) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(activity: activity, references: [_ref(1), _ref(2)]),
          ],
        ),
        tab: 'Usos',
      );
      final title = tester.getRect(find.text(activity));
      final toggle = tester.getRect(_toggle('Ver 2 citas'));
      expect(toggle.left, greaterThanOrEqualTo(title.right));
      expect(
        (tester.getCenter(find.text(activity)).dy -
                tester.getCenter(_toggle('Ver 2 citas')).dy)
            .abs(),
        lessThan(2),
      );
      // Only the icon: no text of the control in the tree.
      expect(find.text('Ver 2 citas'), findsNothing);
      expect(find.text('Ocultar citas'), findsNothing);
    });

    testWidgets('el área táctil mide al menos 48 dp por cada lado', (
      tester,
    ) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(activity: activity, references: [_ref(1)]),
          ],
        ),
        tab: 'Usos',
      );
      final size = tester.getSize(_toggle('Ver 1 cita'));
      expect(size.width, greaterThanOrEqualTo(48));
      expect(size.height, greaterThanOrEqualTo(48));
    });

    testWidgets('el icono es pequeño, verde y cambia al desplegar', (
      tester,
    ) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(activity: activity, references: [_ref(1)]),
          ],
        ),
        tab: 'Usos',
      );
      final closedIcon = find.descendant(
        of: _toggle('Ver 1 cita'),
        matching: find.byIcon(Icons.book_outlined),
      );
      expect(closedIcon, findsOneWidget);
      expect(tester.widget<Icon>(closedIcon).size, 20);
      expect(tester.widget<Icon>(closedIcon).color, passportGreen);
      await tester.tap(_toggle('Ver 1 cita'));
      await tester.pumpAndSettle();
      expect(
        find.descendant(
          of: _toggle('Ocultar citas'),
          matching: find.byIcon(Icons.menu_book),
        ),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: _toggle('Ocultar citas'),
          matching: find.byIcon(Icons.book_outlined),
        ),
        findsNothing,
      );
      expect(find.text('Cita sintetica 1'), findsOneWidget);
    });

    testWidgets('el tooltip y la etiqueta semántica dicen Ver N citas', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(activity: activity, references: [_ref(1), _ref(2), _ref(3)]),
          ],
        ),
        tab: 'Usos',
      );
      expect(find.byTooltip('Ver 3 citas'), findsOneWidget);
      final closed = tester
          .getSemantics(_toggle('Ver 3 citas'))
          .getSemanticsData();
      expect(closed.label, 'Ver 3 citas de $activity');
      expect(closed.flagsCollection.isButton, isTrue);
      expect(closed.flagsCollection.isExpanded, ui.Tristate.isFalse);
      await tester.tap(_toggle('Ver 3 citas'));
      await tester.pumpAndSettle();
      expect(find.byTooltip('Ocultar citas'), findsOneWidget);
      final opened = tester
          .getSemantics(_toggle('Ocultar citas'))
          .getSemanticsData();
      expect(opened.label, 'Ocultar citas de $activity');
      expect(opened.flagsCollection.isExpanded, ui.Tristate.isTrue);
      handle.dispose();
    });

    testWidgets('un grupo con una cita dice Ver 1 cita en el tooltip', (
      tester,
    ) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(activity: activity, references: [_ref(1)]),
          ],
        ),
        tab: 'Usos',
      );
      expect(find.byTooltip('Ver 1 cita'), findsOneWidget);
      expect(find.byTooltip('Ver 1 citas'), findsNothing);
    });

    testWidgets('la explicación y las citas no mueven el icono de la fila', (
      tester,
    ) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(
              activity: activity,
              references: [_ref(1)],
              glossary: _glossary(),
            ),
          ],
        ),
        tab: 'Usos',
      );
      final before = tester.getTopLeft(_toggle('Ver 1 cita'));
      await tester.tap(_toggle('Ver 1 cita'));
      await tester.pumpAndSettle();
      expect(tester.getTopLeft(_toggle('Ocultar citas')), before);
      expect(find.text('Cita sintetica 1'), findsOneWidget);
    });

    testWidgets('países en el grupo: ninguna línea de datos', (tester) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(
              activity: activity,
              countries: const ['Guatemala', 'Honduras', 'México'],
              references: [_ref(1)],
            ),
          ],
        ),
        tab: 'Usos',
      );
      expect(find.textContaining('Lugares'), findsNothing);
      expect(find.textContaining('Guatemala'), findsNothing);
      expect(_toggle('Ver 1 cita'), findsOneWidget);
    });

    testWidgets('los iconos de plegado y desplegado se dibujan distintos', (
      tester,
    ) async {
      await _loadMaterialIcons(tester);
      final closed = await _iconPixels(tester, Icons.book_outlined);
      final open = await _iconPixels(tester, Icons.menu_book);
      expect(closed.any((b) => b != 0), isTrue, reason: 'glifo cerrado vacío');
      expect(open.any((b) => b != 0), isTrue, reason: 'glifo abierto vacío');
      expect(closed, isNot(equals(open)));
    });

    testWidgets('un toque a 3 dp de cada borde del cuadrado de 48x48 '
        'despliega y pliega las citas', (tester) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(activity: activity, references: [_ref(1)]),
          ],
        ),
        tab: 'Usos',
      );
      final rect = tester.getRect(
        find.descendant(of: _titleRow(), matching: find.byType(IconButton)),
      );
      expect(rect.size, const Size(48, 48));
      const inset = 3.0;
      final points = {
        'superior': Offset(rect.center.dx, rect.top + inset),
        'inferior': Offset(rect.center.dx, rect.bottom - inset),
        'izquierdo': Offset(rect.left + inset, rect.center.dy),
        'derecho': Offset(rect.right - inset, rect.center.dy),
        'esquina superior izquierda': rect.topLeft + const Offset(inset, inset),
        'esquina inferior derecha':
            rect.bottomRight - const Offset(inset, inset),
      };
      for (final entry in points.entries) {
        await tester.tapAt(entry.value);
        await tester.pumpAndSettle();
        expect(
          find.text('Cita sintetica 1'),
          findsOneWidget,
          reason: 'desplegar, borde ${entry.key}',
        );
        await tester.tapAt(entry.value);
        await tester.pumpAndSettle();
        expect(
          find.text('Cita sintetica 1'),
          findsNothing,
          reason: 'plegar, borde ${entry.key}',
        );
      }
    });

    testWidgets('el área táctil queda entera dentro de la fila del título', (
      tester,
    ) async {
      await showPassport(
        tester,
        _synthetic(
          groups: [
            _group(activity: activity, references: [_ref(1)]),
          ],
        ),
        tab: 'Usos',
      );
      final row = tester.getRect(_titleRow());
      final button = tester.getRect(
        find.descendant(of: _titleRow(), matching: find.byType(IconButton)),
      );
      expect(row.contains(button.topLeft), isTrue);
      expect(
        row.contains(button.bottomRight - const Offset(0.01, 0.01)),
        isTrue,
      );
      expect(button.top, greaterThanOrEqualTo(row.top));
      expect(button.bottom, lessThanOrEqualTo(row.bottom));
      expect(button.right, lessThanOrEqualTo(row.right));
    });

    for (final scale in [1.0, 2.0]) {
      testWidgets('a 360 dp y ${(scale * 100).round()} % de texto: sin '
          'desbordes, icono a la derecha y primera línea alineada', (
        tester,
      ) async {
        tester.view.physicalSize = const Size(360, 640);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        const long =
            'Actividad con un nombre bastante largo que ocupa '
            'varias líneas en pantallas angostas';
        for (final name in [activity, long]) {
          await tester.pumpWidget(const SizedBox.shrink());
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
                    plant: _synthetic(
                      groups: [
                        _group(activity: name, references: [_ref(1)]),
                      ],
                    ),
                    expandedGroups: const {},
                    onToggleGroup: (_) {},
                    expandedGlossaries: const {},
                    onToggleGlossary: (_) {},
                  ),
                ),
              ),
            ),
          );
          expect(tester.takeException(), isNull);
          final row = tester.getRect(_titleRow());
          final button = tester.getRect(
            find.descendant(of: _titleRow(), matching: find.byType(IconButton)),
          );
          expect(row.height, greaterThanOrEqualTo(48));
          expect(button.top, row.top);
          expect(button.right, row.right);
          expect(button.size, const Size(48, 48));
          final text = tester.getRect(find.text(name));
          expect(text.right, lessThanOrEqualTo(button.left));
          // First line of the title centered on the icon.
          final paragraph = tester.renderObject<RenderParagraph>(
            find.text(name),
          );
          final firstLine = paragraph
              .getBoxesForSelection(
                const TextSelection(baseOffset: 0, extentOffset: 1),
              )
              .first;
          final lineCenter = text.top + (firstLine.top + firstLine.bottom) / 2;
          expect(
            (lineCenter - button.center.dy).abs(),
            lessThan(2),
            reason: '$name a $scale',
          );
        }
      });
    }
  });
}
