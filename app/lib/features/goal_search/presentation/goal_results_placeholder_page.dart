import 'package:flutter/material.dart';

import 'goal_list_shell.dart';

/// PLACEHOLDER for P07 (group 5 of `enable-goal-search`). It only exists so
/// that `/goals/:goalId/plants` can be routed and tested; group 5 replaces it
/// with `goal_results_page.dart`. It makes no request and lists no plants.
class GoalResultsPlaceholderPage extends StatelessWidget {
  const GoalResultsPlaceholderPage({
    required this.goalId,
    required this.onBack,
    required this.onHome,
    this.subareaId,
    super.key,
  });

  final String goalId;
  final String? subareaId;
  final VoidCallback onBack;
  final VoidCallback onHome;

  @override
  Widget build(BuildContext context) => GoalListShell(
    title: 'Recomendaciones',
    backLabel: 'Volver',
    onBack: onBack,
    onHome: onHome,
    children: [
      GoalMessage(
        key: const ValueKey('goal-results-placeholder'),
        icon: Icons.construction,
        text:
            'Pantalla provisional (grupo 5): $goalId'
            '${subareaId == null ? '' : ' / $subareaId'}',
      ),
    ],
  );
}
