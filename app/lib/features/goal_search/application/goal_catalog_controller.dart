import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/data/catalog_client_exception.dart';
import '../../catalog/data/catalog_providers.dart';
import '../../catalog/domain/goal.dart';

/// Status of the goal catalog request.
enum GoalCatalogPhase { loading, error, ready }

const _genericError = 'No se pudo cargar el catálogo.';

@immutable
class GoalCatalogState {
  GoalCatalogState({
    this.phase = GoalCatalogPhase.loading,
    List<Goal> goals = const [],
    this.errorMessage,
  }) : goals = List.unmodifiable(goals);

  final GoalCatalogPhase phase;

  /// Goals in the order of `GET /v1/goals`.
  final List<Goal> goals;

  /// Readable message when [phase] is [GoalCatalogPhase.error].
  final String? errorMessage;

  /// The goal with [id], or `null` while it is not loaded or unknown.
  Goal? goalById(String id) {
    for (final goal in goals) {
      if (goal.id == id) return goal;
    }
    return null;
  }
}

/// State of P06 and of the subareas screen. It is auto-disposed: while the
/// subareas screen is open over P06 both are mounted and share one request;
/// leaving the flow drops the state (the app keeps no cache).
final goalCatalogControllerProvider =
    NotifierProvider.autoDispose<GoalCatalogController, GoalCatalogState>(
      GoalCatalogController.new,
      // Errors are shown at once; retrying is the user's decision.
      retry: (_, _) => null,
    );

class GoalCatalogController extends Notifier<GoalCatalogState> {
  /// Bumped on every request: a response that carries an older value is
  /// dropped, so a late answer never replaces the current one.
  int _generation = 0;

  @override
  GoalCatalogState build() {
    // State is only touched after the first await, never while building.
    unawaited(_load(reset: false));
    return GoalCatalogState();
  }

  /// Repeats the request after an error.
  void retry() => unawaited(_load());

  Future<void> _load({bool reset = true}) async {
    final generation = ++_generation;
    if (reset) state = GoalCatalogState();
    try {
      final goals = await ref.read(catalogRepositoryProvider).listGoals();
      if (!ref.mounted || generation != _generation) return;
      state = GoalCatalogState(phase: GoalCatalogPhase.ready, goals: goals);
    } catch (error) {
      if (!ref.mounted || generation != _generation) return;
      state = GoalCatalogState(
        phase: GoalCatalogPhase.error,
        errorMessage: error is CatalogClientException
            ? error.message
            : _genericError,
      );
    }
  }
}
