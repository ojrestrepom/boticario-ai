import 'package:boticario_ai/app/theme.dart';
import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:boticario_ai/features/home/presentation/home_page.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// Mensajes normativos del delta `home-screen`, literales a propósito: no se
/// derivan de `homeActionMessage` para no validar la emisión contra el helper.
const Map<HomeAction, String> _expectedMessages = {
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

/// Las 4 tarjetas en orden de fila.
const List<String> _cardLabels = [
  'Explorar plantas y aceites',
  'Buscar por objetivo',
  'Identificar con cámara',
  'Formular mezclas',
];

/// Acciones de la barra inferior: fuera del scroll, siempre visibles.
const Set<HomeAction> _bottomBarActions = {
  HomeAction.tabHome,
  HomeAction.tabFavorites,
  HomeAction.tabHistory,
  HomeAction.tabProfile,
};

/// Acciones de las 4 tarjetas en orden de fila.
const List<HomeAction> _cardActions = [
  HomeAction.explorePlantsAndOils,
  HomeAction.searchByGoal,
  HomeAction.identifyWithCamera,
  HomeAction.formulateBlends,
];

/// Etiqueta semántica esperada de cada uno de los 11 controles.
const Map<HomeAction, String> _expectedLabels = {
  HomeAction.headerMenu: 'Menú',
  HomeAction.headerProfile: 'Perfil de cabecera',
  HomeAction.explorePlantsAndOils: 'Explorar plantas y aceites',
  HomeAction.searchByGoal: 'Buscar por objetivo',
  HomeAction.identifyWithCamera: 'Identificar con cámara',
  HomeAction.formulateBlends: 'Formular mezclas',
  HomeAction.askTheBoticario: 'Preguntar al Boticario',
  HomeAction.tabHome: 'Inicio',
  HomeAction.tabFavorites: 'Favoritos',
  HomeAction.tabHistory: 'Historial',
  HomeAction.tabProfile: 'Perfil',
};

/// Textos del contrato demo que ya no deben aparecer.
const List<String> _demoTexts = [
  'Hola, Boticario AI',
  'Contador',
  'Incrementar',
];

Finder _actionKey(HomeAction action) => find.byKey(ValueKey(action));

/// Fija el viewport de referencia 360x640 dp (dpr 1) y lo restaura al final.
void _usePhoneViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(360, 640);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
}

/// Ejecuta [body] interceptando `debugPrint` y recoge solo los mensajes con
/// prefijo `[Home]`. Restaura `debugPrint` en `finally`, antes de que el
/// framework verifique que no quedaron variables de depuración alteradas.
Future<void> _withHomeLogs(
  Future<void> Function(List<String> logs) body,
) async {
  final logs = <String>[];
  final DebugPrintCallback original = debugPrint;
  debugPrint = (String? message, {int? wrapWidth}) {
    if (message != null && message.startsWith('[Home]')) {
      logs.add(message);
    } else {
      // Reenvía lo ajeno a Home para no ocultar diagnósticos reales.
      original(message, wrapWidth: wrapWidth);
    }
  };
  try {
    await body(logs);
  } finally {
    debugPrint = original;
  }
}

/// Indica si el control semántico de [action] está marcado como seleccionado.
bool _isSelected(WidgetTester tester, HomeAction action) {
  return tester
          .getSemantics(_actionKey(action))
          .flagsCollection
          .isSelected
          .toBoolOrNull() ??
      false;
}

/// Insets de sistema representativos (notch/barra) para las pruebas de layout.
const EdgeInsets _testInsets = EdgeInsets.only(
  top: 24,
  left: 8,
  right: 12,
  bottom: 24,
);

/// Harness simple: `MaterialApp.home` con el tema real, sin GoRouter.
///
/// [padding] se inyecta como `MediaQuery` dentro del `MaterialApp` para
/// simular notch/insets del sistema y comprobar `SafeArea`.
Widget _buildHomeHarness({
  TextScaler textScaler = TextScaler.noScaling,
  EdgeInsets padding = EdgeInsets.zero,
}) {
  return MaterialApp(
    theme: buildBoticarioTheme(),
    home: Builder(
      builder: (context) => MediaQuery(
        data: MediaQuery.of(context).copyWith(
          textScaler: textScaler,
          padding: padding,
          viewPadding: padding,
        ),
        child: const HomePage(),
      ),
    ),
  );
}

