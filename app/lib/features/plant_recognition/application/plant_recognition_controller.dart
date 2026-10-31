import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/plant_predictions.dart';
import '../data/plant_recognition_service.dart';
import 'plant_image_controller.dart';

enum PlantRecognitionStatus { initial, processing, result, error }

class PlantRecognitionState {
  const PlantRecognitionState({
    this.status = PlantRecognitionStatus.initial,
    this.busy = false,
    this.predictions = const [],
    this.error,
  });

  final PlantRecognitionStatus status;
  // Remains true until an obsolete request releases its native resources.
  final bool busy;
  final List<PlantPrediction> predictions;
  final String? error;
}

/// One instance per acquisition screen session; never reused by a later visit.
final plantRecognitionControllerProvider = NotifierProvider.autoDispose
    .family<PlantRecognitionController, PlantRecognitionState, int>(
      PlantRecognitionController.new,
    );

class PlantRecognitionController extends Notifier<PlantRecognitionState> {
  PlantRecognitionController(this.sessionId);
  final int sessionId;
  int _revision = 0;
  bool _active = true;
  bool _running = false;

  @override
  PlantRecognitionState build() {
    ref.onDispose(stop);
    ref.listen<Uint8List?>(
      plantImageControllerProvider.select((value) => value.image),
      (previous, next) {
        if (!identical(previous, next) && _active) {
          _revision++;
          state = PlantRecognitionState(busy: _running);
        }
      },
    );
    return const PlantRecognitionState();
  }

  /// Synchronous guard only: safe during widget disposal, without notifications.
  void stop() {
    _active = false;
    _revision++;
  }

  Future<void> identify() async {
    if (!_active || _running) return;
    final acquisition = ref.read(plantImageControllerProvider);
    final image = acquisition.image;
    if (acquisition.busy || image == null) return;
    final revision = ++_revision;
    _running = true;
    state = const PlantRecognitionState(
      status: PlantRecognitionStatus.processing,
      busy: true,
    );
    bool current() =>
        _active &&
        revision == _revision &&
        identical(ref.read(plantImageControllerProvider).image, image);
    try {
      final predictions = await ref
          .read(plantRecognitionServiceProvider)
          .recognize(image);
      if (current()) {
        state = PlantRecognitionState(
          status: PlantRecognitionStatus.result,
          busy: true,
          predictions: List.unmodifiable(predictions),
        );
      }
    } catch (_) {
      if (current()) {
        state = const PlantRecognitionState(
          status: PlantRecognitionStatus.error,
          busy: true,
          error: 'No se pudo identificar la planta. Inténtalo de nuevo o selecciona otra fotografía.',
        );
      }
    } finally {
      _running = false;
      if (_active) {
        state = PlantRecognitionState(
          status: state.status,
          predictions: state.predictions,
          error: state.error,
        );
      }
    }
  }
}
