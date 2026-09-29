import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// Harness de widget test: ProviderScope aislado + MaterialApp con el tema real.
///
/// [textScaler] permite simular el escalado de texto del sistema.
Widget _buildHomeHarness({TextScaler textScaler = TextScaler.noScaling}) {
  return ProviderScope(
    child: MaterialApp(
      theme: buildBoticarioTheme(),
      home: Builder(
        builder: (context) {
          return MediaQuery(
            data: MediaQuery.of(context).copyWith(textScaler: textScaler),
            child: const HomePage(),
          );
        },
      ),
    ),
  );
}

Finder get _incrementButton => find.widgetWithText(FilledButton, 'Incrementar');

void main() {
  testWidgets('muestra el saludo exacto', (tester) async {
    await tester.pumpWidget(_buildHomeHarness());

    expect(find.text('Hola, Boticario AI'), findsOneWidget);
  });

  testWidgets('inicia en Contador: 0 con el botón visible', (tester) async {
    await tester.pumpWidget(_buildHomeHarness());

    expect(find.text('Contador: 0'), findsOneWidget);
    expect(_incrementButton, findsOneWidget);
  });

  testWidgets('un tap incrementa a Contador: 1', (tester) async {
    await tester.pumpWidget(_buildHomeHarness());

    await tester.tap(_incrementButton);
    await tester.pump();

    expect(find.text('Contador: 1'), findsOneWidget);
  });

  testWidgets('N taps muestran Contador: N', (tester) async {
    await tester.pumpWidget(_buildHomeHarness());

    const activations = 4;
    for (var i = 0; i < activations; i++) {
      await tester.tap(_incrementButton);
      await tester.pump();
    }

    expect(find.text('Contador: $activations'), findsOneWidget);
  });

  testWidgets('expone semántica accesible del botón y del contador', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    try {
      await tester.pumpWidget(_buildHomeHarness());

      expect(find.bySemanticsLabel('Incrementar'), findsOneWidget);
      expect(find.bySemanticsLabel('Contador: 0'), findsOneWidget);

      await tester.tap(_incrementButton);
      await tester.pump();

      expect(find.bySemanticsLabel('Contador: 1'), findsOneWidget);
    } finally {
      // Liberar incluso si un assert falla: evita leaks y fallos secundarios.
      handle.dispose();
    }
  });

  testWidgets('a 200% de texto en 360x640 dp todo sigue visible y usable', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      _buildHomeHarness(textScaler: TextScaler.linear(2)),
    );

    // Ningún overflow de layout (RenderFlex u otro) debe reportarse.
    expect(tester.takeException(), isNull);

    const viewport = Rect.fromLTWH(0, 0, 360, 640);
    void expectWithinViewport(Rect rect, String label) {
      expect(
        rect.left,
        greaterThanOrEqualTo(viewport.left),
        reason: 'saludo/contador/botón: $label recortado por la izquierda',
      );
      expect(
        rect.top,
        greaterThanOrEqualTo(viewport.top),
        reason: 'saludo/contador/botón: $label recortado por arriba',
      );
      expect(
        rect.right,
        lessThanOrEqualTo(viewport.right),
        reason: 'saludo/contador/botón: $label recortado por la derecha',
      );
      expect(
        rect.bottom,
        lessThanOrEqualTo(viewport.bottom),
        reason: 'saludo/contador/botón: $label recortado por abajo',
      );
    }

    expectWithinViewport(
      tester.getRect(find.text('Hola, Boticario AI')),
      'saludo',
    );
    expectWithinViewport(tester.getRect(find.text('Contador: 0')), 'contador');
    expectWithinViewport(tester.getRect(_incrementButton), 'botón');

    // El botón sigue siendo hittable: el tap actualiza el contador.
    await tester.tap(_incrementButton);
    await tester.pump();

    expect(find.text('Contador: 1'), findsOneWidget);
  });
}
