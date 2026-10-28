import 'dart:async';

import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_json_parser.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/catalog/data/catalog_repository.dart';
import 'package:boticario_ai/features/catalog/domain/goal.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_summary.dart';
import 'package:boticario_ai/features/goal_search/application/goal_results_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_catalog_api.dart';

class _Call {
  _Call(this.goalId, this.subarea, this.limit, this.offset);
  final String goalId;
  final String? subarea;
  final int limit;
  final int offset;
  final completer = Completer<GoalPlantPage?>();
}

/// Repository whose `listGoalPlants` answers are controlled by the test.
class _ControlledRepository implements CatalogRepository {
  final calls = <_Call>[];

  @override
  Future<GoalPlantPage?> listGoalPlants(
    String goalId, {
    String? subarea,
    int limit = 20,
    int offset = 0,
  }) {
    final call = _Call(goalId, subarea, limit, offset);
    calls.add(call);
    return call.completer.future;
  }

  @override
  Future<List<Goal>> listGoals() async => throw UnimplementedError();

  @override
  Future<PlantPage> listPlants({
    String query = '',
    int limit = 50,
    int offset = 0,
  }) async => throw UnimplementedError();

  @override
  Future<Plant?> getPlant(String id) async => throw UnimplementedError();
}

GoalPlant _plant(String id) => GoalPlant(
  id: id,
  scientificName: 'Sci $id',
  commonNames: const [],
  areas: const ['Área'],
  hasSafety: true,
);

GoalPlantPage _page(
  List<String> ids, {
  required int total,
  int offset = 0,
  GoalRef? subarea,
}) => GoalPlantPage(
  goal: const GoalRef(id: 'g', name: 'Objetivo G'),
  subarea: subarea,
  items: [for (final id in ids) _plant(id)],
  total: total,
  limit: 20,
  offset: offset,
);

List<String> _ids(int from, int count) => [
  for (var i = from; i < from + count; i++) 'p$i',
];

