import 'package:boticario_ai/features/plant_recognition/data/plant_image_source.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';

import '../../support/fake_plant_image_source.dart';

class TestPicker extends ImagePicker {
  XFile? file;
  Object? error;
  LostDataResponse lost = LostDataResponse.empty();
  ImageSource? source;
  bool? metadata;
  @override
  Future<XFile?> pickImage({
    required ImageSource source,
    double? maxWidth,
    double? maxHeight,
    int? imageQuality,
    CameraDevice preferredCameraDevice = CameraDevice.rear,
    bool requestFullMetadata = true,
  }) async {
    this.source = source;
    metadata = requestFullMetadata;
    if (error != null) throw error!;
    return file;
  }

  @override
  Future<LostDataResponse> retrieveLostData() async => lost;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('camera/gallery mapping and cancellation', () async {
    final picker = TestPicker();
    final source = PickerPlantImageSource(picker);
    expect(await source.pick(PlantImageOrigin.camera), isNull);
    expect(picker.source, ImageSource.camera);
    expect(picker.metadata, isFalse);
    expect(await source.pick(PlantImageOrigin.gallery), isNull);
    expect(picker.source, ImageSource.gallery);
    expect(await source.recover(), isNull);
  });
  test(
    'valid images and recovered file are decoded before returning',
    () async {
      final picker = TestPicker();
      final bytes = await plantTestImage();
      picker.file = XFile.fromData(bytes, name: 'plant.png');
      final source = PickerPlantImageSource(picker);
      expect(await source.pick(PlantImageOrigin.camera), bytes);
      picker.lost = LostDataResponse(
        files: [picker.file!],
        type: RetrieveType.image,
      );
      expect(await source.recover(), bytes);
    },
  );
  test(
    'invalid bytes, missing files and oversized input are readable failures',
    () async {
      final picker = TestPicker();
      final source = PickerPlantImageSource(picker);
      for (final file in [
        XFile.fromData(Uint8List.fromList([1, 2])),
        XFile('missing-plant-image.png'),
        XFile.fromData(Uint8List(32 * 1024 * 1024 + 1)),
      ]) {
        picker.file = file;
        await expectLater(
          source.pick(PlantImageOrigin.gallery),
          throwsA(isA<PlantImageFailure>()),
        );
      }
    },
  );
  for (final code in [
    'camera_access_denied',
    'photo_access_denied',
    'no_available_camera',
    'already_active',
    'unknown',
  ]) {
    test('plugin error $code is translated without native details', () async {
      final picker = TestPicker()
        ..error = PlatformException(
          code: code,
          message: 'native-private-detail',
        );
      await expectLater(
        PickerPlantImageSource(picker).pick(PlantImageOrigin.camera),
        throwsA(
          isA<PlantImageFailure>().having(
            (e) => e.message,
            'message',
            isNot(contains('native-private-detail')),
          ),
        ),
      );
    });
  }
  test('recovery error is translated', () async {
    final picker = TestPicker()
      ..lost = LostDataResponse(
        exception: PlatformException(code: 'photo_access_denied'),
      );
    await expectLater(
      PickerPlantImageSource(picker).recover(),
      throwsA(isA<PlantImageFailure>()),
    );
  });
}
