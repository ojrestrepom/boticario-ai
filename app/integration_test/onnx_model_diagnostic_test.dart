import 'dart:io';

import 'package:boticario_ai/features/plant_recognition/data/onnx_model_diagnostic.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Android CPU loads ONNX asset and returns 1081 finite logits', (
    tester,
  ) async {
    expect(Platform.isAndroid, isTrue, reason: 'Run on the Android emulator.');
    final diagnostic = OnnxModelDiagnostic();
    // Repeat with a fresh session to exercise native cleanup and reload.
    for (var run = 1; run <= 2; run++) {
      final watch = Stopwatch()..start();
      final logits = await diagnostic.run();
      watch.stop();
      expect(logits, hasLength(1081));
      expect(logits.every((value) => value.isFinite), isTrue);
      debugPrint(
        '[ONNX diagnostic] run=$run CPU float32 [1,1081] '
        'finite=1081/1081 elapsedMs=${watch.elapsedMilliseconds}',
      );
    }
  });
}