/// Harness con GoRouter real de una única ruta `/`.
Widget _buildRoutedHarness(GoRouter router) {
  return MaterialApp.router(theme: buildBoticarioTheme(), routerConfig: router);
}

GoRouter _createHomeRouter() {
  return GoRouter(
    initialLocation: '/',
    routes: [GoRoute(path: '/', builder: (context, state) => const HomePage())],
  );
}

/// Pulsa el widget real de [action]; hace scroll si vive dentro del cuerpo.
Future<void> _tapAction(WidgetTester tester, HomeAction action) async {
  final finder = _actionKey(action);
  if (!_bottomBarActions.contains(action)) {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
  }
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// Comprueba la disposición 2x2 por posiciones reales de las 4 tarjetas.
void _expectTwoColumnLayout(WidgetTester tester) {
  final r0 = tester.getRect(_actionKey(_cardActions[0]));
  final r1 = tester.getRect(_actionKey(_cardActions[1]));
  final r2 = tester.getRect(_actionKey(_cardActions[2]));
  final r3 = tester.getRect(_actionKey(_cardActions[3]));

  expect(r0.top, closeTo(r1.top, 1.0));
  expect(r2.top, closeTo(r3.top, 1.0));
  expect(r2.top, greaterThan(r0.bottom));
  expect(r3.top, greaterThan(r1.bottom));
  expect(r0.left, closeTo(r2.left, 1.0));
  expect(r1.left, closeTo(r3.left, 1.0));
  expect(r0.left, lessThan(r1.left));
  expect(r2.left, lessThan(r3.left));
}

/// Comprueba la disposición a 1 columna conservando el orden de fila.
void _expectSingleColumnLayout(WidgetTester tester) {
  final rects = [
    for (final action in _cardActions) tester.getRect(_actionKey(action)),
  ];
  for (var i = 1; i < rects.length; i++) {
    expect(rects[i].left, closeTo(rects[0].left, 1.0), reason: 'columna $i');
    expect(rects[i].top, greaterThan(rects[i - 1].bottom), reason: 'orden $i');
  }
}

void main() {
  group('4.1 estructura y textos', () {
    testWidgets('muestra los textos exactos y no los demo', (tester) async {
      _usePhoneViewport(tester);
      await tester.pumpWidget(_buildHomeHarness());
      await tester.pumpAndSettle();

      expect(find.text('Boticario AI'), findsOneWidget);
      expect(
        find.text('Pequeñas esencias, grandes posibilidades'),
        findsOneWidget,
      );
      expect(find.text('Preguntar al Boticario'), findsOneWidget);
      for (final label in _cardLabels) {
        expect(find.text(label), findsOneWidget);
      }
      for (final tab in ['Inicio', 'Favoritos', 'Historial', 'Perfil']) {
        expect(find.text(tab), findsOneWidget);
      }
      expect(find.byIcon(Icons.menu), findsOneWidget);
      expect(find.byIcon(Icons.person), findsOneWidget);
      for (final demo in _demoTexts) {
        expect(find.textContaining(demo), findsNothing);
      }
    });

    testWidgets('cuadrícula 2x2 en orden de fila por posición', (tester) async {
      _usePhoneViewport(tester);
      await tester.pumpWidget(_buildHomeHarness());
      await tester.pumpAndSettle();

      final topLeft = tester.getRect(
        _actionKey(HomeAction.explorePlantsAndOils),
      );
      final topRight = tester.getRect(_actionKey(HomeAction.searchByGoal));
      final bottomLeft = tester.getRect(
        _actionKey(HomeAction.identifyWithCamera),
      );
      final bottomRight = tester.getRect(
        _actionKey(HomeAction.formulateBlends),
      );

      // Primera fila compartida y ordenada por x; segunda fila debajo.
      expect(topLeft.top, closeTo(topRight.top, 1.0));
      expect(topLeft.left, lessThan(topRight.left));
      expect(bottomLeft.top, closeTo(bottomRight.top, 1.0));
      expect(bottomLeft.left, lessThan(bottomRight.left));
      expect(bottomLeft.top, greaterThan(topLeft.bottom));
      expect(bottomRight.top, greaterThan(topRight.bottom));
      expect(topLeft.left, closeTo(bottomLeft.left, 1.0));
      expect(topRight.left, closeTo(bottomRight.left, 1.0));

      // Icono arriba y centrado sobre el label dentro de la tarjeta.
      final card = _actionKey(HomeAction.explorePlantsAndOils);
      final iconRect = tester.getRect(
        find.descendant(of: card, matching: find.byType(Icon)),
      );
      final labelRect = tester.getRect(
        find.descendant(of: card, matching: find.text(_cardLabels.first)),
      );
      expect(iconRect.center.dy, lessThan(labelRect.center.dy));
      expect(iconRect.center.dx, closeTo(labelRect.center.dx, 2.0));
    });

    testWidgets('la barra inferior tiene altura natural', (tester) async {
      _usePhoneViewport(tester);
      await tester.pumpWidget(_buildHomeHarness());
      await tester.pumpAndSettle();

      final tabRect = tester.getRect(_actionKey(HomeAction.tabHome));
      expect(tabRect.height, greaterThanOrEqualTo(48));
      expect(tabRect.height, lessThan(200));
      expect(find.byType(HomePage), findsOneWidget);
    });
  });

  group('4.2 contrato de logs de las 11 acciones', () {
    testWidgets('construir sin pulsar no emite ningún log', (tester) async {
      _usePhoneViewport(tester);
      await _withHomeLogs((logs) async {
        await tester.pumpWidget(_buildHomeHarness());
        await tester.pumpAndSettle();

        expect(logs, isEmpty);
      });
    });

    for (final entry in _expectedMessages.entries) {
      testWidgets('${entry.key.name} emite una vez su mensaje exacto', (
        tester,
      ) async {
        _usePhoneViewport(tester);
        await _withHomeLogs((logs) async {
          await tester.pumpWidget(_buildHomeHarness());
          await tester.pumpAndSettle();
          expect(logs, isEmpty);

          await _tapAction(tester, entry.key);

          expect(logs, [entry.value]);
        });
      });
    }

    testWidgets('distingue Cabecera: Perfil de Pestaña: Perfil', (
      tester,
    ) async {
      _usePhoneViewport(tester);
      await _withHomeLogs((logs) async {
        await tester.pumpWidget(_buildHomeHarness());
        await tester.pumpAndSettle();

        await _tapAction(tester, HomeAction.headerProfile);
        await _tapAction(tester, HomeAction.tabProfile);

        expect(logs, ['[Home] Cabecera: Perfil', '[Home] Pestaña: Perfil']);
      });
    });

    testWidgets('Inicio ya activo emite y sigue seleccionado', (tester) async {
      _usePhoneViewport(tester);
      final semantics = tester.ensureSemantics();
      try {
        await _withHomeLogs((logs) async {
          await tester.pumpWidget(_buildHomeHarness());
          await tester.pumpAndSettle();

          await _tapAction(tester, HomeAction.tabHome);

          expect(logs, ['[Home] Pestaña: Inicio']);
          expect(_isSelected(tester, HomeAction.tabHome), isTrue);
        });
      } finally {
        semantics.dispose();
      }
    });
  });

  group('4.3 no mutación y sin logs automáticos', () {
    testWidgets('la ruta / se mantiene tras las 11 acciones', (tester) async {
      _usePhoneViewport(tester);
      final router = _createHomeRouter();
      addTearDown(router.dispose);
      final semantics = tester.ensureSemantics();
      try {
        await _withHomeLogs((logs) async {
          await tester.pumpWidget(_buildRoutedHarness(router));
          await tester.pumpAndSettle();
          expect(logs, isEmpty);

          for (final action in _expectedMessages.keys) {
            await _tapAction(tester, action);
            expect(
              GoRouter.of(tester.element(find.byType(HomePage))).state.uri.path,
              '/',
            );
          }

          expect(logs, hasLength(_expectedMessages.length));
          expect(find.byType(HomePage), findsOneWidget);
          expect(find.byType(SnackBar), findsNothing);
          expect(find.byType(Dialog), findsNothing);
          expect(find.byType(Drawer), findsNothing);

          expect(_isSelected(tester, HomeAction.tabHome), isTrue);
          const otherTabs = [
            HomeAction.tabFavorites,
            HomeAction.tabHistory,
            HomeAction.tabProfile,
          ];
          for (final action in otherTabs) {
            expect(_isSelected(tester, action), isFalse);
          }
        });
      } finally {
        semantics.dispose();
      }
    });

    testWidgets('rebuild y reassemble no emiten logs', (tester) async {
      _usePhoneViewport(tester);
      await _withHomeLogs((logs) async {
        await tester.pumpWidget(_buildHomeHarness());
        await tester.pumpAndSettle();
        expect(logs, isEmpty);

        await tester.pumpWidget(_buildHomeHarness());
        await tester.pumpAndSettle();
        expect(logs, isEmpty);

        // Reassemble simulada en widget test; la recarga en caliente real es
        // revisión manual (7.2). No se espera la Future antes del frame (el
        // binding la completa al pintar, esperar antes produce deadlock): se
        // captura, se provoca el frame y se espera después.
        final reassemble = tester.binding.reassembleApplication();
        await tester.pump();
        await tester.pumpAndSettle();
        await reassemble;
        expect(logs, isEmpty);
      });
    });
  });

  group('4.4 accesibilidad', () {
    testWidgets('los 11 controles exponen label único, rol de botón y tap', (
      tester,
    ) async {
      _usePhoneViewport(tester);
      final semantics = tester.ensureSemantics();
      try {
        await tester.pumpWidget(_buildHomeHarness());
        await tester.pumpAndSettle();

        final labels = <String>[];
        for (final entry in _expectedLabels.entries) {
          final node = tester.getSemantics(_actionKey(entry.key));
          expect(node.label, entry.value, reason: 'label de ${entry.key}');
          expect(
            node.getSemanticsData().hasAction(SemanticsAction.tap),
            isTrue,
            reason: 'acción tap de ${entry.key}',
          );
          expect(
            node.flagsCollection.isButton,
            isTrue,
            reason: 'rol de botón de ${entry.key}',
          );
          // Si un icono decorativo duplicara la lectura, el label aparecería
          // más de una vez o no sería único.
          expect(
            find.bySemanticsLabel(entry.value),
            findsOneWidget,
            reason: 'label único de ${entry.key}',
          );
          labels.add(node.label);
        }
        expect(labels.toSet(), hasLength(_expectedLabels.length));

        expect(_isSelected(tester, HomeAction.tabHome), isTrue);
        for (final action in [
          HomeAction.tabFavorites,
          HomeAction.tabHistory,
          HomeAction.tabProfile,
        ]) {
          expect(_isSelected(tester, action), isFalse, reason: '$action');
        }
      } finally {
        semantics.dispose();
      }
    });

    testWidgets('los 11 controles tienen área de toque >= 48x48 lógicos', (
      tester,
    ) async {
      _usePhoneViewport(tester);
      await tester.pumpWidget(_buildHomeHarness());
      await tester.pumpAndSettle();

      for (final action in HomeAction.values) {
        final finder = _actionKey(action);
        if (!_bottomBarActions.contains(action)) {
          await tester.ensureVisible(finder);
          await tester.pumpAndSettle();
        }
        final size = tester.getSize(finder);
        expect(size.width, greaterThanOrEqualTo(48.0), reason: 'ancho $action');
        expect(size.height, greaterThanOrEqualTo(48.0), reason: 'alto $action');
      }
      expect(tester.takeException(), isNull);
    });
  });

  group('4.5 layout, zonas seguras y texto', () {
    for (final (label, scaler, twoColumns) in <(String, TextScaler, bool)>[
      ('100%', TextScaler.noScaling, true),
      ('200%', TextScaler.linear(2), false),
    ]) {
      testWidgets('cuadrícula sin overflow a $label en 360x640', (
        tester,
      ) async {
        _usePhoneViewport(tester);
        await tester.pumpWidget(
          _buildHomeHarness(textScaler: scaler, padding: _testInsets),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);

        if (twoColumns) {
          _expectTwoColumnLayout(tester);
        } else {
          _expectSingleColumnLayout(tester);
        }
        expect(tester.takeException(), isNull);
      });
    }

    for (final (label, scaler) in <(String, TextScaler)>[
      ('100%', TextScaler.noScaling),
      ('200%', TextScaler.linear(2)),
    ]) {
      testWidgets('SafeArea protege cabecera y footer con insets a $label', (
        tester,
      ) async {
        _usePhoneViewport(tester);
        await tester.pumpWidget(
          _buildHomeHarness(textScaler: scaler, padding: _testInsets),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);

        final scrollable = tester.state<ScrollableState>(
          find.descendant(
            of: find.byType(HomePage),
            matching: find.byType(Scrollable),
          ),
        );
        expect(scrollable.position.pixels, 0.0);

        final header = tester.getRect(_actionKey(HomeAction.headerMenu));
        expect(header.top, greaterThanOrEqualTo(_testInsets.top));
        expect(header.left, greaterThanOrEqualTo(_testInsets.left));
        expect(header.right, lessThanOrEqualTo(360 - _testInsets.right));

        final footer = tester.getRect(_actionKey(HomeAction.tabHome));
        expect(footer.left, greaterThanOrEqualTo(_testInsets.left));
        expect(footer.right, lessThanOrEqualTo(360 - _testInsets.right));
        expect(footer.bottom, lessThanOrEqualTo(640 - _testInsets.bottom));
      });

      testWidgets('los 11 controles son alcanzables y hittestables a $label', (
        tester,
      ) async {
        _usePhoneViewport(tester);
        await _withHomeLogs((logs) async {
          await tester.pumpWidget(_buildHomeHarness(textScaler: scaler));
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);

          for (final action in HomeAction.values) {
            final finder = _actionKey(action);
            if (!_bottomBarActions.contains(action)) {
              await tester.ensureVisible(finder);
              await tester.pumpAndSettle();
            }
            final size = tester.getSize(finder);
            expect(
              size.width,
              greaterThanOrEqualTo(48.0),
              reason: 'ancho $action ($label)',
            );
            expect(
              size.height,
              greaterThanOrEqualTo(48.0),
              reason: 'alto $action ($label)',
            );

            // El tap solo emite si realmente alcanza el widget real.
            logs.clear();
            await tester.tap(finder);
            await tester.pumpAndSettle();
            expect(logs, [
              _expectedMessages[action],
            ], reason: 'tap no alcanzó $action ($label)');
          }
          expect(tester.takeException(), isNull);
        });
      });

      testWidgets(
        'textos esenciales íntegros sin recorte ni elipsis a $label',
        (tester) async {
          _usePhoneViewport(tester);
          await tester.pumpWidget(
            _buildHomeHarness(textScaler: scaler, padding: _testInsets),
          );
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);

          final texts = <String>[
            'Boticario AI',
            'Pequeñas esencias, grandes posibilidades',
            'Preguntar al Boticario',
            ..._cardLabels,
            'Inicio',
            'Favoritos',
            'Historial',
            'Perfil',
          ];
          for (final text in texts) {
            final finder = find.text(text);
            expect(finder, findsOneWidget, reason: '$text ($label)');
            final paragraph = tester.renderObject<RenderParagraph>(finder);
            expect(
              paragraph.text.toPlainText(),
              text,
              reason: 'texto vivo de $text ($label)',
            );
            expect(
              paragraph.didExceedMaxLines,
              isFalse,
              reason: 'recorte/elipsis de $text ($label)',
            );
            final rect = tester.getRect(finder);
            expect(rect.left, greaterThanOrEqualTo(0.0), reason: '$text izq');
            expect(rect.right, lessThanOrEqualTo(360.0), reason: '$text der');
          }
          expect(tester.takeException(), isNull);
        },
      );
    }
  });
}
