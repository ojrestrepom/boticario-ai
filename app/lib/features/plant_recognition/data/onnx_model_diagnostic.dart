import 'dart:typed_data';

import 'onnx_plant_model.dart';

/// Stage 3.1 smoke test sharing the reusable model implementation.
class OnnxModelDiagnostic {
  Future<Float32List> run() async {
    final model = await OnnxPlantModel.load();
    try {
      return await model.run(Float32List(3 * 224 * 224));
    } finally {
      await model.close();
    }
  }
}
