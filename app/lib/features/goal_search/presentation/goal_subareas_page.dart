import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../application/goal_catalog_controller.dart';
import 'goal_list_shell.dart';

/// Subareas of a goal («Otros objetivos»): one row per subarea with plants,
/// in the API order. Each row opens the plants (P07) filtered by it.
class GoalSubareasPage extends ConsumerWidget {
  const GoalSubareasPage({
    required this.goalId,
    required this.onBack,
    required this.onHome,
    required this.onOpenPlants,
    super.key,
  });

  final String goalId;
  final VoidCallback onBack;
  final VoidCallback onHome;

  /// Receives the goal id and the id of the chosen subarea.
  final void Function(String goalId, String subareaId) onOpenPlants;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(goalCatalogControllerProvider);
    final goal = state.goalById(goalId);
    final status = goalCatalogStatus(
      state,
      ref.read(goalCatalogControllerProvider.notifier).retry,
    );
    // An empty subarea is optional and is not listed.
    final subareas = [
      for (final subarea in goal?.subareas ?? const [])
        if (subarea.plantCount > 0) subarea,
    ];
    return GoalListShell(
      title: goal?.name ?? 'Objetivos',
      backLabel: 'Volver a objetivos',
      onBack: onBack,
      onHome: onHome,
      children: [
        ?status,
        if (status == null && goal == null)
          const GoalMessage(
            key: ValueKey('goal-not-found'),
            icon: Icons.search_off,
            text: 'Objetivo no encontrado',
          ),
        if (status == null && goal != null && subareas.isEmpty)
          const GoalMessage(
            key: ValueKey('subareas-empty'),
            icon: Icons.search_off,
            text: 'Aún no hay subáreas con plantas para este objetivo',
          ),
        for (final subarea in subareas)
          GoalRow(
            key: ValueKey('subarea-${subarea.id}'),
            label: subarea.name,
            icon: goalIconFor(subarea.id),
            onTap: () => onOpenPlants(goalId, subarea.id),
          ),
      ],
    );
  }
}
