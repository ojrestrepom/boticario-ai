import 'dart:typed_data';

import 'package:boticario_ai/features/plant_recognition/data/plant_predictions.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_recognition_service.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_species_metadata.dart';

class FakePlantRecognitionService implements PlantRecognitionService {
  Future<List<PlantPrediction>> Function(Uint8List)? onRecognize;
  final images = <Uint8List>[];

  static final candidates = List<PlantPrediction>.generate(
    5,
    (index) => PlantPrediction(
      PlantSpecies(index, '$index', 'Species candidate $index'),
      [0.531234, 0.2, 0.1, 0.05, 0.01][index],
    ),
  );

  @override
  Future<List<PlantPrediction>> recognize(Uint8List image) async {
    images.add(image);
    return onRecognize == null ? candidates : await onRecognize!(image);
  }
}
