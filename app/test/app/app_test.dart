import 'package:boticario_ai/app/app.dart';
import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Router real de la app a través de su API pública, sin tocar campos privados.
GoRouter _currentRouter(WidgetTester tester) {
  return GoRouter.of(tester.element(find.byType(HomePage)));
}

void main() {
  testWidgets('arranca en / con HomePage, la marca y sin el demo', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    // Ruta inicial y pantalla renderizada vía API pública de go_router.
    expect(_currentRouter(tester).state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);

    // Contrato de Home: marca, banner y ausencia del saludo/contador demo.
    expect(find.text('Boticario AI'), findsOneWidget);
    expect(
      find.text('Pequeñas esencias, grandes posibilidades'),
      findsOneWidget,
    );
    expect(find.text('Hola, Boticario AI'), findsNothing);
    expect(find.textContaining('Contador'), findsNothing);
    expect(find.text('Incrementar'), findsNothing);

    // Se aplica el tema real de la app, no uno genérico del harness.
    final theme = Theme.of(tester.element(find.byType(HomePage)));
    expect(theme.colorScheme, buildBoticarioTheme().colorScheme);
  });

  testWidgets('activar controles de Home no cambia la ruta /', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    final router = _currentRouter(tester);
    expect(router.state.uri.path, '/');

    // Cabecera y barra inferior están visibles sin scroll.
    await tester.tap(find.byIcon(Icons.person));
    await tester.pump();
    await tester.tap(find.text('Favoritos'));
    await tester.pump();
    await tester.tap(find.text('Perfil'));
    await tester.pump();

    // La interacción emite su acción, pero la ruta y la pantalla no mutan.
    expect(router.state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);
  });

  testWidgets('dos ProviderScope no comparten el GoRouter', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: BoticarioApp()));
    await tester.pumpAndSettle();

    final firstRouter = _currentRouter(tester);

    // Montar un scope nuevo desmonta el anterior: el router del primer scope
    // se libera y el segundo scope queda operativo e independiente.
    await tester.pumpWidget(
      ProviderScope(key: UniqueKey(), child: const BoticarioApp()),
    );
    await tester.pumpAndSettle();

    final secondRouter = _currentRouter(tester);

    expect(identical(firstRouter, secondRouter), isFalse);
    expect(secondRouter.state.uri.path, '/');
    expect(find.byType(HomePage), findsOneWidget);
    expect(find.text('Boticario AI'), findsOneWidget);

    // El router del scope nuevo sigue respondiendo tras el disposal del previo.
    await tester.tap(find.text('Favoritos'));
    await tester.pump();
    expect(secondRouter.state.uri.path, '/');
  });
}