void main() {
  late _ControlledRepository repo;
  late ProviderContainer container;
  late GoalResultsQuery query;

  GoalResultsState read() =>
      container.read(goalResultsControllerProvider(query));
  GoalResultsController notifier() =>
      container.read(goalResultsControllerProvider(query).notifier);

  void init({String? subarea}) {
    query = (goalId: 'g', subareaId: subarea);
    repo = _ControlledRepository();
    container = ProviderContainer(
      overrides: [catalogRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);
    container.listen(goalResultsControllerProvider(query), (_, _) {});
  }

  testWidgets('requests the first page of 20 and keeps the API order', (
    tester,
  ) async {
    init();
    expect(read().phase, GoalResultsPhase.loading);
    expect(repo.calls, hasLength(1));
    final call = repo.calls.single;
    expect(
      (call.goalId, call.subarea, call.limit, call.offset),
      ('g', null, 20, 0),
    );
    call.completer.complete(_page(['b', 'a'], total: 2));
    await tester.pump();
    expect(read().phase, GoalResultsPhase.ready);
    expect([for (final plant in read().items) plant.id], ['b', 'a']);
    expect(read().total, 2);
    expect(read().hasMore, isFalse);
    expect(read().targetName, 'Objetivo G');
  });

  testWidgets('the name comes from the subarea when there is one', (
    tester,
  ) async {
    init(subarea: 's');
    expect(repo.calls.single.subarea, 's');
    repo.calls.single.completer.complete(
      _page(
        ['a'],
        total: 1,
        subarea: const GoalRef(id: 's', name: 'Subárea S'),
      ),
    );
    await tester.pump();
    expect(read().targetName, 'Subárea S');
  });

  testWidgets('loads the next page at the offset of what is loaded', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 20), total: 45));
    await tester.pump();
    expect(read().hasMore, isTrue);

    notifier().loadMore();
    notifier().loadMore(); // Ignored while the page is loading.
    expect(read().loadingMore, isTrue);
    expect(repo.calls, hasLength(2));
    expect((repo.calls[1].limit, repo.calls[1].offset), (20, 20));
    repo.calls[1].completer.complete(
      _page(_ids(20, 20), total: 45, offset: 20),
    );
    await tester.pump();
    expect(read().loadingMore, isFalse);
    expect(read().items, hasLength(40));
    expect(read().items[20].id, 'p20');

    notifier().loadMore();
    expect(repo.calls[2].offset, 40);
    repo.calls[2].completer.complete(_page(_ids(40, 5), total: 45, offset: 40));
    await tester.pump();
    expect(read().items, hasLength(45));
    expect(read().items.map((p) => p.id).toSet(), hasLength(45));
  });

  testWidgets('at the end of the list no more pages are requested', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 20), total: 20));
    await tester.pump();
    expect(read().hasMore, isFalse);
    notifier().loadMore();
    expect(repo.calls, hasLength(1));
  });

  testWidgets('an empty page ends the list even if the total promised more', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 20), total: 30));
    await tester.pump();
    notifier().loadMore();
    repo.calls[1].completer.complete(_page([], total: 30, offset: 20));
    await tester.pump();
    expect(read().items, hasLength(20));
    expect(read().hasMore, isFalse);
  });

  testWidgets('a failed next page keeps what is loaded and retries', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 20), total: 40));
    await tester.pump();
    notifier().loadMore();
    repo.calls[1].completer.completeError(
      const CatalogClientException(
        CatalogClientErrorKind.network,
        'No se pudo conectar con el servidor.',
      ),
    );
    await tester.pump();
    expect(read().phase, GoalResultsPhase.ready);
    expect(read().items, hasLength(20));
    expect(read().footerError, 'No se pudo conectar con el servidor.');
    expect(read().loadingMore, isFalse);

    // No new request until the user retries.
    notifier().loadMore();
    expect(repo.calls, hasLength(2));

    notifier().retryMore();
    expect(read().footerError, isNull);
    expect(repo.calls, hasLength(3));
    expect(repo.calls[2].offset, 20);
    repo.calls[2].completer.complete(
      _page(_ids(20, 20), total: 40, offset: 20),
    );
    await tester.pump();
    expect(read().items, hasLength(40));
  });

  testWidgets('a goal with no plants is ready and empty', (tester) async {
    init();
    repo.calls[0].completer.complete(_page([], total: 0));
    await tester.pump();
    expect(read().phase, GoalResultsPhase.ready);
    expect(read().items, isEmpty);
    expect(read().total, 0);
    expect(read().hasMore, isFalse);
  });

  testWidgets('a 404 is not found, not a retryable error', (tester) async {
    init();
    repo.calls[0].completer.complete(null);
    await tester.pump();
    expect(read().phase, GoalResultsPhase.notFound);
    expect(read().errorMessage, isNull);
  });

  testWidgets('a 401 is an error message without the token', (tester) async {
    final api = FakeCatalogApi.real(requiredToken: testApiToken);
    final real = ProviderContainer(
      overrides: [
        httpClientProvider.overrideWithValue(api.client),
        // A wrong token: the fake answers 401.
        apiTokenProvider.overrideWithValue(
          'wrong-token-wrong-token-wrong-token',
        ),
      ],
    );
    addTearDown(real.dispose);
    const q = (goalId: 'relajacion-estres', subareaId: null);
    real.listen(goalResultsControllerProvider(q), (_, _) {});
    await tester.pump(const Duration(milliseconds: 10));
    await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    await tester.pump();
    final state = real.read(goalResultsControllerProvider(q));
    expect(state.phase, GoalResultsPhase.error);
    expect(state.errorMessage, contains('no está autorizada'));
    expect(state.errorMessage, isNot(contains('wrong-token')));
    expect(state.errorMessage, isNot(contains(testApiToken)));
  });

  testWidgets('a failure of the first page is an error and retry reloads', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.completeError(StateError('boom'));
    await tester.pump();
    expect(read().phase, GoalResultsPhase.error);
    expect(read().errorMessage, 'No se pudo cargar el catálogo.');

    notifier().retry();
    expect(read().phase, GoalResultsPhase.loading);
    expect(repo.calls, hasLength(2));
    repo.calls[1].completer.complete(_page(['a'], total: 1));
    await tester.pump();
    expect(read().phase, GoalResultsPhase.ready);
  });

  testWidgets('drops a late first page that a retry has superseded', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.completeError(StateError('first'));
    await tester.pump();
    notifier().retry();
    notifier().retry();
    expect(repo.calls, hasLength(3));

    repo.calls[2].completer.complete(_page(['new'], total: 1));
    await tester.pump();
    repo.calls[1].completer.complete(_page(['old'], total: 1));
    await tester.pump();
    expect([for (final plant in read().items) plant.id], ['new']);
  });

  testWidgets('drops a late next page after a retry reset the list', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 20), total: 40));
    await tester.pump();
    notifier().loadMore();
    notifier().retry();
    expect(read().items, isEmpty);
    repo.calls[2].completer.complete(_page(['fresh'], total: 1));
    await tester.pump();
    repo.calls[1].completer.complete(
      _page(_ids(20, 20), total: 40, offset: 20),
    );
    await tester.pump();
    expect([for (final plant in read().items) plant.id], ['fresh']);
    expect(read().loadingMore, isFalse);
  });

  testWidgets('a response after the state was disposed is ignored', (
    tester,
  ) async {
    init();
    container.dispose();
    repo.calls[0].completer.complete(_page(['a'], total: 1));
    await tester.pump();
  });

  test('parses the real page used by the fake API', () {
    expect(
      parseGoalPlantPage(apiFixture('goal_plants_relajacion-estres.json'))
          .items,
      hasLength(17),
    );
  });
}
