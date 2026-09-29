import 'package:boticario_ai/features/home/presentation/home_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('HomeController', () {
    test('estado inicial es 0', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      expect(container.read(homeControllerProvider), 0);
    });

    test('cada activación suma exactamente 1', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final controller = container.read(homeControllerProvider.notifier);

      controller.increment();
      expect(container.read(homeControllerProvider), 1);

      for (var i = 0; i < 9; i++) {
        controller.increment();
      }
      expect(container.read(homeControllerProvider), 10);
    });

    test('N activaciones suman N', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final controller = container.read(homeControllerProvider.notifier);
      const activations = 5;
      for (var i = 0; i < activations; i++) {
        controller.increment();
      }

      expect(container.read(homeControllerProvider), activations);
    });

    test('containers independientes no comparten estado', () {
      final first = ProviderContainer();
      final second = ProviderContainer();
      addTearDown(first.dispose);
      addTearDown(second.dispose);

      first.read(homeControllerProvider.notifier).increment();
      first.read(homeControllerProvider.notifier).increment();

      expect(first.read(homeControllerProvider), 2);
      // Un container nuevo (instancia en frío) parte de 0.
      expect(second.read(homeControllerProvider), 0);

      second.read(homeControllerProvider.notifier).increment();

      expect(second.read(homeControllerProvider), 1);
      expect(first.read(homeControllerProvider), 2);
    });
  });
}
