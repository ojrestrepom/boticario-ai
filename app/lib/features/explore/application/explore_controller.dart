import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/catalog_client_exception.dart';
import '../../catalog/data/catalog_providers.dart';
import '../../catalog/domain/plant_summary.dart';

/// Local filter chips of Explorar. The catalog has no oils, so `oils` never
/// reaches the network.
enum ExploreFilter { all, plants, oils }

/// Status of the first page of the current query.
enum ExplorePhase { loading, error, ready }

/// Page size requested from `GET /v1/plants`.
const explorePageSize = 50;

/// Quiet time after the last keystroke before the query is sent.
const exploreDebounce = Duration(milliseconds: 300);

const _genericError = 'No se pudo cargar el catálogo.';

String _messageOf(Object error) =>
    error is CatalogClientException ? error.message : _genericError;

@immutable
class ExploreState {
  ExploreState({
    this.query = '',
    this.filter = ExploreFilter.all,
    List<PlantSummary> items = const [],
    this.total = 0,
    this.phase = ExplorePhase.loading,
    this.errorMessage,
    this.loadingMore = false,
    this.footerError,
  }) : items = List.unmodifiable(items);

  /// Text of the search field, as typed (not trimmed).
  final String query;
  final ExploreFilter filter;

  /// Plants loaded so far for the current query, in API order.
  final List<PlantSummary> items;
  final int total;
  final ExplorePhase phase;

  /// Readable message when [phase] is [ExplorePhase.error].
  final String? errorMessage;
  final bool loadingMore;

  /// Readable message when the last "load more" request failed.
  final String? footerError;

  bool get hasMore => items.length < total;

  /// Whether the oils filter is selected (empty state, no plants shown).
  bool get showsOils => filter == ExploreFilter.oils;

  ExploreState copyWith({
    String? query,
    ExploreFilter? filter,
    List<PlantSummary>? items,
    int? total,
    ExplorePhase? phase,
    String? Function()? errorMessage,
    bool? loadingMore,
    String? Function()? footerError,
  }) => ExploreState(
    query: query ?? this.query,
    filter: filter ?? this.filter,
    items: items ?? this.items,
    total: total ?? this.total,
    phase: phase ?? this.phase,
    errorMessage: errorMessage == null ? this.errorMessage : errorMessage(),
    loadingMore: loadingMore ?? this.loadingMore,
    footerError: footerError == null ? this.footerError : footerError(),
  );
}

/// Debounce duration; tests may override it.
final exploreDebounceProvider = Provider<Duration>((ref) => exploreDebounce);

/// State of Explorar. It is auto-disposed: while the passport is open on top
/// of the list the page is still mounted and watching, so query, filter and
/// loaded pages survive; leaving Explorar resets it.
final exploreControllerProvider =
    NotifierProvider.autoDispose<ExploreController, ExploreState>(
      ExploreController.new,
      // Errors are shown at once; retrying is the user's decision.
      retry: (_, _) => null,
    );

class ExploreController extends Notifier<ExploreState> {
  Timer? _debounce;

  /// Bumped on every new first-page request: a response that carries an older
  /// value is dropped, so a late answer never replaces the current query's.
  int _generation = 0;

  /// Trimmed query of the latest first-page request.
  String _requestedQuery = '';

  @override
  ExploreState build() {
    ref.onDispose(() => _debounce?.cancel());
    final initial = ExploreState();
    // The first page is requested right away; state is only touched after
    // the first await, never while building.
    unawaited(_loadFirstPage('', reset: false));
    return initial;
  }

  /// Called on every edit of the search field.
  void setQuery(String text) {
    if (text == state.query) return;
    _debounce?.cancel();
    state = state.copyWith(query: text);
    if (state.showsOils) return; // Fetched when leaving `Aceites`.
    _debounce = Timer(ref.read(exploreDebounceProvider), _applyQuery);
  }

  void setFilter(ExploreFilter filter) {
    if (filter == state.filter) return;
    state = state.copyWith(filter: filter);
    if (filter == ExploreFilter.oils) {
      _debounce?.cancel();
      return;
    }
    // Back from `Aceites` with a query edited meanwhile: fetch it now.
    if (_debounce?.isActive != true && _trimmed != _requestedQuery) {
      _applyQuery();
    }
  }

  /// Repeats the first-page request of the current query.
  void retry() {
    _debounce?.cancel();
    unawaited(_loadFirstPage(_trimmed));
  }

  /// Requests the next page. Safe to call repeatedly: it does nothing while
  /// a page is loading, after a footer error (use [retryMore]) or at the end.
  void loadMore() {
    if (state.phase != ExplorePhase.ready ||
        state.showsOils ||
        state.loadingMore ||
        state.footerError != null ||
        !state.hasMore) {
      return;
    }
    unawaited(_fetchNextPage());
  }

  /// Retries only the failed next page, keeping what is already loaded.
  void retryMore() {
    if (state.footerError == null || state.loadingMore) return;
    state = state.copyWith(footerError: () => null);
    loadMore();
  }

  String get _trimmed => state.query.trim();

  void _applyQuery() {
    // Same effective query (e.g. only outer spaces changed): the current
    // list, or the request in flight, is already the right one.
    if (_trimmed == _requestedQuery) return;
    unawaited(_loadFirstPage(_trimmed));
  }

  Future<void> _loadFirstPage(String query, {bool reset = true}) async {
    final generation = ++_generation;
    _requestedQuery = query;
    if (reset) {
      state = state.copyWith(
        items: const [],
        total: 0,
        phase: ExplorePhase.loading,
        errorMessage: () => null,
        loadingMore: false,
        footerError: () => null,
      );
    }
    try {
      final page = await ref
          .read(catalogRepositoryProvider)
          .listPlants(query: query, limit: explorePageSize, offset: 0);
      if (!ref.mounted || generation != _generation) return;
      state = state.copyWith(
        items: page.items,
        total: page.items.isEmpty ? 0 : page.total,
        phase: ExplorePhase.ready,
      );
    } catch (error) {
      if (!ref.mounted || generation != _generation) return;
      state = state.copyWith(
        phase: ExplorePhase.error,
        errorMessage: () => _messageOf(error),
      );
    }
  }

  Future<void> _fetchNextPage() async {
    final generation = _generation;
    final offset = state.items.length;
    state = state.copyWith(loadingMore: true);
    try {
      final page = await ref
          .read(catalogRepositoryProvider)
          .listPlants(
            query: _requestedQuery,
            limit: explorePageSize,
            offset: offset,
          );
      if (!ref.mounted || generation != _generation) return;
      final items = [...state.items, ...page.items];
      state = state.copyWith(
        items: items,
        // An empty page ends the list even if `total` promised more.
        total: page.items.isEmpty ? items.length : page.total,
        loadingMore: false,
      );
    } catch (error) {
      if (!ref.mounted || generation != _generation) return;
      state = state.copyWith(
        loadingMore: false,
        footerError: () => _messageOf(error),
      );
    }
  }
}
