import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_consolidated.dart';
import 'passport_link.dart';
import 'passport_style.dart';
import 'passport_texts.dart';

/// Dimmed ink of unresolved citations; the text and italics carry the state,
/// so it does not depend on color alone.
const _dimmedInk = Color(0xFF5B665F);

/// Key of a use group within its plant. The activity alone is not unique
/// (two source terms can map to the same activity), so the position and the
/// source activity are part of it.
String useGroupKey(int index, UseGroup group) =>
    '$index|${group.activity}|${group.activitySource}';

/// `Usos` tab content: the compact notice line, then the use groups.
class PassportUsesTab extends StatelessWidget {
  const PassportUsesTab({
    required this.plant,
    required this.expandedGroups,
    required this.onToggleGroup,
    super.key,
  });

  final Plant plant;

  /// Keys (see [useGroupKey]) of the groups whose citations are open.
  final Set<String> expandedGroups;
  final ValueChanged<String> onToggleGroup;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const _UsesNotice(),
      if (plant.useGroups.isEmpty)
        const Text(PassportTexts.noUses)
      else
        for (var i = 0; i < plant.useGroups.length; i++)
          _UseGroupCard(
            group: plant.useGroups[i],
            expanded: expandedGroups.contains(
              useGroupKey(i, plant.useGroups[i]),
            ),
            onToggle: () => onToggleGroup(useGroupKey(i, plant.useGroups[i])),
          ),
    ],
  );
}

/// Compact line that replaces the always-visible box: one button of at least
/// 48 dp that opens the full notice in a dialog.
class _UsesNotice extends StatelessWidget {
  const _UsesNotice();

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 6),
    child: Align(
      alignment: Alignment.centerLeft,
      child: Semantics(
        container: true,
        button: true,
        label: PassportTexts.usesNoticeLabel,
        onTap: () => _showUsesNotice(context),
        excludeSemantics: true,
        child: InkWell(
          key: const ValueKey('uses-notice-line'),
          borderRadius: BorderRadius.circular(8),
          onTap: () => _showUsesNotice(context),
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48, minWidth: 48),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.warning_amber, color: passportGreen),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      PassportTexts.usesNoticeLabel,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: passportInk,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

Future<void> _showUsesNotice(BuildContext context) => showDialog<void>(
  context: context,
  builder: (_) => const _UsesNoticeDialog(),
);

/// Full fixed notice. Closes with «Entendido», the system back or a tap
/// outside.
class _UsesNoticeDialog extends StatelessWidget {
  const _UsesNoticeDialog();

  @override
  Widget build(BuildContext context) => AlertDialog(
    key: const ValueKey('uses-notice-dialog'),
    title: Semantics(
      header: true,
      child: const Text(PassportTexts.usesNoticeLabel),
    ),
    content: const SingleChildScrollView(child: Text(PassportTexts.usesNotice)),
    actions: [
      TextButton(
        style: TextButton.styleFrom(
          minimumSize: const Size(48, 48),
          foregroundColor: passportGreen,
        ),
        onPressed: () => Navigator.of(context).pop(),
        child: const Text(PassportTexts.usesNoticeClose),
      ),
    ],
  );
}

class _UseGroupCard extends StatelessWidget {
  const _UseGroupCard({
    required this.group,
    required this.expanded,
    required this.onToggle,
  });

  final UseGroup group;
  final bool expanded;
  final VoidCallback onToggle;

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
          if (group.glossary case final glossary?) _Glossary(glossary),
          if (PassportTexts.useGroupPlaces(group.countries) case final places?)
            Text(places, style: theme.bodyMedium?.copyWith(color: passportInk)),
          _CitationsToggle(
            activity: group.activity,
            count: group.references.length,
            expanded: expanded,
            onToggle: onToggle,
          ),
          if (expanded)
            for (final reference in group.references)
              _Citation(reference: reference),
          const Divider(height: 20),
        ],
      ),
    );
  }
}

/// Meaning of the group's term: a gray label, then
/// `Term: «text» (Source)` with the source linked in line. The texts come
/// from the API as they are; only the label, quotes and "adaptado de" are
/// the app's own.
class _Glossary extends StatelessWidget {
  const _Glossary(this.glossary);

  final GlossaryEntry glossary;

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.bodySmall
        ?.copyWith(color: passportMuted);
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(PassportTexts.glossaryLabel, style: style),
          PassportLinkedText(
            style: style,
            parts: [
              PassportLinkPart(
                '${glossary.term}: ${PassportTexts.glossaryOpenQuote}'
                '${glossary.text}${PassportTexts.glossaryCloseQuote} ('
                '${glossary.adapted ? '${PassportTexts.glossaryAdaptedFrom} ' : ''}',
              ),
              PassportLinkPart(
                glossary.sourceName,
                url: glossary.url,
                destination: PassportTexts.glossarySourceDestination,
              ),
              const PassportLinkPart(')'),
            ],
          ),
        ],
      ),
    );
  }
}

/// Button that opens and closes the citations of a group. The state shows in
/// the text, the icon and the semantics.
class _CitationsToggle extends StatelessWidget {
  const _CitationsToggle({
    required this.activity,
    required this.count,
    required this.expanded,
    required this.onToggle,
  });

  final String activity;
  final int count;
  final bool expanded;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    button: true,
    expanded: expanded,
    label: expanded
        ? PassportTexts.hideCitationsSemantics(activity)
        : PassportTexts.showCitationsSemantics(count, activity),
    onTap: onToggle,
    excludeSemantics: true,
    child: TextButton.icon(
      onPressed: onToggle,
      style: TextButton.styleFrom(
        foregroundColor: passportGreen,
        minimumSize: const Size(48, 48),
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.only(right: 12),
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      icon: Icon(expanded ? Icons.expand_less : Icons.expand_more),
      label: Text(
        expanded
            ? PassportTexts.hideCitations
            : PassportTexts.showCitations(count),
      ),
    ),
  );
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
