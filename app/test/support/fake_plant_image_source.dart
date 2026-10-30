import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:boticario_ai/features/plant_recognition/data/plant_image_source.dart';

class FakePlantImageSource implements PlantImageSource {
  Future<Uint8List?> Function(PlantImageOrigin)? onPick;
  Future<Uint8List?> Function()? onRecover;
  final origins = <PlantImageOrigin>[];
  int recoveryCalls = 0;

  @override
  Future<Uint8List?> pick(PlantImageOrigin origin) async {
    origins.add(origin);
    return onPick == null ? null : onPick!(origin);
  }

  @override
  Future<Uint8List?> recover() async {
    recoveryCalls++;
    return onRecover == null ? null : onRecover!();
  }
}

Future<Uint8List> plantTestImage({int width = 8, int height = 4}) async {
  final recorder = ui.PictureRecorder();
  ui.Canvas(recorder).drawColor(const ui.Color(0xFF236335), ui.BlendMode.src);
  final picture = recorder.endRecording();
  final image = await picture.toImage(width, height);
  try {
    return (await image.toByteData(format: ui.ImageByteFormat.png))!.buffer
        .asUint8List();
  } finally {
    image.dispose();
    picture.dispose();
  }
}
