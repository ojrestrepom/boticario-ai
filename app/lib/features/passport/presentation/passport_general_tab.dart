import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_consolidated.dart';
import 'passport_style.dart';
import 'passport_texts.dart';

/// `General` tab content.
class PassportGeneralTab extends StatelessWidget {
  const PassportGeneralTab({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) {
    final primary = plant.primaryName;
    // Without a Spanish common name the display name is the scientific name,
    // which is not shown as a common name.
    final hasCommonName = primary != plant.scientificName;
    final others = _otherCommonNames(primary);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (plant.safety?.level == SafetyLevel.high) const _HighLevelNotice(),
        PassportField(
          PassportTexts.commonNameLabel,
          hasCommonName ? primary : PassportTexts.noSpanishCommonName,
        ),
        if (plant.synonyms.isEmpty)
          const PassportField(
            PassportTexts.synonymsLabel,
            PassportTexts.noSynonyms,
          )
        else
          PassportFieldLines(PassportTexts.synonymsLabel, plant.synonyms),
        PassportField(
          PassportTexts.familyLabel,
          plant.family ?? PassportTexts.notAvailable,
        ),
        PassportField(
          PassportTexts.originLabel,
          plant.origin ?? PassportTexts.notAvailable,
        ),
        PassportField(
          PassportTexts.partLabel,
          plant.parts.isEmpty ? PassportTexts.noParts : plant.parts.join(', '),
        ),
        PassportField(
          PassportTexts.oilLabel,
          plant.oil?.type ?? PassportTexts.notAvailable,
        ),
        PassportField(
          PassportTexts.descriptionLabel,
          plant.description ?? PassportTexts.notAvailable,
        ),
        if (others.isEmpty)
          const PassportField(
            PassportTexts.otherCommonNamesLabel,
            PassportTexts.noCommonNames,
          )
        else
          PassportFieldLines(PassportTexts.otherCommonNamesLabel, [
            for (final name in others) '${name.text} (${name.language})',
          ]),
      ],
    );
  }

  /// Common names except the one shown as `Nombre común` (first match only).
  List<PlantName> _otherCommonNames(String primary) {
    final others = [...plant.commonNames];
    final index = others.indexWhere((name) => name.text == primary);
    if (index >= 0) others.removeAt(index);
    return others;
  }
}

/// Notice for `safety.level == alto`. The level is text, not only color.
class _HighLevelNotice extends StatelessWidget {
  const _HighLevelNotice();

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    margin: const EdgeInsets.only(bottom: 14),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: const Color(0xFFFFF1E6),
      border: Border.all(color: const Color(0xFF8A3B00)),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          PassportTexts.highLevelNoticeTitle,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: const Color(0xFF5C2600),
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          PassportTexts.highLevelNoticeBody,
          style: Theme.of(context).textTheme.bodyMedium
              ?.copyWith(color: passportInk),
        ),
      ],
    ),
  );
}
