import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/explore/presentation/explore_page.dart';
import '../features/home/presentation/home_page.dart';
import '../features/passport/presentation/plant_passport_page.dart';

/// Router de la app: Home contiene Explorar, que contiene el pasaporte.
///
/// Se construye una instancia por scope (`ProviderScope` de app o test) y se
/// libera con `router.dispose` al descartarse el provider.
final appRouterProvider = Provider<GoRouter>((ref) {
  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) =>
            HomePage(onExplore: () => context.push('/explore')),
        routes: [
          GoRoute(
            path: 'explore',
            builder: (context, state) => ExplorePage(
              onBack: () => context.pop(),
              onHome: () => context.go('/'),
              onPlantSelected: (id) => context.push('/explore/$id'),
            ),
            routes: [
              GoRoute(
                path: ':plantId',
                builder: (context, state) => PlantPassportRoutePage(
                  plantId: state.pathParameters['plantId']!,
                  onBack: () => context.pop(),
                  onHome: () => context.go('/'),
                ),
              ),
            ],
          ),
        ],
      ),
    ],
  );

  ref.onDispose(router.dispose);

  return router;
});
