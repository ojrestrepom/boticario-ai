import 'dart:async';
import 'dart:typed_data';

import 'package:boticario_ai/features/plant_recognition/application/plant_image_controller.dart';
import 'package:boticario_ai/features/plant_recognition/application/plant_recognition_controller.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_image_source.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_predictions.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_recognition_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_plant_image_source.dart';
import '../../support/fake_plant_recognition_service.dart';

void main() {
  late ProviderContainer container;
  late FakePlantImageSource source;
  late FakePlantRecognitionService service;
  late PlantImageController acquisition;
  late PlantRecognitionController controller;
  final provider = plantRecognitionControllerProvider(1);
  final first = Uint8List.fromList([1]);
  final second = Uint8List.fromList([2]);

  setUp(() {
    source = FakePlantImageSource()..onPick = (_) async => first;
    service = FakePlantRecognitionService();
    container = ProviderContainer(
      overrides: [
        plantImageSourceProvider.overrideWithValue(source),
        plantImageRecoveryEnabledProvider.overrideWithValue(false),
        plantRecognitionServiceProvider.overrideWithValue(service),
      ],
    );
    container.listen(provider, (_, _) {});
    acquisition = container.read(plantImageControllerProvider.notifier);
    acquisition.beginSession();
    controller = container.read(provider.notifier);
  });
  tearDown(() => container.dispose());

  PlantRecognitionState state() => container.read(provider);

  test('no image, processing, result and re-identification', () async {
    await controller.identify();
    expect(service.images, isEmpty);
    await acquisition.pick(PlantImageOrigin.gallery);
    final pending = Completer<List<PlantPrediction>>();
    service.onRecognize = (_) => pending.future;
    final run = controller.identify();
    expect(state().status, PlantRecognitionStatus.processing);
    expect(state().busy, isTrue);
    await controller.identify();
    expect(service.images, hasLength(1));
    pending.complete(FakePlantRecognitionService.candidates);
    await run;
    expect(state().status, PlantRecognitionStatus.result);
    expect(state().busy, isFalse);
    expect(state().predictions, hasLength(5));
    await controller.identify();
    expect(service.images, hasLength(2));
  });

  test(
    'replacement and discard clear results; cancellation keeps them',
    () async {
      await acquisition.pick(PlantImageOrigin.camera);
      await controller.identify();
      source.onPick = (_) async => null;
      await acquisition.pick(PlantImageOrigin.gallery);
      expect(state().status, PlantRecognitionStatus.result);
      source.onPick = (_) async => second;
      await acquisition.pick(PlantImageOrigin.gallery);
      expect(state().status, PlantRecognitionStatus.initial);
      expect(state().predictions, isEmpty);
      await controller.identify();
      acquisition.discard();
      expect(state().status, PlantRecognitionStatus.initial);
      expect(state().predictions, isEmpty);
    },
  );

  for (final discard in [false, true]) {
    test('obsolete inference cannot publish after discard=$discard', () async {
      await acquisition.pick(PlantImageOrigin.gallery);
      final pending = Completer<List<PlantPrediction>>();
      service.onRecognize = (_) => pending.future;
      final run = controller.identify();
      if (discard) {
        acquisition.discard();
      } else {
        source.onPick = (_) async => second;
        await acquisition.pick(PlantImageOrigin.gallery);
      }
      expect(state().predictions, isEmpty);
      await controller.identify();
      expect(service.images, hasLength(1));
      pending.complete(FakePlantRecognitionService.candidates);
      await run;
      expect(state().status, PlantRecognitionStatus.initial);
      expect(state().busy, isFalse);
      expect(state().predictions, isEmpty);
    });
  }

  test('errors are safe and retry works', () async {
    await acquisition.pick(PlantImageOrigin.gallery);
    service.onRecognize = (_) async =>
        throw StateError('secret native exception');
    await controller.identify();
    expect(state().status, PlantRecognitionStatus.error);
    expect(state().error, contains('Inténtalo de nuevo'));
    expect(state().error, isNot(contains('secret')));
    service.onRecognize = null;
    await controller.identify();
    expect(state().status, PlantRecognitionStatus.result);
    expect(state().error, isNull);
  });

  test('leaving and disposal ignore a late native failure', () async {
    await acquisition.pick(PlantImageOrigin.gallery);
    final pending = Completer<List<PlantPrediction>>();
    service.onRecognize = (_) => pending.future;
    final run = controller.identify();
    controller.stop();
    acquisition.endSession();
    final next = plantRecognitionControllerProvider(2);
    container.listen(next, (_, _) {});
    expect(container.read(next).status, PlantRecognitionStatus.initial);
    container.dispose();
    pending.completeError(StateError('late failure'));
    await run;
    // tearDown may safely dispose the already disposed container.
  });
}
