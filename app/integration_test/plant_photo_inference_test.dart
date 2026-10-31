import 'dart:io';

import 'package:boticario_ai/features/plant_recognition/data/onnx_plant_model.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_image_preprocessor.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_predictions.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_species_metadata.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Android photo Top-5 agrees with four Colab reference classes', (
    tester,
  ) async {
    expect(Platform.isAndroid, isTrue);
    final metadata = await PlantSpeciesMetadata.load();
    final model = await OnnxPlantModel.load();
    final actual = <int>[];
    const expected = [4, 144, 187, 529];
    try {
      for (var i = 1; i <= 4; i++) {
        final bytes = await rootBundle.load('assets/images/test/$i.jpg');
        final tensor = await compute(
          PlantImagePreprocessor().prepare,
          bytes.buffer.asUint8List(bytes.offsetInBytes, bytes.lengthInBytes),
        );
        expect(tensor.length, 150528);
        expect(tensor.every((value) => value.isFinite), isTrue);
        final logits = await model.run(tensor);
        final predictions = plantTopFive(logits, metadata);
        expect(predictions, hasLength(5));
        debugPrint('[Photo ONNX] $i.jpg reference=${expected[i - 1]}');
        for (final prediction in predictions) {
          debugPrint(
            'class=${prediction.species.classIndex} '
            'speciesId=${prediction.species.speciesId} '
            'name=${prediction.species.scientificName} '
            'score=${prediction.score.toStringAsFixed(8)}',
          );
        }
        actual.add(predictions.first.species.classIndex);
      }
    } finally {
      await model.close();
    }
    // Compare after all images so a mismatch never hides the remaining Top-5s.
    expect(
      actual,
      expected,
      reason: 'Compare preprocessing before changing parameters.',
    );
  });
}
