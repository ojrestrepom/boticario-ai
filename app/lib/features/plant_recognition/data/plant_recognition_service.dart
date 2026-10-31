import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'onnx_plant_model.dart';
import 'plant_image_preprocessor.dart';
import 'plant_predictions.dart';
import 'plant_species_metadata.dart';

abstract interface class PlantRecognitionService {
  Future<List<PlantPrediction>> recognize(Uint8List image);
}

final plantRecognitionServiceProvider = Provider<PlantRecognitionService>(
  (ref) => const LocalPlantRecognitionService(),
);

/// Each request owns its native session, including when its caller leaves.
/// Preprocessing runs in a worker isolate; the Android plugin runs inference
/// on its background task queue. No network or catalog dependency is involved.
class LocalPlantRecognitionService implements PlantRecognitionService {
  const LocalPlantRecognitionService();

  @override
  Future<List<PlantPrediction>> recognize(Uint8List image) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      throw UnsupportedError('Local recognition requires Android.');
    }
    final tensor = await compute(PlantImagePreprocessor().prepare, image);
    final metadata = await PlantSpeciesMetadata.load();
    final model = await OnnxPlantModel.load();
    try {
      return plantTopFive(await model.run(tensor), metadata);
    } finally {
      await model.close();
    }
  }
}
