import 'package:boticario_ai/features/home/presentation/home_action.dart';
import 'package:flutter_test/flutter_test.dart';

/// Cadenas normativas tomadas del delta `home-screen`, literales a propósito:
/// no se derivan de `homeActionMessage` para no validar la implementación
/// contra sí misma.
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

void main() {
  group('homeActionMessage en modo permitido', () {
    for (final entry in _expectedMessages.entries) {
      test('${entry.key} devuelve "${entry.value}"', () {
        expect(homeActionMessage(entry.key, isDebugMode: true), entry.value);
      });
    }
  });

  group('homeActionMessage en modo no permitido', () {
    // Estas pruebas ejercen el cálculo puro con `isDebugMode: false`. No
    // ejecutan un binario release/profile real ni demuestran su silencio: solo
    // verifican la política de decisión del helper.
    for (final action in _expectedMessages.keys) {
      test('$action devuelve null', () {
        expect(homeActionMessage(action, isDebugMode: false), isNull);
      });
    }
  });

  group('cobertura del enum', () {
    test('HomeAction expone exactamente 11 acciones', () {
      expect(HomeAction.values, hasLength(11));
    });

    test('cada acción tiene un mensaje exacto y distinto', () {
      final messages = <String>{};
      for (final action in HomeAction.values) {
        final message = homeActionMessage(action, isDebugMode: true);
        expect(message, isNotNull, reason: 'sin mensaje para $action');
        messages.add(message!);
      }
      expect(messages, hasLength(HomeAction.values.length));
    });

    test('los mensajes en modo permitido coinciden con el contrato', () {
      for (final entry in _expectedMessages.entries) {
        expect(
          homeActionMessage(entry.key, isDebugMode: true),
          entry.value,
          reason: 'mensaje inesperado para ${entry.key}',
        );
      }
      expect(_expectedMessages.keys.toSet(), HomeAction.values.toSet());
    });

    test('Cabecera: Perfil y Pestaña: Perfil son distintos', () {
      final header = homeActionMessage(
        HomeAction.headerProfile,
        isDebugMode: true,
      );
      final tab = homeActionMessage(HomeAction.tabProfile, isDebugMode: true);

      expect(header, '[Home] Cabecera: Perfil');
      expect(tab, '[Home] Pestaña: Perfil');
      expect(header, isNot(equals(tab)));
    });
  });
}
