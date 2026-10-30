import 'dart:async';
import 'dart:typed_data';

import 'package:boticario_ai/features/plant_recognition/application/plant_image_controller.dart';
import 'package:boticario_ai/features/plant_recognition/data/plant_image_source.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_plant_image_source.dart';

void main() {
  late FakePlantImageSource source;
  late ProviderContainer container;
  late PlantImageController controller;
  setUp(() {
    source = FakePlantImageSource();
    container = ProviderContainer(
      overrides: [
        plantImageSourceProvider.overrideWithValue(source),
        plantImageRecoveryEnabledProvider.overrideWithValue(false),
      ],
    );
    controller = container.read(plantImageControllerProvider.notifier);
    controller.beginSession();
  });
  tearDown(() => container.dispose());
  PlantImageState state() => container.read(plantImageControllerProvider);
  final first = Uint8List.fromList([1]);
  final second = Uint8List.fromList([2]);

  test(
    'cancel and recoverable errors retain image; discard explicitly clears it',
    () async {
      source.onPick = (_) async => first;
      await controller.pick(PlantImageOrigin.camera);
      source.onPick = (_) async => null;
      await controller.pick(PlantImageOrigin.gallery);
      expect(state().image, same(first));
      expect(state().error, isNull);
      source.onPick = (_) async => throw const PlantImageFailure('Sin permiso');
      await controller.pick(PlantImageOrigin.gallery);
      expect(state().image, same(first));
      expect(state().error, 'Sin permiso');
      controller.discard();
      expect(state().image, isNull);
      expect(state().error, isNull);
    },
  );

  test(
    'single native selection; leave and reenter ignore old result',
    () async {
      final pending = Completer<Uint8List?>();
      source.onPick = (_) => pending.future;
      final pick = controller.pick(PlantImageOrigin.camera);
      expect(state().busy, isTrue);
      await controller.pick(PlantImageOrigin.gallery);
      expect(source.origins, hasLength(1));
      controller.endSession();
      controller.beginSession();
      expect(state().image, isNull);
      pending.complete(first);
      await pick;
      expect(state().image, isNull);
      expect(state().busy, isFalse);
      source.onPick = (_) async => second;
      await controller.pick(PlantImageOrigin.gallery);
      expect(state().image, same(second));
    },
  );

  test('discard invalidates pending selection', () async {
    final pending = Completer<Uint8List?>();
    source.onPick = (_) => pending.future;
    final pick = controller.pick(PlantImageOrigin.camera);
    controller.discard();
    pending.complete(first);
    await pick;
    expect(state().image, isNull);
  });

  test('a disposed page cannot clear a newer session', () async {
    final oldSession = controller.beginSession();
    controller.endSession(oldSession);
    controller.beginSession();
    source.onPick = (_) async => first;
    await controller.pick(PlantImageOrigin.camera);
    controller.endSession(oldSession);
    expect(state().image, same(first));
  });

  test('completion after provider disposal is harmless', () async {
    final pending = Completer<Uint8List?>();
    source.onPick = (_) => pending.future;
    final pick = controller.pick(PlantImageOrigin.camera);
    controller.endSession();
    container.dispose();
    pending.complete(first);
    await pick;
    // A second container is only for the common tearDown.
    container = ProviderContainer();
  });

  for (final newerAction in ['none', 'pick', 'cancel', 'discard', 'leave']) {
    test('startup recovery once; late recovery versus $newerAction', () async {
      final recovered = Completer<Uint8List?>();
      source.onRecover = () => recovered.future;
      final startup = ProviderContainer(
        overrides: [
          plantImageSourceProvider.overrideWithValue(source),
          plantImageRecoveryEnabledProvider.overrideWithValue(true),
        ],
      );
      addTearDown(startup.dispose);
      final active = startup.read(plantImageControllerProvider.notifier);
      await Future<void>.delayed(Duration.zero);
      startup.read(plantImageControllerProvider);
      expect(source.recoveryCalls, 1);
      active.beginSession();
      if (newerAction == 'pick' || newerAction == 'cancel') {
        source.onPick = (_) async => newerAction == 'cancel' ? null : second;
        await active.pick(PlantImageOrigin.gallery);
      } else if (newerAction == 'discard') {
        active.discard();
      } else if (newerAction == 'leave') {
        active.endSession();
      }
      recovered.complete(first);
      await Future<void>.delayed(Duration.zero);
      final result = startup.read(plantImageControllerProvider);
      expect(
        result.image,
        newerAction == 'none'
            ? same(first)
            : newerAction == 'pick'
            ? same(second)
            : isNull,
      );
      expect(source.recoveryCalls, 1);
    });
  }

  test('startup error is readable; a later pick clears it', () async {
    source.onRecover = () async =>
        throw const PlantImageFailure('No se pudo recuperar la imagen');
    final startup = ProviderContainer(
      overrides: [
        plantImageSourceProvider.overrideWithValue(source),
        plantImageRecoveryEnabledProvider.overrideWithValue(true),
      ],
    );
    addTearDown(startup.dispose);
    final active = startup.read(plantImageControllerProvider.notifier);
    await Future<void>.delayed(Duration.zero);
    expect(
      startup.read(plantImageControllerProvider).error,
      'No se pudo recuperar la imagen',
    );
    active.beginSession();
    source.onPick = (_) async => first;
    await active.pick(PlantImageOrigin.camera);
    expect(startup.read(plantImageControllerProvider).error, isNull);
  });
}
