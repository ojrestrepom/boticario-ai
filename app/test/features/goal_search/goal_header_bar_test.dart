import 'dart:io';

import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/goal_search/presentation/goal_list_shell.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
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
  });

  Future<void> show(WidgetTester tester, String title, double scale) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBoticarioTheme(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: TextScaler.linear(scale)),
          child: child!,
        ),
        home: Scaffold(
          body: GoalHeaderBar(title: title, backLabel: 'Volver', onBack: () {}),
        ),
      ),
    );
  }

  double oneLine(WidgetTester tester, Finder title) {
    final style = tester.widget<Text>(title).style!;
    final painter = TextPainter(
      text: TextSpan(text: 'R', style: style),
      textDirection: TextDirection.ltr,
      textScaler: MediaQuery.textScalerOf(tester.element(title)),
    )..layout();
    return painter.height;
  }

  testWidgets('a long single-word title stays on one line at 200 %', (
    tester,
  ) async {
    await show(tester, 'Recomendaciones', 2);
    final title = find.text('Recomendaciones');
    expect(
      tester.getSize(title).height,
      lessThanOrEqualTo(oneLine(tester, title)),
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('a very long word shrinks the title until it fits', (
    tester,
  ) async {
    await show(tester, 'Electroencefalografistas', 2);
    final title = find.text('Electroencefalografistas');
    expect(
      tester.getSize(title).height,
      lessThanOrEqualTo(oneLine(tester, title)),
    );
  });

  testWidgets('a multi-word title keeps its size and wraps between words', (
    tester,
  ) async {
    await show(tester, '¿Qué deseas lograr?', 2);
    final title = find.text('¿Qué deseas lograr?');
    expect(tester.widget<Text>(title).textScaler, isNull);
    expect(tester.getSize(title).height, greaterThan(oneLine(tester, title)));
  });

  testWidgets('at 100 % the title is not reduced', (tester) async {
    await show(tester, 'Recomendaciones', 1);
    expect(
      tester.widget<Text>(find.text('Recomendaciones')).textScaler,
      isNull,
    );
  });
}
