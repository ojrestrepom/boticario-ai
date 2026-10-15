import 'dart:async';

import 'package:boticario_ai/features/catalog/data/catalog_client_exception.dart';
import 'package:boticario_ai/features/catalog/data/catalog_providers.dart';
import 'package:boticario_ai/features/catalog/data/catalog_repository.dart';
import 'package:boticario_ai/features/catalog/domain/plant.dart';
import 'package:boticario_ai/features/catalog/domain/plant_summary.dart';
import 'package:boticario_ai/features/explore/application/explore_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class _Call {
  _Call(this.query, this.limit, this.offset);
  final String query;
  final int limit;
  final int offset;
  final completer = Completer<PlantPage>();
}

/// Repository whose answers are controlled by the test, one per request.
class _ControlledRepository implements CatalogRepository {
  final calls = <_Call>[];

  @override
  Future<PlantPage> listPlants({
    String query = '',
    int limit = 50,
    int offset = 0,
  }) {
    final call = _Call(query, limit, offset);
    calls.add(call);
    return call.completer.future;
  }

  @override
  Future<Plant?> getPlant(String id) async => null;
}

PlantPage _page(List<String> ids, {required int total, int offset = 0}) =>
    PlantPage(
      items: [
        for (final id in ids)
          PlantSummary(id: id, scientificName: 'Sci $id', commonNames: []),
      ],
      total: total,
      limit: 50,
      offset: offset,
    );

List<String> _ids(int from, int count) => [
  for (var i = from; i < from + count; i++) 'p$i',
];

const _failure = CatalogClientException(
  CatalogClientErrorKind.network,
  'No se pudo conectar con el servidor.',
);

