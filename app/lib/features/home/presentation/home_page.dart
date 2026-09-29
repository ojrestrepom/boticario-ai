import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'home_controller.dart';

/// Pantalla inicial del bootstrap: saludo fijo y contador demo.
class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final count = ref.watch(homeControllerProvider);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Hola, Boticario AI',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 16),
                Semantics(
                  liveRegion: true,
                  label: 'Contador: $count',
                  excludeSemantics: true,
                  child: Text(
                    'Contador: $count',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: () {
                    ref.read(homeControllerProvider.notifier).increment();
                  },
                  child: const Text('Incrementar'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
