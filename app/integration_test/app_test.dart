import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:boticario_ai/main.dart' as app;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';

/// Mensajes normativos literales de las 11 acciones (spec `home-screen`).
///
/// El test no calcula los esperados con el helper de producción: los fija
/// aquí como oráculo del contrato.
const Map<HomeAction, String> _expectedMessages = <HomeAction, String>{
  HomeAction.headerMenu: '[Home] Cabecera: Menú',
  HomeAction.headerProfile: '[Home] Cabecera: Perfil',
  HomeAction.explorePlantsAndOils: '[Home] Explorar plantas y aceites',
  HomeAction.searchByGoal: '[Home] Buscar por objetivo',
  HomeAction.identifyWithCamera: '[Home] Identificar con cámara',
  HomeAction.formulateBlends: '[Home] Formular mezclas',
  HomeAction.askTheBoticario: '[Home] Preguntar al Boticario',
  HomeAction.tabHome: '[Home] Pestaña: Inicio',
  HomeAction.tabFavorites: '[Home] Pestaña: Favoritos',
  HomeAction.tabHistory: '[Home] Pestaña: Historial',
  HomeAction.tabProfile: '[Home] Pestaña: Perfil',
};

/// Acciones de la barra inferior: viven fuera del scroll vertical del cuerpo.
const Set<HomeAction> _footerActions = <HomeAction>{
  HomeAction.tabHome,
  HomeAction.tabFavorites,
  HomeAction.tabHistory,
  HomeAction.tabProfile,
};

/// Ruta real del router de la app, vía API pública de go_router.
String _routerPath(WidgetTester tester) {
  return GoRouter.of(tester.element(find.byType(HomePage))).state.uri.path;
}

/// Activa el control de [action]: asegura visibilidad en el cuerpo y pulsa.
Future<void> _activate(WidgetTester tester, HomeAction action) async {
  final Finder control = find.byKey(ValueKey<HomeAction>(action));
  if (!_footerActions.contains(action)) {
    await tester.ensureVisible(control);
    await tester.pumpAndSettle();
  }
  await tester.tap(control);
  await tester.pumpAndSettle();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('arranque real de Home: ruta /, 11 acciones y barra inmóvil', (
    tester,
  ) async {
    final originalDebugPrint = debugPrint;
    final List<String> homeLogs = <String>[];
    final semanticsHandle = tester.ensureSemantics();

    // Intercepta solo `[Home]`, reenviando el resto a la consola real.
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null && message.startsWith('[Home]')) {
        homeLogs.add(message);
      }
      originalDebugPrint(message, wrapWidth: wrapWidth);
    };

    try {
      app.main();
      await tester.pumpAndSettle();

      // Arranque real: Home en `/`, marca y banner, sin demo ni logs.
      expect(find.byType(HomePage), findsOneWidget);
      expect(_routerPath(tester), '/');
      expect(find.text('Boticario AI'), findsOneWidget);
      expect(
        find.text('Pequeñas esencias, grandes posibilidades'),
        findsOneWidget,
      );
      expect(find.text('Hola, Boticario AI'), findsNothing);
      expect(find.textContaining('Contador'), findsNothing);
      expect(find.text('Incrementar'), findsNothing);
      expect(homeLogs, isEmpty);

      // Cada una de las 11 acciones: 1 activación -> 1 mensaje normativo.
      for (final MapEntry<HomeAction, String> expected
          in _expectedMessages.entries) {
        await _activate(tester, expected.key);
        expect(homeLogs, <String>[
          expected.value,
        ], reason: '${expected.key} debe emitir exactamente su mensaje');
        homeLogs.clear();
        expect(
          _routerPath(tester),
          '/',
          reason: '${expected.key} no cambia la ruta',
        );
        expect(find.byType(HomePage), findsOneWidget);
        expect(find.byType(SnackBar), findsNothing);
        expect(find.byType(Dialog), findsNothing);
        expect(find.byType(Drawer), findsNothing);
      }
      expect(_expectedMessages.length, HomeAction.values.length);

      // Barra inferior: `Inicio` seleccionado; el resto no.
      expect(
        tester.getSemantics(
          find.byKey(const ValueKey<HomeAction>(HomeAction.tabHome)),
        ),
        isSemantics(
          label: 'Inicio',
          isButton: true,
          hasSelectedState: true,
          isSelected: true,
          hasTapAction: true,
        ),
      );
      for (final HomeAction tab in <HomeAction>[
        HomeAction.tabFavorites,
        HomeAction.tabHistory,
        HomeAction.tabProfile,
      ]) {
        expect(
          tester.getSemantics(find.byKey(ValueKey<HomeAction>(tab))),
          isSemantics(isSelected: false),
          reason: '$tab no debe quedar seleccionada',
        );
      }
    } finally {
      debugPrint = originalDebugPrint;
      semanticsHandle.dispose();
    }
  });
}
