import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/catalog_client_exception.dart';
import '../../catalog/data/catalog_providers.dart';
import '../../catalog/domain/goal.dart';

/// Page size requested from `GET /v1/goals/{goalId}/plants`.
const goalResultsPageSize = 20;

/// Status of the first page.
enum GoalResultsPhase { loading, error, notFound, ready }

/// What P07 lists: a goal, or one of its subareas when [subareaId] is set.
typedef GoalResultsQuery = ({String goalId, String? subareaId});

const _genericError = 'No se pudo cargar el catálogo.';

@immutable
class GoalResultsState {
  GoalResultsState({
    this.phase = GoalResultsPhase.loading,
    this.goal,
    this.subarea,
    List<GoalPlant> items = const [],
    this.total = 0,
    this.errorMessage,
    this.loadingMore = false,
    this.footerError,
  }) : items = List.unmodifiable(items);

  final GoalResultsPhase phase;

  /// Goal and subarea as the API names them (the subtitle comes from here).
  final GoalRef? goal;
  final GoalRef? subarea;

  /// Plants loaded so far, in API order.
  final List<GoalPlant> items;
  final int total;

  /// Readable message when [phase] is [GoalResultsPhase.error].
  final String? errorMessage;
  final bool loadingMore;

  /// Readable message when the last "load more" request failed.
  final String? footerError;

  bool get hasMore => items.length < total;

  /// Name for the subtitle: the subarea if there is one, else the goal.
  String? get targetName => (subarea ?? goal)?.name;

  GoalResultsState copyWith({
    GoalResultsPhase? phase,
    List<GoalPlant>? items,
    int? total,
    bool? loadingMore,
    String? Function()? footerError,
  }) => GoalResultsState(
    phase: phase ?? this.phase,
    goal: goal,
    subarea: subarea,
    items: items ?? this.items,
    total: total ?? this.total,
    errorMessage: errorMessage,
    loadingMore: loadingMore ?? this.loadingMore,
    footerError: footerError == null ? this.footerError : footerError(),
  );
}

/// State of P07 for one goal (and subarea). It is auto-disposed: while the
/// passport is open on top of P07 the page is still mounted and watching, so
/// the loaded pages survive; leaving P07 drops them.
final goalResultsControllerProvider = NotifierProvider.autoDispose
    .family<GoalResultsController, GoalResultsState, GoalResultsQuery>(
      GoalResultsController.new,
      // Errors are shown at once; retrying is the user's decision.
      retry: (_, _) => null,
    );

class GoalResultsController extends Notifier<GoalResultsState> {
  GoalResultsController(this.query);

  final GoalResultsQuery query;

  /// Bumped on every first-page request: a response that carries an older
  /// value is dropped, so a late answer never replaces the current one.
  int _generation = 0;

  @override
  GoalResultsState build() {
    // State is only touched after the first await, never while building.
    unawaited(_loadFirstPage(reset: false));
    return GoalResultsState();
  }

  /// Repeats the first-page request.
  void retry() => unawaited(_loadFirstPage());

  /// Requests the next page. Safe to call repeatedly: it does nothing while
  /// a page is loading, after a footer error (use [retryMore]) or at the end.
  void loadMore() {
    if (state.phase != GoalResultsPhase.ready ||
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

  Future<void> _loadFirstPage({bool reset = true}) async {
    final generation = ++_generation;
    if (reset) state = GoalResultsState();
    try {
      final page = await ref
          .read(catalogRepositoryProvider)
          .listGoalPlants(
            query.goalId,
            subarea: query.subareaId,
            limit: goalResultsPageSize,
            offset: 0,
          );
      if (!ref.mounted || generation != _generation) return;
      state = page == null
          ? GoalResultsState(phase: GoalResultsPhase.notFound)
          : GoalResultsState(
              phase: GoalResultsPhase.ready,
              goal: page.goal,
              subarea: page.subarea,
              items: page.items,
              total: page.items.isEmpty ? 0 : page.total,
            );
    } catch (error) {
      if (!ref.mounted || generation != _generation) return;
      state = GoalResultsState(
        phase: GoalResultsPhase.error,
        errorMessage: error is CatalogClientException
            ? error.message
            : _genericError,
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
          .listGoalPlants(
            query.goalId,
            subarea: query.subareaId,
            limit: goalResultsPageSize,
            offset: offset,
          );
      if (!ref.mounted || generation != _generation) return;
      if (page == null) {
        state = state.copyWith(
          loadingMore: false,
          footerError: () => 'Objetivo no encontrado',
        );
        return;
      }
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
        footerError: () =>
            error is CatalogClientException ? error.message : _genericError,
      );
    }
  }
}
