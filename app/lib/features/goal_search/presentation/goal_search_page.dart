import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../catalog/domain/goal.dart';
import '../application/goal_catalog_controller.dart';
import 'goal_list_shell.dart';

/// P06: one row per goal of `GET /v1/goals`, in the API order. A goal with
/// subareas opens the subareas screen; the others open their plants (P07).
/// Navigation is provided by the app shell.
class GoalSearchPage extends ConsumerWidget {
  const GoalSearchPage({
    required this.onBack,
    required this.onHome,
    required this.onOpenSubareas,
    required this.onOpenPlants,
    super.key,
  });

  final VoidCallback onBack;
  final VoidCallback onHome;

  /// Receives the id of a goal that has subareas.
  final ValueChanged<String> onOpenSubareas;

  /// Receives the id of a goal without subareas.
  final ValueChanged<String> onOpenPlants;

  void _open(Goal goal) =>
      goal.hasSubareas ? onOpenSubareas(goal.id) : onOpenPlants(goal.id);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(goalCatalogControllerProvider);
    final status = goalCatalogStatus(
      state,
      ref.read(goalCatalogControllerProvider.notifier).retry,
    );
    return GoalListShell(
      title: '¿Qué deseas lograr?',
      subtitle: 'Selecciona un objetivo principal',
      backLabel: 'Volver a Inicio',
      onBack: onBack,
      onHome: onHome,
      children: [
        ?status,
        if (status == null)
          for (final goal in state.goals)
            GoalRow(
              key: ValueKey('goal-${goal.id}'),
              label: goal.name,
              icon: goalIconFor(goal.id),
              onTap: () => _open(goal),
            ),
      ],
    );
  }
}
