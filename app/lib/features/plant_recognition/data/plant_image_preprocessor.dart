import 'dart:typed_data';

import 'package:image/image.dart' as img;

class PlantImagePreprocessor {
  static const size = 224;
  static const mean = [0.4425, 0.4695, 0.3266];
  static const std = [0.2353, 0.2219, 0.2325];

  /// RGB, EXIF orientation, direct bicubic resize, normalization, planar NCHW.
  /// CenterCrop(224) is a no-op after Resize((224, 224)). Cubic interpolation
  /// may differ numerically from Pillow's antialiased bicubic implementation.
  Float32List prepare(Uint8List bytes) {
    final decoded = img.decodeImage(bytes);
    if (decoded == null) throw const FormatException('Cannot decode image.');
    final rgb = img
        .bakeOrientation(decoded)
        .convert(format: img.Format.uint8, numChannels: 3);
    final resized = img.copyResize(
      rgb,
      width: size,
      height: size,
      maintainAspect: false,
      interpolation: img.Interpolation.cubic,
    );
    final tensor = Float32List(3 * size * size);
    for (var y = 0; y < size; y++) {
      for (var x = 0; x < size; x++) {
        final pixel = resized.getPixel(x, y);
        final channels = [pixel.r, pixel.g, pixel.b];
        for (var c = 0; c < 3; c++) {
          tensor[c * size * size + y * size + x] =
              (channels[c] / 255.0 - mean[c]) / std[c];
        }
      }
    }
    return tensor;
  }
}
