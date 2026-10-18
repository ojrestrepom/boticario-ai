import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'router.dart';
import 'theme.dart';

/// Shell de la app: `MaterialApp.router` con el router y el tema reales.
class BoticarioApp extends ConsumerWidget {
  const BoticarioApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'Boticario AI',
      theme: buildBoticarioTheme(),
      routerConfig: router,
    );
  }
}
