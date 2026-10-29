import 'dart:io';
import 'dart:typed_data';

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/data/plant_image_policy.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/passport/presentation/plant_passport_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart' show FontLoader;
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

/// Parses a real consolidated API fixture (`consolidated_<id>.json`).
Plant consolidatedPlant(String id) =>
    parsePlant(apiFixture('consolidated_$id.json'));

/// Pumps the passport of [plant] and selects [tab] (`General` by default).
Future<void> showPassport(
  WidgetTester tester,
  Plant plant, {
  String tab = 'General',
  ImageProvider? Function(String? url)? imageProviderFor,
}) async {
  tester.view.physicalSize = const Size(360, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  // A fresh tree, so the scroll position of a previous pump is not reused.
  await tester.pumpWidget(const SizedBox.shrink());
  await tester.pumpWidget(
    MaterialApp(
      theme: buildBoticarioTheme(),
      home: PlantPassportPage(
        plant: plant,
        onBack: () {},
        onHome: () {},
        imageProviderFor:
            imageProviderFor ?? PlantImagePolicy.thumbnailProviderFor,
      ),
    ),
  );
  if (tab != 'General') {
    await tester.tap(find.text(tab));
    await tester.pumpAndSettle();
  }
}

/// The `TextSpan`s with text under [root] (a `Text.rich` finder).
List<TextSpan> textSpansOf(WidgetTester tester, Finder root) {
  final rich = tester.widget<RichText>(
    find.descendant(of: root, matching: find.byType(RichText)).first,
  );
  final spans = <TextSpan>[];
  rich.text.visitChildren((span) {
    if (span is TextSpan && span.text != null) spans.add(span);
    return true;
  });
  return spans;
}

/// The spans of [root] that are links (they carry a recognizer).
List<TextSpan> linkSpansOf(WidgetTester tester, Finder root) => [
  for (final span in textSpansOf(tester, root))
    if (span.recognizer != null) span,
];

/// Center of [substring] inside the first paragraph under [root], on screen.
Offset spanCenter(WidgetTester tester, Finder root, String substring) {
  final render = tester.renderObject<RenderParagraph>(
    find.descendant(of: root, matching: find.byType(RichText)).first,
  );
  final text = render.text.toPlainText(includeSemanticsLabels: false);
  final start = text.indexOf(substring);
  expect(start, greaterThanOrEqualTo(0), reason: '"$substring" in "$text"');
  final boxes = render.getBoxesForSelection(
    TextSelection(baseOffset: start, extentOffset: start + substring.length),
  );
  final rect = boxes.first.toRect();
  return render.localToGlobal(rect.center);
}

Future<void> tapSpan(WidgetTester tester, Finder root, String substring) async {
  await tester.tapAt(spanCenter(tester, root, substring));
  await tester.pump();
}

Future<void> longPressSpan(
  WidgetTester tester,
  Finder root,
  String substring,
) async {
  await tester.longPressAt(spanCenter(tester, root, substring));
  await tester.pump();
}

/// Every semantics node on screen announced as a link (needs
/// `tester.ensureSemantics()`).
List<SemanticsData> linkSemantics(WidgetTester tester) {
  final links = <SemanticsData>[];
  void visit(SemanticsNode node) {
    final data = node.getSemanticsData();
    if (data.flagsCollection.isLink) links.add(data);
    node.visitChildren((child) {
      visit(child);
      return true;
    });
  }

  // The test binding builds semantics on its own (deprecated) pipeline owner.
  // ignore: deprecated_member_use
  final owner = tester.binding.pipelineOwner.semanticsOwner!;
  visit(owner.rootSemanticsNode!);
  return links;
}

/// `Text` widgets whose visible text (without semantic replacements) is
/// [text]. `find.text` would match the announced label of linked spans.
Finder plainText(String text) => find.byWidgetPredicate(
  (w) =>
      w is Text &&
      (w.data ?? w.textSpan?.toPlainText(includeSemanticsLabels: false)) ==
          text,
  description: 'Text "$text"',
);

/// The text of each rendered line of [paragraph], by character position.
List<String> paragraphLines(RenderParagraph paragraph) {
  final text = paragraph.text.toPlainText(includeSemanticsLabels: false);
  final lines = <String>[];
  double? lastTop;
  for (var i = 0; i < text.length; i++) {
    final boxes = paragraph.getBoxesForSelection(
      TextSelection(baseOffset: i, extentOffset: i + 1),
    );
    if (boxes.isEmpty) {
      if (lines.isNotEmpty) lines[lines.length - 1] += text[i];
      continue;
    }
    final top = boxes.first.top.roundToDouble();
    if (lastTop == null || top > lastTop + 1) {
      lines.add('');
      lastTop = top;
    }
    lines[lines.length - 1] += text[i];
  }
  return lines;
}

/// Loads the real Roboto so line breaks match a device (the default test font
/// has square glyphs and wraps far earlier).
Future<void> loadRobotoForLayout() async {
  final loader = FontLoader('Roboto');
  for (final name in ['Roboto-Regular.ttf', 'Roboto-Medium.ttf']) {
    loader.addFont(
      Future.value(
        ByteData.sublistView(
          File('test/fixtures/fonts/$name').readAsBytesSync(),
        ),
      ),
    );
  }
  await loader.load();
}
