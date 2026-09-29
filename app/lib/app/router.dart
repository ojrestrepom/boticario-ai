import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/home/presentation/home_page.dart';

/// Router de la app: una única ruta `/` que renderiza la pantalla inicial.
///
/// Se construye una instancia por scope (`ProviderScope` de app o test) y se
/// libera con `router.dispose` al descartarse el provider. Sin redirects ni
/// rutas adicionales.
final appRouterProvider = Provider<GoRouter>((ref) {
  final router = GoRouter(
    initialLocation: '/',
    routes: [GoRoute(path: '/', builder: (context, state) => const HomePage())],
  );

  ref.onDispose(router.dispose);

  return router;
});
