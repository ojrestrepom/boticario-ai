import 'package:boticario_ai/main.dart' as app;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

/// Smoke de integración Android: arranca la app real (`main()` con su
/// `ProviderScope`, router y tema reales) y verifica el saludo, el estado
/// inicial del contador y que los taps incrementan de a 1.
///
/// No reinicia providers para simular un arranque en frío del proceso: eso se
/// comprueba en el checklist manual, no aquí.
Finder get _incrementButton => find.widgetWithText(FilledButton, 'Incrementar');

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('arranca la app real y los taps incrementan el contador', (
    tester,
  ) async {
    app.main();
    await tester.pumpAndSettle();

    // Arranque en `/` con el saludo exacto, el botón y el estado inicial 0.
    expect(find.text('Hola, Boticario AI'), findsOneWidget);
    expect(find.text('Contador: 0'), findsOneWidget);
    expect(_incrementButton, findsOneWidget);

    // Una activación suma exactamente 1.
    await tester.tap(_incrementButton);
    await tester.pumpAndSettle();
    expect(find.text('Contador: 1'), findsOneWidget);

    // N activaciones adicionales suman N.
    const activations = 4;
    for (var i = 0; i < activations; i++) {
      await tester.tap(_incrementButton);
      await tester.pumpAndSettle();
    }
    expect(find.text('Contador: ${1 + activations}'), findsOneWidget);
  });
}