void main() {
  late _ControlledRepository repo;
  late ProviderContainer container;

  ExploreState read() => container.read(exploreControllerProvider);
  ExploreController notifier() =>
      container.read(exploreControllerProvider.notifier);

  // Created inside each test body so its futures run in the test's fake zone.
  void init() {
    repo = _ControlledRepository();
    container = ProviderContainer(
      overrides: [catalogRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);
    // Keeps the provider alive and starts the first request.
    container.listen(exploreControllerProvider, (_, _) {});
  }

  testWidgets('requests the first page of 50 without a query and shows it', (
    tester,
  ) async {
    init();
    expect(read().phase, ExplorePhase.loading);
    expect(repo.calls, hasLength(1));
    expect(repo.calls.single.query, isEmpty);
    expect(repo.calls.single.limit, 50);
    expect(repo.calls.single.offset, 0);

    repo.calls.single.completer.complete(_page(_ids(0, 50), total: 120));
    await tester.pump();
    expect(read().phase, ExplorePhase.ready);
    expect(read().items, hasLength(50));
    expect(read().total, 120);
    expect(read().hasMore, isTrue);
  });

  testWidgets('paginates with accumulated offsets until total is reached', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 50), total: 120));
    await tester.pump();

    notifier().loadMore();
    notifier().loadMore(); // Ignored while a page is loading.
    expect(read().loadingMore, isTrue);
    expect(repo.calls, hasLength(2));
    expect(repo.calls[1].offset, 50);
    expect(repo.calls[1].limit, 50);
    repo.calls[1].completer.complete(
      _page(_ids(50, 50), total: 120, offset: 50),
    );
    await tester.pump();
    expect(read().items, hasLength(100));
    expect(read().items.first.id, 'p0');
    expect(read().items.last.id, 'p99');
    expect(read().loadingMore, isFalse);

    notifier().loadMore();
    expect(repo.calls[2].offset, 100);
    repo.calls[2].completer.complete(
      _page(_ids(100, 20), total: 120, offset: 100),
    );
    await tester.pump();
    expect(read().items, hasLength(120));
    expect(read().hasMore, isFalse);

    notifier().loadMore();
    expect(repo.calls, hasLength(3), reason: 'end of list: no more requests');
  });

  testWidgets('a single short page is the end of the list', (tester) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 7), total: 7));
    await tester.pump();
    notifier().loadMore();
    expect(repo.calls, hasLength(1));
    expect(read().hasMore, isFalse);
  });

  testWidgets('an empty page ends the list even if total promised more', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 50), total: 120));
    await tester.pump();
    notifier().loadMore();
    repo.calls[1].completer.complete(_page([], total: 120, offset: 50));
    await tester.pump();
    expect(read().items, hasLength(50));
    expect(read().hasMore, isFalse);
  });

  testWidgets('error loading more keeps the loaded items; retry asks only '
      'for that page', (tester) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 50), total: 120));
    await tester.pump();

    notifier().loadMore();
    repo.calls[1].completer.completeError(_failure);
    await tester.pump();
    expect(read().items, hasLength(50));
    expect(read().phase, ExplorePhase.ready);
    expect(read().loadingMore, isFalse);
    expect(read().footerError, _failure.message);

    notifier().loadMore(); // No automatic retry after a failure.
    expect(repo.calls, hasLength(2));

    notifier().retryMore();
    expect(repo.calls, hasLength(3));
    expect(repo.calls[2].offset, 50);
    expect(read().footerError, isNull);
    expect(read().items, hasLength(50));
    repo.calls[2].completer.complete(
      _page(_ids(50, 50), total: 120, offset: 50),
    );
    await tester.pump();
    expect(read().items, hasLength(100));
    expect(read().footerError, isNull);
  });

  testWidgets('first page error is readable and retry repeats the request', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.completeError(_failure);
    await tester.pump();
    expect(read().phase, ExplorePhase.error);
    expect(read().errorMessage, _failure.message);
    expect(repo.calls, hasLength(1), reason: 'no automatic retry');

    notifier().retry();
    expect(read().phase, ExplorePhase.loading);
    expect(repo.calls, hasLength(2));
    expect(repo.calls[1].offset, 0);
    repo.calls[1].completer.complete(_page(_ids(0, 3), total: 3));
    await tester.pump();
    expect(read().phase, ExplorePhase.ready);
    expect(read().errorMessage, isNull);
    expect(read().items, hasLength(3));
  });

  testWidgets('an unexpected error shows a generic message, not its text', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.completeError(StateError('private detail'));
    await tester.pump();
    expect(read().phase, ExplorePhase.error);
    expect(read().errorMessage, isNot(contains('private detail')));
    expect(read().errorMessage, isNotEmpty);
  });

  testWidgets('debounce sends one request with the final query', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 5), total: 5));
    await tester.pump();

    notifier().setQuery('l');
    await tester.pump(const Duration(milliseconds: 100));
    notifier().setQuery('la');
    await tester.pump(const Duration(milliseconds: 100));
    notifier().setQuery('lav');
    await tester.pump(const Duration(milliseconds: 299));
    expect(repo.calls, hasLength(1), reason: 'still inside the quiet period');
    expect(read().query, 'lav', reason: 'the field state updates at once');

    await tester.pump(const Duration(milliseconds: 1));
    expect(repo.calls, hasLength(2));
    expect(repo.calls[1].query, 'lav');
    expect(repo.calls[1].offset, 0);
    expect(read().phase, ExplorePhase.loading);
  });

  testWidgets('the query is sent trimmed', (tester) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 5), total: 5));
    await tester.pump();
    notifier().setQuery('  lavanda  ');
    await tester.pump(exploreDebounce);
    expect(repo.calls[1].query, 'lavanda');
  });

  testWidgets('a late response of an older query never replaces the current '
      'one', (tester) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 5), total: 5));
    await tester.pump();

    notifier().setQuery('a');
    await tester.pump(exploreDebounce);
    notifier().setQuery('ab');
    await tester.pump(exploreDebounce);
    expect(repo.calls.map((c) => c.query), ['', 'a', 'ab']);

    repo.calls[2].completer.complete(_page(['ab-1'], total: 1));
    await tester.pump();
    expect(read().items.map((i) => i.id), ['ab-1']);

    repo.calls[1].completer.complete(_page(['a-1', 'a-2'], total: 2));
    await tester.pump();
    expect(read().items.map((i) => i.id), ['ab-1']);
    expect(read().total, 1);
  });

  testWidgets('a late "load more" of an older query is discarded', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 50), total: 120));
    await tester.pump();
    notifier().loadMore();
    notifier().setQuery('zz');
    await tester.pump(exploreDebounce);
    repo.calls[2].completer.complete(_page(['zz-1'], total: 1));
    await tester.pump();
    repo.calls[1].completer.complete(
      _page(_ids(50, 50), total: 120, offset: 50),
    );
    await tester.pump();
    expect(read().items.map((i) => i.id), ['zz-1']);
    expect(read().loadingMore, isFalse);
  });

  testWidgets('an empty query lists everything again', (tester) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 5), total: 5));
    await tester.pump();
    notifier().setQuery('abc');
    await tester.pump(exploreDebounce);
    repo.calls[1].completer.complete(_page(['abc-1'], total: 1));
    await tester.pump();

    notifier().setQuery('');
    await tester.pump(exploreDebounce);
    expect(repo.calls, hasLength(3));
    expect(repo.calls[2].query, isEmpty);
    repo.calls[2].completer.complete(_page(_ids(0, 5), total: 5));
    await tester.pump();
    expect(read().items, hasLength(5));
  });

  testWidgets('Aceites never reaches the network; Todas and Plantas share '
      'the loaded list', (tester) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 5), total: 5));
    await tester.pump();

    notifier().setFilter(ExploreFilter.plants);
    notifier().setFilter(ExploreFilter.all);
    notifier().setFilter(ExploreFilter.oils);
    expect(read().showsOils, isTrue);
    notifier().loadMore();
    notifier().setQuery('rose');
    await tester.pump(exploreDebounce);
    expect(repo.calls, hasLength(1), reason: 'no request for Aceites');

    notifier().setFilter(ExploreFilter.plants);
    expect(repo.calls, hasLength(2), reason: 'query edited under Aceites');
    expect(repo.calls[1].query, 'rose');
    notifier().setFilter(ExploreFilter.all);
    expect(repo.calls, hasLength(2));
    expect(read().filter, ExploreFilter.all);
  });

  testWidgets('leaving Aceites without a query change does not refetch', (
    tester,
  ) async {
    init();
    repo.calls[0].completer.complete(_page(_ids(0, 5), total: 5));
    await tester.pump();
    notifier().setFilter(ExploreFilter.oils);
    notifier().setFilter(ExploreFilter.plants);
    expect(repo.calls, hasLength(1));
    expect(read().items, hasLength(5));
  });
}
