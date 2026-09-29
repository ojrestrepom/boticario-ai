import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

Finder get _incrementButton => find.widgetWithText(FilledButton, 'Incrementar');

/// Router real de la app a través de su API pública, sin tocar campos privados.
GoRouter _currentRouter(WidgetTester tester) {
  return GoRouter.of(tester.element(find.byType(HomePage)));
}

void main() {
  testWidgets('arranca en / con la home, el saludo y Contador: 0', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    // Ruta inicial y pantalla renderizada vía API pública de go_router.
    expect(_currentRouter(tester).state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);

    expect(find.text('Hola, Boticario AI'), findsOneWidget);
    expect(find.text('Contador: 0'), findsOneWidget);
    expect(_incrementButton, findsOneWidget);

    // Se aplica el tema real de la app, no uno genérico del harness.
    final theme = Theme.of(tester.element(find.byType(HomePage)));
    expect(theme.colorScheme, buildBoticarioTheme().colorScheme);
  });

  testWidgets('un tap incrementa el contador', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    await tester.tap(_incrementButton);
    await tester.pump();

    expect(find.text('Contador: 1'), findsOneWidget);
  });

  testWidgets('un ProviderScope nuevo resetea el contador y aísla el router', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    final firstRouter = _currentRouter(tester);
    await tester.tap(_incrementButton);
    await tester.pump();
    expect(find.text('Contador: 1'), findsOneWidget);

    // Un scope nuevo reemplaza el árbol: Flutter desmonta el ProviderScope
    // anterior (sin `dispose` manual) y monta uno limpio.
    await tester.pumpWidget(
      ProviderScope(key: UniqueKey(), child: const BoticarioApp()),
    );
    await tester.pumpAndSettle();

    final secondRouter = _currentRouter(tester);

    // Router nuevo por scope y contador reiniciado a 0.
    expect(identical(firstRouter, secondRouter), isFalse);
    expect(secondRouter.state.uri.path, '/');
    expect(find.text('Contador: 0'), findsOneWidget);
    expect(_incrementButton, findsOneWidget);
  });
}
