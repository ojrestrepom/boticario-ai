import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_consolidated.dart';
import 'passport_link.dart';
import 'passport_style.dart';
import 'passport_texts.dart';

/// `Fuentes` section, shown after the active tab content in every tab.
///
/// Plant-level credits and the image entry; it never says which field comes
/// from which source.
class PassportSourcesSection extends StatelessWidget {
  const PassportSourcesSection({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) {
    final image = plant.image;
    final empty = plant.credits.isEmpty && image == null;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(height: 24),
          const PassportSectionTitle(PassportTexts.sourcesTitle),
          const SizedBox(height: 8),
          if (empty)
            const Text(PassportTexts.noSources)
          else ...[
            const Text(PassportTexts.sourcesIntro),
            const SizedBox(height: 12),
            for (final credit in plant.credits) _CreditEntry(credit: credit),
            if (image != null) _ImageEntry(image: image),
          ],
        ],
      ),
    );
  }
}

class _EntryTitle extends StatelessWidget {
  const _EntryTitle(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: Theme.of(context).textTheme.titleSmall
        ?.copyWith(color: passportInk, fontWeight: FontWeight.w700),
  );
}

class _CreditEntry extends StatelessWidget {
  const _CreditEntry({required this.credit});
  final PlantCredit credit;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _EntryTitle(credit.name),
        Text('${PassportTexts.licensePrefix}: ${credit.license}'),
        if (credit.licenseUrl != null)
          PassportLink(
            label: PassportTexts.licenseUrlPrefix,
            url: credit.licenseUrl!,
          ),
        Text('${PassportTexts.attributionPrefix}: ${credit.attribution}'),
        if (credit.url != null)
          PassportLink(label: PassportTexts.pageUrlPrefix, url: credit.url!),
      ],
    ),
  );
}

class _ImageEntry extends StatelessWidget {
  const _ImageEntry({required this.image});
  final PlantImage image;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _EntryTitle(PassportTexts.imageSourceTitle),
        Text(
          '${PassportTexts.authorPrefix}: '
          '${image.author ?? PassportTexts.notAvailable}',
        ),
        Text('${PassportTexts.licensePrefix}: ${image.license}'),
        if (image.licenseUrl != null)
          PassportLink(
            label: PassportTexts.licenseUrlPrefix,
            url: image.licenseUrl!,
          ),
        PassportLink(label: PassportTexts.pageUrlPrefix, url: image.pageUrl),
      ],
    ),
  );
}
