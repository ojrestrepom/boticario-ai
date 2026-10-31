import 'package:flutter/foundation.dart';
import 'package:flutter_onnxruntime/flutter_onnxruntime.dart';

/// CPU model session. The caller owns closing it after sequential runs.
class OnnxPlantModel {
  OnnxPlantModel._(this._session);
  final OrtSession _session;
  static const modelAsset = 'assets/models/mobilenet_v3_small.onnx';
  static const inputShape = [1, 3, 224, 224];
  static const outputShape = [1, 1081];

  static Future<OnnxPlantModel> load() async {
    final session = await OnnxRuntime().createSessionFromAsset(
      modelAsset,
      options: OrtSessionOptions(providers: [OrtProvider.CPU]),
    );
    try {
      if (!listEquals(session.inputNames, ['image']) ||
          !listEquals(session.outputNames, ['logits'])) {
        throw StateError('Unexpected ONNX input/output names.');
      }
      return OnnxPlantModel._(session);
    } catch (_) {
      await session.close();
      rethrow;
    }
  }

  /// Returns copied logits, releasing all per-run native tensors.
  Future<Float32List> run(Float32List tensor) async {
    if (tensor.length != 3 * 224 * 224 ||
        tensor.any((value) => !value.isFinite)) {
      throw ArgumentError('Expected 150528 finite float32 input values.');
    }
    final input = await OrtValue.fromList(tensor, inputShape);
    try {
      if (input.dataType != OrtDataType.float32 ||
          !listEquals(input.shape, inputShape)) {
        throw StateError('Expected float32 input $inputShape.');
      }
      final outputs = await _session.run({'image': input});
      try {
        final output = outputs['logits'];
        if (output == null ||
            output.dataType != OrtDataType.float32 ||
            !listEquals(output.shape, outputShape)) {
          throw StateError('Expected float32 logits $outputShape.');
        }
        final data = await output.asList();
        if (data.length != 1 || data.single is! List) {
          throw StateError('Expected one batch of logits.');
        }
        final row = data.single as List;
        if (row.length != 1081 ||
            row.any((value) => value is! num || !value.isFinite)) {
          throw StateError('Expected 1081 finite logits.');
        }
        return Float32List.fromList(
          row.map((value) => (value as num).toDouble()).toList(),
        );
      } finally {
        await Future.wait(outputs.values.map((value) => value.dispose()));
      }
    } finally {
      await input.dispose();
    }
  }

  Future<void> close() => _session.close();
}
