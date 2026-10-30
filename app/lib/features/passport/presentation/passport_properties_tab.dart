import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_consolidated.dart';
import 'passport_style.dart';
import 'passport_texts.dart';

/// `Propiedades` tab content: EMA goals and precautions.
class PassportPropertiesTab extends StatelessWidget {
  const PassportPropertiesTab({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) {
    final safety = plant.safety;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const PassportSectionTitle(PassportTexts.goalsTitle),
        const SizedBox(height: 8),
        if (plant.goals.isEmpty)
          const Padding(
            padding: EdgeInsets.only(bottom: 14),
            child: Text(PassportTexts.noGoals),
          )
        else
          for (final goal in plant.goals) _GoalCard(goal: goal),
        const SizedBox(height: 8),
        const PassportSectionTitle(PassportTexts.safetyTitle),
        const SizedBox(height: 8),
        if (safety == null)
          const Text(PassportTexts.noSafety)
        else ...[
          if (safety.level != null)
            PassportField(
              PassportTexts.safetyLevelLabel,
              _levelText(safety.level!),
            ),
          Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: Text(safety.text),
          ),
          _Citations(references: safety.references),
        ],
      ],
    );
  }

  static String _levelText(SafetyLevel level) => switch (level) {
    SafetyLevel.high => PassportTexts.levelHigh,
    SafetyLevel.medium => PassportTexts.levelMedium,
    SafetyLevel.low => PassportTexts.levelLow,
  };
}

class _GoalCard extends StatelessWidget {
  const _GoalCard({required this.goal});
  final PlantGoal goal;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          goal.name,
          style: Theme.of(context).textTheme.titleSmall
              ?.copyWith(color: passportInk, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        if (goal.subarea != null)
          PassportField(PassportTexts.subareaLabel, goal.subarea!),
        PassportField(PassportTexts.areaLabel, goal.area),
        PassportField(PassportTexts.documentTypeLabel, goal.evidence),
        _Citations(references: goal.references),
        Text(
          PassportTexts.goalDisclaimer,
          style: Theme.of(context).textTheme.bodySmall
              ?.copyWith(color: passportInk),
        ),
      ],
    ),
  );
}

class _Citations extends StatelessWidget {
  const _Citations({required this.references});
  final List<CitedReference> references;

  @override
  Widget build(BuildContext context) => references.isEmpty
      ? const SizedBox.shrink()
      : PassportFieldLines(PassportTexts.citationsLabel, [
          for (final reference in references) reference.citation,
        ]);
}
