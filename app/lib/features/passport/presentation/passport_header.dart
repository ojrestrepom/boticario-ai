import 'package:flutter/material.dart';

import '../../catalog/data/plant_image_policy.dart';
import '../../catalog/domain/plant.dart';
import '../../catalog/domain/plant_consolidated.dart';
import '../../catalog/presentation/plant_photo.dart';
import 'passport_link.dart';
import 'passport_style.dart';
import 'passport_texts.dart';

/// Back label when the passport is opened from Explorar.
const defaultPassportBackLabel = 'Volver a Explorar';

/// Passport header: back button, plant icon, names and the favorite stub,
/// plus the plant photo with its attribution when there is one.
///
/// The photo is the 500 px Wikimedia thumbnail of `image.url` (design D9).
/// While it loads, if it fails or if the plant has no usable image, the local
/// art stays and no attribution is shown.
class PassportHeader extends StatelessWidget {
  const PassportHeader({
    required this.plant,
    required this.onBack,
    this.backLabel = defaultPassportBackLabel,
    this.imageProviderFor = PlantImagePolicy.thumbnailProviderFor,
    super.key,
  });

  final Plant plant;
  final VoidCallback onBack;

  /// Label of the back button: it names the screen the passport came from.
  final String backLabel;
  final ImageProvider? Function(String? url) imageProviderFor;

  @override
  Widget build(BuildContext context) {
    final image = plant.image;
    final provider = image == null ? null : imageProviderFor(image.url);
    return Column(
      children: [
        _titleRow(context),
        if (image != null && provider != null)
          _PlantPhoto(
            plantName: plant.primaryName,
            image: image,
            provider: provider,
          ),
      ],
    );
  }

  Widget _titleRow(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
    child: Row(
      children: [
        SizedBox(
          width: 48,
          height: 48,
          child: IconButton(
            tooltip: backLabel,
            onPressed: onBack,
            icon: const Icon(Icons.chevron_left),
            color: passportGreen,
          ),
        ),
        const ExcludeSemantics(
          child: Icon(Icons.local_florist, color: passportGreen, size: 34),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                plant.primaryName,
                style: Theme.of(context).textTheme.titleLarge
                    ?.copyWith(color: passportInk),
              ),
              if (plant.secondaryName != null)
                Text(
                  plant.secondaryName!,
                  style: Theme.of(context).textTheme.bodyMedium
                      ?.copyWith(color: passportInk),
                ),
            ],
          ),
        ),
        Semantics(
          label: 'Favorito no disponible',
          button: true,
          enabled: false,
          child: const SizedBox(
            width: 48,
            height: 48,
            child: Icon(Icons.favorite_border, color: Colors.grey),
          ),
        ),
      ],
    ),
  );
}

class _PlantPhoto extends StatelessWidget {
  const _PlantPhoto({
    required this.plantName,
    required this.image,
    required this.provider,
  });

  final String plantName;
  final PlantImage image;
  final ImageProvider provider;

  static const _height = 140.0;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
    child: PlantPhotoImage(
      provider: provider,
      height: _height,
      placeholder: const PlantArtPlaceholder(height: _height),
      failed: const SizedBox.shrink(),
      loaded: (context, photo) => _loaded(context, photo),
    ),
  );

  Widget _loaded(BuildContext context, Widget photo) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Semantics(
        image: true,
        label: PassportTexts.imageDescription(plantName),
        child: ClipRRect(borderRadius: BorderRadius.circular(12), child: photo),
      ),
      const SizedBox(height: 4),
      Text(
        '${PassportTexts.authorPrefix}: '
        '${image.author ?? PassportTexts.notAvailable}',
        style: Theme.of(context).textTheme.bodyMedium
            ?.copyWith(color: passportInk),
      ),
      Text(
        '${PassportTexts.licensePrefix}: ${image.license}',
        style: Theme.of(context).textTheme.bodyMedium
            ?.copyWith(color: passportInk),
      ),
      PassportLink(label: PassportTexts.imageFilePageLabel, url: image.pageUrl),
    ],
  );
}
