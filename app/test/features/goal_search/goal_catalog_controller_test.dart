import 'dart:async';

import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/catalog/data/catalog_repository.dart';
import 'package:boticario_ai/features/catalog/domain/goal.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_summary.dart';
import 'package:boticario_ai/features/goal_search/application/goal_catalog_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// Repository whose `listGoals` answers are controlled by the test.
class _ControlledRepository implements CatalogRepository {
  final calls = <Completer<List<Goal>>>[];

  @override
  Future<List<Goal>> listGoals() {
    final completer = Completer<List<Goal>>();
    calls.add(completer);
    return completer.future;
  }

  @override
  Future<PlantPage> listPlants({
    String query = '',
    int limit = 50,
    int offset = 0,
  }) async => throw UnimplementedError();

  @override
  Future<Plant?> getPlant(String id) async => throw UnimplementedError();

  @override
  Future<GoalPlantPage?> listGoalPlants(
    String goalId, {
    String? subarea,
    int limit = 20,
    int offset = 0,
  }) async => throw UnimplementedError();
}

Goal _goal(String id) =>
    Goal(id: id, name: 'Objetivo $id', plantCount: 1, subareas: const []);

void main() {
  late _ControlledRepository repo;
  late ProviderContainer container;

  GoalCatalogState read() => container.read(goalCatalogControllerProvider);

  void init() {
    repo = _ControlledRepository();
    container = ProviderContainer(
      overrides: [catalogRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);
    container.listen(goalCatalogControllerProvider, (_, _) {});
  }

  testWidgets('requests the catalog once and keeps the API order', (
    tester,
  ) async {
    init();
    expect(read().phase, GoalCatalogPhase.loading);
    expect(repo.calls, hasLength(1));
    repo.calls.single.complete([_goal('b'), _goal('a')]);
    await tester.pump();
    expect(read().phase, GoalCatalogPhase.ready);
    expect([for (final goal in read().goals) goal.id], ['b', 'a']);
    expect(read().goalById('a')?.name, 'Objetivo a');
    expect(read().goalById('zzz'), isNull);
  });

  testWidgets('shows a readable error and retries from loading', (
    tester,
  ) async {
    init();
    repo.calls[0].completeError(
      const CatalogClientException(
        CatalogClientErrorKind.network,
        'No se pudo conectar con el servidor.',
      ),
    );
    await tester.pump();
    expect(read().phase, GoalCatalogPhase.error);
    expect(read().errorMessage, 'No se pudo conectar con el servidor.');

    container.read(goalCatalogControllerProvider.notifier).retry();
    expect(read().phase, GoalCatalogPhase.loading);
    expect(repo.calls, hasLength(2));
    repo.calls[1].complete([_goal('a')]);
    await tester.pump();
    expect(read().phase, GoalCatalogPhase.ready);
    expect(read().goals, hasLength(1));
  });

  testWidgets('a non-client error gets the generic message', (tester) async {
    init();
    repo.calls[0].completeError(StateError('boom'));
    await tester.pump();
    expect(read().phase, GoalCatalogPhase.error);
    expect(read().errorMessage, 'No se pudo cargar el catálogo.');
  });

  testWidgets('drops a late answer that a retry has superseded', (
    tester,
  ) async {
    init();
    repo.calls[0].completeError(StateError('first'));
    await tester.pump();
    container.read(goalCatalogControllerProvider.notifier).retry();
    container.read(goalCatalogControllerProvider.notifier).retry();
    expect(repo.calls, hasLength(3));

    repo.calls[2].complete([_goal('new')]);
    await tester.pump();
    repo.calls[1].complete([_goal('old')]);
    await tester.pump();
    expect([for (final goal in read().goals) goal.id], ['new']);
    expect(read().phase, GoalCatalogPhase.ready);
  });
}
