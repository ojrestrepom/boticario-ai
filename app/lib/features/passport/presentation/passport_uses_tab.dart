import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_consolidated.dart';
import 'passport_style.dart';
import 'passport_texts.dart';

/// Dimmed ink of unresolved citations; the text and italics carry the state,
/// so it does not depend on color alone.
const _dimmedInk = Color(0xFF5B665F);

/// `Usos` tab content: the fixed notice, then the use groups.
class PassportUsesTab extends StatelessWidget {
  const PassportUsesTab({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const _UsesNotice(),
      if (plant.useGroups.isEmpty)
        const Text(PassportTexts.noUses)
      else
        for (final group in plant.useGroups) _UseGroupCard(group: group),
    ],
  );
}

class _UsesNotice extends StatelessWidget {
  const _UsesNotice();

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    margin: const EdgeInsets.only(bottom: 14),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: const Color(0xFFEAF2EC),
      border: Border.all(color: passportGreen),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Text(
      PassportTexts.usesNotice,
      style: Theme.of(context).textTheme.bodyMedium
          ?.copyWith(color: passportInk),
    ),
  );
}

class _UseGroupCard extends StatelessWidget {
  const _UseGroupCard({required this.group});

  final UseGroup group;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            group.activity,
            style: theme.titleSmall?.copyWith(
              color: passportInk,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            PassportTexts.traditionalRecord,
            style: theme.labelLarge?.copyWith(color: passportGreen),
          ),
          Text(
            PassportTexts.recordCount(group.count),
            style: theme.bodyMedium?.copyWith(color: passportInk),
          ),
          if (group.countries.isNotEmpty) ...[
            const SizedBox(height: 6),
            PassportField(
              PassportTexts.countriesLabel,
              group.countries.join(', '),
            ),
          ],
          Text(
            PassportTexts.useGroupClarification,
            style: theme.bodySmall?.copyWith(color: passportInk),
          ),
          const SizedBox(height: 8),
          for (final reference in group.references)
            _Citation(reference: reference),
          const Divider(height: 20),
        ],
      ),
    );
  }
}

class _Citation extends StatelessWidget {
  const _Citation({required this.reference});

  final CitedReference reference;

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.bodyMedium;
    final text =
        !reference.resolved &&
            !reference.citation.endsWith(PassportTexts.unresolvedSuffix)
        ? '${reference.citation} ${PassportTexts.unresolvedSuffix}'
        : reference.citation;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text(
        text,
        style: reference.resolved
            ? style?.copyWith(color: passportInk)
            : style?.copyWith(color: _dimmedInk, fontStyle: FontStyle.italic),
      ),
    );
  }
}
