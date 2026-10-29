import 'package:flutter/material.dart';

import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_consolidated.dart';
import 'passport_link.dart';
import 'passport_style.dart';
import 'passport_texts.dart';

/// `Fuentes` tab: the fourth tab of the passport.
///
/// Plant-level credits and the image entry. Names are linked, URLs are never
/// shown as text, and it never says which field comes from which source.
class PassportSourcesTab extends StatelessWidget {
  const PassportSourcesTab({required this.plant, super.key});

  final Plant plant;

  @override
  Widget build(BuildContext context) {
    final image = plant.image;
    final empty = plant.credits.isEmpty && image == null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (empty)
          const Text(PassportTexts.noSources)
        else ...[
          const Text(PassportTexts.sourcesIntro),
          const SizedBox(height: 12),
          for (final credit in plant.credits) _CreditEntry(credit: credit),
          if (image != null) _ImageEntry(image: image),
        ],
      ],
    );
  }
}

TextStyle? _titleStyle(BuildContext context) =>
    Theme.of(context).textTheme.titleSmall
        ?.copyWith(color: passportInk, fontWeight: FontWeight.w700);

class _EntryTitle extends StatelessWidget {
  const _EntryTitle(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(text, style: _titleStyle(context));
}

class _LicenseRow extends StatelessWidget {
  const _LicenseRow({required this.license, required this.licenseUrl});
  final String license;
  final String? licenseUrl;

  @override
  Widget build(BuildContext context) => PassportInlineLink(
    prefix: '${PassportTexts.licensePrefix}: ',
    text: license,
    url: licenseUrl,
    destination: PassportTexts.licenseTextDestination,
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
        PassportInlineLink(
          text: credit.name,
          url: credit.url,
          destination: PassportTexts.sourcePageDestination,
          style: _titleStyle(context),
        ),
        _LicenseRow(license: credit.license, licenseUrl: credit.licenseUrl),
        Text(
          '${PassportTexts.attributionPrefix}: ${credit.attribution}',
          style: Theme.of(context).textTheme.bodySmall
              ?.copyWith(color: passportMuted),
        ),
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
        _LicenseRow(license: image.license, licenseUrl: image.licenseUrl),
        PassportInlineLink(
          text: PassportTexts.imageFileLinkLabel,
          url: image.pageUrl,
          destination: PassportTexts.imageFileDestination,
        ),
      ],
    ),
  );
}
