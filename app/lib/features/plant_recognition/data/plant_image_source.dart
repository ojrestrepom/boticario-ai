import 'dart:ui' as ui;

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

enum PlantImageOrigin { camera, gallery }

class PlantImageFailure implements Exception {
  const PlantImageFailure(this.message);
  final String message;
}

/// Null means cancellation (or no pending recovery), never an error.
abstract interface class PlantImageSource {
  Future<Uint8List?> pick(PlantImageOrigin origin);
  Future<Uint8List?> recover();
}

final plantImageSourceProvider = Provider<PlantImageSource>(
  (ref) => PickerPlantImageSource(ImagePicker()),
);

/// Owns plugin details. Images stay in memory/cache, never in permanent storage.
class PickerPlantImageSource implements PlantImageSource {
  PickerPlantImageSource(this._picker);
  final ImagePicker _picker;

  @override
  Future<Uint8List?> pick(PlantImageOrigin origin) => _guard(() async {
    final file = await _picker.pickImage(
      source: origin == PlantImageOrigin.camera
          ? ImageSource.camera
          : ImageSource.gallery,
      maxWidth: 2048,
      maxHeight: 2048,
      imageQuality: 90,
      requestFullMetadata: false,
    );
    return file == null ? null : _read(file);
  });

  @override
  Future<Uint8List?> recover() => _guard(() async {
    final result = await _picker.retrieveLostData();
    if (result.exception != null) throw result.exception!;
    final files = result.files;
    return files == null || files.isEmpty ? null : _read(files.first);
  });

  Future<Uint8List> _read(XFile file) async {
    if (await file.length() > 32 * 1024 * 1024) {
      throw const PlantImageFailure(
        'La imagen es demasiado grande. Selecciona otra imagen.',
      );
    }
    final bytes = await file.readAsBytes();
    // Verify decoding before replacing the previous valid image.
    final codec = await ui.instantiateImageCodec(
      bytes,
      targetWidth: 1600,
      allowUpscaling: false,
    );
    try {
      final frame = await codec.getNextFrame();
      frame.image.dispose();
    } finally {
      codec.dispose();
    }
    return bytes;
  }

  Future<Uint8List?> _guard(Future<Uint8List?> Function() action) async {
    try {
      return await action();
    } on PlantImageFailure {
      rethrow;
    } on PlatformException catch (error) {
      final message = switch (error.code) {
        'camera_access_denied' || 'camera_access_restricted' =>
          'No se pudo acceder a la cámara. Revisa los permisos en Ajustes.',
        'photo_access_denied' || 'photo_access_restricted' =>
          'No se pudo acceder a la galería. Revisa los permisos en Ajustes.',
        'no_available_camera' =>
          'No hay una cámara disponible en este dispositivo.',
        'already_active' => 'Ya hay una selección de imagen en curso.',
        _ => 'No se pudo obtener la imagen. Inténtalo de nuevo.',
      };
      throw PlantImageFailure(message);
    } on MissingPluginException {
      throw const PlantImageFailure(
        'La adquisición de imágenes no está disponible en este dispositivo.',
      );
    } catch (_) {
      throw const PlantImageFailure(
        'No se pudo leer la imagen. Selecciona otra imagen.',
      );
    }
  }
}
