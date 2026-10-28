import 'package:flutter/material.dart';

/// Color of the local art shown instead of a photo.
const plantArtGreen = Color(0xFF236335);

/// Image of a plant (the 500 px Wikimedia thumbnail) shared by the passport
/// header and the cards of P07.
///
/// While the photo downloads it shows [placeholder] (the local art). When it
/// fails it shows [failed]. Once the first frame is there it shows
/// [loaded] with the photo, so the caller can put the attribution next to it
/// only when the photo is really visible.
class PlantPhotoImage extends StatelessWidget {
  const PlantPhotoImage({
    required this.provider,
    required this.height,
    required this.placeholder,
    required this.failed,
    required this.loaded,
    super.key,
  });

  final ImageProvider provider;
  final double height;
  final Widget placeholder;
  final Widget failed;
  final Widget Function(BuildContext context, Widget photo) loaded;

  @override
  Widget build(BuildContext context) => Image(
    image: provider,
    width: double.infinity,
    height: height,
    fit: BoxFit.cover,
    excludeFromSemantics: true,
    frameBuilder: (context, child, frame, wasSynchronouslyLoaded) {
      if (frame == null) return placeholder;
      return loaded(context, child);
    },
    errorBuilder: (context, error, stackTrace) => failed,
  );
}

/// The local art, decorative: it is excluded from semantics.
class PlantArtPlaceholder extends StatelessWidget {
  const PlantArtPlaceholder({
    required this.height,
    this.iconSize = 64,
    super.key,
  });

  final double height;
  final double iconSize;

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: Container(
      height: height,
      decoration: BoxDecoration(
        color: plantArtGreen.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      alignment: Alignment.center,
      child: Icon(Icons.local_florist, color: plantArtGreen, size: iconSize),
    ),
  );
}
