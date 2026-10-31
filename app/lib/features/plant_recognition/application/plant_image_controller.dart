import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/plant_image_source.dart';

final plantImageRecoveryEnabledProvider = Provider<bool>(
  (ref) => !kIsWeb && defaultTargetPlatform == TargetPlatform.android,
);

class PlantImageState {
  const PlantImageState({this.image, this.busy = false, this.error});
  final Uint8List? image;
  final bool busy;
  final String? error;
}

/// App-scoped so startup recovery survives until /identify opens.
final plantImageControllerProvider =
    NotifierProvider<PlantImageController, PlantImageState>(
      PlantImageController.new,
    );

class PlantImageController extends Notifier<PlantImageState> {
  int _revision = 0;
  bool _alive = true;
  bool _session = false;
  int _sessionId = 0;
  int _nextSessionId = 0;
  bool _pickerBusy = false;
  bool _recoveryStarted = false;

  @override
  PlantImageState build() {
    ref.onDispose(() {
      _alive = false;
      _revision++;
    });
    // Only this provider instance owns recovery; rebuilds do not repeat it.
    if (ref.read(plantImageRecoveryEnabledProvider) && !_recoveryStarted) {
      _recoveryStarted = true;
      final revision = _revision;
      unawaited(Future<void>.microtask(() => _recover(revision)));
    }
    return const PlantImageState();
  }

  bool _current(int revision) => _alive && revision == _revision;

  Future<void> _recover(int revision) async {
    if (!_alive) return;
    try {
      final image = await ref.read(plantImageSourceProvider).recover();
      if (_current(revision) && image != null) {
        state = PlantImageState(image: image, busy: _pickerBusy);
      }
    } catch (error) {
      if (_current(revision)) {
        state = PlantImageState(
          image: state.image,
          busy: _pickerBusy,
          error: _message(error),
        );
      }
    }
  }

  int beginSession() {
    _session = true;
    return _sessionId = ++_nextSessionId;
  }

  void endSession([int? sessionId]) {
    if (sessionId != null && sessionId != _sessionId) return;
    _sessionId = 0;
    _session = false;
    _revision++;
    // Native dialogs cannot be cancelled here. Keep the lock until they finish.
    if (_alive) state = PlantImageState(busy: _pickerBusy);
  }

  void discard() {
    _revision++;
    state = PlantImageState(busy: _pickerBusy);
  }

  Future<void> pick(PlantImageOrigin origin) async {
    if (!_session || _pickerBusy || !_alive) return;
    final revision = ++_revision;
    _pickerBusy = true;
    state = PlantImageState(image: state.image, busy: true);
    try {
      final image = await ref.read(plantImageSourceProvider).pick(origin);
      if (_current(revision) && _session) {
        state = PlantImageState(image: image ?? state.image, busy: true);
      }
    } catch (error) {
      if (_current(revision) && _session) {
        state = PlantImageState(
          image: state.image,
          busy: true,
          error: _message(error),
        );
      }
    } finally {
      _pickerBusy = false;
      if (_alive) {
        state = PlantImageState(image: state.image, error: state.error);
      }
    }
  }

  String _message(Object error) => error is PlantImageFailure
      ? error.message
      : 'No se pudo obtener la imagen. Inténtalo de nuevo.';
}
